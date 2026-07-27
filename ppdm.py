import re
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

# -----------------------------------------------------------------------------
# 1. KONFIGURASI HALAMAN
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Pertanahan Sulteng 2026",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. KONEKSI DATA (MENGAMBIL DARI STREAMLIT SECRETS)
# -----------------------------------------------------------------------------
USERS_DB = st.secrets.get("users", {})
SHEET_ID = st.secrets.get("gsheet_id", "")
GSHEET_WEBAPP_URL = st.secrets.get("gsheet_webapp_url", "")

@st.cache_data(ttl=3600)  # Cache data selama 1 jam
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:        
        return pd.read_csv(url, dtype=str)
    except Exception as e:
        st.error(f"Gagal memuat data GID {gid}: {e}")
        return pd.DataFrame()

# Memuat data utama di awal
df_layanan = load_data("1447858691")
df_elektronik = load_data("1848496896")
df_sdm = load_data("1168898330")
df_psn = load_data("193371600")
df_progress_raw = load_data("386436131")  # Data Progress Harian
df_peringkat_raw = load_data("880542789")
df_isu_raw = load_data("1699480367")

# -----------------------------------------------------------------------------
# 3. MODUL HALAMAN UTAMA (DEKLARASI FUNGSI RENDER TAMPILAN)
# -----------------------------------------------------------------------------

