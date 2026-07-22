import datetime
import re
import pandas as pd
import plotly.express as px
import streamlit as st

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
df_progress_raw  = load_data("386436131")  # Data Progress Harian (Card 9)
df_peringkat_raw = load_data("880542789")

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
            
            # Konversi dari m2 ke ha (dibagi 10.000)
            luas_adm_ha = luas_adm_m2 / 10_000.0
            luas_apl_ha = luas_apl_m2 / 10_000.0
            
            # Persentase APL terhadap ADM
            persen_apl_adm = (luas_apl_m2 / luas_adm_m2 * 100) if luas_adm_m2 > 0 else 0.0
        else:
            jml_kec, jml_desa, luas_adm_ha, luas_apl_ha, persen_apl_adm = 0, 0, 0.0, 0.0, 0.0

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
            render_modern_card("Luas ADM", f"{fmt_decimal(luas_adm_ha)} <span style='font-size:0.8rem;'>Ha</span>")
        with c6:
            render_modern_card(
                "Luas APL", 
                f"{fmt_decimal(luas_apl_ha)} <span style='font-size:0.8rem;'>Ha</span>", 
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
    
    if df_filtered_psn.empty:
        st.warning("Data PSN tidak ditemukan atau kosong untuk filter yang dipilih.")
        return

    # ==========================================
    # 1. KAMUS SINGKATAN KABUPATEN
    # ==========================================
    KAB_MAP = {
        'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
        'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
        'Poso': 'PS', 'Tojo Una-una': 'TU', 'Toli-toli': 'TL',
        'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL',
        'Sigi': 'SG', 'Sulawesi Tengah': 'ST'
    }

    # ==========================================
    # 2. FUNGSI PEMBERSIH ANGKA TERPISAH PRESISI
    # ==========================================
    def clean_integer_field(val):
        """
        Khusus SHAT, Redis, Lintor & Target PBT (SATUAN BIDANG / BULAT MURNI).
        Memastikan 2.000 -> 2000, 1.050 -> 1050, 1.700 -> 1700, 600 -> 600.
        """
        if pd.isna(val): 
            return 0.0
            
        # Jika terbaca sebagai float oleh Pandas (seperti 2.0 dari '2.000' atau 1.7 dari '1.700')
        if isinstance(val, float):
            if val == 0: 
                return 0.0
            # Jika angka pecahan/float di bawah 10 (contoh: 2.0 -> 2000, 1.7 -> 1700, 1.05 -> 1050, 1.264 -> 1264)
            if 0 < val < 10:
                return float(round(val * 1000))
            return float(val)
            
        if isinstance(val, int):
            return float(val)
            
        # Jika berupa string murni dari Google Sheets (misal "2.000" atau "1.050")
        s_val = str(val).replace('Rp', '').strip()
        if not s_val: 
            return 0.0
        
        # Hapus seluruh titik pemisah ribuan
        clean_str = s_val.replace('.', '').replace(',', '.')
        try:
            return float(clean_str)
        except ValueError:
            return 0.0
        
        # Hapus seluruh titik ribuan
        clean_str = s_val.replace('.', '').replace(',', '.')
        try:
            return float(clean_str)
        except ValueError:
            return 0.0

    def clean_pbt_decimal_field(val):
        """
        Khusus REALISASI PBT (SATUAN HEKTAR) yang memiliki angka desimal koma asli (misal: 510,75)
        """
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        
        s_val = str(val).replace('Rp', '').strip()
        if not s_val: return 0.0
        
        if ',' in s_val:
            clean_str = s_val.replace('.', '').replace(',', '.')
        else:
            clean_str = s_val.replace('.', '')
            
        try:
            return float(clean_str)
        except ValueError:
            return 0.0

    def fmt_idr(val):
        """Format ribuan titik untuk satuan Bidang (contoh: 1.050)"""
        return f"{val:,.0f}".replace(',', '.')

    def fmt_decimal(val):
        """Format desimal koma untuk satuan Hektar (contoh: 510,75)"""
        parts = f"{val:,.2f}".split('.')
        integer_part = parts[0].replace(',', '.')
        decimal_part = parts[1]
        return f"{integer_part},{decimal_part}"

    # ==========================================
    # 3. PERSIAPAN DATA & CLEANING
    # ==========================================
    df = df_filtered_psn.copy()
    if 'kabupaten_kota' in df.columns:
        df['kab_singkat'] = df['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x))
    else:
        df['kab_singkat'] = '-'

    # Kolom realisasi PBT (Hektar desimal)
    pbt_real_cols = ['realisasi_baru', 'realisasi_k4', 'realisasi_repo']
    
    # Seluruh kolom SHAT, Redis, Lintor & Target PBT (Bidang / Bulat Murni)
    integer_cols = [
        'target_pbt', 'target_shat', 'puldadis', 'berkas', 'potensi', 'k1', 
        'siap_serah', 'diserahkan', 'target_redis', 'pos_redis', 'sk_redis', 
        'sertipikat_redis', 'target_lintor', 'lintor_su', 'lintor_sk', 
        'lintor_sertipikat', 'lintor_serah'
    ]

    for col in integer_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_integer_field)
        else:
            df[col] = 0.0

    for col in pbt_real_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_pbt_decimal_field)
        else:
            df[col] = 0.0

    cols_to_clean = integer_cols + pbt_real_cols
    df_rekap = df.groupby('kab_singkat')[cols_to_clean].sum().reset_index()

    # ==========================================
    # 4. FUNGSI PEMBUAT GRAFIK PLOTLY
    # ==========================================
    def create_psn_chart(title, df_data, target_col, metrics_dict, color_sequence, unit="Bdg", is_stacked=False):
        df_valid = df_data[df_data[target_col] > 0].copy()
        
        if df_valid.empty:
            fig_empty = px.bar(title=f"{title} (Tidak ada target aktif)")
            fig_empty.update_layout(
                height=310, 
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=30, b=10)
            )
            return fig_empty

        long_rows = []
        for _, row in df_valid.iterrows():
            kab = row['kab_singkat']
            target_val = row[target_col]
            
            for label, col_name in metrics_dict.items():
                real_val = row[col_name]
                pct = (real_val / target_val * 100) if target_val > 0 else 0.0
                
                # Format hover sesuai satuan (Ha = desimal koma, Bdg = bulat titik)
                real_fmt_str = fmt_decimal(real_val) if unit == "Ha" else fmt_idr(real_val)
                target_fmt_str = fmt_decimal(target_val) if unit == "Ha" else fmt_idr(target_val)

                long_rows.append({
                    'Kab/Kota': kab,
                    'Indikator': label,
                    'Persentase': pct,
                    'Realisasi': real_val,
                    'Target': target_val,
                    'Pct_Fmt': fmt_decimal(pct),
                    'Real_Fmt': f"{real_fmt_str} {unit}",
                    'Target_Fmt': f"{target_fmt_str} {unit}"
                })
                
        df_long = pd.DataFrame(long_rows)
        mode_bar = 'relative' if is_stacked else 'group'

        fig = px.bar(
            df_long,
            x='Kab/Kota',
            y='Persentase',
            color='Indikator',
            barmode=mode_bar,
            title=title,
            color_discrete_sequence=color_sequence,
            custom_data=['Real_Fmt', 'Target_Fmt', 'Pct_Fmt']
        )

        fig.update_traces(
            hovertemplate=(
                "<b>Kab/Kota: %{x}</b><br>"
                "Indikator: %{fullData.name}<br>"
                "Realisasi: %{customdata[0]}<br>"
                "Target: %{customdata[1]}<br>"
                "Persentase: %{customdata[2]}%<extra></extra>"
            ),
            marker=dict(line=dict(width=1.2, color='#111111'))
        )

        fig.update_layout(
            height=310,
            xaxis_title="",
            yaxis_title="",
            legend_title_text="",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=5, r=5, t=32, b=5),
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1,
                font=dict(size=10)
            ),
            title=dict(font=dict(size=14)),
            yaxis=dict(gridcolor='#c4c4c4', tickfont=dict(size=9)),
            xaxis=dict(showgrid=False, tickfont=dict(size=9))
        )
        return fig

    # ==========================================
    # 5. LAYOUT GRID 2x2 DENGAN BINGKAI (#dbdbdb)
    # ==========================================
    card_wrapper_start = """
    <div style="
        background-color: #dbdbdb;
        border-radius: 10px;
        padding: 6px 10px 4px 10px;
        margin-bottom: 8px;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
    ">
    """
    card_wrapper_end = "</div>"

    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)

    # 1. GRAFIK 1: Realisasi PBT
    with row1_col1:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        metrics_pbt = {
            'Realisasi Baru': 'realisasi_baru',
            'Realisasi K4': 'realisasi_k4',
            'Realisasi Repo': 'realisasi_repo'
        }
        fig_pbt = create_psn_chart(
            "1. Realisasi PBT", df_rekap, 'target_pbt', metrics_pbt, 
            ['#636EFA', '#EF553B', '#00CC96'], unit="Ha", is_stacked=True
        )
        st.plotly_chart(fig_pbt, use_container_width=True)
        st.markdown(card_wrapper_end, unsafe_allow_html=True)

    # 2. GRAFIK 2: Realisasi SHAT
    with row1_col2:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        metrics_shat = {
            'Puldadis': 'puldadis',
            'Berkas': 'berkas',
            'K1': 'k1',
            'Diserahkan': 'diserahkan'
        }
        fig_shat = create_psn_chart(
            "2. Realisasi SHAT", df_rekap, 'target_shat', metrics_shat, 
            ['#AB63FA', '#FFA15A', '#19D3F3', '#FF6692'], unit="Bdg"
        )
        st.plotly_chart(fig_shat, use_container_width=True)
        st.markdown(card_wrapper_end, unsafe_allow_html=True)

    # 3. GRAFIK 3: Realisasi Redistribusi
    with row2_col1:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        metrics_redis = {
            'Subyek Obyek': 'pos_redis',
            'SK Redis': 'sk_redis',
            'Sertipikat Redis': 'sertipikat_redis'
        }
        fig_redis = create_psn_chart(
            "3. Realisasi Redistribusi", df_rekap, 'target_redis', metrics_redis, 
            ['#17BECF', '#FECB52', '#B6E880'], unit="Bdg"
        )
        st.plotly_chart(fig_redis, use_container_width=True)
        st.markdown(card_wrapper_end, unsafe_allow_html=True)

    # 4. GRAFIK 4: Realisasi Lintor
    with row2_col2:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        lintor_serah_col = 'lintor_serah' if 'lintor_serah' in df_rekap.columns and df_rekap['lintor_serah'].sum() > 0 else 'lintor_sertipikat'
        metrics_lintor = {
            'Lintor SU': 'lintor_su',
            'Lintor SK': 'lintor_sk',
            'Lintor Sertipikat': lintor_serah_col
        }
        fig_lintor = create_psn_chart(
            "4. Realisasi Lintor", df_rekap, 'target_lintor', metrics_lintor, 
            ['#FF97FF', '#2CA02C', '#D62728'], unit="Bdg"
        )
        st.plotly_chart(fig_lintor, use_container_width=True)
        st.markdown(card_wrapper_end, unsafe_allow_html=True)

