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

# Acuan tanggal hari ini untuk hitung SOP
hari_ini = pd.Timestamp(datetime.now().date())
df['tgl_deadline'] = df['tgl_mulai'] + pd.to_timedelta(df['durasi'], unit='D')
df['lewat_sop'] = clarified_status = hari_ini > df['tgl_deadline']

# Filter hanya untuk 4 posisi berkas
kategori_posisi = ['Kakan', 'Kasi SP', 'Kasi PHP', 'Loket']
df_filtered = df[df['posisi_berkas'].isin(kategori_posisi)].copy()

# --- 3. TAMPILAN UTAMA & INDIKATOR STROBO ---
st.title("📊 Dashboard Pemantauan Berkas Kabupaten/Kota")
st.markdown("---")

# Gaya CSS untuk Lampu Strobo Berkedip
st.markdown("""
<style>
@keyframes blink-red {
    0% { background-color: #ff4b4b; box-shadow: 0 0 10px #ff4b4b; }
    50% { background-color: #8b0000; box-shadow: 0 0 0px #8b0000; }
    100% { background-color: #ff4b4b; box-shadow: 0 0 10px #ff4b4b; }
}
.strobo-red {
    animation: blink-red 1s infinite;
    color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold;
}
.box-green {
    background-color: #28a745; color: white; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

st.subheader("🚨 Indikator Kepatuhan SOP Kontinuitas Berkas")
cols = st.columns(4)

for i, posisi in enumerate(kategori_posisi):
    df_pos = df_filtered[df_filtered['posisi_berkas'] == posisi]
    total_lewat = df_pos['lewat_sop'].sum()
    
    with cols[i]:
        if total_lewat > 0:
            st.markdown(f"""
            <div class="strobo-red">
                {posisi}<br>
                <span style="font-size:20px;">{total_lewat} Berkas Lewat SOP</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="box-green">
                {posisi}<br>
                <span style="font-size:20px;">Semua Aman</span>
            </div>
            """, unsafe_allow_html=True)

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
