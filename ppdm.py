import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

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
    # FUNGSI PEMBANTU PERSIAPAN DATA & FORMAT
    # ==========================================
    KAB_MAP = {
        'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
        'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
        'Poso': 'PS', 'Tojo Una-una': 'TU', 'Toli-toli': 'TL', 'Toli Toli': 'TL',
        'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL', 'Kota Palu': 'PL', 
        'Sigi': 'SG', 'Sulawesi Tengah': 'ST', 'Provinsi Sulawesi Tengah': 'ST'
    }

    def clean_num(val):
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
        return f"{val:,.0f}".replace(',', '.')

    def fmt_decimal(val):
        parts = f"{val:,.2f}".split('.')
        integer_part = parts[0].replace(',', '.')
        decimal_part = parts[1]
        return f"{integer_part},{decimal_part}"

    # Salin data & tambahkan singkatan kabupaten
    df = df_filtered_psn.copy()
    if 'kabupaten_kota' in df.columns:
        df['kab_singkat'] = df['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x))
    else:
        df['kab_singkat'] = '-'

    # Bersihkan seluruh kolom numerik
    cols_to_clean = [
        'target_pbt', 'realisasi_baru', 'realisasi_k4', 'realisasi_repo',
        'target_shat', 'puldadis', 'berkas', 'k1', 'diserahkan',
        'target_redis', 'pos_redis', 'sk_redis', 'sertipikat_redis',
        'target_lintor', 'lintor_su', 'lintor_sk', 'lintor_sertipikat', 'lintor_serah'
    ]
    
    target_cols = ['target_pbt', 'target_shat', 'target_redis', 'target_lintor']
    
    for col in cols_to_clean:
        if col in df.columns:
            if col in target_cols:
                def fix_target_num(x):
                    if pd.isna(x): return 0.0
                    if isinstance(x, float) and 0 < x < 10:
                        return round(x * 1000)
                    return clean_num(x)
                df[col] = df[col].apply(fix_target_num)
            else:
                df[col] = df[col].apply(clean_num)
        else:
            df[col] = 0.0

    # Agregasi data per kabupaten
    df_rekap = df.groupby('kab_singkat')[cols_to_clean].sum().reset_index()

    # Fungsi pembuat grafik dengan dukungan mode stacked / group
    def create_psn_chart(title, df_data, target_col, metrics_dict, color_sequence, unit="Bdg", is_stacked=False):
        df_valid = df_data[df_data[target_col] > 0].copy()
        
        if df_valid.empty:
            fig_empty = px.bar(title=f"{title} (Tidak ada target aktif)")
            fig_empty.update_layout(
                height=230, 
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

        # Mode Tumpuk (relative) untuk PBT, Mode Grouped untuk grafik lainnya
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
            marker=dict(
                line=dict(width=1.2, color='#111111')
            )
        )

        fig.update_layout(
            height=230, # Diperkecil agar muat 1 layar laptop
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
    # LAYOUT GRID 2x2 DENGAN BINGKAI (#dbdbdb)
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

    # 1. GRAFIK 1: Realisasi PBT (Stacked Column: Realisasi Baru -> K4 -> Repo)
    with row1_col1:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        # Urutan dict menentukan urutan tumpukan dari bawah ke atas
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
    # 1. FUNGSI PEMBANTU FORMAT BERKAS & TANGGAL
    # ==========================================
    def clean_num(val):
        if pd.isna(val): return 0
        try: return int(float(str(val).replace('.', '').replace(',', '.').strip()))
        except: return 0

    def fmt_no_thn(val):
        """Menghilangkan .0 pada nomor atau tahun berkas"""
        if pd.isna(val): return "-"
        s_val = str(val).strip()
        if s_val.endswith('.0'):
            return s_val[:-2]
        return s_val

    df['durasi_clean'] = df['durasi'].apply(clean_num)
    df['tgl_mulai_dt'] = pd.to_datetime(df['tgl_mulai'], errors='coerce')
    
    # Tanggal hari ini
    today = pd.to_datetime(datetime.date.today())
    
    # Hitung batas SOP: tgl_mulai + durasi (hari)
    df['tgl_batas_sop'] = df['tgl_mulai_dt'] + pd.to_timedelta(df['durasi_clean'], unit='D')
    
    # Filter berkas yang MELEBIHI DURASI SOP
    df_overdue = df[today > df['tgl_batas_sop']].copy()

    # Format nomor dan tahun berkas bersih tanpa desimal
    df_overdue['no_clean'] = df_overdue['nmr_berkas'].apply(fmt_no_thn)
    df_overdue['thn_clean'] = df_overdue['thn_berkas'].apply(fmt_no_thn)
    df_overdue['berkas_thn'] = df_overdue['no_clean'] + "/" + df_overdue['thn_clean']

    POSISI_TARGET = ["Kakan", "Kasi SP", "Kasi PHP", "Loket"]

    # ==========================================
    # 2. CSS STROBO KOMPAK & DESAIN PADAT
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

    # ==========================================
    # 3. MATRIKS STROBO (RINGKAS & COMPACT)
    # ==========================================
    list_kab = sorted(df['kabupaten_kota'].dropna().unique().tolist())

    # Header Tabel
    col_kab, col_p1, col_p2, col_p3, col_p4 = st.columns([2.2, 1.8, 1.8, 1.8, 1.8])
    with col_kab: st.markdown("<div class='table-hdr'>Kantor Pertanahan</div>", unsafe_allow_html=True)
    with col_p1: st.markdown("<div class='table-hdr'>Kakan</div>", unsafe_allow_html=True)
    with col_p2: st.markdown("<div class='table-hdr'>Kasi SP</div>", unsafe_allow_html=True)
    with col_p3: st.markdown("<div class='table-hdr'>Kasi PHP</div>", unsafe_allow_html=True)
    with col_p4: st.markdown("<div class='table-hdr'>Loket Penyerahan</div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 4px;'></div>", unsafe_allow_html=True)

    # Render Baris Strobo
    for kab in list_kab:
        c_kab, c_p1, c_p2, c_p3, c_p4 = st.columns([2.2, 1.8, 1.8, 1.8, 1.8])
        
        with c_kab:
            st.markdown(f"<div style='font-size: 0.80rem; font-weight: 600; padding-top: 2px;'>📍 {kab}</div>", unsafe_allow_html=True)
            
        cols_pos = [c_p1, c_p2, c_p3, c_p4]
        
        for idx, pos in enumerate(POSISI_TARGET):
            with cols_pos[idx]:
                # Pencarian posisi berkas yang presisi dan fleksibel
                sub_df = df_overdue[
                    (df_overdue['kabupaten_kota'] == kab) & 
                    (df_overdue['posisi_berkas'].astype(str).str.contains(pos, case=False, na=False))
                ]
                
                jml_berkas = len(sub_df)
                
                if jml_berkas > 0:
                    # Susun rincian tooltip tanpa angka .0
                    tooltip_items = []
                    for _, r in sub_df.iterrows():
                        no_thn = r.get('berkas_thn', '-')
                        proc = str(r.get('nama_prosedur', '-'))
                        tooltip_items.append(f"• [{no_thn}] {proc}")
                        
                    tooltip_text = f"Kab: {kab}&#10;Posisi: {pos}&#10;Total: {jml_berkas} Berkas&#10;&#10;Rincian Prosedur:&#10;" + "&#10;".join(tooltip_items[:10])
                    if len(tooltip_items) > 10:
                        tooltip_text += f"&#10;...dan {len(tooltip_items)-10} berkas lainnya"

                    st.markdown(
                        f"<div class='strobo-red-compact' title='{tooltip_text}'>🚨 {jml_berkas} Berkas</div>", 
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("<div class='tuntas-green-compact'>✔ Tuntas</div>", unsafe_allow_html=True)
                    
        st.markdown("<div style='margin-bottom: 2px;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    # ==========================================
    # 4. GRAFIK TUNGGAL UTAMA (RINGKAS)
    # ==========================================
    if not df_overdue.empty:
        df_g1 = df_overdue.groupby(['kabupaten_kota', 'posisi_berkas']).agg(
            jml_berkas=('nmr_berkas', 'count'),
            list_berkas=('berkas_thn', lambda x: ", ".join(x.unique()[:6]))
        ).reset_index()

        fig_pos = px.bar(
            df_g1, x='kabupaten_kota', y='jml_berkas', color='posisi_berkas',
            title="Rekapitulasi Berkas Melebihi SOP per Posisi Berkas",
            custom_data=df_g1[['posisi_berkas', 'list_berkas']],
            barmode='group',
            color_discrete_sequence=['#FF4136', '#FF851B', '#FFDC00', '#2ECC40']
        )
        
        fig_pos.update_traces(
            hovertemplate="<b>Kab/Kota: %{x}</b><br>Posisi: %{customdata[0]}<br>Jumlah: %{y} Berkas<br>Sampel No Berkas: %{customdata[1]}<extra></extra>",
            marker=dict(line=dict(width=1, color='#111111'))
        )
        
        fig_pos.update_layout(
            height=200, # Diperkecil agar muat penuh dalam 1 layar laptop
            xaxis_title="",
            yaxis_title="",
            legend_title_text="",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=5, r=5, t=28, b=5),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
            title=dict(font=dict(size=12)),
            yaxis=dict(gridcolor='#e0e0e0', tickfont=dict(size=8)),
            xaxis=dict(showgrid=False, tickfont=dict(size=8))
        )
        st.plotly_chart(fig_pos, use_container_width=True)
    else:
        st.success("🎉 Seluruh berkas layanan pertanahan tepat waktu (SOP Tuntas).")


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
        df_elek_rekap['Persentase'] = (df_elek_rekap['pra_sertel'] / df_elek_rekap['bt_valid'].replace(0, 1)) * 100
        df_elek_rekap = df_elek_rekap.sort_values(by='Persentase', ascending=False)
        
        fig_elek = px.bar(
            df_elek_rekap, x='kab_singkat', y='Persentase',
            title="Persentase Prasertel",
            custom_data=df_elek_rekap[['pra_sertel', 'bt_valid']]
        )
        fig_elek.update_traces(
            hovertemplate="<b>Kab/Kota: %{x}</b><br>Persentase: %{y:.2f}%<br>Jumlah Prasertel: %{customdata[0]}<br>Jumlah BT Valid: %{customdata[1]}<extra></extra>",
            marker_color='#00CC96'
        )
        fig_elek.update_layout(
            showlegend=False, height=250,
            xaxis_title="", yaxis_title="",
            xaxis={'categoryorder':'total descending'},
            margin=dict(l=10, r=10, t=35, b=10)
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
