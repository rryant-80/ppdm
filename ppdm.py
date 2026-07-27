import re
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# 1. KONFIGURASI HALAMAN & UTILITY FUNCTIONS (GLOBAL)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Pertanahan Sulteng 2026",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

USERS_DB = st.secrets.get("users", {})
SHEET_ID = st.secrets["gsheet_id"]
GSHEET_WEBAPP_URL = st.secrets["gsheet_webapp_url"]

KAB_MAP = {
    'Banggai': 'BG', 'Banggai Kepulauan': 'BK', 'Banggai Laut': 'BL',
    'Buol': 'BU', 'Donggala': 'DG', 'Parigi Moutong': 'PM',
    'Poso': 'PS', 'Tojo Una-una': 'TU', 'Toli-toli': 'TL', 'Toli Toli': 'TL',
    'Morowali': 'MW', 'Morowali Utara': 'MU', 'Palu': 'PL', 'Kota Palu': 'PL',
    'Sigi': 'SG', 'Sulawesi Tengah': 'ST'
}
REVERSE_KAB_MAP = {v: k for k, v in KAB_MAP.items()}

# Fungsi Pembantu Global (Menghindari Redundansi)
def parse_num(val, is_float=False):
    """Membersihkan nilai numerik dari teks, simbol, atau error #N/A."""
    if pd.isna(val) or val is None:
        return 0.0 if is_float else 0
    s_val = str(val).replace('Rp', '').replace('%', '').strip()
    if s_val.lower() in {'#n/a', 'nan', 'none', '', '#ref!', '#value!'}:
        return 0.0 if is_float else 0
    clean_str = s_val.replace('.', '').replace(',', '.') if ',' in s_val else s_val.replace('.', '')
    try:
        return float(clean_str) if is_float else int(round(float(s_val.replace('.', '').replace(',', ''))))
    except ValueError:
        return 0.0 if is_float else 0

def fmt_idr(val):
    return f"{val:,.0f}".replace(',', '.')

def fmt_pct(val):
    return f"{val:.2f}".replace('.', ',')

def fmt_decimal(val):
    parts = f"{val:,.2f}".split('.')
    return f"{parts[0].replace(',', '.')},{parts[1]}"

