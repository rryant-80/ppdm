import streamlit as st
import pandas as pd
import plotly.express as px

# Konfigurasi Halaman
st.set_page_config(
    page_title="Dashboard Pertanahan Sulteng 2026",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 1. KONEKSI DATA (GOOGLE SHEETS VIA SECRETS)
# -----------------------------------------------------------------------------
SHEET_ID = st.secrets["gsheet_id"]

@st.cache_data(ttl=3600)  # Cache data selama 1 jam agar loading cepat
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Gagal memuat data GID {gid}: {e}")
        return pd.DataFrame()

# Memuat semua data di awal
df_layanan = load_data("1447858691")
df_elektronik = load_data("1848496896")
df_sdm = load_data("1168898330")
df_psn = load_data("193371600")

# -----------------------------------------------------------------------------
# 2. MODUL HALAMAN UTAMA (Dipisah per fungsi agar mudah diubah)
# -----------------------------------------------------------------------------

def render_profil_anggaran(df_filtered_sdm):
    st.title("🏛️ Profil & Anggaran")
    st.markdown("---")
    st.subheader("Konten Menu 1 (Menunggu gambaran dari Anda)")
    st.write("Data SDM & Anggaran yang terfilter:", df_filtered_sdm.head())


def render_psn_2026(df_filtered_psn):
    st.title("🎯 Proyek Strategis Nasional (PSN) 2026")
    st.markdown("---")
    st.subheader("Konten Menu 2 (Menunggu gambaran dari Anda)")
    st.write("Data PSN yang terfilter:", df_filtered_psn.head())


def render_layanan_pertanahan(df_filtered_layanan):
    st.title("💼 Layanan Pertanahan")
    st.markdown("---")
    st.subheader("Konten Menu 3 (Menunggu gambaran dari Anda)")
    st.write("Data Layanan Pertanahan yang terfilter:", df_filtered_layanan.head())


def render_pertanahan_elektronik(df_filtered_elektronik):
    st.title("⚡ Pertanahan Elektronik")
    st.markdown("---")
    st.subheader("Konten Menu 4 (Menunggu gambaran dari Anda)")
    st.write("Data Pertanahan Elektronik yang terfilter:", df_filtered_elektronik.head())


# -----------------------------------------------------------------------------
# 3. SIDEBAR: FILTER & NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("📍 Filter Wilayah")
    
    # Filter Kabupaten/Kota (diambil dari gabungan semua dataframe agar aman)
    list_kabupaten = sorted(list(set(
        df_layanan['kabupaten_kota'].dropna().unique().tolist() +
        df_elektronik['kabupaten_kota'].dropna().unique().tolist() +
        df_sdm['kabupaten_kota'].dropna().unique().tolist() +
        df_psn['kabupaten_kota'].dropna().unique().tolist()
    )))
    list_kabupaten.insert(0, "Semua Kabupaten/Kota")
    selected_kab = st.selectbox("Kabupaten / Kota", list_kabupaten)
    
    # Filter Kecamatan (Hanya muncul/relevan jika ada di df_elektronik yang memiliki kolom kecamatan)
    if selected_kab != "Semua Kabupaten/Kota":
        df_kec_pool = df_elektronik[df_elektronik['kabupaten_kota'] == selected_kab]
        list_kecamatan = sorted(df_kec_pool['kecamatan'].dropna().unique().tolist())
    else:
        list_kecamatan = sorted(df_elektronik['kecamatan'].dropna().unique().tolist())
        
    list_kecamatan.insert(0, "Semua Kecamatan")
    selected_kec = st.selectbox("Kecamatan", list_kecamatan)
    
    st.markdown("---")
    st.header("🗂️ Menu Utama")
    
    # Navigasi Menggunakan Radio Button / Tombol Bergaya Menu
    menu_pilihan = st.radio(
        "Pilih Halaman:",
        [
            "🏛️ Profil & Anggaran",
            "🎯 PSN 2026",
            "💼 Layanan Pertanahan",
            "⚡ Pertanahan Elektronik"
        ]
    )
    
    st.markdown("---")
    st.header("📊 Grafik Rekapitulasi (Sulteng)")

    # --- GRAFIK 1: SDM (Jumlah Pegawai tiap Kabupaten) ---
    if not df_sdm.empty:
        df_sdm_rekap = df_sdm.groupby('kabupaten_kota').size().reset_index(name='Jumlah Pegawai')
        fig_sdm = px.bar(df_sdm_rekap, x='kabupaten_kota', y='Jumlah Pegawai', 
                         title="Jumlah Pegawai per Kab/Kota", labels={'kabupaten_kota': 'Kab/Kota'})
        fig_sdm.update_layout(showlegend=False, height=250, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_sdm, use_container_width=True)

    # --- GRAFIK 2: Layanan Pertanahan (Banyaknya nmr_berkas tiap Kabupaten) ---
    if not df_layanan.empty:
        df_layanan_rekap = df_layanan.groupby('kabupaten_kota')['nmr_berkas'].count().reset_index(name='Total Berkas')
        fig_layanan = px.bar(df_layanan_rekap, x='kabupaten_kota', y='Total Berkas', 
                             title="Banyaknya Berkas per Kab/Kota", labels={'kabupaten_kota': 'Kab/Kota'})
        fig_layanan.update_layout(showlegend=False, height=250, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_layanan, use_container_width=True)

    # --- GRAFIK 3: Sertipikat Elektronik (Persentase pra_btel dengan bt_valid) ---
    if not df_elektronik.empty:
        df_elek_rekap = df_elektronik.groupby('kabupaten_kota')[['pra_btel', 'bt_valid']].sum().reset_index()
        # Menghindari pembagian dengan nol
        df_elek_rekap['Persentase Valid (%)'] = (df_elek_rekap['bt_valid'] / df_elek_rekap['pra_btel'].replace(0, 1)) * 100
        fig_elek = px.bar(df_elek_rekap, x='kabupaten_kota', y='Persentase Valid (%)', 
                           title="Persentase BT Valid vs Pra BTel", labels={'kabupaten_kota': 'Kab/Kota'})
        fig_elek.update_layout(showlegend=False, height=250, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_elek, use_container_width=True)


# -----------------------------------------------------------------------------
# 4. PROSES FILTERING DATA
# -----------------------------------------------------------------------------
# Salinan dataframe untuk difilter berdasarkan sidebar
df_f_layanan = df_layanan.copy()
df_f_elektronik = df_elektronik.copy()
df_f_sdm = df_sdm.copy()
df_f_psn = df_psn.copy()

if selected_kab != "Semua Kabupaten/Kota":
    df_f_layanan = df_f_layanan[df_f_layanan['kabupaten_kota'] == selected_kab]
    df_f_elektronik = df_f_elektronik[df_f_elektronik['kabupaten_kota'] == selected_kab]
    df_f_sdm = df_f_sdm[df_f_sdm['kabupaten_kota'] == selected_kab]
    df_f_psn = df_f_psn[df_f_psn['kabupaten_kota'] == selected_kab]

if selected_kec != "Semua Kecamatan":
    # Hanya df_elektronik yang memiliki kolom 'kecamatan' secara eksplisit di daftar Anda
    if 'kecamatan' in df_f_elektronik.columns:
        df_f_elektronik = df_f_elektronik[df_f_elektronik['kecamatan'] == selected_kec]


# -----------------------------------------------------------------------------
# 5. ROUTING HALAMAN UTAMA
# -----------------------------------------------------------------------------
if menu_pilihan == "🏛️ Profil & Anggaran":
    render_profil_anggaran(df_f_sdm)
elif menu_pilihan == "🎯 PSN 2026":
    render_psn_2026(df_f_psn)
elif menu_pilihan == "💼 Layanan Pertanahan":
    render_layanan_pertanahan(df_f_layanan)
elif menu_pilihan == "⚡ Pertanahan Elektronik":
    render_pertanahan_elektronik(df_f_elektronik)
