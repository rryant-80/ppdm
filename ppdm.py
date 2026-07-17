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

# Acuan tanggal hari ini untuk hitung SOP (Tahun 2026)
hari_ini = pd.Timestamp(datetime.now().date())
df['tgl_deadline'] = df['tgl_mulai'] + pd.to_timedelta(df['durasi'], unit='D')
df['lewat_sop'] = hari_ini > df['tgl_deadline']

# Filter hanya untuk 4 posisi berkas
kategori_posisi = ['Kakan', 'Kasi SP', 'Kasi PHP', 'Loket']
df_filtered = df[df['posisi_berkas'].isin(kategori_posisi)].copy()

# --- 3. TAMPILAN UTAMA & INDIKATOR STROBO (URAI PER KABUPATEN/KOTA) ---
st.title("📊 Dashboard Pemantauan Berkas Kabupaten/Kota")
st.markdown("---")

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
}
.box-green-mini {
    background-color: #28a745; color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 13px;
}
.kantah-header {
    font-size: 16px; font-weight: bold; color: #1E1E1E; padding-top: 5px;
}
</style>
""", unsafe_allow_html=True)

st.subheader("🚨 Peta Kepatuhan SOP Kontinuitas Berkas per Kantor Pertanahan")
st.caption("Menampilkan detail langsung jumlah berkas menunggak yang melebihi durasi SOP di masing-masing wilayah.")

# Dapatkan daftar kabupaten_kota unik yang ada di data
daftar_kab_ind = sorted(df_filtered['kabupaten_kota'].unique())

# Membuat header kolom tabel indikator
col_h0, col_h1, col_h2, col_h3, col_h4 = st.columns([2, 1, 1, 1, 1])
with col_h0: st.markdown("**Kantor Pertanahan (Kab/Kota)**")
with col_h1: st.markdown("<center><b>Kakan</b></center>", unsafe_allow_html=True)
with col_h2: st.markdown("<center><b>Kasi SP</b></center>", unsafe_allow_html=True)
with col_h3: st.markdown("<center><b>Kasi PHP</b></center>", unsafe_allow_html=True)
with col_h4: st.markdown("<center><b>Loket</b></center>", unsafe_allow_html=True)
st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)

# Lakukan perulangan untuk menampilkan status per Kabupaten/Kota
for kab in daftar_kab_ind:
    df_kab = df_filtered[df_filtered['kabupaten_kota'] == kab]
    
    # Buat baris layout baru untuk tiap daerah
    col_b0, col_b1, col_b2, col_b3, col_b4 = st.columns([2, 1, 1, 1, 1])
    
    with col_b0:
        st.markdown(f"<div class='kantah-header'>📍 {kab}</div>", unsafe_allow_html=True)
        
    # Cek masing-masing posisi berkas di kabupaten terkait
    for i, posisi in enumerate(kategori_posisi):
        df_pos = df_kab[df_kab['posisi_berkas'] == posisi]
        total_lewat = df_pos['lewat_sop'].sum()
        
        target_col = [col_b1, col_b2, col_b3, col_b4][i]
        
        with target_col:
            if total_lewat > 0:
                st.markdown(f"""
                <div class="strobo-red-mini">
                    🚨 {total_lewat} Berkas
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="box-green-mini">
                    ✅ Aman
                </div>
                """, unsafe_allow_html=True)
                
    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

st.markdown("---")

# --- 4. PEMBUATAN GRAFIK BATANG MULTI-KATEGORI ---
st.subheader("📈 Grafik Jumlah Prosedur berdasarkan Kabupaten/Kota dan Posisi Berkas")
st.info("⚡ **Interaktif:** Klik langsung pada salah satu batang grafik di bawah untuk memunculkan tabel detail.")

df_filtered['no_thn_berkas'] = df_filtered['nmr_berkas'].astype(str) + "/" + df_filtered['thn_berkas'].astype(str)

df_grouped = df_filtered.groupby(['kabupaten_kota', 'posisi_berkas', 'nama_prosedur']).agg(
    banyak_berkas=('nmr_berkas', 'count'),
    daftar_berkas=('no_thn_berkas', lambda x: ", ".join(x.unique()))
).reset_index()

fig = go.Figure()
# Mengurutkan nama kabupaten/kota agar indeks pencocokan koordinat stabil
daftar_kab_kota = sorted(df_grouped['kabupaten_kota'].unique())

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

# Menggunakan plotly_events untuk menangkap data koordinat klik secara real-time
selected_point = plotly_events(fig, click_event=True, hover_event=False, select_event=False)

st.markdown("---")

# --- 5. TABEL DRILLDOWN OTOMATIS BERDASARKAN KLIK GRAFIK ---
if selected_point:
    # Mengambil indeks data dari event klik grafik
    point_index = selected_point[0]['pointNumber']
    trace_index = selected_point[0]['curveNumber']
    
    # Menemukan nama Kabupaten/Kota dan Posisi Berkas berdasarkan indeks yang diklik
    klik_kabupaten = daftar_kab_kota[point_index]
    klik_posisi = kategori_posisi[trace_index]
    
    st.subheader(f"📋 Detail Berkas: Kabupaten/Kota {klik_kabupaten} - Posisi {klik_posisi}")
    
    # Filter data utama
    df_drilldown = df[
        (df['kabupaten_kota'] == klik_kabupaten) & 
        (df['posisi_berkas'] == klik_posisi)
    ].copy()
    
    if not df_drilldown.empty:
        # Format string tanggal (YYYY-MM-DD)
        df_drilldown['tgl_mulai'] = pd.to_datetime(df_drilldown['tgl_mulai']).dt.strftime('%Y-%m-%d')
        
        # Susun kolom sesuai instruksi
        df_drilldown_display = df_drilldown[['kabupaten_kota', 'nmr_berkas', 'tgl_mulai', 'nama_prosedur']].copy()
        
        # Penomoran otomatis kolom "No."
        df_drilldown_display.insert(0, 'No.', range(1, len(df_drilldown_display) + 1))
        
        # Tampilkan Tabel Drilldown
        st.dataframe(df_drilldown_display, use_container_width=True, hide_index=True)
    else:
        st.info("Tidak ada data berkas yang terdaftar untuk kombinasi ini.")
else:
    st.info("Silakan klik pada salah satu batang di grafik Kabupaten/Kota untuk menampilkan detail data di sini.")
