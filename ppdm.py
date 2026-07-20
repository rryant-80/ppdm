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

    # Dikitonari untuk mempersingkat nama kabupaten
    KAB_MAP = {
        'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
        'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
        'Poso': 'PS', 'Tojo Una-Una': 'TU', 'Tojo Una-una': 'TU', 'Tolitoli': 'TL', 'Toli-toli': 'TL', 'Toli Toli': 'TL',
        'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL', 'Kota Palu': 'PL', 
        'Sigi': 'SG', 'Sulawesi Tengah': 'ST', 'Provinsi Sulawesi Tengah': 'ST'
    }
    
    # Fungsi pembantu untuk menyingkat nama kabupaten di DataFrame
    def singkat_kab(df):
        if not df.empty and 'kabupaten_kota' in df.columns:
            df['kab_singkat'] = df['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x))
        return df

    # Terapkan singkatan ke dataframe rekap
    df_sdm_singkat = singkat_kab(df_sdm.copy())
    df_layanan_singkat = singkat_kab(df_layanan.copy())
    df_elek_singkat = singkat_kab(df_elektronik.copy())

    # ==========================================
    # 1. GRAFIK: Distribusi Pegawai (Stacked Bar - Terurut)
    # ==========================================
    if not df_sdm_singkat.empty and 'kategori_asn' in df_sdm_singkat.columns:
        # Rekap jumlah berdasarkan kabupaten dan kategori ASN
        df_sdm_rekap = df_sdm_singkat.groupby(['kab_singkat', 'kategori_asn']).size().reset_index(name='jumlah')
        
        # Buat pivot untuk hover teks
        df_sdm_pivot = df_sdm_rekap.pivot(index='kab_singkat', columns='kategori_asn', values='jumlah').fillna(0).astype(int)
        
        # Hitung total per kabupaten untuk sorting dan hover
        df_sdm_total = df_sdm_singkat.groupby('kab_singkat').size().reset_index(name='total_all')
        df_sdm_rekap = df_sdm_rekap.merge(df_sdm_pivot, on='kab_singkat').merge(df_sdm_total, on='kab_singkat')
        
        # Urutkan berdasarkan total_all tertinggi ke terendah
        df_sdm_rekap = df_sdm_rekap.sort_values(by='total_all', ascending=False)
        
        # Dinamis teks hover
        hover_text = "<b>Kab/Kota: %{x}</b><br>Total ASN: %{customdata[0]} orang<br>"
        custom_data_cols = ['total_all']
        for i, col in enumerate(df_sdm_pivot.columns):
            hover_text += f"{col}: %{{customdata[{i+1}]}} orang<br>"
            custom_data_cols.append(col)

        fig_sdm = px.bar(
            df_sdm_rekap, x='kab_singkat', y='jumlah', color='kategori_asn',
            title="Distribusi Pegawai",
            custom_data=df_sdm_rekap[custom_data_cols]
        )
        fig_sdm.update_traces(hovertemplate=hover_text + "<extra></extra>")
        fig_sdm.update_layout(
            showlegend=True, legend_title_text='', height=280,
            xaxis_title="", yaxis_title="",
            xaxis={'categoryorder':'total descending'}, # Memastikan urutan bar menurun
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_sdm, use_container_width=True)


    # ==========================================
    # 2. GRAFIK: Berkas Lewat SOP (Terurut)
    # ==========================================
    if not df_layanan_singkat.empty and 'nmr_berkas' in df_layanan_singkat.columns:
        df_layanan_total = df_layanan_singkat.groupby('kab_singkat')['nmr_berkas'].count().reset_index(name='total_berkas')
        
        # Urutkan dari tertinggi ke terendah
        df_layanan_total = df_layanan_total.sort_values(by='total_berkas', ascending=False)
        
        if 'posisi_berkas' in df_layanan_singkat.columns:
            df_layanan_pos = df_layanan_singkat.groupby(['kab_singkat', 'posisi_berkas']).size().reset_index(name='jml_pos')
            df_layanan_pivot = df_layanan_pos.pivot(index='kab_singkat', columns='posisi_berkas', values='jml_pos').fillna(0).astype(int)
            df_layanan_total = df_layanan_total.merge(df_layanan_pivot, on='kab_singkat')
            
            hover_layanan = "<b>Kab/Kota: %{x}</b><br>Total Berkas: %{y}<br>--- Detail Posisi ---<br>"
            custom_data_layanan = ['total_berkas']
            for i, col in enumerate(df_layanan_pivot.columns):
                hover_layanan += f"{col}: %{{customdata[{i+1}]}}<br>"
                custom_data_layanan.append(col)
        else:
            hover_layanan = "<b>Kab/Kota: %{x}</b><br>Total Berkas: %{y}<extra></extra>"
            custom_data_layanan = ['total_berkas']

        fig_layanan = px.bar(
            df_layanan_total, x='kab_singkat', y='total_berkas',
            title="Berkas Lewat SOP",
            custom_data=df_layanan_total[custom_data_layanan] if custom_data_layanan else None
        )
        fig_layanan.update_traces(hovertemplate=hover_layanan + "<extra></extra>", marker_color='#EF553B')
        fig_layanan.update_layout(
            showlegend=False, height=250,
            xaxis_title="", yaxis_title="",
            xaxis={'categoryorder':'total descending'},
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_layanan, use_container_width=True)


    # ==========================================
    # 3. GRAFIK: Persentase Prasertel (Formula Diperbaiki & Terurut)
    # ==========================================
    if not df_elek_singkat.empty and 'pra_sertel' in df_elek_singkat.columns and 'bt_valid' in df_elek_singkat.columns:
        df_elek_rekap = df_elek_singkat.groupby('kab_singkat')[['pra_sertel', 'bt_valid']].sum().reset_index()
        
        # Perbaikan Formula: pra_sertel / bt_valid
        df_elek_rekap['Persentase'] = (df_elek_rekap['pra_sertel'] / df_elek_rekap['bt_valid'].replace(0, 1)) * 100
        
        # Urutkan dari persentase tertinggi ke terendah
        df_elek_rekap = df_elek_rekap.sort_values(by='Persentase', ascending=False)
        
        fig_elek = px.bar(
            df_elek_rekap, x='kab_singkat', y='Persentase',
            title="Persentase Prasertel",
            custom_data=df_elek_rekap[['pra_sertel', 'bt_valid']]
        )
        fig_elek.update_traces(
            # Format %{y:.2f}% untuk menampilkan dua angka di belakang koma pada hover
            hovertemplate="<b>Kab/Kota: %{x}</b><br>Persentase: %{y:.2f}%<br>Jumlah Prasertel: %{customdata[0]}<br>Jumlah BT Valid: %{customdata[1]}<extra></extra>",
            marker_color='#00CC96'
        )
        fig_elek.update_layout(
            showlegend=False, height=250,
            xaxis_title="", yaxis_title="",
            xaxis={'categoryorder':'total descending'},
            yaxis=dict(tickformat=".2f"), # Format angka sumbu Y menjadi 2 desimal jika diperlukan
            margin=dict(l=10, r=10, t=40, b=10)
        )
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
    def render_profil_anggaran(df_filtered_sdm):
    st.title("🏛️ Profil & Anggaran")
    st.markdown("---")
    
    # Kebutuhan data eksternal untuk card wilayah (menggunakan data global yang terfilter di lingkup utama)
    # Catatan: df_f_elektronik harus diakses. Agar aman, kita ambil data dari context filter utama app
    df_elek_ctx = globals().get('df_f_elektronik', pd.DataFrame())

    # ==========================================
    # FUNCTION PEMBANTU UNTUK PEJABAT / FOTO
    # ==========================================
    def get_pejabat_info(df, jabatan_name):
        # Cari data berdasarkan kolom jabatan
        match = df[df['jabatan'].astype(str).str.contains(jabatan_name, case=False, na=False)]
        if not match.empty:
            row = match.iloc[0]
            # Menghitung persentase realisasi individual
            target = row.get('target_dipa', 0)
            realisasi = row.get('realisasi_dipa', 0)
            persen = (realisasi / target * 100) if target > 0 else 0.0
            
            return {
                "nama": row.get('pegawai', '-'),
                "jabatan": row.get('jabatan', jabatan_name),
                "url": row.get('url', 'https://via.placeholder.com/150'),
                "target": target,
                "realisasi": realisasi,
                "persen": persen
            }
        return {
            "nama": "Belum Ada Data", "jabatan": jabatan_name, 
            "url": "https://via.placeholder.com/150", "target": 0, "realisasi": 0, "persen": 0.0
        }

    # Ambil data pimpinan teratas (berdasarkan df sdm terfilter)
    pimpinan_1 = get_pejabat_info(df_filtered_sdm, "Bendahara")
    pimpinan_2 = get_pejabat_info(df_filtered_sdm, "Kepala Kantor")

    # ==========================================
    # BARIS 1: FOTO UTAMA & METRIK CARDS
    # ==========================================
    col_layout_left, col_layout_right = st.columns([2, 3])

    with col_layout_left:
        # Foto 1 & Foto 2 Berdampingan
        col_pic1, col_pic2 = st.columns(2)
        with col_pic1:
            st.image(pimpinan_1["url"], use_container_width=True, caption=f"{pimpinan_1['jabatan']}")
            st.caption(f"**{pimpinan_1['nama']}**")
        with col_pic2:
            st.image(pimpinan_2["url"], use_container_width=True, caption=f"{pimpinan_2['jabatan']}")
            st.caption(f"**{pimpinan_2['nama']}**")

    with col_layout_right:
        # Susunan Grid Card 3x2 (Card 1 sampai Card 6, di layout gambar Anda Card 3 tertulis dua kali, disesuaikan urutannya)
        c1, c2, c3 = st.columns(3)
        c4, c5, c6 = st.columns(3)

        # Hitung Nilai Agregat Metrik
        jml_pegawai = len(df_filtered_sdm)
        
        if not df_elek_ctx.empty:
            jml_kec = df_elek_ctx['kecamatan'].nunique() if 'kecamatan' in df_elek_ctx.columns else 0
            jml_desa = df_elek_ctx['desa_kelurahan'].nunique() if 'desa_kelurahan' in df_elek_ctx.columns else 0
            luas_adm = df_elek_ctx['luas_adm'].sum() if 'luas_adm' in df_elek_ctx.columns else 0
            luas_apl = df_elek_ctx['luas_apl'].sum() if 'luas_apl' in df_elek_ctx.columns else 0
        else:
            jml_kec, jml_desa, luas_adm, luas_apl = 0, 0, 0, 0

        total_target = df_filtered_sdm['target_dipa'].sum() if 'target_dipa' in df_filtered_sdm.columns else 0
        total_realisasi = df_filtered_sdm['realisasi_dipa'].sum() if 'realisasi_dipa' in df_filtered_sdm.columns else 0
        total_persen_dipa = (total_realisasi / total_target * 100) if total_target > 0 else 0.0

        # Render masing-masing card
        c1.metric("Jumlah Pegawai (Card 1)", f"{jml_pegawai} Orang")
        c2.metric("Jumlah Kecamatan (Card 2)", f"{jml_kec}")
        c3.metric("Jumlah Desa/Kel (Card 3)", f"{jml_desa}")
        
        # Card 4 dengan detail Rupiah Realisasi
        c4.metric(
            "Total % Realisasi Dipa (Card 4)", 
            f"{total_persen_dipa:.2f}%", 
            help=f"Total Realisasi: Rp {total_realisasi:,.0f}"
        )
        c4.markdown(f"<small style='color:gray;'>Rp {total_realisasi:,.0f}</small>", unsafe_allow_html=True)
        
        c5.metric("Luas ADM (Card 5)", f"{luas_adm:,.2f} Ha")
        c6.metric("Luas APL (Card 6)", f"{luas_apl:,.2f} Ha")

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # BARIS 2: GRID PEJABAT STRUKTURAL (F1 - F6)
    # ==========================================
    st.subheader("👥 Pejabat Struktural")
    
    # Definisikan list jabatan untuk F1 s.d F6
    jabatan_list = [
        "Tata Usaha", 
        "Survei dan Pemetaan", 
        "Penetapan Hak dan Pendaftaran", 
        "Penataan dan Pemberdayaan", 
        "Pengadaan Tanah dan Pengembangan", 
        "Pengendalian dan Penanganan Sengketa"
    ]

    # Render Baris Pertama (F1, F2, F3) dan Baris Kedua (F4, F5, F6)
    row1_cols = st.columns(3)
    row2_cols = st.columns(3)
    all_f_cols = row1_cols + row2_cols

    for idx, jab in enumerate(jabatan_list):
        p_info = get_pejabat_info(df_filtered_sdm, jab)
        
        with all_f_cols[idx]:
            # Pembungkus visual berupa kontainer/box
            with st.container(border=True):
                sub_c1, sub_c2 = st.columns([1, 2])
                
                with sub_c1:
                    # Kotak Foto Profil Pejabat
                    st.image(p_info["url"], use_container_width=True)
                    st.markdown(f"<center><b>F{idx+1}</b></center>", unsafe_allow_html=True)
                    
                with sub_c2:
                    st.markdown(f"##### {p_info['nama']}")
                    st.markdown(f"<small style='color:gray;'>{p_info['jabatan']}</small>", unsafe_allow_html=True)
                    st.markdown(f"<small>Target: <b>Rp {p_info['target']:,.0f}</b></small>", unsafe_allow_html=True)
                    
                    # Progress Bar Realisasi Dipa
                    # Streamlit progress membutuhkan nilai antara 0.0 s.d 1.0
                    progress_val = min(max(p_info['persen'] / 100.0, 0.0), 1.0)
                    st.progress(progress_val)
                    
                    st.markdown(
                        f"<div style='text-align: right;'><small>Realisasi: <b style='color:#00CC96;'>{p_info['persen']:.2f}%</b> (Rp {p_info['realisasi']:,.0f})</small></div>", 
                        unsafe_allow_html=True
                    )
elif menu_pilihan == "🎯 PSN 2026":
    render_psn_2026(df_f_psn)
elif menu_pilihan == "💼 Layanan Pertanahan":
    render_layanan_pertanahan(df_f_layanan)
elif menu_pilihan == "⚡ Pertanahan Elektronik":
    render_pertanahan_elektronik(df_f_elektronik)