def render_layanan_pertanahan(df_filtered_layanan):
    st.markdown("### 🚨 Berkas Melebihi Durasi SOP")
    st.markdown("<small style='color:gray;'>💡 Tips: Arahkan kursor ke kotak merah strobo untuk melihat detail nama prosedur dan nomor berkas.</small>", unsafe_allow_html=True)

    if df_filtered_layanan.empty:
        st.warning("Data Layanan Pertanahan tidak ditemukan atau kosong untuk filter yang dipilih.")
        return

    df = df_filtered_layanan.copy()

    # ==========================================
    # 1. PEMBERSIH FLEKSIBEL TANGGAL & DURASI
    # ==========================================
    def parse_date_flexible(val):
        if pd.isna(val):
            return pd.NaT
        if isinstance(val, (pd.Timestamp, datetime.date, datetime.datetime)):
            return pd.to_datetime(val)
        s_val = str(val).strip()
        if not s_val or s_val.lower() in ['nan', 'none', '-']:
            return pd.NaT
        dt = pd.to_datetime(s_val, dayfirst=True, errors='coerce')
        if pd.isna(dt):
            dt = pd.to_datetime(s_val, errors='coerce')
        return dt

    def clean_durasi(val):
        if pd.isna(val): return 0
        s_val = str(val).strip()
        match = re.search(r'\d+', s_val)
        if match:
            return int(match.group())
        return 0

    def fmt_no_thn(val):
        if pd.isna(val): return "-"
        s_val = str(val).strip()
        if s_val.endswith('.0'):
            return s_val[:-2]
        return s_val

    def fmt_idr(val):
        return f"{val:,.0f}".replace(',', '.')

    # ==========================================
    # 2. NORMALISASI NAMA KABUPATEN
    # ==========================================
    KAB_NAME_CLEAN = {
        'Kota Palu': 'Palu',
        'Kab. Morowali Utara': 'Morowali Utara',
        'Kab. Banggai': 'Banggai',
        'Kab. Banggai Kepulauan': 'Banggai Kepulauan',
        'Kab. Banggai Laut': 'Banggai Laut',
        'Kab. Buol': 'Buol',
        'Kab. Donggala': 'Donggala',
        'Kab. Morowali': 'Morowali',
        'Kab. Parigi Moutong': 'Parigi Moutong',
        'Kab. Poso': 'Poso',
        'Kab. Sigi': 'Sigi',
        'Kab. Tojo Una-una': 'Tojo Una-una',
        'Kab. Toli-toli': 'Tolitoli',
        'Toli-toli': 'Tolitoli',
        'Toli Toli': 'Tolitoli'
    }

    if 'kabupaten_kota' in df.columns:
        df['kab_clean'] = df['kabupaten_kota'].astype(str).str.strip().map(lambda x: KAB_NAME_CLEAN.get(x, x))
    else:
        df['kab_clean'] = '-'

    # ==========================================
    # 3. KALKULASI OVERDUE SOP & TAHUN
    # ==========================================
    df['durasi_clean'] = df['durasi'].apply(clean_durasi)
    df['tgl_mulai_dt'] = df['tgl_mulai'].apply(parse_date_flexible)
    
    today = pd.to_datetime(datetime.date.today())
    
    # Hitung tgl batas SOP
    df['tgl_batas_sop'] = df['tgl_mulai_dt'] + pd.to_timedelta(df['durasi_clean'], unit='D')
    
    # Filter berkas terlambat
    df_overdue = df[(today > df['tgl_batas_sop']) & (df['tgl_mulai_dt'].notna())].copy()

    # Format nomor/tahun bersih & buat kolom thn_num
    df_overdue['no_clean'] = df_overdue['nmr_berkas'].apply(fmt_no_thn)
    df_overdue['thn_clean'] = df_overdue['thn_berkas'].apply(fmt_no_thn)
    df_overdue['thn_num'] = df_overdue['thn_clean'].apply(clean_durasi)
    df_overdue['berkas_thn'] = df_overdue['no_clean'] + "/" + df_overdue['thn_clean']

    POSISI_TARGET = ["Kakan", "Kasi SP", "Kasi PHP", "Loket"]

    # ==========================================
    # 4. TAMPILAN CSS STROBO & CARD HIJAU
    # ==========================================
    st.markdown("""
    <style>
    .strobo-red-compact {
        background: linear-gradient(135deg, #ff3333 0%, #cc0000 100%);
        color: white;
        font-weight: 700;
        text-align: center;
        padding: 4px 8px;
        border-radius: 6px;
        box-shadow: 0 0 8px rgba(255, 0, 0, 0.6);
        animation: pulse-red 1.5s infinite;
        cursor: pointer;
        font-size: 0.78rem;
        line-height: 1.2;
    }
    @keyframes pulse-red {
        0% { box-shadow: 0 0 3px rgba(255, 0, 0, 0.4); }
        50% { box-shadow: 0 0 12px rgba(255, 0, 0, 0.9); }
        100% { box-shadow: 0 0 3px rgba(255, 0, 0, 0.4); }
    }
    .tuntas-green-compact {
        background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
        color: white;
        font-weight: 600;
        text-align: center;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        line-height: 1.2;
    }
    .table-hdr {
        font-weight: 700;
        text-align: center;
        padding: 4px;
        background-color: #e9ecef;
        border-radius: 4px;
        font-size: 0.80rem;
    }
    </style>
    """, unsafe_allow_html=True)

    def render_green_card(title, value, sub_text=""):
        card_html = f"""
        <div style="
            background: linear-gradient(135deg, #ffffff 0%, #f0fff4 100%);
            border-left: 5px solid #28a745;
            border-radius: 8px;
            padding: 8px 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            margin-top: 6px;
            margin-bottom: 4px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="color: #444444; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                {title}
            </div>
            <div style="color: #1e7e34; font-size: 1.15rem; font-weight: 700; margin-top: 1px; word-break: break-word;">
                {value}
            </div>
            {f'<div style="color: #666666; font-size: 0.68rem; margin-top: 1px;">{sub_text}</div>' if sub_text else ''}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    # ==========================================
    # 5. RENDER MATRIKS STROBO UTAMA
    # ==========================================
    list_kab = sorted(df['kab_clean'].dropna().unique().tolist())

    col_kab, col_p1, col_p2, col_p3, col_p4 = st.columns([2.2, 1.8, 1.8, 1.8, 1.8])
    with col_kab: st.markdown("<div class='table-hdr'>Kantor Pertanahan</div>", unsafe_allow_html=True)
    with col_p1: st.markdown("<div class='table-hdr'>Kakan</div>", unsafe_allow_html=True)
    with col_p2: st.markdown("<div class='table-hdr'>Kasi SP</div>", unsafe_allow_html=True)
    with col_p3: st.markdown("<div class='table-hdr'>Kasi PHP</div>", unsafe_allow_html=True)
    with col_p4: st.markdown("<div class='table-hdr'>Loket Penyerahan</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)

    for kab in list_kab:
        c_kab, c_p1, c_p2, c_p3, c_p4 = st.columns([2.2, 1.8, 1.8, 1.8, 1.8])
        
        with c_kab:
            st.markdown(f"<div style='font-size: 0.80rem; font-weight: 600; padding-top: 2px;'>📍 {kab}</div>", unsafe_allow_html=True)
            
        cols_pos = [c_p1, c_p2, c_p3, c_p4]
        
        for idx, pos in enumerate(POSISI_TARGET):
            with cols_pos[idx]:
                sub_df = df_overdue[
                    (df_overdue['kab_clean'] == kab) & 
                    (df_overdue['posisi_berkas'].astype(str).str.strip().str.contains(pos, case=False, na=False))
                ]
                
                jml_berkas = len(sub_df)
                
                if jml_berkas > 0:
                    tooltip_items = []
                    for _, r in sub_df.iterrows():
                        no_thn = r.get('berkas_thn', '-')
                        proc = str(r.get('nama_prosedur', '-'))
                        tooltip_items.append(f"• [{no_thn}] {proc}")
                        
                    tooltip_text = f"Kab: {kab}&#10;Posisi: {pos}&#10;Total: {jml_berkas} Berkas&#10;&#10;Rincian Prosedur:&#10;" + "&#10;".join(tooltip_items[:12])
                    if len(tooltip_items) > 12:
                        tooltip_text += f"&#10;...dan {len(tooltip_items)-12} berkas lainnya"

                    st.markdown(
                        f"<div class='strobo-red-compact' title='{tooltip_text}'>🚨 {jml_berkas} Berkas</div>", 
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("<div class='tuntas-green-compact'>✔ Tuntas</div>", unsafe_allow_html=True)
                    
        st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    # ==========================================
    # 6. GRAFIK REKAPITULASI POSISI BERKAS
    # ==========================================
    if not df_overdue.empty:
        df_g1 = df_overdue.groupby(['kab_clean', 'posisi_berkas']).agg(
            jml_berkas=('nmr_berkas', 'count'),
            list_berkas=('berkas_thn', lambda x: ", ".join(x.unique()[:6]))
        ).reset_index()

        pastel_colors = [
            '#779ECB', '#FFB347', '#C23B22', '#03C03C', '#B19CD9', 
            '#FFD1DC', '#AEC6CF', '#F49AC2', '#CB99C9', '#E6E6FA'
        ]

        fig_pos = px.bar(
            df_g1, x='kab_clean', y='jml_berkas', color='posisi_berkas',
            custom_data=df_g1[['posisi_berkas', 'list_berkas']],
            barmode='group',
            color_discrete_sequence=pastel_colors
        )
        
        fig_pos.update_traces(
            hovertemplate="<b>Kab/Kota: %{x}</b><br>Posisi: %{customdata[0]}<br>Jumlah: %{y} Berkas<br>Sampel No Berkas: %{customdata[1]}<extra></extra>",
            marker=dict(line=dict(width=1, color='#222222'))
        )
        
        fig_pos.update_layout(
            height=450,
            xaxis_title="",
            yaxis_title="",
            legend_title_text="",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=80, b=10),
            
            title=dict(
                text="Rekapitulasi Berkas Melebihi SOP per Posisi Berkas",
                font=dict(size=13, color="#2c3e50"),
                x=0.0,
                y=0.98,
                xanchor='left',
                yanchor='top'
            ),
            
            legend=dict(
                orientation="h", 
                yanchor="top", 
                y=1.08, 
                xanchor="left", 
                x=0.0,
                font=dict(size=8.5)
            ),
            yaxis=dict(gridcolor='#e0e0e0', tickfont=dict(size=9)),
            xaxis=dict(showgrid=False, tickfont=dict(size=8.5))
        )
        st.plotly_chart(fig_pos, use_container_width=True)

        # ==========================================
        # 7. CARD MODERN HIJAU BERKAS PER TAHUN
        # ==========================================
        b_17_26 = len(df_overdue[(df_overdue['thn_num'] >= 2017) & (df_overdue['thn_num'] <= 2026)])
        b_17_24 = len(df_overdue[(df_overdue['thn_num'] >= 2017) & (df_overdue['thn_num'] <= 2024)])
        b_25    = len(df_overdue[df_overdue['thn_num'] == 2025])
        b_26    = len(df_overdue[df_overdue['thn_num'] == 2026])

        col_c1, col_c2, col_c3, col_c4 = st.columns(4)

        with col_c1:
            render_green_card("Total Berkas (2017 - 2026)", f"{fmt_idr(b_17_26)} Berkas", "Akumulasi Berkas Melebihi SOP")

        with col_c2:
            render_green_card("Tahun 2017 - 2024", f"{fmt_idr(b_17_24)} Berkas", "Berkas Tunggakan Lama")

        with col_c3:
            render_green_card("Tahun 2025", f"{fmt_idr(b_25)} Berkas", "Berkas Tunggakan 2025")

        with col_c4:
            render_green_card("Tahun 2026", f"{fmt_idr(b_26)} Berkas", "Berkas Berjalan 2026")

        # ==========================================
        # 8. TABEL HTML MODERN DENGAN WRAP TEXT FULL
        # ==========================================
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 Rincian Berkas Melebihi Durasi SOP")

        df_table = df_overdue.copy()

        if 'kab_clean' in df_table.columns and 'thn_num' in df_table.columns:
            df_table = df_table.sort_values(by=['kab_clean', 'thn_num', 'no_clean'], ascending=[True, True, True])

        def clean_formula_text(df_source, col_name):
            if col_name not in df_source.columns:
                return pd.Series(['-'] * len(df_source))
            invalid_patterns = {'#n/a', 'nan', 'none', '', '#ref!', '#value!', '#name?', '#null!'}
            def transform_val(val):
                if pd.isna(val) or val is None:
                    return '-'
                s_str = str(val).strip()
                if not s_str or s_str.lower() in invalid_patterns:
                    return '-'
                # Escape karakter HTML agar aman
                return s_str.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return df_source[col_name].apply(transform_val)

        df_table['pemohon_clean'] = clean_formula_text(df_table, 'nama')
        df_table['kendala_clean'] = clean_formula_text(df_table, 'kendala')
        df_table['upaya_clean'] = clean_formula_text(df_table, 'upaya_penyelesaian')
        df_table['prosedur_clean'] = clean_formula_text(df_table, 'nama_prosedur')
        df_table['posisi_clean'] = clean_formula_text(df_table, 'posisi_berkas')

        # BENTUK BARIS TABEL DENGAN FORMATING TIGHT (TANPA INDENTASI SPASI DI AWAL BARIS)
        rows_html_list = []
        for idx, (_, row) in enumerate(df_table.iterrows(), start=1):
            r_html = (
                f"<tr>"
                f"<td style='text-align: center; font-weight: bold; width: 40px;'>{idx}</td>"
                f"<td style='width: 110px;'><b>{row['kab_clean']}</b></td>"
                f"<td style='width: 110px;'>{row['berkas_thn']}</td>"
                f"<td style='width: 140px;'>{row['pemohon_clean']}</td>"
                f"<td style='width: 180px;'>{row['prosedur_clean']}</td>"
                f"<td style='width: 120px;'>{row['posisi_clean']}</td>"
                f"<td style='width: 280px; color: #c0392b;'>{row['kendala_clean']}</td>"
                f"<td style='width: 280px; color: #27ae60;'>{row['upaya_clean']}</td>"
                f"</tr>"
            )
            rows_html_list.append(r_html)

        rows_html = "".join(rows_html_list)

        # HTML DAN CSS TANPA SPASI INDENTASI DI AWAL BARIS
        full_table_html = f"""<style>
