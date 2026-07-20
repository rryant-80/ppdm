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
    
    # Kebutuhan data eksternal untuk card wilayah
    df_elek_ctx = globals().get('df_f_elektronik', pd.DataFrame())

    # ==========================================
    # FUNGSI PEMBANTU FORMAT ANGKA INDONESIA
    # ==========================================
    def clean_number(val):
        if pd.isna(val):
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        clean_str = str(val).replace('.', '').replace(',', '').replace('Rp', '').strip()
        try:
            return float(clean_str)
        except ValueError:
            return 0.0

    def fmt_idr(val):
        """Format angka ke Rupiah standar Indonesia: ribuan titik (1.000.000)"""
        return f"{val:,.0f}".replace(',', '.')

    def fmt_pct(val):
        """Format persentase desimal koma (59,76%)"""
        return f"{val:.2f}".replace('.', ',')

    def fmt_decimal(val):
        """Format angka desimal lengkap dengan pemisah ribuan titik dan desimal koma (misal: 6.910.824,75)"""
        parts = f"{val:,.2f}".split('.')
        integer_part = parts[0].replace(',', '.')
        decimal_part = parts[1]
        return f"{integer_part},{decimal_part}"

    # ==========================================
    # FUNCTION PEMBANTU UNTUK PEJABAT / FOTO
    # ==========================================
    def get_pejabat_info(df, jabatan_name):
        match = df[df['jabatan'].astype(str).str.contains(jabatan_name, case=False, na=False)]
        DEFAULT_IMG = "https://via.placeholder.com/150?text=No+Image"
        
        if not match.empty:
            row = match.iloc[0]
            target = clean_number(row.get('target_dipa', 0))
            realisasi = clean_number(row.get('realisasi_dipa', 0))
            persen = (realisasi / target * 100) if target > 0 else 0.0
            
            url_val = row.get('url', '')
            if pd.isna(url_val) or not str(url_val).startswith('http'):
                url_val = DEFAULT_IMG
                
            return {
                "nama": row.get('pegawai', '-'),
                "jabatan": row.get('jabatan', jabatan_name),
                "url": url_val,
                "target": target,
                "realisasi": realisasi,
                "persen": persen
            }
            
        return {
            "nama": "Belum Ada Data", "jabatan": jabatan_name, 
            "url": DEFAULT_IMG, "target": 0, "realisasi": 0, "persen": 0.0
        }

    # Ambil data pimpinan & foto gedung/kantor
    pimpinan_0 = get_pejabat_info(df_filtered_sdm, "Juru Ukur")      # Foto 1 (Kiri Baru)
    pimpinan_1 = get_pejabat_info(df_filtered_sdm, "Bendahara")   # Foto 2 (Tengah)
    pimpinan_2 = get_pejabat_info(df_filtered_sdm, "Kepala Kantor")# Foto 3 (Kanan)

    # ==========================================
    # FUNCTION PEMBANTU CARD MODERN AKSEN BIRU
    # ==========================================
    def render_modern_card(title, value, sub_value=""):
        card_html = f"""
        <div style="
            background: linear-gradient(135deg, #ffffff 0%, #f0f7ff 100%);
            border-left: 5px solid #1E88E5;
            border-radius: 8px;
            padding: 10px 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            margin-bottom: 10px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="color: #555555; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {title}
            </div>
            <div style="color: #0D47A1; font-size: 1.15rem; font-weight: 700; margin-top: 2px; word-break: break-word;">
                {value}
            </div>
            {f'<div style="color: #666666; font-size: 0.70rem; margin-top: 1px;">{sub_value}</div>' if sub_value else ''}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    # ==========================================
    # BARIS 1: FOTO UTAMA (3 FOTO) & METRIK CARDS
    # ==========================================
    # Pembagian rasio: 2 bagian untuk 3 Foto, 3 bagian untuk 6 Cards
    col_layout_left, col_layout_right = st.columns([2, 3])

    with col_layout_left:
        # 3 Foto Berdampingan Ukuran Sama
        col_pic1, col_pic2, col_pic3 = st.columns(3)
        with col_pic1:
            st.image(pimpinan_0["url"], use_column_width=True)
        with col_pic2:
            st.image(pimpinan_1["url"], use_column_width=True)
        with col_pic3:
            st.image(pimpinan_2["url"], use_column_width=True)

    with col_layout_right:
        jml_pegawai = len(df_filtered_sdm)
        
        if not df_elek_ctx.empty:
            jml_kec = df_elek_ctx['kecamatan'].nunique() if 'kecamatan' in df_elek_ctx.columns else 0
            jml_desa = df_elek_ctx['desa_kelurahan'].nunique() if 'desa_kelurahan' in df_elek_ctx.columns else 0
            
            # Ambil total nilai m2 dari Google Sheet
            luas_adm_m2 = df_elek_ctx['luas_adm'].apply(clean_number).sum() if 'luas_adm' in df_elek_ctx.columns else 0
            luas_apl_m2 = df_elek_ctx['luas_apl'].apply(clean_number).sum() if 'luas_apl' in df_elek_ctx.columns else 0
            
            # Konversi dari m2 ke km2 (dibagi 1.000.000)
            luas_adm_km2 = luas_adm_m2 / 1_000_000.0
            luas_apl_km2 = luas_apl_m2 / 1_000_000.0
            
            # Persentase APL terhadap ADM
            persen_apl_adm = (luas_apl_m2 / luas_adm_m2 * 100) if luas_adm_m2 > 0 else 0.0
        else:
            jml_kec, jml_desa, luas_adm_km2, luas_apl_km2, persen_apl_adm = 0, 0, 0.0, 0.0, 0.0

        total_target = df_filtered_sdm['target_dipa'].apply(clean_number).sum() if 'target_dipa' in df_filtered_sdm.columns else 0.0
        total_realisasi = df_filtered_sdm['realisasi_dipa'].apply(clean_number).sum() if 'realisasi_dipa' in df_filtered_sdm.columns else 0.0
        total_persen_dipa = (total_realisasi / total_target * 100) if total_target > 0 else 0.0

        c1, c2, c3 = st.columns(3)
        with c1:
            render_modern_card("Jumlah Pegawai", f"{jml_pegawai} Orang")
        with c2:
            render_modern_card("Jumlah Kecamatan", f"{fmt_idr(jml_kec)}")
        with c3:
            render_modern_card("Jumlah Desa/Kel", f"{fmt_idr(jml_desa)}")

        c4, c5, c6 = st.columns(3)
        with c4:
            render_modern_card("Total % Realisasi Dipa", f"{fmt_pct(total_persen_dipa)}%", f"Rp {fmt_idr(total_realisasi)}")
        with c5:
            render_modern_card("Luas ADM", f"{fmt_decimal(luas_adm_km2)} <span style='font-size:0.8rem;'>km²</span>")
        with c6:
            render_modern_card(
                "Luas APL", 
                f"{fmt_decimal(luas_apl_km2)} <span style='font-size:0.8rem;'>km²</span>", 
                f"{fmt_pct(persen_apl_adm)}% dari Luas ADM"
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # BARIS 2: GRID PEJABAT STRUKTURAL
    # ==========================================
    st.subheader("👥 Pejabat Struktural")
    
    jabatan_list = [
        "Tata Usaha", 
        "Survei dan Pemetaan", 
        "Penetapan Hak dan Pendaftaran", 
        "Penataan dan Pemberdayaan", 
        "Pengadaan Tanah dan Pengembangan", 
        "Pengendalian dan Penanganan Sengketa"
    ]

    row1_cols = st.columns(3)
    row2_cols = st.columns(3)
    all_f_cols = row1_cols + row2_cols

    for idx, jab in enumerate(jabatan_list):
        p_info = get_pejabat_info(df_filtered_sdm, jab)
        
        with all_f_cols[idx]:
            with st.container(border=True):
                sub_c1, sub_c2 = st.columns([1, 2.2])
                
                with sub_c1:
                    st.image(p_info["url"], use_column_width=True)
                    
                with sub_c2:
                    html_content = f"""
                    <div style="line-height: 1.25; margin-bottom: 4px;">
                        <div style="font-weight: 700; font-size: 0.88rem; color: #111111; word-break: break-word;">
                            {p_info['nama']}
                        </div>
                        <div style="font-size: 0.75rem; color: #666666; margin-top: 2px; margin-bottom: 6px;">
                            {p_info['jabatan']}
                        </div>
                        <div style="font-size: 0.75rem; color: #333333;">
                            Target: <b>Rp {fmt_idr(p_info['target'])}</b>
                        </div>
                    </div>
                    """
                    st.markdown(html_content, unsafe_allow_html=True)
                    
                    # Progress Bar Realisasi
                    progress_val = min(max(p_info['persen'] / 100.0, 0.0), 1.0)
                    st.progress(progress_val)
                    
                    # Realisasi ditulis menyambung (contoh: Realisasi: 59,76% (Rp 200.000.988))
                    html_realisasi = f"""
                    <div style="text-align: right; line-height: 1.2; margin-top: 2px; font-size: 0.70rem; color: #555555;">
                        Realisasi: <b style="font-size: 0.72rem; color: #00CC96;">{fmt_pct(p_info['persen'])}%</b> (Rp {fmt_idr(p_info['realisasi'])})
                    </div>
                    """
                    st.markdown(html_realisasi, unsafe_allow_html=True)
    
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
    render_profil_anggaran(df_f_sdm)
elif menu_pilihan == "🎯 PSN 2026":
    render_psn_2026(df_f_psn)
elif menu_pilihan == "💼 Layanan Pertanahan":
    render_layanan_pertanahan(df_f_layanan)
elif menu_pilihan == "⚡ Pertanahan Elektronik":
    render_pertanahan_elektronik(df_f_elektronik)
