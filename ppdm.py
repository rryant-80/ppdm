import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Konfigurasi Halaman
st.set_page_config(layout="wide", page_title="Monitoring SOP Pertanahan")

# --- 1. MEMBACA DATA DARI GOOGLE SHEETS ---
try:
    SHEET_ID = st.secrets["gsheet_id"] 
    GID = "1447858691"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"
    df = pd.read_csv(url)
except Exception as e:
    st.error(f"Gagal memuat data. Pastikan ID Sheet di Secret sudah benar. Error: {e}")
    st.stop()

# --- 2. PREPROCESSING DATA ---
df['tgl_mulai'] = pd.to_datetime(df['tgl_mulai'], errors='coerce')
df['durasi'] = pd.to_numeric(df['durasi'], errors='coerce').fillna(0)

# Bersihkan data kabupaten_kota dan posisi_berkas dari spasi berlebih
df['kabupaten_kota'] = df['kabupaten_kota'].astype(str).str.strip()
df['posisi_berkas'] = df['posisi_berkas'].astype(str).str.strip()
df['nama_prosedur'] = df['nama_prosedur'].astype(str).str.strip()

# Acuan tanggal hari ini untuk hitung SOP (Tahun 2026)
hari_ini = pd.Timestamp(datetime.now().date())
df['tgl_deadline'] = df['tgl_mulai'] + pd.to_timedelta(df['durasi'], unit='D')
df['lewat_sop'] = hari_ini > df['tgl_deadline']

# Filter khusus indikator strobo (tetap menggunakan 4 kategori utama sesuai instruksi sebelumnya)
kategori_posisi_strobo = ['Kakan', 'Kasi SP', 'Kasi PHP', 'Loket']
df_filtered_strobo = df[df['posisi_berkas'].isin(kategori_posisi_strobo)].copy()


# --- 3. TAMPILAN UTAMA & INDIKATOR STROBO (URAI SEMUA KABUPATEN/KOTA) ---

st.markdown("""
<style>
@keyframes blink-red {
    0% { background-color: #ff4b4b; box-shadow: 0 0 8px #ff4b4b; }
    50% { background-color: #8b0000; box-shadow: 0 0 0px #8b0000; }
    100% { background-color: #ff4b4b; box-shadow: 0 0 8px #ff4b4b; }
}
.strobo-red-mini {
    animation: blink-red 1s infinite;
    color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 13px;
    cursor: help;
}
.box-green-mini {
    background-color: #28a745; color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 13px;
}
.kantah-header {
    font-size: 16px; font-weight: bold; color: #1E1E1E; padding-top: 5px;
}
</style>
""", unsafe_allow_html=True)

st.subheader("🚨 Berkas Melebihi Durasi SOP")
st.caption("💡 **Tips:** Arahkan kursor ke kotak merah untuk melihat detail nomor berkas dan nama prosedur.")

# Mengambil daftar seluruh kabupaten dari data master asli
daftar_kab_ind = sorted([
    kab for kab in df['kabupaten_kota'].unique() 
    if pd.notna(kab) and kab.lower() != 'nan' and kab.strip() != ''
])

# Membuat header kolom tabel indikator
col_h0, col_h1, col_h2, col_h3, col_h4 = st.columns([1, 1, 1, 1, 1])
with col_h0: st.markdown("**Kantor Pertanahan (Kab/Kota)**")
with col_h1: st.markdown("<center><b>Kakan</b></center>", unsafe_allow_html=True)
with col_h2: st.markdown("<center><b>Kasi SP</b></center>", unsafe_allow_html=True)
with col_h3: st.markdown("<center><b>Kasi PHP</b></center>", unsafe_allow_html=True)
with col_h4: st.markdown("<center><b>Loket Penyerahan</b></center>", unsafe_allow_html=True)
st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)

