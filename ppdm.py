import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_plotly_events import plotly_events

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

# Bersihkan data kabupaten_kota dari spasi berlebih agar pengelompokan stabil
df['kabupaten_kota'] = df['kabupaten_kota'].astype(str).str.strip()

# Acuan tanggal hari ini untuk hitung SOP (Tahun 2026)
hari_ini = pd.Timestamp(datetime.now().date())
df['tgl_deadline'] = df['tgl_mulai'] + pd.to_timedelta(df['durasi'], unit='D')
df['lewat_sop'] = hari_ini > df['tgl_deadline']

# Filter untuk 4 posisi berkas utama
kategori_posisi = ['Kakan', 'Kasi SP', 'Kasi PHP', 'Loket']
df_filtered = df[df['posisi_berkas'].isin(kategori_posisi)].copy()


# --- 3. TAMPILAN UTAMA & INDIKATOR STROBO (URAI SEMUA KABUPATEN/KOTA) ---
# Gaya CSS untuk Lampu Strobo Berkedip & layout kartu mini
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

# PERBAIKAN UTAMA: Mengambil daftar kabupaten langsung dari master data 'df' asli 
# dan mengeliminasi teks kosong atau string penanda kosong seperti 'nan'
daftar_kab_ind = sorted([
    kab for kab in df['kabupaten_kota'].unique() 
    if pd.notna(kab) and kab.lower() != 'nan' and kab.strip() != ''
])

# Membuat header kolom tabel indikator
col_h0, col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1, 1, 1, 1])
with col_h0: st.markdown("**Kantor Pertanahan (Kab/Kota)**")
with col_h1: st.markdown("<center><b>Kakan</b></center>", unsafe_allow_html=True)
with col_h2: st.markdown("<center><b>Kasi SP</b></center>", unsafe_allow_html=True)
with col_h3: st.markdown("<center><b>Kasi PHP</b></center>", unsafe_allow_html=True)
with col_h4: st.markdown("<center><b>Loket Penyerahan</b></center>", unsafe_allow_html=True)
st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)

# Perulangan wajib memetakan TOTAL seluruh Kabupaten/Kota tanpa terkecuali
for kab in daftar_kab_ind:
    col_b0, col_b1, col_b2, col_b3, col_b4 = st.columns([2, 1, 1, 1, 1])
    
    with col_b0:
        st.markdown(f"<div class='kantah-header'>📍 {kab}</div>", unsafe_allow_html=True)
        
    for i, posisi in enumerate(kategori_posisi):
        # Filter berkas yang spesifik pada baris kabupaten ini
        df_lewat = df_filtered[
            (df_filtered['kabupaten_kota'] == kab) & 
            (df_filtered['posisi_berkas'] == posisi) & 
            (df_filtered['lewat_sop'] == True)
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
                # Jika kabupaten tidak punya berkas sama sekali di posisi ini, otomatis berstatus Aman
                st.markdown("""
                <div class="box-green-mini">
                    ✅ Tuntas
                </div>
                """, unsafe_allow_html=True)
                
    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

st.markdown("---")

# --- 4. PEMBUATAN GRAFIK BATANG MULTI-KATEGORI ---
st.subheader("📈 Grafik Jumlah Prosedur berdasarkan Kabupaten/Kota dan Posisi Berkas")

df_filtered['no_thn_berkas'] = df_filtered['nmr_berkas'].astype(str) + "/" + df_filtered['thn_berkas'].astype(str)

df_grouped = df_filtered.groupby(['kabupaten_kota', 'posisi_berkas', 'nama_prosedur']).agg(
    banyak_berkas=('nmr_berkas', 'count'),
    daftar_berkas=('no_thn_berkas', lambda x: ", ".join(x.unique()))
).reset_index()

fig = go.Figure()
daftar_kab_kota = df_grouped['kabupaten_kota'].unique()

for posisi in kategori_posisi:
    df_trace = df_grouped[df_grouped['posisi_berkas'] == posisi]
    
    x_data = []
    y_data = []
    hover_text = []
    
    for kab in daftar_kab_kota:
        row = df_trace[df_trace['kabupaten_kota'] == kab]
        x_data.append(kab)
        if not row.empty:
            y_data.append(row['banyak_berkas'].sum())
            prosedur_list = "<br>".join([f"- {p}" for p in row['nama_prosedur'].unique()])
            text = (
                f"<b>Posisi: {posisi}</b><br>"
                f"Prosedur:<br>{prosedur_list}<br>"
                f"Banyak Berkas: {row['banyak_berkas'].sum()}<br>"
                f"No/Thn Berkas: {row['daftar_berkas'].iloc[0]}"
            )
            hover_text.append(text)
        else:
            y_data.append(0)
            hover_text.append(f"<b>Posisi: {posisi}</b><br>Tidak ada berkas")

    fig.add_trace(go.Bar(
        name=posisi,
        x=x_data,
        y=y_data,
        hoverinfo="text",
        hovertext=hover_text
    ))

fig.update_layout(
    barmode='group',
    xaxis_title="Kabupaten / Kota",
    yaxis_title="Jumlah Prosedur (Banyak Berkas)",
    legend_title="Posisi Berkas",
    hoverlabel=dict(bgcolor="white", font_size=12),
    height=500
)

# Tampilkan grafik secara statis standar (Lebih kompatibel)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# --- 5. PANEL FILTER DRILLDOWN (PENGGANTI KLIK GRAFIK) ---
st.subheader("🔍 Drilldown Detail Berkas")
col_f1, col_f2 = st.columns(2)

with col_f1:
    pilihan_kab = st.selectbox("Pilih Kabupaten/Kota untuk Detail:", ["-- Pilih Kabupaten/Kota --"] + list(daftar_kab_kota))
with col_f2:
    pilihan_pos = st.selectbox("Pilih Posisi Berkas untuk Detail:", ["-- Pilih Posisi Berkas --"] + kategori_posisi)

# Logika pemicu tabel drilldown berdasarkan pilihan selectbox
if pilihan_kab != "-- Pilih Kabupaten/Kota --" and pilihan_pos != "-- Pilih Posisi Berkas --":
    
    st.subheader(f"📋 Detail Berkas: Kabupaten/Kota {pilihan_kab} - Posisi {pilihan_pos}")
    
    # Filter data utama
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
        
        # Tampilkan Tabel
        st.dataframe(df_drilldown_display, use_container_width=True, hide_index=True)
    else:
        st.info("Tidak ada data berkas yang terdaftar untuk kombinasi ini.")
else:
    st.info("Silakan tentukan Kabupaten/Kota dan Posisi Berkas pada pilihan di atas untuk memunculkan tabel detail.")