def render_card(title, value, sub_value="", border_color="#1E88E5", bg_gradient="#f0f7ff"):
    card_html = f"""
    <div style="background: linear-gradient(135deg, #ffffff 0%, {bg_gradient} 100%);
                border-left: 5px solid {border_color}; border-radius: 8px; padding: 10px 12px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.05); margin-bottom: 10px; height: 100%;
                display: flex; flex-direction: column; justify-content: center;">
        <div style="color: #555; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;">{title}</div>
        <div style="color: #0D47A1; font-size: 1.15rem; font-weight: 700; margin-top: 2px;">{value}</div>
        {f'<div style="color: #666; font-size: 0.70rem; margin-top: 1px;">{sub_value}</div>' if sub_value else ''}
    </div>"""
    st.markdown(card_html, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOAD DATA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_data(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:        
        return pd.read_csv(url, dtype=str)
    except Exception as e:
        st.error(f"Gagal memuat data GID {gid}: {e}")
        return pd.DataFrame()

df_layanan = load_data("1447858691")
df_elektronik = load_data("1848496896")
df_sdm = load_data("1168898330")
df_psn = load_data("193371600")
df_progress_raw = load_data("386436131")
df_peringkat_raw = load_data("880542789")
df_isu_raw = load_data("1699480367")

# -----------------------------------------------------------------------------
# 3. MODUL HALAMAN
# -----------------------------------------------------------------------------
def render_profil_anggaran(df_filtered_sdm):
    st.title("🏛️ Profil & Anggaran")
    st.markdown("---")
    df_elek_ctx = globals().get('df_f_elektronik', pd.DataFrame())

    def get_pejabat_info(df, jabatan_name):
        match = df[df['jabatan'].astype(str).str.contains(jabatan_name, case=False, na=False)]
        DEFAULT_IMG = "https://via.placeholder.com/150?text=No+Image"
        if not match.empty:
            row = match.iloc[0]
            target, realisasi = parse_num(row.get('target_dipa', 0), True), parse_num(row.get('realisasi_dipa', 0), True)
            url_val = row.get('url', '')
            return {
                "nama": row.get('pegawai', '-'), "jabatan": row.get('jabatan', jabatan_name),
                "url": url_val if pd.notna(url_val) and str(url_val).startswith('http') else DEFAULT_IMG,
                "target": target, "realisasi": realisasi, "persen": (realisasi / target * 100) if target > 0 else 0.0
            }
        return {"nama": "Belum Ada Data", "jabatan": jabatan_name, "url": DEFAULT_IMG, "target": 0, "realisasi": 0, "persen": 0.0}

    p0, p1, p2 = get_pejabat_info(df_filtered_sdm, "Juru Ukur"), get_pejabat_info(df_filtered_sdm, "Bendahara"), get_pejabat_info(df_filtered_sdm, "Kepala Kantor")

    col_l, col_r = st.columns([2, 3])
    with col_l:
        c1, c2, c3 = st.columns(3)
        c1.image(p0["url"], use_column_width=True)
        c2.image(p1["url"], use_column_width=True)
        c3.image(p2["url"], use_column_width=True)

    with col_r:
        jml_peg = len(df_filtered_sdm)
        jml_kec = df_elek_ctx['kecamatan'].nunique() if 'kecamatan' in df_elek_ctx.columns else 0
        jml_desa = df_elek_ctx['desa_kelurahan'].nunique() if 'desa_kelurahan' in df_elek_ctx.columns else 0
        
        luas_adm_ha = df_elek_ctx['luas_adm'].apply(parse_num, is_float=True).sum() / 10000.0 if 'luas_adm' in df_elek_ctx.columns else 0
        luas_apl_ha = df_elek_ctx['luas_apl'].apply(parse_num, is_float=True).sum() / 10000.0 if 'luas_apl' in df_elek_ctx.columns else 0
        pct_apl = (luas_apl_ha / luas_adm_ha * 100) if luas_adm_ha > 0 else 0.0

        tot_target = df_filtered_sdm['target_dipa'].apply(parse_num, is_float=True).sum() if 'target_dipa' in df_filtered_sdm.columns else 0.0
        tot_real = df_filtered_sdm['realisasi_dipa'].apply(parse_num, is_float=True).sum() if 'realisasi_dipa' in df_filtered_sdm.columns else 0.0
        tot_pct = (tot_real / tot_target * 100) if tot_target > 0 else 0.0

        c1, c2, c3 = st.columns(3)
        with c1: render_card("Jumlah Pegawai", f"{jml_peg} Orang")
        with c2: render_card("Jumlah Kecamatan", f"{fmt_idr(jml_kec)}")
        with c3: render_card("Jumlah Desa/Kelurahan", f"{fmt_idr(jml_desa)}")

        c4, c5, c6 = st.columns(3)
        with c4: render_card("Realisasi Dipa", f"{fmt_pct(tot_pct)}%", f"Rp {fmt_idr(tot_real)}")
        with c5: render_card("Luas Wilayah", f"{fmt_decimal(luas_adm_ha)} Ha")
        with c6: render_card("Luas APL", f"{fmt_decimal(luas_apl_ha)} Ha", f"{fmt_pct(pct_apl)}% dari Luas Wilayah")

    st.subheader("👥 Pejabat Struktural")
    jabatans = ["Tata Usaha", "Survei dan Pemetaan", "Penetapan Hak dan Pendaftaran", "Penataan dan Pemberdayaan", "Pengadaan Tanah dan Pengembangan", "Pengendalian dan Penanganan Sengketa"]
    cols = st.columns(3) + st.columns(3)
    for idx, jab in enumerate(jabatans):
        p = get_pejabat_info(df_filtered_sdm, jab)
        with cols[idx]:
            with st.container(border=True):
                sc1, sc2 = st.columns([1, 2.2])
                sc1.image(p["url"], use_column_width=True)
                with sc2:
                    st.markdown(f"<b>{p['nama']}</b><br><small>{p['jabatan']}</small><br><small>Target: <b>Rp {fmt_idr(p['target'])}</b></small>", unsafe_allow_html=True)
                    st.progress(min(max(p['persen'] / 100.0, 0.0), 1.0))
                    st.markdown(f"<div style='text-align:right; font-size:0.7rem;'>Realisasi: <b style='color:#00CC96;'>{fmt_pct(p['persen'])}%</b> (Rp {fmt_idr(p['realisasi'])})</div>", unsafe_allow_html=True)

def render_psn_2026(df_filtered_psn):
    st.title("🎯 Proyek Strategis Nasional (PSN) 2026")
    if df_filtered_psn.empty:
        st.warning("Data PSN kosong untuk filter yang dipilih.")
        return

    df = df_filtered_psn.copy()
    df['kab_singkat'] = df['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x)) if 'kabupaten_kota' in df.columns else '-'
    
    pbt_real_cols = ['realisasi_baru', 'realisasi_k4', 'realisasi_repo']
    integer_cols = ['target_pbt', 'target_shat', 'puldadis', 'berkas', 'potensi', 'k1', 'siap_serah', 'diserahkan', 'target_redis', 'pos_redis', 'sk_redis', 'sertipikat_redis', 'target_lintor', 'lintor_su', 'lintor_sk', 'lintor_sertipikat', 'lintor_serah']

    for c in integer_cols: df[c] = df[c].apply(parse_num) if c in df.columns else 0
    for c in pbt_real_cols: df[c] = df[c].apply(parse_num, is_float=True) if c in df.columns else 0.0

    df_rekap = df.groupby('kab_singkat')[integer_cols + pbt_real_cols].sum().reset_index()

    def create_psn_chart(title, target_col, metrics_dict, colors, unit="Bdg", is_stacked=False):
        df_v = df_rekap[df_rekap[target_col] > 0].copy()
        if df_v.empty: return px.bar(title=f"{title} (Tidak ada target aktif)")
        
        long_rows = []
        for _, row in df_v.iterrows():
            tgt = row[target_col]
            for label, col in metrics_dict.items():
                real = row[col]
                pct = (real / tgt * 100) if tgt > 0 else 0.0
                long_rows.append({
                    'Kab/Kota': row['kab_singkat'], 'Indikator': label, 'Persentase': pct,
                    'Real_Fmt': f"{fmt_decimal(real) if unit=='Ha' else fmt_idr(real)} {unit}",
                    'Target_Fmt': f"{fmt_decimal(tgt) if unit=='Ha' else fmt_idr(tgt)} {unit}",
                    'Pct_Fmt': fmt_decimal(pct)
                })
        fig = px.bar(pd.DataFrame(long_rows), x='Kab/Kota', y='Persentase', color='Indikator', barmode='relative' if is_stacked else 'group', title=title, color_discrete_sequence=colors, custom_data=['Real_Fmt', 'Target_Fmt', 'Pct_Fmt'])
        fig.update_traces(hovertemplate="<b>Kab/Kota: %{x}</b><br>Indikator: %{fullData.name}<br>Realisasi: %{customdata[0]}<br>Target: %{customdata[1]}<br>Persentase: %{customdata[2]}%<extra></extra>")
        fig.update_layout(height=310, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=5, r=5, t=32, b=5), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        return fig

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)
    c1.plotly_chart(create_psn_chart("1. Realisasi PBT", 'target_pbt', {'Bidang Baru': 'realisasi_baru', 'Pemetaan K4': 'realisasi_k4', 'Reposisi Bidang': 'realisasi_repo'}, ['#dbdbdb', '#a9a9a9', '#656565'], "Ha", True), use_container_width=True)
    c2.plotly_chart(create_psn_chart("2. Realisasi SHAT", 'target_shat', {'Puldadis': 'puldadis', 'Berkas': 'berkas', 'K1': 'k1', 'Diserahkan': 'diserahkan'}, ['#b4ffb3', '#44bc43', '#1f9f1d', '#026b00']), use_container_width=True)
    c3.plotly_chart(create_psn_chart("3. Realisasi Redistribusi", 'target_redis', {'Subyek Obyek': 'pos_redis', 'SK Redis': 'sk_redis', 'Sertipikat Redis': 'sertipikat_redis'}, ['#99eaf2', '#17BECF', '#0097a6']), use_container_width=True)
    c4.plotly_chart(create_psn_chart("4. Realisasi Lintor", 'target_lintor', {'Lintor SU': 'lintor_su', 'Lintor SK': 'lintor_sk', 'Lintor Sertipikat': 'lintor_serah' if 'lintor_serah' in df_rekap.columns and df_rekap['lintor_serah'].sum() > 0 else 'lintor_sertipikat'}, ['#f0d9a0', '#FECB52', '#fcb100']), use_container_width=True)

def render_layanan_pertanahan(df_filtered_layanan):
    st.markdown("### 🚨 Berkas Tunggakan PDDM")
    if df_filtered_layanan.empty:
        st.warning("Data Layanan Pertanahan kosong.")
        return

    df = df_filtered_layanan.copy()
    df['durasi_clean'] = df['durasi'].apply(parse_num)
    df['tgl_mulai_dt'] = pd.to_datetime(df['tgl_mulai'], dayfirst=True, errors='coerce')
    df['tgl_batas_sop'] = df['tgl_mulai_dt'] + pd.to_timedelta(df['durasi_clean'], unit='D')
    
    today = pd.to_datetime(date.today())
    df_overdue = df[(today > df['tgl_batas_sop']) & (df['tgl_mulai_dt'].notna())].copy()
    df_overdue['kab_clean'] = df_overdue['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x))
    df_overdue['berkas_thn'] = df_overdue['nmr_berkas'].astype(str) + "/" + df_overdue['thn_berkas'].astype(str)

    # Styling Matrix Strobo
    st.markdown("<style>.strobo{background:linear-gradient(135deg, #ff3333, #cc0000); color:white; font-weight:700; text-align:center; padding:4px; border-radius:6px; font-size:0.78rem;}.tuntas{background:#28a745; color:white; text-align:center; padding:4px; border-radius:6px; font-size:0.78rem;}</style>", unsafe_allow_html=True)
    
    POSISI = ["Kakan", "Kasi SP", "Kasi PHP", "Loket"]
    cols = st.columns([2.2, 1.8, 1.8, 1.8, 1.8])
    cols[0].markdown("<b>Kantor Pertanahan</b>", unsafe_allow_html=True)
    for i, p in enumerate(POSISI): cols[i+1].markdown(f"<b>{p}</b>", unsafe_allow_html=True)

    for kab in sorted(df_overdue['kab_clean'].dropna().unique()):
        cols = st.columns([2.2, 1.8, 1.8, 1.8, 1.8])
        cols[0].markdown(f"<small>📍 {kab}</small>", unsafe_allow_html=True)
        for i, pos in enumerate(POSISI):
            cnt = len(df_overdue[(df_overdue['kab_clean'] == kab) & (df_overdue['posisi_berkas'].str.contains(pos, case=False, na=False))])
            if cnt > 0:
                cols[i+1].markdown(f"<div class='strobo'>🚨 {cnt} Berkas</div>", unsafe_allow_html=True)
            else:
                cols[i+1].markdown("<div class='tuntas'>✔ Tuntas</div>", unsafe_allow_html=True)

    if not df_overdue.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 Detail Berkas Tunggakan PDDM")
        st.dataframe(df_overdue[['kab_clean', 'berkas_thn', 'nama', 'nama_prosedur', 'posisi_berkas', 'kendala', 'upaya_penyelesaian']], use_container_width=True)

def render_pertanahan_elektronik(df_elektronik, df_progress=None, df_peringkat=None, selected_kab=None, selected_kec=None):
    st.title("💻 Data Elektronik")
    if df_elektronik.empty: return

    df = df_elektronik.copy()
    for col in ['luas_adm', 'luas_apl', 'luas_persil', 'luas_persil_valid']: df[col] = df[col].apply(parse_num, is_float=True) if col in df.columns else 0.0
    for col in ['jumlah_persil', 'jumlah_kw456', 'jumlah_bt', 'bt_valid', 'jumlah_su', 'pra_suel', 'pra_btel', 'pra_sertel']: df[col] = df[col].apply(parse_num) if col in df.columns else 0

    df_clean = df[~df['kabupaten_kota'].astype(str).str.contains('Total|Jumlah', case=False, na=False)].copy()

    # Cards Grid
    c1, c2, c3, c4, c5 = st.columns(5)
    tot_adm, tot_apl = df_clean['luas_adm'].sum()/10000.0, df_clean['luas_apl'].sum()/10000.0
    render_card("Luas APL", f"{fmt_pct((tot_apl/tot_adm*100) if tot_adm>0 else 0)}%", f"{fmt_decimal(tot_apl)} Ha", border_color="#f39c12")
    render_card("Luas Persil", f"{fmt_decimal(df_clean['luas_persil'].sum()/10000.0)} Ha", border_color="#f39c12")
    render_card("Jumlah BT Valid", f"{fmt_idr(df_clean['bt_valid'].sum())} BT", border_color="#f39c12")
    render_card("Progress Terbaru", f"+{fmt_idr(0)} Pra Sertel", border_color="#0451c9")
    render_card("Peringkat Nasional", "Sulteng #-", border_color="#0451c9")

    # Chart Section
    st.markdown("---")
    df_clean['pct_pra_sertel'] = (df_clean['pra_sertel'] / df_clean['jumlah_bt'].replace(0, 1)) * 100.0
    fig = px.bar(df_clean.sort_values(by='pct_pra_sertel', ascending=False), x='kabupaten_kota', y='pct_pra_sertel', title="📊 Grafik Capaian Pra-SERTEL")
    st.plotly_chart(fig, use_container_width=True)

def render_isu_strategis(df_isu):
    st.title("✍️ Diskusi Isu Strategis")
    with st.expander("➕ Tambah Isu Strategis Baru"):
        with st.form("form_isu"):
            pembuat = st.text_input("Nama & Jabatan")
            isu = st.text_area("Deskripsi Isu")
            if st.form_submit_button("Kirim"):
                if pembuat and isu:
                    payload = {"gid": "1699480367", "tgl_jam": datetime.now(ZoneInfo("Asia/Makassar")).strftime("%Y-%m-%d %H:%M:%S"), "isu_strategis": isu, "pembuat": pembuat}
                    requests.post(GSHEET_WEBAPP_URL, json=payload)
                    st.cache_data.clear()
                    st.rerun()

    if df_isu is not None and not df_isu.empty:
        for idx, row in df_isu.iterrows():
            st.info(f"**{row.get('pembuat','-')}**: {row.get('isu_strategis','-')}")

# -----------------------------------------------------------------------------
# 4. SIDEBAR: MENU UTAMA DIPINDAHKAN KE ATAS GRAFIK
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("🗂️ Menu Utama")
    
    # 1. MENU UTAMA RADIO BUTTON DITAROH DI ATAS (Sesuai Permintaan)
    user_access = st.session_state.get("user_info", {}).get("akses_menu", [
        "🏛️ Profil & Anggaran", "🎯 PSN 2026", "💼 Layanan Pertanahan", "⚡ Data Elektronik", "📌 Isu Strategis"
    ])
    
    menu_pilihan = st.radio(
        "Pilih Halaman:",
        user_access,
        key="main_menu_pilihan"
    )
    
    st.markdown("---")
    st.header("📋 Filter Data")
    
    list_kabupaten = sorted(list(set(
        df_layanan['kabupaten_kota'].dropna().unique().tolist() +
        df_elektronik['kabupaten_kota'].dropna().unique().tolist()
    )))
    list_kabupaten.insert(0, "Semua Kabupaten/Kota")
    selected_kab = st.selectbox("Kabupaten / Kota", list_kabupaten)
    
    list_kecamatan = sorted(df_elektronik[df_elektronik['kabupaten_kota'] == selected_kab]['kecamatan'].dropna().unique().tolist()) if selected_kab != "Semua Kabupaten/Kota" else sorted(df_elektronik['kecamatan'].dropna().unique().tolist())
    list_kecamatan.insert(0, "Semua Kecamatan")
    selected_kec = st.selectbox("Kecamatan", list_kecamatan)
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("📊 ringkasan Wilayah")

    # 2. GRAFIK-GRAFIK SIDEBAR (Ditaruh di Bawah Menu Utama)
    if not df_sdm.empty:
        df_sdm_singkat = df_sdm.copy()
        df_sdm_singkat['kab_singkat'] = df_sdm_singkat['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x))
        df_sdm_rekap = df_sdm_singkat.groupby(['kab_singkat', 'kategori_asn']).size().reset_index(name='jumlah')
        fig_sdm = px.bar(df_sdm_rekap, x='kab_singkat', y='jumlah', color='kategori_asn', title="Distribusi Pegawai")
        fig_sdm.update_layout(height=220, showlegend=False, margin=dict(l=5, r=5, t=25, b=5))
        st.plotly_chart(fig_sdm, use_container_width=True)

    if not df_layanan.empty:
        df_lay_singkat = df_layanan.copy()
        df_lay_singkat['kab_singkat'] = df_lay_singkat['kabupaten_kota'].map(lambda x: KAB_MAP.get(x, x))
        df_lay_rekap = df_lay_singkat.groupby('kab_singkat')['nmr_berkas'].count().reset_index(name='total')
        fig_lay = px.bar(df_lay_rekap, x='kab_singkat', y='total', title="Berkas Tunggakan PDDM")
        fig_lay.update_traces(marker_color='#EF553B')
        fig_lay.update_layout(height=200, margin=dict(l=5, r=5, t=25, b=5))
        st.plotly_chart(fig_lay, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. FILTERING DATA GLOBAL
# -----------------------------------------------------------------------------
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
    df_f_elektronik = df_f_elektronik[df_f_elektronik['kecamatan'] == selected_kec]

# -----------------------------------------------------------------------------
# 6. ROUTING DAN AUTHENTICATION
# -----------------------------------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔐 Login Dashboard Pertanahan</h2>", unsafe_allow_html=True)
    with st.form("form_login"):
        kode_input = st.text_input("Kode Akses / PIN", type="password").strip()
        if st.form_submit_button("🔑 Masuk Dashboard", use_container_width=True):
            if kode_input in USERS_DB:
                st.session_state.logged_in = True
                st.session_state.user_info = USERS_DB[kode_input]
                st.rerun()
            else:
                st.error("❌ Kode akses salah!")
else:
    # Router Halaman Berdasarkan Radio Button Pilihan di Sidebar Atas
    if menu_pilihan == "🏛️ Profil & Anggaran":
        render_profil_anggaran(df_f_sdm)
    elif menu_pilihan == "🎯 PSN 2026":
        render_psn_2026(df_f_psn)
    elif menu_pilihan == "💼 Layanan Pertanahan":
        render_layanan_pertanahan(df_f_layanan)
    elif menu_pilihan == "⚡ Data Elektronik":
        render_pertanahan_elektronik(df_f_elektronik, df_progress_raw, df_peringkat_raw, selected_kab, selected_kec)
    elif menu_pilihan == "📌 Isu Strategis":
        render_isu_strategis(df_isu_raw)