for kab in daftar_kab_ind:
    col_b0, col_b1, col_b2, col_b3, col_b4 = st.columns([1, 1, 1, 1, 1])
    
    with col_b0:
        st.markdown(f"<div class='kantah-header'>📍 {kab}</div>", unsafe_allow_html=True)
        
    for i, posisi in enumerate(kategori_posisi_strobo):
        df_lewat = df_filtered_strobo[
            (df_filtered_strobo['kabupaten_kota'] == kab) & 
            (df_filtered_strobo['posisi_berkas'] == posisi) & 
            (df_filtered_strobo['lewat_sop'] == True)
        ]
        
        total_lewat = len(df_lewat)
        target_col = [col_b1, col_b2, col_b3, col_b4][i]
        
        with target_col:
            if total_lewat > 0:
                detail_hover = "Berkas melebihi SOP :\n"
                for idx, row in enumerate(df_lewat.itertuples(), 1):
                    detail_hover += f"{idx}. No : {row.nmr_berkas}/{row.thn_berkas} - {row.nama_prosedur}\n"
                
                st.markdown(f"""
                <div class="strobo-red-mini" title="{detail_hover.strip()}">
                    🚨 {total_lewat} Berkas
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="box-green-mini">
                    ✅ Tuntas
                </div>
                """, unsafe_allow_html=True)
                
    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

st.markdown("---")

# --- 4. PEMBUATAN GRAFIK BATANG TUNGGAL (URUTAN TERBANYAK KANAN-KIRI) ---
st.subheader("📈 Grafik Berkas Permohonan melebihi Durasi SOP")

# 1. Hitung total berkas per Kabupaten/Kota untuk pengurutan
df_total_kab = df.groupby('kabupaten_kota')['nmr_berkas'].count().reset_index()
df_total_kab = df_total_kab.sort_values(by='nmr_berkas', ascending=False)

# Mengambil daftar kabupaten yang sudah terurut dari terbanyak ke tersedikit
daftar_kab_terurut = df_total_kab['kabupaten_kota'].tolist()

# 2. Agregasi data untuk menyusun isi hover template (nama_prosedur : jumlah)
df_hover_prep = df.groupby(['kabupaten_kota', 'nama_prosedur']).size().reset_index(name='jumlah')

x_data = []
y_data = []
hover_text = []

# Loop berdasarkan urutan kabupaten terbanyak
for kab in daftar_kab_terurut:
    df_kab_prosedur = df_hover_prep[df_hover_prep['kabupaten_kota'] == kab]
    
    total_berkas = df_kab_prosedur['jumlah'].sum()
    
    x_data.append(kab)
    y_data.append(total_berkas)
    
    # Menyusun format hover template: nama_prosedur : jumlah
    detail_hover_list = []
    for row in df_kab_prosedur.itertuples():
        detail_hover_list.append(f"{row.nama_prosedur}: {row.jumlah}")
        
    prosedur_hover_string = "<br>".join(detail_hover_list)
    
    text = (
        f"<b>{kab}</b><br>"
        f"Total Berkas : {total_berkas}<br><br>"
        f"<b>Detail Prosedur :</b><br>{prosedur_hover_string}"
    )
    hover_text.append(text)

# 3. Membuat grafik batang tunggal
fig = go.Figure()

fig.add_trace(go.Bar(
    x=x_data,
    y=y_data,
    hoverinfo="text",
    hovertext=hover_text,
    marker_color='#1f77b4'  # Warna batang biru seragam agar bersih
))