.custom-table-container {{
    max-height: 480px;
    overflow-y: auto;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-top: 10px;
}}
.custom-table {{
    width: 100%;
    border-collapse: collapse;
    font-family: sans-serif;
    font-size: 0.82rem;
}}
.custom-table th {{
    position: sticky;
    top: 0;
    background-color: #f1f3f5;
    color: #333;
    font-weight: bold;
    padding: 8px 10px;
    text-align: left;
    border-bottom: 2px solid #dee2e6;
    z-index: 10;
}}
.custom-table td {{
    padding: 8px 10px;
    border-bottom: 1px solid #e9ecef;
    vertical-align: top;
    white-space: normal !important;
    word-wrap: break-word !important;
}}
.custom-table tr:hover {{
    background-color: #f8f9fa;
}}
</style>
<div class="custom-table-container">
<table class="custom-table">
<thead>
<tr>
<th style="text-align: center;">No</th>
<th>Satker</th>
<th>Nomor Berkas</th>
<th>Pemohon</th>
<th>Prosedur</th>
<th>Posisi Digital</th>
<th>Kendala / Hambatan</th>
<th>Upaya Penyelesaian</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>"""

        st.markdown(full_table_html, unsafe_allow_html=True)

    else:
        st.success("🎉 Seluruh berkas layanan pertanahan tepat waktu (SOP Tuntas).")

def render_pertanahan_elektronik(df_elektronik, df_progress=None, df_peringkat=None, selected_kab=None, selected_kec=None):
    st.title("💻 Data Elektronik")
    st.markdown("---")

    if df_elektronik.empty:
        st.warning("Data Elektronik (GID 1848496896) tidak ditemukan atau kosong.")
        return

    df = df_elektronik.copy()

    # ==========================================
    # 1. PARSER KETAT: BILANGAN CACAH & ERROR #N/A -> 0
    # ==========================================
    def parse_bilangan_cacah(val):
        """
        Mengonversi string/number dari Google Sheets menjadi Bilangan Cacah (Integer Murni).
        Mengubah #N/A, NaN, None, atau string kosong menjadi 0.
        """
        if pd.isna(val) or val is None:
            return 0
        s_val = str(val).strip()
        invalid_patterns = {'#n/a', 'nan', 'none', '', '#ref!', '#value!', '#name?', '#null!'}
        if s_val.lower() in invalid_patterns:
            return 0
        
        # Hapus simbol non-numerik dan titik pemisah ribuan Google Sheet
        s_val = s_val.replace('Rp', '').replace('%', '').replace('.', '').replace(',', '').strip()
        
        try:
            return int(round(float(s_val)))
        except ValueError:
            return 0

    def parse_luas_m2(val):
        """Membaca angka Luas murni dari Google Sheets sebagai M2 (Bilangan Cacah)."""
        return float(parse_bilangan_cacah(val))

    def fmt_idr(val):
        """Format bulat integer dengan titik ribuan (contoh: 1.362.086)"""
        return f"{int(round(val)):,}".replace(',', '.')

    def fmt_dec2(val):
        """Format desimal 2 digit di belakang koma (contoh: 246,73 atau 37,28%)"""
        parts = f"{val:,.2f}".split('.')
        return f"{parts[0].replace(',', '.')},{parts[1]}"

    # Salin & bersihkan kolom luas (M2) -> Bilangan Cacah M2
    luas_cols = ['luas_adm', 'luas_apl', 'luas_persil', 'luas_persil_valid', 'luas_persil_deliniasi', 'luas_kw456']
    for col in luas_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_luas_m2)
        else:
            df[col] = 0.0

    # Salin & bersihkan kolom jumlah berkas/unit -> Bilangan Cacah Murni
    int_cols = [
        'jumlah_persil', 'jumlah_kw456', 'jumlah_bt', 'bt_valid', 
        'jumlah_su', 'jumlah_suvalid', 'pra_suel', 'pra_btel', 'pra_sertel'
    ]
    for col in int_cols:
        if col in df.columns:
            df[col] = df[col].apply(parse_bilangan_cacah)
        else:
            df[col] = 0

    # Filter baris agar tidak menghitung baris rekapitulasi/total ganda
    if 'kabupaten_kota' in df.columns:
        df_clean = df[~df['kabupaten_kota'].astype(str).str.contains('Total|Jumlah|Sulawesi Tengah', case=False, na=False)].copy()
    else:
        df_clean = df.copy()

    # Total Akumulasi Murni M2 & Jumlah Berkas
    tot_adm_m2          = df_clean['luas_adm'].sum()
    tot_apl_m2          = df_clean['luas_apl'].sum()
    tot_persil_m2       = df_clean['luas_persil'].sum()
    tot_jml_persil      = df_clean['jumlah_persil'].sum()
    tot_persil_valid_m2 = df_clean['luas_persil_valid'].sum()
    tot_kw456           = df_clean['jumlah_kw456'].sum()
    tot_luas_kw456_m2   = df_clean['luas_kw456'].sum()
    tot_bt              = df_clean['jumlah_bt'].sum()
    tot_bt_valid        = df_clean['bt_valid'].sum()
    tot_su              = df_clean['jumlah_su'].sum()
    tot_pra_suel        = df_clean['pra_suel'].sum()
    tot_pra_btel        = df_clean['pra_btel'].sum()
    tot_pra_sertel      = df_clean['pra_sertel'].sum()

    # KONVERSI SATUAN LUAS: M2 -> Ha (dibagi 10.000)
    tot_adm_ha          = tot_adm_m2 / 10000.0
    tot_apl_ha          = tot_apl_m2 / 10000.0
    tot_persil_ha       = tot_persil_m2 / 10000.0
    tot_persil_valid_ha = tot_persil_valid_m2 / 10000.0
    tot_luas_kw456_ha   = tot_luas_kw456_m2 / 10000.0

    # ==========================================
    # 2. KALKULASI CARD 9 (GID 386436131) & CARD 10 (GID 880542789)
    # ==========================================
    val_prog_harian = 0
    sub_card9 = "Tidak ada perubahan data"

    rank_num_val = "-"
    sub_card10 = "0,00% dari 0 BT"

    # ------------------------------------------
    # CARD 9: PROGRESS HARIAN DESA (GID 386436131)
    # ------------------------------------------
    if df_progress is not None and not df_progress.empty:
        df_p = df_progress.copy()
        df_p.columns = [str(c).strip().lower() for c in df_p.columns]

        col_tgl  = next((c for c in df_p.columns if 'tgl' in c), 'tgl_data')
        col_kab  = next((c for c in df_p.columns if 'kab' in c), 'kabupaten_kota')
        col_kec  = next((c for c in df_p.columns if 'kec' in c), 'kecamatan')
        col_des  = next((c for c in df_p.columns if 'desa' in c or 'kelurahan' in c), 'desa_kelurahan')
        col_pdes = next((c for c in df_p.columns if 'prasertel_des' in c or 'prasertel_desa' in c), 'prasertel_desa')

        if col_tgl in df_p.columns and col_pdes in df_p.columns:
            # Ambil data yang memiliki tanggal
            df_p_valid = df_p[df_p[col_tgl].notna() & (df_p[col_tgl].astype(str).str.strip() != '')].copy()
            
            # Urutkan berdasarkan nilai tgl_data unik secara otomatis
            df_p_valid['tgl_dt'] = pd.to_datetime(df_p_valid[col_tgl], format='%d/%m/%Y', errors='coerce')
            if df_p_valid['tgl_dt'].isna().all():
                df_p_valid['tgl_dt'] = pd.to_datetime(df_p_valid[col_tgl], dayfirst=True, errors='coerce')

            list_tgl_dt = sorted(df_p_valid['tgl_dt'].dropna().unique())

            if len(list_tgl_dt) >= 2:
                tgl_new    = list_tgl_dt[-1]  # Tanggal Terbaru (misal 22/07/2026)
                tgl_latest = list_tgl_dt[-2]  # Tanggal Sebelumnya (misal 14/07/2026)

                df_new    = df_p_valid[df_p_valid['tgl_dt'] == tgl_new].copy()
                df_latest = df_p_valid[df_p_valid['tgl_dt'] == tgl_latest].copy()

                df_new['val_pdes']    = df_new[col_pdes].apply(parse_bilangan_cacah)
                df_latest['val_pdes'] = df_latest[col_pdes].apply(parse_bilangan_cacah)

                # Pengecekan Hirarki Filter Aktif
                is_kec_active = selected_kec and str(selected_kec).strip() not in ['', 'Semua', 'All', 'None', 'Semua Kecamatan']
                is_kab_active = selected_kab and str(selected_kab).strip() not in ['', 'Semua', 'All', 'None', 'Semua Kabupaten/Kota', 'Semua Kab/Kota']

                if is_kec_active:
                    group_keys = [k for k in [col_kab, col_kec, col_des] if k in df_p_valid.columns]
                    entity_label = "Desa/Kelurahan"
                elif is_kab_active:
                    group_keys = [k for k in [col_kab, col_kec] if k in df_p_valid.columns]
                    entity_label = "Kecamatan"
                else:
                    group_keys = [k for k in [col_kab] if k in df_p_valid.columns]
                    entity_label = "Kabupaten/Kota"

                grp_new    = df_new.groupby(group_keys)['val_pdes'].sum().reset_index()
                grp_latest = df_latest.groupby(group_keys)['val_pdes'].sum().reset_index()

                m_grp = pd.merge(grp_new, grp_latest, on=group_keys, suffixes=('_new', '_latest'))
                m_grp['diff'] = m_grp['val_pdes_new'] - m_grp['val_pdes_latest']

                df_changed = m_grp[m_grp['diff'] > 0]
                val_prog_harian = df_changed['diff'].sum()
                jml_entity_progres = len(df_changed)

                if jml_entity_progres > 0:
                    sub_card9 = f"{jml_entity_progres} {entity_label} mengalami perubahan"
                else:
                    sub_card9 = "Tidak ada perubahan data"
            elif len(list_tgl_dt) == 1:
                sub_card9 = "Data H-1 belum tersedia"

    # ==========================================
    # CARD 10: PERINGKAT NASIONAL (GID 880542789)
    # ==========================================
    rank_num_val = "-"
    sub_card10 = "0,00% dari 0 BT"

    if df_peringkat is not None and not df_peringkat.empty:
        df_rank = df_peringkat.copy()
        # Bersihkan nama kolom dari spasi dan ubah ke huruf kecil
        df_rank.columns = [str(c).strip().lower() for c in df_rank.columns]

        # Cari kolom secara fleksibel
        col_prov = next((c for c in df_rank.columns if 'prov' in c), 'provinsi')
        col_rank = next((c for c in df_rank.columns if 'ringkat' in c), 'peringkat')
        col_pnas = next((c for c in df_rank.columns if 'prasertel' in c), 'prasertel_nasional')
        col_bnas = next((c for c in df_rank.columns if 'btvalid' in c), 'btvalid_nasional')

        if col_prov in df_rank.columns:
            # Cari baris yang mengandung Sulteng / Sulawesi Tengah
            sulteng_df = df_rank[df_rank[col_prov].astype(str).str.contains('sulteng|sulawesi tengah', case=False, na=False)]

            if not sulteng_df.empty:
                row_s = sulteng_df.iloc[0]

                # 1. Ambil Angka Peringkat secara dinamis dari sheet
                if col_rank in sulteng_df.columns and pd.notna(row_s[col_rank]):
                    raw_r = str(row_s[col_rank]).strip()
                    if raw_r and raw_r.lower() != 'nan':
                        rank_num_val = raw_r.replace('.0', '')

                # 2. Ambil prasertel_nasional & btvalid_nasional dari sheet
                p_nas_val = parse_bilangan_cacah(row_s.get(col_pnas, 0))
                b_nas_val = parse_bilangan_cacah(row_s.get(col_bnas, 0))

                # 3. Hitung persentase dinamis: (prasertel_nasional / btvalid_nasional) * 100
                pct_nas = (p_nas_val / b_nas_val * 100.0) if b_nas_val > 0 else 0.0

                # 4. Format tampilan Keterangan Bawah
                sub_card10 = f"{fmt_dec2(pct_nas)}% dari {fmt_idr(b_nas_val)} BT"

    # ==========================================
    # 3. CSS COMPONENT CARD (ORANGE & BLUE)
    # ==========================================
    st.markdown("""
    <style>
    /* Style Card Standar (Orange) */
    .orange-card-box {
        background: linear-gradient(135deg, #ffffff 0%, #fff8f0 100%);
        border: 2px solid #f39c12;
        border-radius: 12px;
        padding: 10px 12px;
        box-shadow: 0 4px 10px rgba(243, 156, 18, 0.12);
        height: 104px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .orange-card-title {
        color: #d35400;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .orange-card-value {
        color: #e67e22;
        font-size: 1.25rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .orange-card-sub {
        color: #7f8c8d;
        font-size: 0.68rem;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* Style Card Khusus Card 9 & Card 10 (Blue #0451c9) */
    .blue-card-box {
        background: linear-gradient(135deg, #ffffff 0%, #f0f5ff 100%);
        border: 2px solid #0451c9;
        border-radius: 12px;
        padding: 10px 12px;
        box-shadow: 0 4px 10px rgba(4, 81, 201, 0.12);
        height: 104px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        margin-bottom: 12px;
    }
    .blue-card-title {
        color: #0451c9;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .blue-card-value {
        color: #0451c9;
        font-size: 1.25rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .blue-card-sub {
        color: #5c7299;
        font-size: 0.68rem;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .chart-container-orange {
        background-color: #ffffff;
        border: 2px solid #f39c12;
        border-radius: 14px;
        padding: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(243, 156, 18, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

    def render_orange_card(title, value_str, sub_text=""):
        html = f"""
        <div class="orange-card-box">
            <div class="orange-card-title" title="{title}">{title}</div>
            <div class="orange-card-value">{value_str}</div>
            <div class="orange-card-sub" title="{sub_text}">{sub_text}</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    def render_blue_card(title, value_str, sub_text=""):
        html = f"""
        <div class="blue-card-box">
            <div class="blue-card-title" title="{title}">{title}</div>
            <div class="blue-card-value">{value_str}</div>
            <div class="blue-card-sub" title="{sub_text}">{sub_text}</div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    # ==========================================
    # 4. RENDER GRID 10 CARDS
    # ==========================================
    # BARIS 1 (CARD 1 - 5)
    r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)

    with r1_c1:
        pct_apl = (tot_apl_m2 / tot_adm_m2 * 100.0) if tot_adm_m2 > 0 else 0.0
        render_orange_card(
            "Luas APL", 
            f"{fmt_dec2(pct_apl)}%", 
            f"Luas: {fmt_dec2(tot_apl_ha)} Ha dari Adm ({fmt_dec2(tot_adm_ha)} Ha)"
        )

    with r1_c2:
        pct_persil = (tot_persil_m2 / tot_apl_m2 * 100.0) if tot_apl_m2 > 0 else 0.0
        render_orange_card(
            "Luas Persil", 
            f"{fmt_dec2(pct_persil)}%", 
            f"Luas: {fmt_dec2(tot_persil_ha)} Ha | {fmt_idr(tot_jml_persil)} Persil"
        )

    with r1_c3:
        pct_persil_valid = (tot_persil_valid_m2 / tot_persil_m2 * 100.0) if tot_persil_m2 > 0 else 0.0
        render_orange_card(
            "Luas Persil Valid", 
            f"{fmt_dec2(pct_persil_valid)}%", 
            f"Luas: {fmt_dec2(tot_persil_valid_ha)} Ha dari Persil"
        )

    with r1_c4:
        render_orange_card(
            "Jumlah KW456", 
            f"{fmt_idr(tot_kw456)} Bidang", 
            f"Luas: {fmt_dec2(tot_luas_kw456_ha)} Ha | Total: {fmt_idr(tot_bt)} BT"
        )

    with r1_c5:
        pct_bt_valid = (tot_bt_valid / tot_bt * 100.0) if tot_bt > 0 else 0.0
        render_orange_card(
            "Jumlah BT Valid", 
            f"{fmt_idr(tot_bt_valid)} BT", 
            f"Total: {fmt_idr(tot_bt)} BT | {fmt_dec2(pct_bt_valid)}% Valid"
        )

    # BARIS 2 (CARD 6 - 10)
    r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)

    with r2_c1:
        pct_pra_suel = (tot_pra_suel / tot_su * 100.0) if tot_su > 0 else 0.0
        render_orange_card(
            "% PRA-SUEL", 
            f"{fmt_dec2(pct_pra_suel)}%", 
            f"{fmt_idr(tot_pra_suel)} dari {fmt_idr(tot_su)} SU"
        )

    with r2_c2:
        pct_pra_btel = (tot_pra_btel / tot_bt_valid * 100.0) if tot_bt_valid > 0 else 0.0
        render_orange_card(
            "% PRA-BTEL", 
            f"{fmt_dec2(pct_pra_btel)}%", 
            f"{fmt_idr(tot_pra_btel)} dari {fmt_idr(tot_bt_valid)} BT Valid"
        )

    with r2_c3:
        pct_pra_sertel = (tot_pra_sertel / tot_bt * 100.0) if tot_bt > 0 else 0.0
        render_orange_card(
            "% PRA-SERTEL", 
            f"{fmt_dec2(pct_pra_sertel)}%", 
            f"{fmt_idr(tot_pra_sertel)} dari {fmt_idr(tot_bt)} BT"
        )

    with r2_c4:
        # CARD 9 MENGGUNAKAN BINGKAI & TEKS BIRU #0451c9
        render_blue_card(
            "Progress Harian", 
            f"+{fmt_idr(val_prog_harian)} Sertel", 
            sub_card9
        )

    with r2_c5:
        # CARD 10 MENGGUNAKAN BINGKAI & TEKS BIRU #0451c9
        render_blue_card(
            "Peringkat Nasional", 
            f"#{rank_num_val}", 
            sub_card10
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 5. GRAFIK KONTEN (BINGKAI AKSEN ORANGE)
    # ==========================================
    KAB_MAP = {
        'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
        'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
        'Poso': 'PS', 'Tojo Una-una': 'TU', 'Toli-toli': 'TL', 'Toli Toli': 'TL',
        'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL', 'Kota Palu': 'PL', 
        'Sigi': 'SG', 'Sulawesi Tengah': 'ST'
    }
    if 'kabupaten_kota' in df_clean.columns:
        df_clean['kab_singkat'] = df_clean['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x))
    else:
        df_clean['kab_singkat'] = '-'

    num_cols_all = luas_cols + int_cols
    df_kab = df_clean.groupby('kab_singkat')[num_cols_all].sum().reset_index()

    # GRAFIK 1: SURAT UKUR ELEKTRONIK
    st.markdown('<div class="chart-container-orange">', unsafe_allow_html=True)
    df_su = df_kab.melt(
        id_vars=['kab_singkat'], 
        value_vars=['jumlah_su', 'pra_suel'],
        var_name='Indikator', value_name='Jumlah'
    )
    df_su['Indikator'] = df_su['Indikator'].map({'jumlah_su': 'Jumlah SU', 'pra_suel': 'Pra-SUEL'})

    fig_su = px.bar(
        df_su, x='kab_singkat', y='Jumlah', color='Indikator',
        barmode='group', title="📊 Grafik Surat Ukur Elektronik (SU vs Pra-SUEL)",
        color_discrete_sequence=['#e67e22', '#f39c12']
    )
    fig_su.update_traces(
        hovertemplate="<b>Kab/Kota: %{x}</b><br>%{fullData.name}: %{y:,.0f}<extra></extra>",
        marker=dict(line=dict(width=1, color='#111111'))
    )
    fig_su.update_layout(
        height=260, xaxis_title="", yaxis_title="",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor='#f2f2f2')
    )
    st.plotly_chart(fig_su, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # GRAFIK 2: BUKU TANAH ELEKTRONIK
    st.markdown('<div class="chart-container-orange">', unsafe_allow_html=True)
    df_bt = df_kab.melt(
        id_vars=['kab_singkat'], 
        value_vars=['bt_valid', 'pra_btel', 'pra_sertel'],
        var_name='Indikator', value_name='Jumlah'
    )
    df_bt['Indikator'] = df_bt['Indikator'].map({
        'bt_valid': 'BT Valid', 
        'pra_btel': 'Pra-BTEL', 
        'pra_sertel': 'Pra-Sertel'
    })

    fig_bt = px.bar(
        df_bt, x='kab_singkat', y='Jumlah', color='Indikator',
        barmode='group', title="📘 Grafik Buku Tanah Elektronik (BT Valid, Pra-BTEL & Pra-Sertel)",
        color_discrete_sequence=['#d35400', '#e67e22', '#f39c12']
    )
    fig_bt.update_traces(
        hovertemplate="<b>Kab/Kota: %{x}</b><br>%{fullData.name}: %{y:,.0f}<extra></extra>",
        marker=dict(line=dict(width=1, color='#111111'))
    )
    fig_bt.update_layout(
        height=260, xaxis_title="", yaxis_title="",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=35, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor='#f2f2f2')
    )
    st.plotly_chart(fig_bt, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

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
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()  # Hapus cache Streamlit
        st.rerun()
    
    st.header("🗂️ Menu Utama")
    
    # TAMBAHKAN key="menu_pilihan" AGAR PILIHAN TERSIMPAN DI SESSION STATE
    menu_pilihan = st.radio(
        "Pilih Halaman:",
        [
            "🏛️ Profil & Anggaran",
            "🎯 PSN 2026",
            "💼 Layanan Pertanahan",
            "⚡ Data Elektronik"
        ],
        key="menu_pilihan"  # <--- Kunci utama agar menu tidak ter-reset
    )
    
    st.markdown("---")
    st.header("📊 Grafik Rekapitulasi (Sulteng)")

    # Kamus untuk mempersingkat nama kabupaten
    KAB_MAP = {
        'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
        'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
        'Poso': 'PS', 'Tojo Una-una': 'TU', 'Toli-toli': 'TL',
        'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL',
        'Sigi': 'SG', 'Sulawesi Tengah': 'ST'
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
        df_sdm_rekap = df_sdm_singkat.groupby(['kab_singkat', 'kategori_asn']).size().reset_index(name='jumlah')
        df_sdm_pivot = df_sdm_rekap.pivot(index='kab_singkat', columns='kategori_asn', values='jumlah').fillna(0).astype(int)
        df_sdm_total = df_sdm_singkat.groupby('kab_singkat').size().reset_index(name='total_all')
        df_sdm_rekap = df_sdm_rekap.merge(df_sdm_pivot, on='kab_singkat').merge(df_sdm_total, on='kab_singkat')
        df_sdm_rekap = df_sdm_rekap.sort_values(by='total_all', ascending=False)
        
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
            showlegend=True, legend_title_text='', height=310,
            xaxis_title="", yaxis_title="",
            xaxis={'categoryorder':'total descending'},
            margin=dict(l=10, r=10, t=35, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_sdm, use_container_width=True)


    # ==========================================
    # 2. GRAFIK BARU: % Realisasi Anggaran (GID 1168898330)
    # ==========================================
    if not df_sdm_singkat.empty and 'target_dipa' in df_sdm_singkat.columns and 'realisasi_dipa' in df_sdm_singkat.columns:
        # Bersihkan nilai numerik
        df_anggaran = df_sdm_singkat.copy()
        
        def clean_num_local(val):
            if pd.isna(val): return 0.0
            if isinstance(val, (int, float)): return float(val)
            clean_str = str(val).replace('.', '').replace(',', '').replace('Rp', '').strip()
            try: return float(clean_str)
            except: return 0.0

        df_anggaran['target_clean'] = df_anggaran['target_dipa'].apply(clean_num_local)
        df_anggaran['realisasi_clean'] = df_anggaran['realisasi_dipa'].apply(clean_num_local)
        
        # Agregasi total per kabupaten
        df_ang_rekap = df_anggaran.groupby('kab_singkat')[['target_clean', 'realisasi_clean']].sum().reset_index()
        df_ang_rekap['persen_realisasi'] = (df_ang_rekap['realisasi_clean'] / df_ang_rekap['target_clean'].replace(0, 1)) * 100
        
        # Format teks Rupiah & Persen untuk hover
        df_ang_rekap['target_fmt'] = df_ang_rekap['target_clean'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
        df_ang_rekap['realisasi_fmt'] = df_ang_rekap['realisasi_clean'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
        df_ang_rekap['persen_fmt'] = df_ang_rekap['persen_realisasi'].apply(lambda x: f"{x:.2f}".replace('.', ','))
        
        # Urutkan dari persentase realisasi tertinggi ke terendah
        df_ang_rekap = df_ang_rekap.sort_values(by='persen_realisasi', ascending=False)

        fig_anggaran = px.bar(
            df_ang_rekap, x='kab_singkat', y='persen_realisasi',
            title="% Realisasi Anggaran",
            custom_data=df_ang_rekap[['target_fmt', 'realisasi_fmt', 'persen_fmt']]
        )
        fig_anggaran.update_traces(
            hovertemplate="<b>Kab/Kota: %{x}</b><br>Rp Target: Rp %{customdata[0]}<br>Rp Realisasi: Rp %{customdata[1]}<br>% Realisasi: %{customdata[2]}%<extra></extra>",
            marker_color='#17BECF'
        )
        fig_anggaran.update_layout(
            showlegend=False, height=250,
            xaxis_title="", yaxis_title="",
            xaxis={'categoryorder':'total descending'},
            margin=dict(l=10, r=10, t=35, b=10)
        )
        st.plotly_chart(fig_anggaran, use_container_width=True)


    # ==========================================
    # 3. GRAFIK: Berkas Lewat SOP (Terurut)
    # ==========================================
    if not df_layanan_singkat.empty and 'nmr_berkas' in df_layanan_singkat.columns:
        df_layanan_total = df_layanan_singkat.groupby('kab_singkat')['nmr_berkas'].count().reset_index(name='total_berkas')
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
            margin=dict(l=10, r=10, t=35, b=10)
        )
        st.plotly_chart(fig_layanan, use_container_width=True)

    # ==========================================
    # 4. GRAFIK: Persentase Prasertel (Terurut)
    # ==========================================
    if not df_elek_singkat.empty and 'pra_sertel' in df_elek_singkat.columns and 'bt_valid' in df_elek_singkat.columns:
        df_elek_rekap = df_elek_singkat.groupby('kab_singkat')[['pra_sertel', 'bt_valid']].sum().reset_index()        
        
        # 1. Konversi Tipe Data Numerik dengan Aman
        s_pra_sertel = pd.to_numeric(df_elek_rekap['pra_sertel'], errors='coerce').fillna(0)
        s_bt_valid   = pd.to_numeric(df_elek_rekap['bt_valid'], errors='coerce').fillna(0)
        
        # 2. Kalkulasi Persentase (Mencegah Pembagian dengan Nol)
        df_elek_rekap['Persentase'] = (s_pra_sertel / s_bt_valid.replace(0, 1)) * 100
        df_elek_rekap = df_elek_rekap.sort_values(by='Persentase', ascending=False)
        
        # 3. Render Bar Chart Plotly
        fig_elek = px.bar(
            df_elek_rekap, x='kab_singkat', y='Persentase',
            title="Persentase Prasertel",
            custom_data=df_elek_rekap[['pra_sertel', 'bt_valid']]
        )
        fig_elek.update_traces(
            hovertemplate="<b>Kab/Kota: %{x}</b><br>Persentase: %{y:.2f}%<br>Jumlah Prasertel: %{customdata[0]:,.0f}<br>Jumlah BT Valid: %{customdata[1]:,.0f}<extra></extra>",
            marker_color='#00CC96'
        )
        fig_elek.update_layout(
            showlegend=False, 
            height=250,
            xaxis_title="", 
            yaxis_title="",
            xaxis={'categoryorder': 'total descending'},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=35, b=10)
        )
        st.plotly_chart(fig_elek, use_container_width=True)

# -----------------------------------------------------------------------------
# 4. PROSES FILTERING DATA
# -----------------------------------------------------------------------------
# Salinan dataframe untuk difilter berdasarkan sidebar
df_f_layanan = df_layanan.copy() if 'df_layanan' in locals() and df_layanan is not None else pd.DataFrame()
df_f_elektronik = df_elektronik.copy() if 'df_elektronik' in locals() and df_elektronik is not None else pd.DataFrame()
df_f_sdm = df_sdm.copy() if 'df_sdm' in locals() and df_sdm is not None else pd.DataFrame()
df_f_psn = df_psn.copy() if 'df_psn' in locals() and df_psn is not None else pd.DataFrame()

# BUAT DENGAN AMAN df_f_progress DARI df_progress (GID 386436131)
if 'df_progress' in locals() and df_progress is not None and not df_progress.empty:
    df_f_progress = df_progress.copy()
elif 'df_progress_raw' in locals() and df_progress_raw is not None and not df_progress_raw.empty:
    df_f_progress = df_progress_raw.copy()
else:
    df_f_progress = pd.DataFrame()

# Filter berdasarkan Kabupaten/Kota
if selected_kab != "Semua Kabupaten/Kota":
    if not df_f_layanan.empty and 'kabupaten_kota' in df_f_layanan.columns:
        df_f_layanan = df_f_layanan[df_f_layanan['kabupaten_kota'] == selected_kab]
    if not df_f_elektronik.empty and 'kabupaten_kota' in df_f_elektronik.columns:
        df_f_elektronik = df_f_elektronik[df_f_elektronik['kabupaten_kota'] == selected_kab]
    if not df_f_sdm.empty and 'kabupaten_kota' in df_f_sdm.columns:
        df_f_sdm = df_f_sdm[df_f_sdm['kabupaten_kota'] == selected_kab]
    if not df_f_psn.empty and 'kabupaten_kota' in df_f_psn.columns:
        df_f_psn = df_f_psn[df_f_psn['kabupaten_kota'] == selected_kab]
    if not df_f_progress.empty and 'kabupaten_kota' in df_f_progress.columns:
        df_f_progress = df_f_progress[df_f_progress['kabupaten_kota'] == selected_kab]

# Filter berdasarkan Kecamatan
if selected_kec != "Semua Kecamatan":
    if not df_f_elektronik.empty and 'kecamatan' in df_f_elektronik.columns:
        df_f_elektronik = df_f_elektronik[df_f_elektronik['kecamatan'] == selected_kec]
    if not df_f_progress.empty and 'kecamatan' in df_f_progress.columns:
        df_f_progress = df_f_progress[df_f_progress['kecamatan'] == selected_kec]

# -----------------------------------------------------------------------------
# 5. ROUTING HALAMAN UTAMA
# -----------------------------------------------------------------------------
if menu_pilihan == "🏛️ Profil & Anggaran":    
    render_profil_anggaran(df_f_sdm)
elif menu_pilihan == "🎯 PSN 2026":
    render_psn_2026(df_f_psn)
elif menu_pilihan == "💼 Layanan Pertanahan":
    render_layanan_pertanahan(df_f_layanan)
elif menu_pilihan == "⚡ Data Elektronik":
    # Ambil dataframe peringkat (GID 880542789) dengan aman
    df_peringkat_data = pd.DataFrame()
    if 'df_peringkat' in locals() and df_peringkat is not None:
        df_peringkat_data = df_peringkat
    elif 'df_peringkat_raw' in locals() and df_peringkat_raw is not None:
        df_peringkat_data = df_peringkat_raw

    render_pertanahan_elektronik(
        df_f_elektronik, 
        df_f_progress, 
        df_peringkat_data,
        selected_kab=selected_kab, 
        selected_kec=selected_kec
    )