def render_profil_anggaran(df_filtered_sdm):
    st.title("🏛️ Profil & Anggaran")
    st.markdown("---")
    
    df_elek_ctx = globals().get('df_f_elektronik', pd.DataFrame())

    def clean_number(val):
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        clean_str = str(val).replace('.', '').replace(',', '').replace('Rp', '').strip()
        try: return float(clean_str)
        except ValueError: return 0.0

    def fmt_idr(val):
        return f"{val:,.0f}".replace(',', '.')

    def fmt_pct(val):
        return f"{val:.2f}".replace('.', ',')

    def fmt_decimal(val):
        parts = f"{val:,.2f}".split('.')
        return f"{parts[0].replace(',', '.')},{parts[1]}"

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

    pimpinan_0 = get_pejabat_info(df_filtered_sdm, "Juru Ukur")
    pimpinan_1 = get_pejabat_info(df_filtered_sdm, "Bendahara")
    pimpinan_2 = get_pejabat_info(df_filtered_sdm, "Kepala Kantor")

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

    col_layout_left, col_layout_right = st.columns([2, 3])

    with col_layout_left:
        col_pic1, col_pic2, col_pic3 = st.columns(3)
        with col_pic1: st.image(pimpinan_0["url"], use_column_width=True)
        with col_pic2: st.image(pimpinan_1["url"], use_column_width=True)
        with col_pic3: st.image(pimpinan_2["url"], use_column_width=True)

    with col_layout_right:
        jml_pegawai = len(df_filtered_sdm)
        
        if not df_elek_ctx.empty:
            jml_kec = df_elek_ctx['kecamatan'].nunique() if 'kecamatan' in df_elek_ctx.columns else 0
            jml_desa = df_elek_ctx['desa_kelurahan'].nunique() if 'desa_kelurahan' in df_elek_ctx.columns else 0
            
            luas_adm_m2 = df_elek_ctx['luas_adm'].apply(clean_number).sum() if 'luas_adm' in df_elek_ctx.columns else 0
            luas_apl_m2 = df_elek_ctx['luas_apl'].apply(clean_number).sum() if 'luas_apl' in df_elek_ctx.columns else 0
            
            luas_adm_ha = luas_adm_m2 / 10_000.0
            luas_apl_ha = luas_apl_m2 / 10_000.0
            persen_apl_adm = (luas_apl_m2 / luas_adm_m2 * 100) if luas_adm_m2 > 0 else 0.0
        else:
            jml_kec, jml_desa, luas_adm_ha, luas_apl_ha, persen_apl_adm = 0, 0, 0.0, 0.0, 0.0

        total_target = df_filtered_sdm['target_dipa'].apply(clean_number).sum() if 'target_dipa' in df_filtered_sdm.columns else 0.0
        total_realisasi = df_filtered_sdm['realisasi_dipa'].apply(clean_number).sum() if 'realisasi_dipa' in df_filtered_sdm.columns else 0.0
        total_persen_dipa = (total_realisasi / total_target * 100) if total_target > 0 else 0.0

        c1, c2, c3 = st.columns(3)
        with c1: render_modern_card("Jumlah Pegawai", f"{jml_pegawai} Orang")
        with c2: render_modern_card("Jumlah Kecamatan", f"{fmt_idr(jml_kec)}")
        with c3: render_modern_card("Jumlah Desa/Kelurahan", f"{fmt_idr(jml_desa)}")

        c4, c5, c6 = st.columns(3)
        with c4: render_modern_card("Realisasi Dipa", f"{fmt_pct(total_persen_dipa)}%", f"Rp {fmt_idr(total_realisasi)}")
        with c5: render_modern_card("Luas Wilayah", f"{fmt_decimal(luas_adm_ha)} <span style='font-size:0.8rem;'>Ha</span>")
        with c6: render_modern_card("Luas APL", f"{fmt_decimal(luas_apl_ha)} <span style='font-size:0.8rem;'>Ha</span>", f"{fmt_pct(persen_apl_adm)}% dari Luas Wilayah")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("👥 Pejabat Struktural")
    
    jabatan_list = [
        "Tata Usaha", "Survei dan Pemetaan", "Penetapan Hak dan Pendaftaran", 
        "Penataan dan Pemberdayaan", "Pengadaan Tanah dan Pengembangan", "Pengendalian dan Penanganan Sengketa"
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
                        <div style="font-weight: 700; font-size: 0.88rem; color: #111111; word-break: break-word;">{p_info['nama']}</div>
                        <div style="font-size: 0.75rem; color: #666666; margin-top: 2px; margin-bottom: 6px;">{p_info['jabatan']}</div>
                        <div style="font-size: 0.75rem; color: #333333;">Target: <b>Rp {fmt_idr(p_info['target'])}</b></div>
                    </div>
                    """
                    st.markdown(html_content, unsafe_allow_html=True)
                    st.progress(min(max(p_info['persen'] / 100.0, 0.0), 1.0))
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

    KAB_MAP = {
        'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
        'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
        'Poso': 'PS', 'Tojo Una-una': 'TU', 'Toli-toli': 'TL',
        'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL',
        'Sigi': 'SG', 'Sulawesi Tengah': 'ST'
    }

    def clean_integer_field(val):
        if pd.isna(val): return 0.0
        if isinstance(val, float):
            if val == 0: return 0.0
            if 0 < val < 10: return float(round(val * 1000))
            return float(val)
        if isinstance(val, int): return float(val)
        s_val = str(val).replace('Rp', '').strip()
        if not s_val: return 0.0
        clean_str = s_val.replace('.', '').replace(',', '.')
        try: return float(clean_str)
        except ValueError: return 0.0

    def clean_pbt_decimal_field(val):
        if pd.isna(val): return 0.0
        if isinstance(val, (int, float)): return float(val)
        s_val = str(val).replace('Rp', '').strip()
        if not s_val: return 0.0
        clean_str = s_val.replace('.', '').replace(',', '.') if ',' in s_val else s_val.replace('.', '')
        try: return float(clean_str)
        except ValueError: return 0.0

    def fmt_idr(val): return f"{val:,.0f}".replace(',', '.')
    def fmt_decimal(val):
        parts = f"{val:,.2f}".split('.')
        return f"{parts[0].replace(',', '.')},{parts[1]}"

    df = df_filtered_psn.copy()
    df['kab_singkat'] = df['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x)) if 'kabupaten_kota' in df.columns else '-'

    pbt_real_cols = ['realisasi_baru', 'realisasi_k4', 'realisasi_repo']
    integer_cols = [
        'target_pbt', 'target_shat', 'puldadis', 'berkas', 'potensi', 'k1', 
        'siap_serah', 'diserahkan', 'target_redis', 'pos_redis', 'sk_redis', 
        'sertipikat_redis', 'target_lintor', 'lintor_su', 'lintor_sk', 
        'lintor_sertipikat', 'lintor_serah'
    ]

    for col in integer_cols: df[col] = df[col].apply(clean_integer_field) if col in df.columns else 0.0
    for col in pbt_real_cols: df[col] = df[col].apply(clean_pbt_decimal_field) if col in df.columns else 0.0

    cols_to_clean = integer_cols + pbt_real_cols
    df_rekap = df.groupby('kab_singkat')[cols_to_clean].sum().reset_index()

    def create_psn_chart(title, df_data, target_col, metrics_dict, color_sequence, unit="Bdg", is_stacked=False):
        df_valid = df_data[df_data[target_col] > 0].copy()
        if df_valid.empty:
            fig_empty = px.bar(title=f"{title} (Tidak ada target aktif)")
            fig_empty.update_layout(height=310, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=30, b=10))
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
                    'Kab/Kota': kab, 'Indikator': label, 'Persentase': pct,
                    'Realisasi': real_val, 'Target': target_val,
                    'Pct_Fmt': fmt_decimal(pct), 'Real_Fmt': f"{real_fmt_str} {unit}", 'Target_Fmt': f"{target_fmt_str} {unit}"
                })
                
        df_long = pd.DataFrame(long_rows)
        fig = px.bar(
            df_long, x='Kab/Kota', y='Persentase', color='Indikator',
            barmode='relative' if is_stacked else 'group', title=title,
            color_discrete_sequence=color_sequence, custom_data=['Real_Fmt', 'Target_Fmt', 'Pct_Fmt']
        )
        fig.update_traces(
            hovertemplate="<b>Kab/Kota: %{x}</b><br>%{fullData.name} | %{customdata[2]}%<extra></extra><br>Target: %{customdata[1]}<br>Realisasi: %{customdata[0]}",
            marker=dict(line=dict(width=1.2, color='#111111'))
        )
        fig.update_layout(
            height=310, xaxis_title="", yaxis_title="", legend_title_text="",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=5, r=5, t=32, b=5),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)),
            title=dict(font=dict(size=14)), yaxis=dict(gridcolor='#c4c4c4', tickfont=dict(size=9)), xaxis=dict(showgrid=False, tickfont=dict(size=9))
        )
        return fig

    card_wrapper_start = "<div style='background-color: #dbdbdb; border-radius: 10px; padding: 6px 10px 4px 10px; margin-bottom: 8px; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);'>"
    card_wrapper_end = "</div>"

    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)

    with row1_col1:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        fig_pbt = create_psn_chart("1. Realisasi PBT", df_rekap, 'target_pbt', {'Bidang Baru': 'realisasi_baru', 'Pemetaan K4': 'realisasi_k4', 'Reposisi Bidang': 'realisasi_repo'}, ['#dbdbdb', '#a9a9a9', '#656565'], unit="Ha", is_stacked=True)
        st.plotly_chart(fig_pbt, use_container_width=True)
        st.markdown(card_wrapper_end, unsafe_allow_html=True)

    with row1_col2:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        fig_shat = create_psn_chart("2. Realisasi SHAT", df_rekap, 'target_shat', {'Puldadis': 'puldadis', 'Berkas': 'berkas', 'K1': 'k1', 'Diserahkan': 'diserahkan'}, ['#b4ffb3', '#44bc43', '#1f9f1d', '#026b00'], unit="Bdg")
        st.plotly_chart(fig_shat, use_container_width=True)
        st.markdown(card_wrapper_end, unsafe_allow_html=True)

    with row2_col1:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        fig_redis = create_psn_chart("3. Realisasi Redistribusi", df_rekap, 'target_redis', {'Subyek Obyek': 'pos_redis', 'SK Redis': 'sk_redis', 'Sertipikat Redis': 'sertipikat_redis'}, ['#99eaf2', '#17BECF', '#0097a6'], unit="Bdg")
        st.plotly_chart(fig_redis, use_container_width=True)
        st.markdown(card_wrapper_end, unsafe_allow_html=True)

    with row2_col2:
        st.markdown(card_wrapper_start, unsafe_allow_html=True)
        lintor_serah_col = 'lintor_serah' if 'lintor_serah' in df_rekap.columns and df_rekap['lintor_serah'].sum() > 0 else 'lintor_sertipikat'
        fig_lintor = create_psn_chart("4. Realisasi Lintor", df_rekap, 'target_lintor', {'Lintor SU': 'lintor_su', 'Lintor SK': 'lintor_sk', 'Lintor Sertipikat': lintor_serah_col}, ['#f0d9a0', '#FECB52', '#fcb100'], unit="Bdg")
        st.plotly_chart(fig_lintor, use_container_width=True)
        st.markdown(card_wrapper_end, unsafe_allow_html=True)

def render_layanan_pertanahan(df_filtered_layanan):
    st.markdown("### 🚨 Berkas Tunggakan PDDM")
    st.markdown("<small style='color:gray;'>💡 Tips: Arahkan kursor ke kotak merah strobo untuk melihat detail nama prosedur dan nomor berkas.</small>", unsafe_allow_html=True)

    if df_filtered_layanan.empty:
        st.warning("Data Layanan Pertanahan tidak ditemukan atau kosong untuk filter yang dipilih.")
        return

    df = df_filtered_layanan.copy()

    def parse_date_flexible(val):
        if pd.isna(val) or val is None or str(val).strip() == '': return pd.NaT
        if isinstance(val, (pd.Timestamp, date, datetime)): return pd.to_datetime(val)
        val_str = str(val).strip()
        try:
            if val_str.isdigit() or (val_str.replace('.', '', 1).isdigit() and float(val_str) > 30000):
                return pd.to_datetime(float(val_str), unit='D', origin='1899-12-30')
        except Exception: pass
        try: return pd.to_datetime(val_str, dayfirst=True, errors='coerce')
        except Exception: return pd.NaT

    def clean_durasi(val):
        if pd.isna(val): return 0
        match = re.search(r'\d+', str(val).strip())
        return int(match.group()) if match else 0

    def fmt_no_thn(val):
        if pd.isna(val): return "-"
        s_val = str(val).strip()
        return s_val[:-2] if s_val.endswith('.0') else s_val

    def fmt_idr(val): return f"{val:,.0f}".replace(',', '.')

    KAB_NAME_CLEAN = {
        'Kota Palu': 'Palu', 'Kab. Morowali Utara': 'Morowali Utara', 'Kab. Banggai': 'Banggai',
        'Kab. Banggai Kepulauan': 'Banggai Kepulauan', 'Kab. Banggai Laut': 'Banggai Laut',
        'Kab. Buol': 'Buol', 'Kab. Donggala': 'Donggala', 'Kab. Morowali': 'Morowali',
        'Kab. Parigi Moutong': 'Parigi Moutong', 'Kab. Poso': 'Poso', 'Kab. Sigi': 'Sigi',
        'Kab. Tojo Una-una': 'Tojo Una-una', 'Kab. Toli-toli': 'Tolitoli', 'Toli-toli': 'Tolitoli', 'Toli Toli': 'Tolitoli'
    }

    df['kab_clean'] = df['kabupaten_kota'].astype(str).str.strip().map(lambda x: KAB_NAME_CLEAN.get(x, x)) if 'kabupaten_kota' in df.columns else '-'
    df['durasi_clean'] = df['durasi'].apply(clean_durasi)
    df['tgl_mulai_dt'] = df['tgl_mulai'].apply(parse_date_flexible)
    today = pd.to_datetime(date.today())
    df['tgl_batas_sop'] = df['tgl_mulai_dt'] + pd.to_timedelta(df['durasi_clean'], unit='D')
    
    df_overdue = df[(today > df['tgl_batas_sop']) & (df['tgl_mulai_dt'].notna())].copy()
    df_overdue['no_clean'] = df_overdue['nmr_berkas'].apply(fmt_no_thn)
    df_overdue['thn_clean'] = df_overdue['thn_berkas'].apply(fmt_no_thn)
    df_overdue['thn_num'] = df_overdue['thn_clean'].apply(clean_durasi)
    df_overdue['berkas_thn'] = df_overdue['no_clean'] + "/" + df_overdue['thn_clean']

    POSISI_TARGET = ["Kakan", "Kasi SP", "Kasi PHP", "Loket"]

    st.markdown("""
    <style>
    .strobo-red-compact { background: linear-gradient(135deg, #ff3333 0%, #cc0000 100%); color: white; font-weight: 700; text-align: center; padding: 4px 8px; border-radius: 6px; box-shadow: 0 0 8px rgba(255, 0, 0, 0.6); animation: pulse-red 1.5s infinite; cursor: pointer; font-size: 0.78rem; line-height: 1.2; }
    @keyframes pulse-red { 0% { box-shadow: 0 0 3px rgba(255, 0, 0, 0.4); } 50% { box-shadow: 0 0 12px rgba(255, 0, 0, 0.9); } 100% { box-shadow: 0 0 3px rgba(255, 0, 0, 0.4); } }
    .tuntas-green-compact { background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%); color: white; font-weight: 600; text-align: center; padding: 4px 8px; border-radius: 6px; font-size: 0.78rem; line-height: 1.2; }
    .table-hdr { font-weight: 700; text-align: center; padding: 4px; background-color: #e9ecef; border-radius: 4px; font-size: 0.80rem; }
    </style>
    """, unsafe_allow_html=True)

    def render_green_card(title, value, sub_text=""):
        card_html = f"""
        <div style="background: linear-gradient(135deg, #ffffff 0%, #f0fff4 100%); border-left: 5px solid #28a745; border-radius: 8px; padding: 8px 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); margin-top: 6px; margin-bottom: 4px; display: flex; flex-direction: column; justify-content: center;">
            <div style="color: #444444; font-size: 0.72rem; font-weight: 600; text-transform: uppercase;">{title}</div>
            <div style="color: #1e7e34; font-size: 1.15rem; font-weight: 700; margin-top: 1px;">{value}</div>
            {f'<div style="color: #666666; font-size: 0.68rem; margin-top: 1px;">{sub_text}</div>' if sub_text else ''}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    list_kab = sorted(df['kab_clean'].dropna().unique().tolist())
    col_kab, col_p1, col_p2, col_p3, col_p4 = st.columns([2.2, 1.8, 1.8, 1.8, 1.8])
    with col_kab: st.markdown("<div class='table-hdr'>Kantor Pertanahan</div>", unsafe_allow_html=True)
    with col_p1: st.markdown("<div class='table-hdr'>Kakan</div>", unsafe_allow_html=True)
    with col_p2: st.markdown("<div class='table-hdr'>Kasi SP</div>", unsafe_allow_html=True)
    with col_p3: st.markdown("<div class='table-hdr'>Kasi PHP</div>", unsafe_allow_html=True)
    with col_p4: st.markdown("<div class='table-hdr'>Loket Penyerahan</div>", unsafe_allow_html=True)

    for kab in list_kab:
        c_kab, c_p1, c_p2, c_p3, c_p4 = st.columns([2.2, 1.8, 1.8, 1.8, 1.8])
        
        with c_kab:
            # 1. Tambahkan margin-bottom: 8px agar teks nama kabupaten sejajar & berjarak
            st.markdown(
                f"<div style='font-size: 0.80rem; font-weight: 600; padding-top: 6px; margin-bottom: 8px;'>📍 {kab}</div>", 
                unsafe_allow_html=True
            )
            
        cols_pos = [c_p1, c_p2, c_p3, c_p4]
        
        for idx, pos in enumerate(POSISI_TARGET):
            with cols_pos[idx]:
                sub_df = df_overdue[
                    (df_overdue['kab_clean'] == kab) & 
                    (df_overdue['posisi_berkas'].astype(str).str.strip().str.contains(pos, case=False, na=False))
                ]
                
                jml_berkas = len(sub_df)
                
                if jml_berkas > 0:
                    tooltip_items = [f"• [{r.get('berkas_thn', '-')}] {r.get('nama_prosedur', '-')}" for _, r in sub_df.iterrows()]
                    tooltip_text = f"Kab: {kab}&#10;Posisi: {pos}&#10;Total: {jml_berkas} Berkas&#10;&#10;Rincian Prosedur:&#10;" + "&#10;".join(tooltip_items[:12])
                    
                    # 2. Tambahkan margin-bottom: 8px pada kotak Strobo Merah
                    st.markdown(
                        f"<div class='strobo-red-compact' style='margin-bottom: 8px;' title='{tooltip_text}'>🚨 {jml_berkas} Berkas</div>", 
                        unsafe_allow_html=True
                    )
                else:
                    # 3. Tambahkan margin-bottom: 8px pada kotak Tuntas Hijau
                    st.markdown(
                        "<div class='tuntas-green-compact' style='margin-bottom: 8px;'>✔ Tuntas</div>", 
                        unsafe_allow_html=True
                    )

    if not df_overdue.empty:
        df_g1 = df_overdue.groupby(['kab_clean', 'posisi_berkas']).agg(
            jml_berkas=('nmr_berkas', 'count'),
            list_berkas=('berkas_thn', lambda x: ", ".join(x.unique()[:6]))
        ).reset_index()

        fig_pos = px.bar(df_g1, x='kab_clean', y='jml_berkas', color='posisi_berkas', custom_data=df_g1[['posisi_berkas', 'list_berkas']], barmode='group')
        fig_pos.update_traces(hovertemplate="<b>Kab/Kota: %{x}</b><br>Posisi: %{customdata[0]}<br>Jumlah: %{y} Berkas<br>Sampel No Berkas: %{customdata[1]}<extra></extra>", marker=dict(line=dict(width=1, color='#222222')))
        fig_pos.update_layout(height=450, xaxis_title="", yaxis_title="", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=80, b=10))
        st.plotly_chart(fig_pos, use_container_width=True)

        b_17_26 = len(df_overdue[(df_overdue['thn_num'] >= 2017) & (df_overdue['thn_num'] <= 2026)])
        b_17_24 = len(df_overdue[(df_overdue['thn_num'] >= 2017) & (df_overdue['thn_num'] <= 2024)])
        b_25    = len(df_overdue[df_overdue['thn_num'] == 2025])
        b_26    = len(df_overdue[df_overdue['thn_num'] == 2026])

        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1: render_green_card("Total Berkas (2017 - 2026)", f"{fmt_idr(b_17_26)} Berkas")
        with col_c2: render_green_card("Tahun 2017 - 2024", f"{fmt_idr(b_17_24)} Berkas")
        with col_c3: render_green_card("Tahun 2025", f"{fmt_idr(b_25)} Berkas")
        with col_c4: render_green_card("Tahun 2026", f"{fmt_idr(b_26)} Berkas")

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 Detail Berkas Tunggakan PDDM")

        df_table = df_overdue.copy()
        col_f1, col_f2 = st.columns(2)
        col_thn_target = 'thn_berkas' if 'thn_berkas' in df_table.columns else ('thn_num' if 'thn_num' in df_table.columns else None)
        
        if col_thn_target:
            list_thn = sorted([t for t in df_table[col_thn_target].dropna().astype(str).str.strip().unique().tolist() if t and t.lower() not in ['nan', 'none', '']])
            list_thn.insert(0, "Semua Tahun")
            with col_f1: selected_thn = st.selectbox("📅 Filter Tahun Berkas", list_thn, key="filter_tbl_thn_berkas")
            if selected_thn != "Semua Tahun": df_table = df_table[df_table[col_thn_target].astype(str).str.strip() == selected_thn]

        if 'posisi_berkas' in df_table.columns:
            list_pos = sorted([p for p in df_table['posisi_berkas'].dropna().astype(str).str.strip().unique().tolist() if p and p.lower() not in ['nan', 'none', '']])
            list_pos.insert(0, "Semua Posisi")
            with col_f2: selected_pos = st.selectbox("📌 Filter Posisi Berkas", list_pos, key="filter_tbl_posisi_berkas")
            if selected_pos != "Semua Posisi": df_table = df_table[df_table['posisi_berkas'].astype(str).str.strip() == selected_pos]

        st.caption(f"Menampilkan **{len(df_table):,.0f}** berkas tunggakan".replace(',', '.'))

        if not df_table.empty:
            df_table = df_table.sort_values(by=['kab_clean', 'thn_num', 'no_clean'], ascending=[True, True, True])

            def clean_formula_text(df_source, col_name):
                if col_name not in df_source.columns: return pd.Series(['-'] * len(df_source))
                invalid_patterns = {'#n/a', 'nan', 'none', '', '#ref!', '#value!', '#name?', '#null!'}
                return df_source[col_name].apply(lambda val: '-' if pd.isna(val) or str(val).strip().lower() in invalid_patterns else str(val).strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

            df_table['pemohon_clean'] = clean_formula_text(df_table, 'nama')
            df_table['kendala_clean'] = clean_formula_text(df_table, 'kendala')
            df_table['upaya_clean'] = clean_formula_text(df_table, 'upaya_penyelesaian')
            df_table['prosedur_clean'] = clean_formula_text(df_table, 'nama_prosedur')
            df_table['posisi_clean'] = clean_formula_text(df_table, 'posisi_berkas')

            rows_html_list = []
            for idx, (_, row) in enumerate(df_table.iterrows(), start=1):
                r_html = (
                    f"<tr>"
                    f"<td style='text-align: center; font-weight: bold; width: 40px;'>{idx}</td>"
                    f"<td style='width: 110px;'><b>{row.get('kab_clean', '-')}</b></td>"
                    f"<td style='width: 110px;'>{row.get('berkas_thn', '-')}</td>"
                    f"<td style='width: 140px;'>{row['pemohon_clean']}</td>"
                    f"<td style='width: 180px;'>{row['prosedur_clean']}</td>"
                    f"<td style='width: 120px;'>{row['posisi_clean']}</td>"
                    f"<td style='width: 280px; color: #c0392b;'>{row['kendala_clean']}</td>"
                    f"<td style='width: 280px; color: #27ae60;'>{row['upaya_clean']}</td>"
                    f"</tr>"
                )
                rows_html_list.append(r_html)

            full_table_html = f"""<style>
.custom-table-container {{ max-height: 480px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; margin-top: 10px; }}
.custom-table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 0.82rem; }}
.custom-table th {{ position: sticky; top: 0; background-color: #f1f3f5; color: #333; font-weight: bold; padding: 8px 10px; text-align: left; border-bottom: 2px solid #dee2e6; z-index: 10; }}
.custom-table td {{ padding: 8px 10px; border-bottom: 1px solid #e9ecef; vertical-align: top; white-space: normal !important; word-wrap: break-word !important; }}
.custom-table tr:hover {{ background-color: #f8f9fa; }}
</style>
<div class="custom-table-container">
<table class="custom-table">
<thead>
<tr>
<th style="text-align: center;">No</th><th>Satker</th><th>Nomor Berkas</th><th>Pemohon</th><th>Prosedur</th><th>Posisi Digital</th><th>Kendala / Hambatan</th><th>Upaya Penyelesaian</th>
</tr>
</thead>
<tbody>
{"".join(rows_html_list)}
</tbody>
</table>
</div>"""
            st.markdown(full_table_html, unsafe_allow_html=True)

def render_pertanahan_elektronik(df_elektronik, df_progress=None, df_peringkat=None, selected_kab=None, selected_kec=None):
    st.title("💻 Data Elektronik")
    st.markdown("---")

    if df_elektronik.empty:
        st.warning("Data Elektronik (GID 1848496896) tidak ditemukan atau kosong.")
        return

    df = df_elektronik.copy()

    def parse_bilangan_cacah(val):
        if pd.isna(val) or val is None: return 0
        s_val = str(val).strip()
        invalid_patterns = {'#n/a', 'nan', 'none', '', '#ref!', '#value!', '#name?', '#null!'}
        if s_val.lower() in invalid_patterns: return 0
        s_val = s_val.replace('Rp', '').replace('%', '').replace('.', '').replace(',', '').strip()
        try: return int(round(float(s_val)))
        except ValueError: return 0

    def parse_luas_m2(val): return float(parse_bilangan_cacah(val))
    def fmt_idr(val): return f"{int(round(val)):,}".replace(',', '.')
    def fmt_dec2(val):
        parts = f"{val:,.2f}".split('.')
        return f"{parts[0].replace(',', '.')},{parts[1]}"

    luas_cols = ['luas_adm', 'luas_apl', 'luas_persil', 'luas_persil_valid', 'luas_persil_deliniasi', 'luas_kw456']
    for col in luas_cols: df[col] = df[col].apply(parse_luas_m2) if col in df.columns else 0.0

    int_cols = ['jumlah_persil', 'jumlah_kw456', 'jumlah_bt', 'bt_valid', 'jumlah_su', 'jumlah_suvalid', 'pra_suel', 'pra_btel', 'pra_sertel']
    for col in int_cols: df[col] = df[col].apply(parse_bilangan_cacah) if col in df.columns else 0

    df_clean = df[~df['kabupaten_kota'].astype(str).str.contains('Total|Jumlah|Sulawesi Tengah', case=False, na=False)].copy() if 'kabupaten_kota' in df.columns else df.copy()

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

    tot_adm_ha          = tot_adm_m2 / 10000.0
    tot_apl_ha          = tot_apl_m2 / 10000.0
    tot_persil_ha       = tot_persil_m2 / 10000.0
    tot_persil_valid_ha = tot_persil_valid_m2 / 10000.0
    tot_luas_kw456_ha   = tot_luas_kw456_m2 / 10000.0

    val_prog_harian = 0
    sub_card9 = "Tidak ada perubahan data"
    rank_num_val = "-"
    sub_card10 = "0,00% dari 0 BT"

    if df_progress is not None and not df_progress.empty:
        df_p = df_progress.copy()
        df_p.columns = [str(c).strip().lower() for c in df_p.columns]
        col_tgl  = next((c for c in df_p.columns if 'tgl' in c), 'tgl_data')
        col_kab  = next((c for c in df_p.columns if 'kab' in c), 'kabupaten_kota')
        col_kec  = next((c for c in df_p.columns if 'kec' in c), 'kecamatan')
        col_des  = next((c for c in df_p.columns if 'desa' in c or 'kelurahan' in c), 'desa_kelurahan')
        col_pdes = next((c for c in df_p.columns if 'prasertel_des' in c or 'prasertel_desa' in c), 'prasertel_desa')

        if col_tgl in df_p.columns and col_pdes in df_p.columns:
            df_p_valid = df_p[df_p[col_tgl].notna() & (df_p[col_tgl].astype(str).str.strip() != '')].copy()
            df_p_valid['tgl_dt'] = pd.to_datetime(df_p_valid[col_tgl], format='%d/%m/%Y', errors='coerce')
            if df_p_valid['tgl_dt'].isna().all():
                df_p_valid['tgl_dt'] = pd.to_datetime(df_p_valid[col_tgl], dayfirst=True, errors='coerce')

            list_tgl_dt = sorted(df_p_valid['tgl_dt'].dropna().unique())
            if len(list_tgl_dt) >= 2:
                df_new    = df_p_valid[df_p_valid['tgl_dt'] == list_tgl_dt[-1]].copy()
                df_latest = df_p_valid[df_p_valid['tgl_dt'] == list_tgl_dt[-2]].copy()

                df_new['val_pdes']    = df_new[col_pdes].apply(parse_bilangan_cacah)
                df_latest['val_pdes'] = df_latest[col_pdes].apply(parse_bilangan_cacah)

                is_kec_active = selected_kec and str(selected_kec).strip() not in ['', 'Semua', 'All', 'None', 'Semua Kecamatan']
                is_kab_active = selected_kab and str(selected_kab).strip() not in ['', 'Semua', 'All', 'None', 'Semua Kabupaten/Kota']

                if is_kec_active: group_keys, entity_label = [k for k in [col_kab, col_kec, col_des] if k in df_p_valid.columns], "Desa/Kelurahan"
                elif is_kab_active: group_keys, entity_label = [k for k in [col_kab, col_kec] if k in df_p_valid.columns], "Kecamatan"
                else: group_keys, entity_label = [k for k in [col_kab] if k in df_p_valid.columns], "Kabupaten/Kota"

                grp_new    = df_new.groupby(group_keys)['val_pdes'].sum().reset_index()
                grp_latest = df_latest.groupby(group_keys)['val_pdes'].sum().reset_index()

                m_grp = pd.merge(grp_new, grp_latest, on=group_keys, suffixes=('_new', '_latest'))
                m_grp['diff'] = m_grp['val_pdes_new'] - m_grp['val_pdes_latest']

                df_changed = m_grp[m_grp['diff'] > 0]
                val_prog_harian = df_changed['diff'].sum()
                sub_card9 = f"{len(df_changed)} {entity_label} berprogres" if len(df_changed) > 0 else "Tidak ada progres"

    if df_peringkat is not None and not df_peringkat.empty:
        df_rank = df_peringkat.copy()
        df_rank.columns = [str(c).strip().lower() for c in df_rank.columns]
        col_prov = next((c for c in df_rank.columns if 'prov' in c), 'provinsi')
        col_rank = next((c for c in df_rank.columns if 'ringkat' in c), 'peringkat')
        col_pnas = next((c for c in df_rank.columns if 'prasertel' in c), 'prasertel_nasional')
        col_bnas = next((c for c in df_rank.columns if 'btvalid' in c), 'btvalid_nasional')

        if col_prov in df_rank.columns:
            sulteng_df = df_rank[df_rank[col_prov].astype(str).str.contains('sulteng|sulawesi tengah', case=False, na=False)]
            if not sulteng_df.empty:
                row_s = sulteng_df.iloc[0]
                if col_rank in sulteng_df.columns and pd.notna(row_s[col_rank]):
                    rank_num_val = str(row_s[col_rank]).strip().replace('.0', '')
                p_nas_val = parse_bilangan_cacah(row_s.get(col_pnas, 0))
                b_nas_val = parse_bilangan_cacah(row_s.get(col_bnas, 0))
                pct_nas = (p_nas_val / b_nas_val * 100.0) if b_nas_val > 0 else 0.0
                sub_card10 = f"{fmt_dec2(pct_nas)}% dari {fmt_idr(b_nas_val)} BT"

    st.markdown("""
    <style>
    .orange-card-box { background: linear-gradient(135deg, #ffffff 0%, #fff8f0 100%); border: 2px solid #f39c12; border-radius: 12px; padding: 10px 12px; height: 104px; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 12px; }
    .orange-card-title { color: #d35400; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; }
    .orange-card-value { color: #e67e22; font-size: 1.25rem; font-weight: 800; line-height: 1.1; }
    .orange-card-sub { color: #7f8c8d; font-size: 0.68rem; font-weight: 500; }
    .blue-card-box { background: linear-gradient(135deg, #ffffff 0%, #f0f5ff 100%); border: 2px solid #0451c9; border-radius: 12px; padding: 10px 12px; height: 104px; display: flex; flex-direction: column; justify-content: space-between; margin-bottom: 12px; }
    .blue-card-title { color: #0451c9; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; }
    .blue-card-value { color: #0451c9; font-size: 1.25rem; font-weight: 800; line-height: 1.1; }
    .blue-card-sub { color: #5c7299; font-size: 0.68rem; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

    def render_orange_card(title, value_str, sub_text=""):
        st.markdown(f'<div class="orange-card-box"><div class="orange-card-title">{title}</div><div class="orange-card-value">{value_str}</div><div class="orange-card-sub">{sub_text}</div></div>', unsafe_allow_html=True)

    def render_blue_card(title, value_str, sub_text=""):
        st.markdown(f'<div class="blue-card-box"><div class="blue-card-title">{title}</div><div class="blue-card-value">{value_str}</div><div class="blue-card-sub">{sub_text}</div></div>', unsafe_allow_html=True)

    r1_c1, r1_c2, r1_c3, r1_c4, r1_c5 = st.columns(5)
    with r1_c1: render_orange_card("Luas APL", f"{fmt_dec2((tot_apl_m2 / tot_adm_m2 * 100.0) if tot_adm_m2 > 0 else 0.0)}%", f"{fmt_dec2(tot_apl_ha)} Ha dari Luas Wilayah ({fmt_dec2(tot_adm_ha)} Ha)")
    with r1_c2: render_orange_card("Luas Persil", f"{fmt_dec2((tot_persil_m2 / tot_apl_m2 * 100.0) if tot_apl_m2 > 0 else 0.0)}%", f"{fmt_dec2(tot_persil_ha)} Ha | {fmt_idr(tot_jml_persil)} Persil")
    with r1_c3: render_orange_card("Luas Persil Valid", f"{fmt_dec2((tot_persil_valid_m2 / tot_persil_m2 * 100.0) if tot_persil_m2 > 0 else 0.0)}%", f"{fmt_dec2(tot_persil_valid_ha)} Ha")
    with r1_c4: render_orange_card("Jumlah KW456", f"{fmt_idr(tot_kw456)} Bidang", f"{fmt_dec2(tot_luas_kw456_ha)} Ha | Total: {fmt_idr(tot_bt)} BT")
    with r1_c5: render_orange_card("Jumlah BT Valid", f"{fmt_idr(tot_bt_valid)} BT", f"{fmt_dec2((tot_bt_valid / tot_bt * 100.0) if tot_bt > 0 else 0.0)} % | {fmt_idr(tot_bt)} BT")

    r2_c1, r2_c2, r2_c3, r2_c4, r2_c5 = st.columns(5)
    with r2_c1: render_orange_card("% PRA-SUEL", f"{fmt_dec2((tot_pra_suel / tot_su * 100.0) if tot_su > 0 else 0.0)}%", f"{fmt_idr(tot_pra_suel)} SU dari {fmt_idr(tot_su)} SU")
    with r2_c2: render_orange_card("% PRA-BTEL", f"{fmt_dec2((tot_pra_btel / tot_bt_valid * 100.0) if tot_bt_valid > 0 else 0.0)}%", f"{fmt_idr(tot_pra_btel)} BT dari {fmt_idr(tot_bt_valid)} BT Valid")
    with r2_c3: render_orange_card("% PRA-SERTEL", f"{fmt_dec2((tot_pra_sertel / tot_bt * 100.0) if tot_bt > 0 else 0.0)}%", f"{fmt_idr(tot_pra_sertel)} BT dari {fmt_idr(tot_bt)} BT")
    with r2_c4: render_blue_card("Progress Terbaru", f"+{fmt_idr(val_prog_harian)} Pra Sertel", sub_card9)
    with r2_c5: render_blue_card("Peringkat Nasional", f"Sulteng #{rank_num_val}", sub_card10)

    st.markdown("<br>", unsafe_allow_html=True)

    KAB_MAP = {
        'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
        'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
        'Poso': 'PS', 'Tojo Una-una': 'TU', 'Toli-toli': 'TL', 'Toli Toli': 'TL',
        'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL', 'Kota Palu': 'PL', 
        'Sigi': 'SG', 'Sulawesi Tengah': 'ST'
    }

    df_chart = df_clean.copy()
    is_kec_active = selected_kec and str(selected_kec).strip() not in ['', 'Semua', 'Semua Kecamatan']
    is_kab_active = selected_kab and str(selected_kab).strip() not in ['', 'Semua', 'Semua Kabupaten/Kota']

    if is_kec_active and 'desa_kelurahan' in df_chart.columns: x_col, x_label = 'desa_kelurahan', "Desa / Kelurahan"
    elif is_kab_active and 'kecamatan' in df_chart.columns: x_col, x_label = 'kecamatan', "Kecamatan"
    else:
        df_chart['x_group'] = df_chart['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x)) if 'kabupaten_kota' in df_chart.columns else '-'
        x_col, x_label = 'x_group', "Kabupaten / Kota"

    req_cols = ['jumlah_su', 'jumlah_suvalid', 'jumlah_bt', 'bt_valid', 'pra_suel', 'pra_btel', 'pra_sertel']
    for c in req_cols:
        if c not in df_chart.columns: df_chart[c] = 0
        else: df_chart[c] = df_chart[c].apply(lambda v: int(str(v).replace('.', '').replace(',', '').strip()) if pd.notna(v) and str(v).replace('.', '').replace(',', '').strip().isdigit() else 0)

    df_grouped = df_chart.groupby(x_col)[req_cols].sum().reset_index()

    df_grouped['pct_su_valid']   = (df_grouped['jumlah_suvalid'] / df_grouped['jumlah_su'].replace(0, 1)) * 100.0
    df_grouped['pct_pra_suel']   = (df_grouped['pra_suel'] / df_grouped['jumlah_su'].replace(0, 1)) * 100.0
    df_grouped['pct_bt_valid']   = (df_grouped['bt_valid'] / df_grouped['jumlah_bt'].replace(0, 1)) * 100.0
    df_grouped['pct_pra_btel']   = (df_grouped['pra_btel'] / df_grouped['bt_valid'].replace(0, 1)) * 100.0
    df_grouped['pct_pra_sertel'] = (df_grouped['pra_sertel'] / df_grouped['jumlah_bt'].replace(0, 1)) * 100.0

    df_grouped = df_grouped.sort_values(by='pct_pra_sertel', ascending=False)
    x_order = df_grouped[x_col].tolist()

    df_merged = df_grouped.melt(
        id_vars=[x_col, 'jumlah_suvalid', 'jumlah_su', 'pra_suel', 'bt_valid', 'jumlah_bt', 'pra_btel', 'pra_sertel'],
        value_vars=['pct_su_valid', 'pct_pra_suel', 'pct_bt_valid', 'pct_pra_btel', 'pct_pra_sertel'],
        var_name='Indikator_Code', value_name='Persentase'
    )

    map_indikator = {'pct_su_valid': '% SU Valid', 'pct_pra_suel': '% Pra-SUEL', 'pct_bt_valid': '% BT Valid', 'pct_pra_btel': '% Pra-BTEL', 'pct_pra_sertel': '% Pra-SERTEL'}
    df_merged['Indikator'] = df_merged['Indikator_Code'].map(map_indikator)

    def get_hover_values(row):
        code = row['Indikator_Code']
        if code == 'pct_su_valid': return [row['jumlah_suvalid'], row['jumlah_su']]
        elif code == 'pct_pra_suel': return [row['pra_suel'], row['jumlah_su']]
        elif code == 'pct_bt_valid': return [row['bt_valid'], row['jumlah_bt']]
        elif code == 'pct_pra_btel': return [row['pra_btel'], row['bt_valid']]
        else: return [row['pra_sertel'], row['jumlah_bt']]

    df_merged['val_realisasi'] = df_merged.apply(lambda r: get_hover_values(r)[0], axis=1)
    df_merged['val_pembagi']   = df_merged.apply(lambda r: get_hover_values(r)[1], axis=1)
    df_merged['realisasi_fmt'] = df_merged['val_realisasi'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
    df_merged['pembagi_fmt']   = df_merged['val_pembagi'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))

    pastel_color_map = {'% SU Valid': '#ffd383', '% Pra-SUEL': '#dc9513', '% BT Valid': '#b4ffb3', '% Pra-BTEL': '#51ce4f', '% Pra-SERTEL': '#1f9f1d'}

    st.markdown("---")
    fig_combined = px.bar(
        df_merged, x=x_col, y='Persentase', color='Indikator', barmode='group',
        title="📊 Grafik Capaian Pra-SERTEL", color_discrete_map=pastel_color_map,
        category_orders={x_col: x_order, 'Indikator': ['% SU Valid', '% Pra-SUEL', '% BT Valid', '% Pra-BTEL', '% Pra-SERTEL']},
        custom_data=df_merged[['realisasi_fmt', 'pembagi_fmt']]
    )

    fig_combined.update_traces(
        hovertemplate=f"<b>{x_label}: %{{x}}</b><br>%{{fullData.name}}: <b>%{{y:.2f}}%</b><br>Jumlah Capaian: <b>%{{customdata[0]}}</b><br>Total Pembagi: <b>%{{customdata[1]}}</b><extra></extra>",
        marker=dict(line=dict(width=1, color='#000000'))
    )

    fig_combined.update_layout(
        height=450, xaxis_title="", yaxis_title="", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=35, b=10), separators=',.',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title_text=''),
        yaxis=dict(gridcolor='#f2f2f2', range=[0, max(df_merged['Persentase'].max() * 1.15, 100)], tickvals=[0, 50, 100], ticktext=['0%', '50%', '100%'])
    )
    st.plotly_chart(fig_combined, use_container_width=True)

    if df_progress is not None and not df_progress.empty:
        df_p_line = df_progress.copy()
        df_p_line.columns = [str(c).strip().lower() for c in df_p_line.columns]

        col_tgl  = next((c for c in df_p_line.columns if 'tgl' in c), 'tgl_data')
        col_kab  = next((c for c in df_p_line.columns if 'kab' in c), 'kabupaten_kota')
        col_kec  = next((c for c in df_p_line.columns if 'kec' in c), 'kecamatan')
        col_des  = next((c for c in df_p_line.columns if 'des' in c or 'kel' in c), 'desa_kelurahan')
        col_pdes = 'prasertel_desa' if 'prasertel_desa' in df_p_line.columns else next((c for c in df_p_line.columns if 'prasertel' in c), 'prasertel_desa')

        if col_tgl in df_p_line.columns and col_pdes in df_p_line.columns:
            df_p_line['tgl_str'] = df_p_line[col_tgl].astype(str).str.strip()
            df_p_line = df_p_line[df_p_line['tgl_str'].notna() & (df_p_line['tgl_str'] != '') & (df_p_line['tgl_str'].str.lower() != 'nan')].copy()

            def parse_prasertel_absolute(val):
                if pd.isna(val) or val is None: return 0
                s = str(val).strip()
                if not s or s.lower() in ['nan', 'none', 'null', '']: return 0
                s = f"{val:.3f}".replace('.', '') if isinstance(val, float) else s.replace('.', '').replace(',', '').replace('Rp', '').replace('%', '').strip()
                try: return int(s)
                except ValueError: return 0

            df_p_line['val_pdes'] = df_p_line[col_pdes].apply(parse_prasertel_absolute)
            unique_tgls = df_p_line['tgl_str'].unique().tolist()

            if is_kec_active and col_des in df_p_line.columns: group_col, hover_area_label, chart_title = col_des, "Desa/Kelurahan", f"📈 Tren Progress Prasertel per Desa/Kelurahan ({selected_kec})"
            elif is_kab_active and col_kec in df_p_line.columns: group_col, hover_area_label, chart_title = col_kec, "Kecamatan", f"📈 Tren Progress Prasertel per Kecamatan ({selected_kab})"
            else: group_col, hover_area_label, chart_title = (col_kab if col_kab in df_p_line.columns else None), "Kab/Kota", "📈 Tren Progres Prasertel"

            if group_col and group_col in df_p_line.columns:
                df_trend = df_p_line.groupby(['tgl_str', group_col], as_index=False)['val_pdes'].sum()
                fig_line = px.line(df_trend, x='tgl_str', y='val_pdes', color=group_col, markers=True, title=chart_title, category_orders={'tgl_str': unique_tgls})
            else:
                df_trend = df_p_line.groupby('tgl_str', as_index=False)['val_pdes'].sum()
                fig_line = px.line(df_trend, x='tgl_str', y='val_pdes', markers=True, title=chart_title, category_orders={'tgl_str': unique_tgls})
                fig_line.update_traces(line_color='#0451C9', line_width=3)

            fig_line.update_traces(hovertemplate=f"<b>{hover_area_label}: %{{fullData.name}}</b><br>Tanggal: %{{x}}<br>Jml Prasertel: <b>%{{y:,.0f}} BT</b><extra></extra>", marker=dict(size=8, line=dict(width=1.5, color='#000000')))
            fig_line.update_layout(height=480, xaxis_title="", yaxis_title="", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=15, r=15, t=60, b=80), separators=',.', yaxis=dict(gridcolor='#f2f2f2'), xaxis=dict(type='category'))

            st.markdown("---")
            st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🎯 Target Harian Prasertel Menuju 70% (Desember 2026)")

    today = datetime.now().date()
    end_date = date(2026, 12, 31)
    sisa_hari_kerja = np.busday_count(today, end_date + timedelta(days=1)) if today < end_date else 1
    st.info(f"📅 **{sisa_hari_kerja} hari kerja** menuju Tgl. 31 Desember 2026")

    df_tabel_target = df_clean.copy()
    if is_kec_active and 'desa_kelurahan' in df_tabel_target.columns: col_wilayah, label_wilayah = 'desa_kelurahan', "Desa / Kelurahan"
    elif is_kab_active and 'kecamatan' in df_tabel_target.columns: col_wilayah, label_wilayah = 'kecamatan', "Kecamatan"
    else: col_wilayah, label_wilayah = 'kabupaten_kota', "Kabupaten / Kota"

    col_bt_source = 'jumlah_bt' if 'jumlah_bt' in df_tabel_target.columns else 'bt_valid'
    def parse_num_table(val):
        if pd.isna(val) or val is None: return 0
        s = str(val).replace('.', '').replace(',', '').strip()
        try: return int(s)
        except: return 0

    df_tabel_target['bt_valid_clean'] = df_tabel_target[col_bt_source].apply(parse_num_table) if col_bt_source in df_tabel_target.columns else 0
    df_tabel_target['pra_sertel_clean'] = df_tabel_target['pra_sertel'].apply(parse_num_table) if 'pra_sertel' in df_tabel_target.columns else 0

    df_target_grp = df_tabel_target.groupby(col_wilayah, as_index=False)[['bt_valid_clean', 'pra_sertel_clean']].sum()
    df_target_grp.rename(columns={'bt_valid_clean': 'bt_valid', 'pra_sertel_clean': 'pra_sertel'}, inplace=True)

    df_target_grp['pct_saat_ini'] = (df_target_grp['pra_sertel'] / df_target_grp['bt_valid'].replace(0, 1)) * 100.0
    df_target_grp['target_bt_70'] = df_target_grp['bt_valid'] * 0.70
    df_target_grp['sisa_bt_kejar'] = (df_target_grp['target_bt_70'] - df_target_grp['pra_sertel']).apply(lambda x: max(0, x))
    df_target_grp['target_harian'] = (df_target_grp['sisa_bt_kejar'] / sisa_hari_kerja).apply(np.ceil).astype(int)

    df_capaian_map = {}
    if df_progress is not None and not df_progress.empty:
        df_p_cap = df_progress.copy()
        df_p_cap.columns = [str(c).strip().lower() for c in df_p_cap.columns]
        c_tgl  = next((c for c in df_p_cap.columns if 'tgl' in c), 'tgl_data')
        c_wil  = next((c for c in df_p_cap.columns if col_wilayah[:3] in c), col_wilayah)
        c_pdes = 'prasertel_desa' if 'prasertel_desa' in df_p_cap.columns else next((c for c in df_p_cap.columns if 'prasertel' in c), 'prasertel_desa')

        if c_tgl in df_p_cap.columns and c_pdes in df_p_cap.columns and c_wil in df_p_cap.columns:
            df_p_cap['tgl_dt'] = pd.to_datetime(df_p_cap[c_tgl], format='%d/%m/%Y', errors='coerce')
            if df_p_cap['tgl_dt'].isna().all(): df_p_cap['tgl_dt'] = pd.to_datetime(df_p_cap[c_tgl], dayfirst=True, errors='coerce')
            unique_dates = sorted(df_p_cap['tgl_dt'].dropna().unique())
            if len(unique_dates) >= 2:
                df_p_cap['val_clean'] = df_p_cap[c_pdes].apply(parse_num_table)
                grp_latest = df_p_cap[df_p_cap['tgl_dt'] == unique_dates[-1]].groupby(c_wil)['val_clean'].sum()
                grp_prev   = df_p_cap[df_p_cap['tgl_dt'] == unique_dates[-2]].groupby(c_wil)['val_clean'].sum()
                for w_name in df_target_grp[col_wilayah]:
                    df_capaian_map[w_name] = grp_latest.get(w_name, 0) - grp_prev.get(w_name, 0)

    df_target_grp = df_target_grp.sort_values(by='pct_saat_ini', ascending=True).reset_index(drop=True)

    rows_target_html = []
    for idx, row in df_target_grp.iterrows():
        wil_name = row[col_wilayah]
        bt_val   = f"{row['bt_valid']:,.0f}".replace(',', '.')
        p_sertel = f"{row['pra_sertel']:,.0f}".replace(',', '.')
        pct_val  = row['pct_saat_ini']
        tgt_hr   = f"{row['target_harian']:,.0f} BT".replace(',', '.')

        badge_class = "badge-red" if pct_val <= 50.0 else ("badge-yellow" if pct_val <= 70.0 else "badge-green")
        pct_formatted = f"<span class='{badge_class}'>{pct_val:.2f}%</span>"

        cap_val = df_capaian_map.get(wil_name, 0)
        cap_formatted = f"<span style='color: #10B981; font-weight: bold;'>+{cap_val:,.0f} BT</span>".replace(',', '.') if cap_val > 0 else (f"<span style='color: #EF4444; font-weight: bold;'>{cap_val:,.0f} BT</span>".replace(',', '.') if cap_val < 0 else "<span style='color: #6B7280;'>0 BT</span>")

        rows_target_html.append(f"<tr><td style='text-align: center; font-weight: bold; width: 50px;'>{idx+1}</td><td style='text-align: left; font-weight: 600;'>{wil_name}</td><td style='text-align: center;'>{bt_val}</td><td style='text-align: center;'>{p_sertel}</td><td style='text-align: center;'>{pct_formatted}</td><td style='text-align: center;'>{cap_formatted}</td><td style='text-align: center; font-weight: bold; color: #1E3A8A;'>{tgt_hr}</td></tr>")

    html_target_table = f"""<style>
.target-table-container {{ width: 100%; border: 1px solid #E5E7EB; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); margin-top: 10px; overflow: hidden; }}
.target-table {{ width: 100%; border-collapse: collapse; font-family: system-ui, -apple-system, sans-serif; font-size: 0.88rem; }}
.target-table th {{ background-color: #1E293B; color: #FFFFFF; font-weight: 700; padding: 12px 10px; text-align: center; border-bottom: 2px solid #0F172A; }}
.target-table th.th-left {{ text-align: left !important; }}
.target-table td {{ padding: 10px 12px; border-bottom: 1px solid #F1F5F9; vertical-align: middle; }}
.target-table tr:nth-child(even) {{ background-color: #F8FAFC; }}
.badge-red {{ background-color: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 6px; font-weight: 700; display: inline-block; }}
.badge-yellow {{ background-color: #FEF3C7; color: #92400E; padding: 4px 10px; border-radius: 6px; font-weight: 700; display: inline-block; }}
.badge-green {{ background-color: #D1FAE5; color: #065F46; padding: 4px 10px; border-radius: 6px; font-weight: 700; display: inline-block; }}
</style>
<div class="target-table-container">
<table class="target-table">
<thead><tr><th>No</th><th class="th-left">{label_wilayah}</th><th>Jumlah BT Valid</th><th>Jumlah Prasertel</th><th>Persentase Saat Ini</th><th>Capaian Terbaru</th><th>Target Harian</th></tr></thead>
<tbody>{"".join(rows_target_html)}</tbody>
</table></div>"""
    st.markdown(html_target_table, unsafe_allow_html=True)

def render_isu_strategis(df_isu):
    st.title("✍️ Diskusi Isu Strategis")
    st.caption("Wadah diskusi & pemantauan isu strategis pertanahan se-Sulawesi Tengah.")

    with st.expander("➕ **Tambah Isu Strategis Baru**", expanded=False):
        with st.form("form_isu_baru", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            list_kab_st = [
                "Sulawesi Tengah (Provinsi)", "Banggai", "Banggai Kepulauan", "Banggai Laut",
                "Buol", "Donggala", "Kota Palu", "Morowali", "Morowali Utara",
                "Parigi Moutong", "Poso", "Sigi", "Tojo Una-Una", "Toli-Toli"
            ]
            list_unit = [
                "Kepala Kantor", "Tata Usaha", "Survei dan Pemetaan",
                "Penetapan Hak dan Pendaftaran", "Penataan dan Pemberdayaan",
                "Pengadaan Tanah dan Pengembangan", "Pengendalian dan Penanganan Sengketa"
            ]
            with col_f1:
                input_kab = st.selectbox("Kabupaten / Kota / Wilayah", list_kab_st)
                input_pembuat = st.text_input("Nama & Jabatan Pembuat Isu", placeholder="Contoh: Ahmad, S.Si.T. (Kasi PHPT)")
            with col_f2:
                input_unit = st.selectbox("Unit Working Group / Seksi", list_unit)

            input_isu = st.text_area("Deskripsi Isu Strategis (Maks. 500 kata)", height=120)
            submit_isu = st.form_submit_button("🚀 Kirim Isu Strategis")

            if submit_isu:
                word_count = len(input_isu.strip().split())
                if not input_pembuat.strip(): st.error("⚠️ Nama & Jabatan Pembuat wajib diisi!")
                elif not input_isu.strip(): st.error("⚠️ Teks Isu Strategis tidak boleh kosong!")
                elif word_count > 500: st.error(f"⚠️ Isu Strategis melebihi batas 500 kata! ({word_count} kata)")
                else:
                    # Kunci Waktu ke WITA (GMT+8)
                    now_str = datetime.now(ZoneInfo("Asia/Makassar")).strftime("%Y-%m-%d %H:%M:%S")
                    payload = {
                        "gid": "1699480367", "kabupaten_kota": input_kab, "unit": input_unit,
                        "tgl_jam": now_str, "isu_strategis": input_isu.strip(),
                        "pembahasan": "-", "pembuat": input_pembuat.strip()
                    }
                    try:
                        requests.post(GSHEET_WEBAPP_URL, json=payload)
                        st.cache_data.clear()
                        st.success("✅ Isu Strategis berhasil ditambahkan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Gagal mengirim data ke Google Sheet: {e}")

    st.markdown("---")

    if df_isu is None or df_isu.empty:
        st.info("ℹ️ Belum ada isu strategis yang tercatat.")
        return

    df_display = df_isu.copy()
    df_display.columns = [str(c).strip().lower().replace(' ', '_') for c in df_display.columns]

    if 'tgl_jam' in df_display.columns:
        df_display['tgl_dt'] = pd.to_datetime(df_display['tgl_jam'], errors='coerce')
        df_display = df_display.sort_values(by='tgl_dt', ascending=False)

    col_f1, col_f2 = st.columns(2)
    with col_f1: f_kab = st.selectbox("🔍 Filter Wilayah", ["Semua Wilayah"] + list_kab_st)
    with col_f2: f_unit = st.selectbox("🔍 Filter Unit", ["Semua Unit"] + list_unit)

    if f_kab != "Semua Wilayah" and 'kabupaten_kota' in df_display.columns: df_display = df_display[df_display['kabupaten_kota'] == f_kab]
    if f_unit != "Semua Unit" and 'unit' in df_display.columns: df_display = df_display[df_display['unit'] == f_unit]

    grouped_isu = df_display.groupby('isu_strategis', sort=False)

    for isu_text, group in grouped_isu:
        if not isu_text or str(isu_text).strip() in ['-', 'nan', '']: continue

        baris_induk = group[group['pembahasan'].astype(str).str.strip().isin(['-', '', 'nan'])]
        if not baris_induk.empty:
            row_utama = baris_induk.sort_values(by='tgl_dt', ascending=True).iloc[0] if 'tgl_dt' in baris_induk.columns else baris_induk.iloc[-1]
        else:
            row_utama = group.sort_values(by='tgl_dt', ascending=True).iloc[0] if 'tgl_dt' in group.columns else group.iloc[0]

        kab_val = row_utama.get('kabupaten_kota', '-')
        unit_val = row_utama.get('unit', '-')
        tgl_val = row_utama.get('tgl_jam', '-')
        pembuat_isu = row_utama.get('pembuat', 'Anonim')

        card_html = f"""
        <style>
        .isu-box {{ background-color: #F8FAFC; border-left: 5px solid #1E40AF; border-radius: 8px; padding: 16px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .isu-header {{ font-size: 0.82rem; color: #64748B; margin-bottom: 8px; }}
        .pembuat-isu {{ color: #1E40AF; font-weight: bold; }}
        .pembuat-bahas {{ color: #D97706; font-weight: bold; }}
        .isu-body {{ font-size: 0.95rem; color: #1E293B; line-height: 1.5; white-space: pre-wrap; }}
        </style>
        <div class="isu-box">
            <div class="isu-header">📍 <b>{kab_val}</b> | 🏢 {unit_val} | 🕒 {tgl_val}<br>Oleh: <span class="pembuat-isu">{pembuat_isu}</span></div>
            <div class="isu-body"><b>ISU STRATEGIS:</b><br>{isu_text}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        group_tanggapan = group.sort_values(by='tgl_dt', ascending=True) if 'tgl_dt' in group.columns else group
        for idx, row in group_tanggapan.iterrows():
            pembahasan_text = str(row.get('pembahasan', '')).strip()
            pembuat_bahas = row.get('pembuat', 'Anonim')
            tgl_bahas = row.get('tgl_jam', '-')

            if pembahasan_text and pembahasan_text not in ['-', 'nan', '']:
                chat_html = f"""
                <div style="margin-left: 30px; background-color: #FFFBEB; border-left: 3px solid #D97706; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                    <div style="font-size: 0.8rem; color: #78350F;">💬 Ditanggapi oleh: <span class="pembuat-bahas">{pembuat_bahas}</span> ({tgl_bahas})</div>
                    <div style="font-size: 0.9rem; color: #451A03; margin-top: 4px;">{pembahasan_text}</div>
                </div>
                """
                st.markdown(chat_html, unsafe_allow_html=True)

        with st.expander("💬 Tambah Tanggapan / Pembahasan Isu Ini", expanded=False):
            with st.form(f"form_reply_{hash(isu_text)}", clear_on_submit=True):
                reply_pembuat = st.text_input("Nama & Jabatan Penanggap", key=f"p_{hash(isu_text)}")
                reply_text = st.text_area("Tanggapan / Perkembangan Terakhir (Maks. 300 kata)", height=80, key=f"t_{hash(isu_text)}")
                submit_reply = st.form_submit_button("💬 Kirim Tanggapan")

                if submit_reply:
                    word_cnt_reply = len(reply_text.strip().split())
                    if not reply_pembuat.strip(): st.error("⚠️ Nama & Jabatan Penanggap wajib diisi!")
                    elif not reply_text.strip(): st.error("⚠️ Teks tanggapan tidak boleh kosong!")
                    elif word_cnt_reply > 300: st.error(f"⚠️ Tanggapan melebihi batas 300 kata! ({word_cnt_reply} kata)")
                    else:
                        now_str = datetime.now(ZoneInfo("Asia/Makassar")).strftime("%Y-%m-%d %H:%M:%S")
                        payload_reply = {
                            "gid": "1699480367", "kabupaten_kota": kab_val, "unit": unit_val,
                            "tgl_jam": now_str, "isu_strategis": isu_text,
                            "pembahasan": reply_text.strip(), "pembuat": reply_pembuat.strip()
                        }
                        try:
                            requests.post(GSHEET_WEBAPP_URL, json=payload_reply)
                            st.cache_data.clear()
                            st.success("✅ Tanggapan berhasil disimpan!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Gagal mengirim tanggapan: {e}")
        st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. FUNGSI AUTENTIKASI (LOGIN & LOGOUT)
# -----------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None

def login():
    st.markdown("<h2 style='text-align: center;'>🔐 Login Dashboard Pertanahan</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Masukkan kode akses resmi untuk melanjutkan</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            kode_input = st.text_input("Kode Akses / PIN", type="password", placeholder="Masukkan kode login Anda...").strip()
            submit = st.form_submit_button("🔑 Masuk Dashboard", use_container_width=True)
            
            if submit:
                if kode_input in USERS_DB:
                    user_data = USERS_DB[kode_input]
                    st.session_state.logged_in = True
                    st.session_state.user_info = user_data
                    st.success(f"Selamat datang, {user_data['nama']}!")
                    st.rerun()
                else:
                    st.error("❌ Kode akses tidak valid! Silakan hubungi Administrator.")

def logout():
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.rerun()

# -----------------------------------------------------------------------------
# 5. SIDEBAR NAVIGATION & ROUTING UTAMA
# -----------------------------------------------------------------------------
if not st.session_state.logged_in:
    login()
else:
    user = st.session_state.user_info
    
    # 💡 KUNCI AMAN: Deklarasikan nama menu dalam konstanta
    MENU_ISU = "✍️ Isu Strategis"

    # Normalisasi daftar menu_diizinkan dari secrets agar selalu cocok
    raw_menu = user.get("akses_menu", [])
    menu_diizinkan = []
    for m in raw_menu:
        if "Isu Strategis" in m:
            menu_diizinkan.append(MENU_ISU)
        else:
            menu_diizinkan.append(m)

    # SIDEBAR ATAS: PROFIL USER & NAVIGASI    
    st.sidebar.markdown(f"**Pengguna:** {user['nama']}")    
    
    if st.sidebar.button("🚪 Keluar (Logout)", use_container_width=True):
        logout()

    if not menu_diizinkan:
        st.sidebar.warning("⚠️ Akun Anda belum diberikan akses ke menu mana pun. Hubungi Admin.")
    else:
        menu_pilihan = st.sidebar.radio(
            "Pilih Menu Dashboard:",
            menu_diizinkan,
            key="dashboard_menu_radio"
        )

        st.sidebar.markdown("---")

        # FILTER KABUPATEN & KECAMATAN DI SIDEBAR
        list_kabupaten = sorted(list(set(
            df_layanan['kabupaten_kota'].dropna().unique().tolist() +
            df_elektronik['kabupaten_kota'].dropna().unique().tolist() +
            df_sdm['kabupaten_kota'].dropna().unique().tolist() +
            df_psn['kabupaten_kota'].dropna().unique().tolist()
        )))
        list_kabupaten.insert(0, "Semua Kabupaten/Kota")
        selected_kab = st.sidebar.selectbox("Kabupaten / Kota", list_kabupaten)
        
        if selected_kab != "Semua Kabupaten/Kota":
            df_kec_pool = df_elektronik[df_elektronik['kabupaten_kota'] == selected_kab]
            list_kecamatan = sorted(df_kec_pool['kecamatan'].dropna().unique().tolist())
        else:
            list_kecamatan = sorted(df_elektronik['kecamatan'].dropna().unique().tolist())
            
        list_kecamatan.insert(0, "Semua Kecamatan")
        selected_kec = st.sidebar.selectbox("Kecamatan", list_kecamatan)
        
        if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        

        # FILTERING DATASET
        df_f_sdm = df_sdm.copy()
        df_f_psn = df_psn.copy()
        df_f_layanan = df_layanan.copy()
        df_f_elektronik = df_elektronik.copy()

        if selected_kab != "Semua Kabupaten/Kota":
            df_f_sdm = df_f_sdm[df_f_sdm['kabupaten_kota'] == selected_kab]
            df_f_psn = df_f_psn[df_f_psn['kabupaten_kota'] == selected_kab]
            df_f_layanan = df_f_layanan[df_f_layanan['kabupaten_kota'] == selected_kab]
            df_f_elektronik = df_f_elektronik[df_f_elektronik['kabupaten_kota'] == selected_kab]

        if selected_kec != "Semua Kecamatan" and 'kecamatan' in df_f_elektronik.columns:
            df_f_elektronik = df_f_elektronik[df_f_elektronik['kecamatan'] == selected_kec]

        globals()['df_f_elektronik'] = df_f_elektronik

        # ROUTING HALAMAN UTAMA
        if menu_pilihan == "🏛️ Profil & Anggaran":
            render_profil_anggaran(df_f_sdm)

        elif menu_pilihan == "🎯 PSN 2026":
            render_psn_2026(df_f_psn)

        elif menu_pilihan == "💼 Layanan Pertanahan":
            render_layanan_pertanahan(df_f_layanan)

        elif menu_pilihan == "⚡ Data Elektronik":
            render_pertanahan_elektronik(
                df_f_elektronik, 
                df_progress_raw, 
                df_peringkat_raw,
                selected_kab=selected_kab, 
                selected_kec=selected_kec
            )

        elif menu_pilihan == MENU_ISU:  # 👈 Menggunakan variabel MENU_ISU agar pasti match!
            render_isu_strategis(df_isu_raw)

        # SIDEBAR BAWAH: GRAFIK REKAPITULASI
        # ... (sisa kode grafik sidebar Anda di bawah) ...

        # SIDEBAR BAWAH: RENDER GRAFIK REKAPITULASI (AKHIR SIDEBAR)
        st.sidebar.markdown("---")
        KAB_MAP = {
            'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
            'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
            'Poso': 'PS', 'Tojo Una-una': 'TU', 'Toli-toli': 'TL',
            'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL',
            'Sigi': 'SG', 'Sulawesi Tengah': 'ST'
        }
        REVERSE_KAB_MAP = {v: k for k, v in KAB_MAP.items()}

        def singkat_kab(df_src):
            if not df_src.empty and 'kabupaten_kota' in df_src.columns:
                df_src['kab_singkat'] = df_src['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x))
            return df_src

        df_sdm_singkat = singkat_kab(df_sdm.copy())
        df_layanan_singkat = singkat_kab(df_layanan.copy())
        df_elek_singkat = singkat_kab(df_elektronik.copy())

        # ==========================================
        # 1. GRAFIK: Distribusi Pegawai (Sidebar - Custom Hover & Legenda Horizontal)
        # ==========================================
        if not df_sdm_singkat.empty and 'kategori_asn' in df_sdm_singkat.columns:
            df_sdm_rekap = df_sdm_singkat.groupby(['kab_singkat', 'kategori_asn']).size().reset_index(name='jumlah')
            df_sdm_pivot = df_sdm_rekap.pivot(index='kab_singkat', columns='kategori_asn', values='jumlah').fillna(0).astype(int)
            df_sdm_total = df_sdm_singkat.groupby('kab_singkat').size().reset_index(name='total_all')
            df_sdm_rekap = df_sdm_rekap.merge(df_sdm_pivot, on='kab_singkat').merge(df_sdm_total, on='kab_singkat')
            df_sdm_rekap = df_sdm_rekap.sort_values(by='total_all', ascending=False)
            
            # Tambahkan kolom nama lengkap untuk hover
            df_sdm_rekap['kab_full'] = df_sdm_rekap['kab_singkat'].map(lambda x: REVERSE_KAB_MAP.get(x, x))
            
            # Format teks hover dinamis berdasarkan kategori ASN yang ada
            hover_text = "<b>%{customdata[0]} | ASN %{customdata[1]} orang</b><br>"
            custom_data_cols = ['kab_full', 'total_all']
            for i, col in enumerate(df_sdm_pivot.columns):
                hover_text += f"{col}: %{{customdata[{i+2}]}} orang<br>"
                custom_data_cols.append(col)

            fig_sdm = px.bar(
                df_sdm_rekap, 
                x='kab_singkat', 
                y='jumlah', 
                color='kategori_asn',
                title="Distribusi Pegawai",
                custom_data=df_sdm_rekap[custom_data_cols]
            )
            
            # Terapkan template hover khusus
            fig_sdm.update_traces(hovertemplate=hover_text + "<extra></extra>")
            
            # Terapkan tata letak legenda horizontal dan tinggi area grafik
            fig_sdm.update_layout(
                showlegend=True, 
                legend_title_text='', 
                height=310,
                xaxis_title="", 
                yaxis_title="",
                xaxis={'categoryorder': 'total descending'},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=35, b=10),
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="right", 
                    x=1,
                    font=dict(size=9)
                )
            )
            
            st.sidebar.plotly_chart(fig_sdm, use_container_width=True)
            
        # 2. GRAFIK Anggaran
        # ==========================================
        # 2. GRAFIK: % Realisasi Anggaran (Sidebar - Custom Hover & Format Indonesia)
        # ==========================================
        if not df_sdm_singkat.empty and 'target_dipa' in df_sdm_singkat.columns and 'realisasi_dipa' in df_sdm_singkat.columns:
            df_anggaran = df_sdm_singkat.copy()
            
            # Fungsi pembersih angka numerik lokal
            def clean_num_local(val):
                if pd.isna(val) or val is None: 
                    return 0.0
                if isinstance(val, (int, float)): 
                    return float(val)
                clean_str = str(val).replace('.', '').replace(',', '').replace('Rp', '').strip()
                try: 
                    return float(clean_str)
                except ValueError: 
                    return 0.0

            # Terjemahkan kolom target dan realisasi
            df_anggaran['target_clean'] = df_anggaran['target_dipa'].apply(clean_num_local)
            df_anggaran['realisasi_clean'] = df_anggaran['realisasi_dipa'].apply(clean_num_local)
            
            # Agregasi total per kabupaten/kota
            df_ang_rekap = df_anggaran.groupby('kab_singkat')[['target_clean', 'realisasi_clean']].sum().reset_index()
            df_ang_rekap['persen_realisasi'] = (df_ang_rekap['realisasi_clean'] / df_ang_rekap['target_clean'].replace(0, 1)) * 100.0
            
            # Format teks Rupiah & Persen untuk Tooltip Hover (Pemisah ribuan titik)
            df_ang_rekap['target_fmt'] = df_ang_rekap['target_clean'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
            df_ang_rekap['realisasi_fmt'] = df_ang_rekap['realisasi_clean'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
            df_ang_rekap['persen_fmt'] = df_ang_rekap['persen_realisasi'].apply(lambda x: f"{x:.2f}".replace('.', ','))
            
            # Tambahkan kolom nama lengkap untuk hover
            df_ang_rekap['kab_full'] = df_ang_rekap['kab_singkat'].map(lambda x: REVERSE_KAB_MAP.get(x, x))
            
            # Urutkan dari persentase realisasi tertinggi ke terendah
            df_ang_rekap = df_ang_rekap.sort_values(by='persen_realisasi', ascending=False)

            # Render Bar Chart Plotly Sidebar
            fig_anggaran = px.bar(
                df_ang_rekap, 
                x='kab_singkat', 
                y='persen_realisasi',
                title="% Realisasi Anggaran",
                custom_data=df_ang_rekap[['kab_full', 'target_fmt', 'realisasi_fmt', 'persen_fmt']]
            )
            
            # Hover format khusus Rupiah & Persen
            fig_anggaran.update_traces(
                hovertemplate="<b>%{customdata[0]} | %{customdata[3]}%</b><br>Target: <b>Rp %{customdata[1]}</b><br>Realisasi: <b>Rp %{customdata[2]}</b><extra></extra>",
                marker_color='#17BECF'
            )
            
            fig_anggaran.update_layout(
                showlegend=False, 
                height=250,
                xaxis_title="", 
                yaxis_title="",
                xaxis={'categoryorder': 'total descending'},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=35, b=10),
                separators=',.',
                yaxis=dict(
                    gridcolor='#f2f2f2',
                    ticksuffix='%' # Menambahkan % pada sumbu-Y
                )
            )
            
            st.sidebar.plotly_chart(fig_anggaran, use_container_width=True)

        # 3. GRAFIK Berkas Tunggakan PDDM
        # ==========================================
        # 3. GRAFIK: Berkas Tunggakan PDDM (Sidebar - Custom Hover & Detail Posisi)
        # ==========================================
        if not df_layanan_singkat.empty and 'nmr_berkas' in df_layanan_singkat.columns:
            df_layanan_total = df_layanan_singkat.groupby('kab_singkat')['nmr_berkas'].count().reset_index(name='total_berkas')
            df_layanan_total = df_layanan_total.sort_values(by='total_berkas', ascending=False)
            
            # Tambahkan kolom nama lengkap untuk hover
            df_layanan_total['kab_full'] = df_layanan_total['kab_singkat'].map(lambda x: REVERSE_KAB_MAP.get(x, x))
            
            # Cek ketersediaan kolom posisi_berkas untuk breakdown detail posisi di hover
            if 'posisi_berkas' in df_layanan_singkat.columns:
                df_layanan_pos = df_layanan_singkat.groupby(['kab_singkat', 'posisi_berkas']).size().reset_index(name='jml_pos')
                df_layanan_pivot = df_layanan_pos.pivot(index='kab_singkat', columns='posisi_berkas', values='jml_pos').fillna(0).astype(int)
                df_layanan_total = df_layanan_total.merge(df_layanan_pivot, on='kab_singkat')
                
                hover_layanan = "<b>%{customdata[0]} | %{y} berkas</b><br>--- Detail Posisi ---<br>"
                custom_data_layanan = ['kab_full', 'total_berkas']
                for i, col in enumerate(df_layanan_pivot.columns):
                    hover_layanan += f"{col}: %{{customdata[{i+2}]}}<br>"
                    custom_data_layanan.append(col)
            else:
                hover_layanan = "<b>%{customdata[0]}</b><br>Total Berkas: %{y} berkas<br>"
                custom_data_layanan = ['kab_full', 'total_berkas']

            # Render Bar Chart Plotly Sidebar
            fig_layanan = px.bar(
                df_layanan_total, 
                x='kab_singkat', 
                y='total_berkas',
                title="Berkas Tunggakan PDDM",
                custom_data=df_layanan_total[custom_data_layanan] if custom_data_layanan else None
            )
            
            fig_layanan.update_traces(
                hovertemplate=hover_layanan + "<extra></extra>", 
                marker_color='#EF553B'
            )
            
            fig_layanan.update_layout(
                showlegend=False, 
                height=250,
                xaxis_title="", 
                yaxis_title="",
                xaxis={'categoryorder': 'total descending'},
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=35, b=10)
            )
            
            st.sidebar.plotly_chart(fig_layanan, use_container_width=True)

        # 4. GRAFIK % Prasertel (Dari jumlah_bt)
        col_bt = 'jumlah_bt' if 'jumlah_bt' in df_elek_singkat.columns else 'bt_valid'
        if not df_elek_singkat.empty and 'pra_sertel' in df_elek_singkat.columns and col_bt in df_elek_singkat.columns:
            df_elek_rekap = df_elek_singkat.copy()
            def parse_sidebar_int(val):
                if pd.isna(val) or val is None: return 0
                s = str(val).strip()
                if not s or s.lower() in ['nan', 'none', 'null', '']: return 0
                s = f"{val:.3f}".replace('.', '') if isinstance(val, float) else s.replace('.', '').replace(',', '').replace('Rp', '').replace('%', '').strip()
                try: return int(s)
                except ValueError: return 0

            df_elek_rekap['pra_sertel_clean'] = df_elek_rekap['pra_sertel'].apply(parse_sidebar_int)
            df_elek_rekap['bt_clean']         = df_elek_rekap[col_bt].apply(parse_sidebar_int)

            df_elek_grp = df_elek_rekap.groupby('kab_singkat')[['pra_sertel_clean', 'bt_clean']].sum().reset_index()
            df_elek_grp['Persentase'] = (df_elek_grp['pra_sertel_clean'] / df_elek_grp['bt_clean'].replace(0, 1)) * 100.0
            df_elek_grp = df_elek_grp.sort_values(by='Persentase', ascending=False)

            df_elek_grp['pra_sertel_fmt'] = df_elek_grp['pra_sertel_clean'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
            df_elek_grp['bt_fmt']         = df_elek_grp['bt_clean'].apply(lambda x: f"{x:,.0f}".replace(',', '.'))
            df_elek_grp['kab_full']       = df_elek_grp['kab_singkat'].map(lambda x: REVERSE_KAB_MAP.get(x, x))

            fig_elek = px.bar(
                df_elek_grp, x='kab_singkat', y='Persentase',
                title="% Prasertel", custom_data=df_elek_grp[['kab_full', 'pra_sertel_fmt', 'bt_fmt']]
            )
            fig_elek.update_traces(
                hovertemplate="<b>%{customdata[0]} | %{y:.2f}%</b><br>Jumlah Prasertel: <b>%{customdata[1]}</b><br>Jumlah BT: <b>%{customdata[2]}</b><extra></extra>",
                marker_color='#00CC96'
            )
            fig_elek.update_layout(
                showlegend=False, height=250, xaxis_title="", yaxis_title="",
                xaxis={'categoryorder': 'total descending'}, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=35, b=10), separators=',.', yaxis=dict(gridcolor='#f2f2f2', ticksuffix='%')
            )
            st.sidebar.plotly_chart(fig_elek, use_container_width=True)