fig.update_layout(
    xaxis_title="Kabupaten / Kota (Diurutkan dari Terbanyak)",
    yaxis_title="Total Jumlah Berkas Prosedur",
    hoverlabel=dict(bgcolor="white", font_size=12),
    height=550,
    margin=dict(l=40, r=40, t=40, b=40)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- 5. PANEL FILTER DRILLDOWN (SEMUA KATEGORI DATABASE DENGAN AUTO-WIDTH) ---
st.subheader("🔍 Drilldown Detail Berkas")
col_f1, col_f2 = st.columns(2)

# Mengambil seluruh kategori posisi berkas yang unik dari database tanpa filter
daftar_seluruh_posisi = sorted([
    pos for pos in df['posisi_berkas'].unique() 
    if pd.notna(pos) and pos.lower() != 'nan' and pos.strip() != ''
])

with col_f1:
    pilihan_kab = st.selectbox("Pilih Kabupaten/Kota untuk Detail:", ["-- Pilih Kabupaten/Kota --"] + list(daftar_kab_ind))
with col_f2:
    pilihan_pos = st.selectbox("Pilih Posisi Berkas untuk Detail:", ["-- Pilih Posisi Berkas --", "-- Semua Posisi --"] + daftar_seluruh_posisi)

if pilihan_kab != "-- Pilih Kabupaten/Kota --" and pilihan_pos != "-- Pilih Posisi Berkas --":
    
    st.subheader(f"📋 Detail Berkas: Kabupaten/Kota {pilihan_kab} - {pilihan_pos if pilihan_pos != '-- Semua Posisi --' else 'Semua Posisi Berkas'}")
    
    # Filter awal berdasarkan Kabupaten/Kota
    df_drilldown = df[df['kabupaten_kota'] == pilihan_kab].copy()
    
    # Jika memilih posisi berkas spesifik (bukan Semua Posisi)
    if pilihan_pos != "-- Semua Posisi --":
        df_drilldown = df_drilldown[df_drilldown['posisi_berkas'] == pilihan_pos].copy()
    
    if not df_drilldown.empty:
        # 1. Mengurutkan tabel berdasarkan tanggal lama ke baru (tgl_mulai)
        df_drilldown = df_drilldown.sort_values(by='tgl_mulai', ascending=True)
        
        # 2. Menghitung Hari Berjalan mengecualikan hari Sabtu & Minggu (5 Hari Kerja Seminggu)
        tgl_hari_ini = hari_ini.date()
        
        def hitung_hari_kerja(tgl_mulai_row):
            tgl_awal = tgl_mulai_row.date()
            try:
                if tgl_awal <= tgl_hari_ini:
                    return int(np.busday_count(tgl_awal, tgl_hari_ini))
                else:
                    return int(-np.busday_count(tgl_hari_ini, tgl_awal))
            except Exception:
                return 0

        df_drilldown['Hari Berjalan'] = df_drilldown['tgl_mulai'].apply(hitung_hari_kerja)
        
        # Format string tanggal asal agar rapi (YYYY-MM-DD)
        df_drilldown['tgl_mulai'] = df_drilldown['tgl_mulai'].dt.strftime('%Y-%m-%d')
        
        # 3. MEMILIH KOLOM BARU
        df_drilldown_display = df_drilldown[['kabupaten_kota', 'nmr_berkas', 'tgl_mulai', 'nama_prosedur', 'posisi_berkas', 'Hari Berjalan']].copy()
        
        # Mengubah nama-nama judul tabel formal
        df_drilldown_display.columns = [
            'Kabupaten / Kota', 
            'Nomor Berkas', 
            'Tanggal Mulai', 
            'Nama Prosedur', 
            'Posisi Berkas',       
            'Hari Berjalan (SOP)'
        ]
        
        # Penomoran otomatis kolom "No."
        df_drilldown_display.insert(0, 'No.', range(1, len(df_drilldown_display) + 1))
        
        # 4. INJEKSI CSS: Teks header tengah, warna biru, bold
        st.markdown("""
        <style>
            div[data-testid="stTable"] th, 
            div[data-testid="stDataFrameData"] th,
            .stDataFrame table thead th,
            th[data-testid="stDataFrameHeaderCell"] {
                color: #1f77b4 !important; 
                font-weight: bold !important; 
                text-align: center !important; 
            }
        </style>
        """, unsafe_allow_html=True)
        
        # 5. MENGATUR ALIGNMENT & UKURAN LEBAR KOLOM (AUTO & DYNAMIC EXPAND)
        # Kita biarkan lebar kolom 'No.', 'Nomor Berkas', dan 'Tanggal Mulai' menyesuaikan otomatis, 
        # sedangkan kolom teks panjang diset fleksibel agar meregang mengikuti teks di bawahnya tanpa tersembunyi.
        konfigurasi_kolom = {
            'No.': st.column_config.Column(alignment="center", width="small"),
            'Kabupaten / Kota': st.column_config.Column(alignment="left", width="medium"),
            'Nomor Berkas': st.column_config.Column(alignment="center", width="medium"),
            'Tanggal Mulai': st.column_config.Column(alignment="center", width="medium"),
            'Nama Prosedur': st.column_config.Column(alignment="left", width="large"), # Memberikan ruang paling besar agar teks prosedur tidak terpotong
            'Posisi Berkas': st.column_config.Column(alignment="left", width="medium"),
            'Hari Berjalan (SOP)': st.column_config.Column(alignment="center", width="medium"),
        }
        
        # Tampilkan Tabel Drilldown final
        st.dataframe(
            df_drilldown_display, 
            use_container_width=True, # Memaksa tabel memanfaatkan seluruh lebar grid halaman
            hide_index=True,
            column_config=konfigurasi_kolom
        )
    else:
        st.info("Tidak ada data berkas yang terdaftar untuk kombinasi wilayah dan posisi ini.")
else:
    st.info("Silakan tentukan Kabupaten/Kota dan Posisi Berkas pada pilihan di atas untuk memunculkan tabel detail.")
