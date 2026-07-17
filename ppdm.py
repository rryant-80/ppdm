import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Konfigurasi Halaman
st.set_page_config(layout="wide", page_title="Dashboard Pemantauan Berkas")

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
st.title("📊 Dashboard Pemantauan Berkas Kabupaten/Kota")
st.markdown("---")

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


# --- 4. PEMBUATAN GRAFIK BATANG MULTI-KATEGORI (NAMA PROSEDUR) ---
st.subheader("📈 Grafik Jumlah Berkas berdasarkan Kabupaten/Kota dan Nama Prosedur")

df['no_thn_berkas'] = df['nmr_berkas'].astype(str) + "/" + df['thn_berkas'].astype(str)

# Mengelompokkan data berdasarkan seluruh nama prosedur
df_grouped = df.groupby(['kabupaten_kota', 'nama_prosedur']).agg(
    banyak_berkas=('nmr_berkas', 'count'),
    daftar_berkas=('no_thn_berkas', lambda x: ", ".join(x.unique().astype(str)))
).reset_index()

fig = go.Figure()

# Mendapatkan seluruh kategori nama prosedur unik di database
daftar_prosedur = sorted([p for p in df['nama_prosedur'].unique() if pd.notna(p) and p.strip() != ''])

for prosedur in daftar_prosedur:
    df_trace = df_grouped[df_grouped['nama_prosedur'] == prosedur]
    
    x_data = []
    y_data = []
    hover_text = []
    
    for kab in daftar_kab_kota:
        row = df_trace[df_trace['kabupaten_kota'] == kab]
        x_data.append(kab)
        if not row.empty:
            jumlah = row['banyak_berkas'].sum()
            y_data.append(jumlah)
            
            text = (
                f"<b>Prosedur: {prosedur}</b><br>"
                f"Kabupaten/Kota: {kab}<br>"
                f"Banyak Berkas: {jumlah}<br>"
                f"No/Thn Berkas: {row['daftar_berkas'].iloc[0]}"
            )
            hover_text.append(text)
        else:
            y_data.append(0)
            hover_text.append(f"<b>Prosedur: {prosedur}</b><br>Tidak ada berkas")

    fig.add_trace(go.Bar(
        name=prosedur,
        x=x_data,
        y=y_data,
        hoverinfo="text",
        hovertext=hover_text
    ))

fig.update_layout(
    barmode='group',
    xaxis_title="Kabupaten / Kota",
    yaxis_title="Jumlah Berkas",
    legend_title="Nama Prosedur",
    hoverlabel=dict(bgcolor="white", font_size=12),
    height=600
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")


# --- 5. PANEL FILTER DRILLDOWN (SEMUA KATEGORI DATABASE) ---
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
    pilihan_pos = st.selectbox("Pilih Posisi Berkas untuk Detail:", ["-- Pilih Posisi Berkas --"] + daftar_seluruh_posisi)

if pilihan_kab != "-- Pilih Kabupaten/Kota --" and pilihan_pos != "-- Pilih Posisi Berkas --":
    
    st.subheader(f"📋 Detail Berkas: Kabupaten/Kota {pilihan_kab} - Posisi {pilihan_pos}")
    
    # Filter data menggunakan data master asli 'df' agar mencakup semua kategori posisi
    df_drilldown = df[
        (df['kabupaten_kota'] == pilihan_kab) & 
        (df['posisi_berkas'] == pilihan_pos)
    ].copy()
    
    if not df_drilldown.empty:
        # Format string tanggal (YYYY-MM-DD)
        df_drilldown['tgl_mulai'] = pd.to_datetime(df_drilldown['tgl_mulai']).dt.strftime('%Y-%m-%d')
        
        # Susun kolom sesuai instruksi
        df_drilldown_display = df_drilldown[['kabupaten_kota', 'nmr_berkas', 'tgl_mulai', 'nama_prosedur']].copy()
        
        # Penomoran otomatis kolom "No."
        df_drilldown_display.insert(0, 'No.', range(1, len(df_drilldown_display) + 1))
        
        st.dataframe(df_drilldown_display, use_container_width=True, hide_index=True)
    else:
        st.info("Tidak ada data berkas yang terdaftar untuk kombinasi ini.")
else:
    st.info("Silakan tentukan Kabupaten/Kota dan Posisi Berkas pada pilihan di atas untuk memunculkan tabel detail.")
