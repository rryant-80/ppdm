import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.markdown("""
<style>
    .profile-box {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
        background-color: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .profile-name {
        font-weight: bold;
        font-size: 14px;
        color: #1e293b;
    }
    .profile-title {
        font-size: 12px;
        color: #64748b;
        margin-bottom: 4px;
    }
    .profile-target {
        font-size: 11px;
        color: #059669;
        margin-bottom: 4px;
    }
    .custom-card {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 6px;
    }
    .card-title {
        font-size: 11px;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .card-value {
        font-size: 18px;
        font-weight: 700;
        color: #0f172a;
        margin: 2px 0;
    }
    .card-subtext {
        font-size: 10px;
        color: #94a3b8;
    }
    /* Efek Kedip Lampu Strobo Merah */
    @keyframes strobo-red {
        0% { background-color: #ef4444; box-shadow: 0 0 4px #ef4444; }
        50% { background-color: #b91c1c; box-shadow: 0 0 16px #b91c1c; }
        100% { background-color: #ef4444; box-shadow: 0 0 4px #ef4444; }
    }
    .strobo-lamp {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
        animation: strobo-red 1s infinite;
        margin-right: 8px;
        vertical-align: middle;
    }
    .strobo-container {
        border: 1px solid #fca5a5;
        border-radius: 8px;
        padding: 12px;
        background-color: #fef2f2;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)
# =========================================================================
# 1. KONEKSI & LOAD DATA DARI GOOGLE SHEETS
# =========================================================================
# Mengambil id sheet dari secrets. Skenario fallback jika nama key berbeda.
sheet_id = st.secrets.get("sheet_id", st.secrets.get("SHEET_ID", None))
gid = "1447858691"

if sheet_id is None:
    st.error("❌ 'id sheet' belum ditemukan di Streamlit Secrets. Pastikan nama key di secrets sesuai (misal: sheet_id = 'YOUR_ID').")
    st.stop()

# Membentuk URL export CSV khusus untuk GID target
sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

@st.cache_data(ttl=300) # Simpan data di cache selama 5 menit agar aplikasi cepat load
def load_data_from_sheets(url):
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"⚠️ Gagal mengambil data dari Google Sheets: {e}")
        return pd.DataFrame()

# Membaca data dasar
df_source = load_data_from_sheets(sheet_url)

# Validasi jika data kosong
if df_source.empty:
    st.warning("Data kosong atau gagal dimuat. Periksa kembali konfigurasi ID Sheet dan koneksi internet Anda.")
    st.stop()

# Menyesuaikan penamaan jika variabel utama sistem Anda menggunakan `df_pros_filtered`
df_pros_filtered = df_source.copy()


# =========================================================================
# 2. MODEL MONITORING LAMPU STROBO SOP (DIBAWAH PROFIL & GRAFIK PERSIL)
# =========================================================================
st.subheader("🚨 Berkas Permohonan Melebihi Durasi SOP per Kantah")

if not df_pros_filtered.empty:
    df_strobo = df_pros_filtered.copy()
    
    # 1. Parsing Tanggal & Kalkulasi Batas Toleransi SOP
    df_strobo['tgl_mulai'] = pd.to_datetime(df_strobo['tgl_mulai'], errors='coerce')
    df_strobo['durasi'] = pd.to_numeric(df_strobo['durasi'], errors='coerce').fillna(0)
    
    # Batas Tanggal Akhir SOP = tgl_mulai + durasi hari
    df_strobo['batas_sop'] = df_strobo['tgl_mulai'] + pd.to_timedelta(df_strobo['durasi'], unit='D')
    
    # Berkas dianggap melebihi SOP jika batas_sop sudah lewat dari waktu sekarang
    waktu_sekarang = pd.Timestamp.now()
    df_strobo['over_sop'] = df_strobo['batas_sop'] < waktu_sekarang
    
    # 2. Filter Kategori Posisi Berkas yang Diijinkan
    kategori_target = ["Kakan", "Kasi SP", "Kasi PHP", "Loket"]
    
    def cek_kategori(posisi):
        pos_clean = str(posisi).strip().lower()
        for kat in kategori_target:
            if kat.lower() in pos_clean:
                return kat
        return None
        
    df_strobo['kategori_clean'] = df_strobo['posisi_berkas'].apply(cek_kategori)
    
    # Menyaring berkas yang: Melebihi SOP DAN masuk dalam 4 Kategori Jabatan
    df_alert = df_strobo[(df_strobo['over_sop'] == True) & (df_strobo['kategori_clean'].notna())].copy()
    
    # PASTIKAN KOLOM KANTAH ADA DAN TIDAK KOSONG
    if 'kantah_kab' not in df_alert.columns:
        if 'kantah' in df_alert.columns:
            df_alert['kantah_kab'] = df_alert['kantah']
        else:
            df_alert['kantah_kab'] = 'Belum Terdata'

    # =====================================================================
    # PENDEKATAN SATU LAYAR: MATRIKS REKAPITULASI TOTAL OVER SOP PER KANTAH
    # =====================================================================
    st.markdown("### 📊 Ringkasan Eksekutif (Dashboard Matriks)")
    
    if not df_alert.empty:
        # Mengelompokkan data berdasarkan Kantah dan Kategori Jabatan
        df_matrix = df_alert.groupby(['kantah_kab', 'kategori_clean']).size().unstack(fill_value=0)
        
        # Memastikan semua kategori target muncul di kolom matriks meskipun 0
        for kat in kategori_target:
            if kat not in df_matrix.columns:
                df_matrix[kat] = 0
                
        # Mengurutkan kolom sesuai urutan SOP workflow
        df_matrix = df_matrix[kategori_target]
        df_matrix['TOTAL OVER SOP'] = df_matrix.sum(axis=1)
        df_matrix = df_matrix.sort_values(by='TOTAL OVER SOP', ascending=False)
        
        # Menampilkan tabel interaktif warna gradasi merah yang muat di satu layar
        st.dataframe(
            df_matrix.style.background_gradient(cmap='Reds', subset=kategori_target)
                           .format("{:,}"),
            use_container_width=True
        )
    else:
        st.success("🎉 Luar biasa! Seluruh berkas di semua Kantah dalam posisi aman & sesuai durasi SOP.")
    
    st.markdown("---")
    st.markdown("### 🔍 Detail Distribusi Visual per Kantah")

    # Pastikan mengambil list kolom penanda daerah/kantah dari data awal agar yang 'Aman' tetap muncul
    kolom_kantah_induk = 'kantah_kab' if 'kantah_kab' in df_pros_filtered.columns else ('kantah' if 'kantah' in df_pros_filtered.columns else None)
    
    if kolom_kantah_induk:
        semua_kantah = sorted(df_pros_filtered[kolom_kantah_induk].dropna().unique())
        
        # Menggunakan container expander horizontal agar hemat space layar
        for kantah in semua_kantah:
            df_kantah = df_alert[df_alert['kantah_kab'] == kantah]
            total_kantah_over = len(df_kantah)
            
            # Penamaan status header kantah
            if total_kantah_over > 0:
                header_text = f"🏢 {str(kantah).upper()} 🔴 ({total_kantah_over} Berkas Over SOP)"
            else:
                header_text = f"🏢 {str(kantah).upper()} 🟢 (Semua Berkas Aman)"
                
            with st.expander(header_text, expanded=(total_kantah_over > 0)):
                if total_kantah_over > 0:
                    c1, c2, c3, c4 = st.columns(4)
                    blocks = [("Kakan", c1), ("Kasi SP", c2), ("Kasi PHP", c3), ("Loket", c4)]
                    
                    for nama_kat, kolom_tujuan in blocks:
                        with kolom_tujuan:
                            df_kat_spesifik = df_kantah[df_kantah['kategori_clean'] == nama_kat].copy()
                            jumlah_over = len(df_kat_spesifik)
                            
                            if jumlah_over > 0:
                                st.markdown(
                                    f'<div style="border:1px solid #fca5a5; border-radius:6px; padding:6px 10px; background-color:#fef2f2; margin-bottom:5px;">'
                                    f'<span style="font-weight:bold; color:#991b1b; font-size:12px;">🔴 {nama_kat.upper()}: {jumlah_over} brks</span>'
                                    f'</div>', 
                                    unsafe_allow_html=True
                                )
                                df_kat_spesifik['nmr_thn'] = df_kat_spesifik['nmr_berkas'].astype(str) + "/" + df_kat_spesifik['thn_berkas'].astype(str)
                                list_brk = ", ".join(df_kat_spesifik['nmr_thn'].tolist())
                                st.caption(f"No: {list_brk}")
                            else:
                                st.markdown(
                                    f'<div style="border:1px solid #e2e8f0; border-radius:6px; padding:6px 10px; background-color:#f8fafc; margin-bottom:5px;">'
                                    f'<span style="color:#64748b; font-size:12px;">🟢 {nama_kat.upper()}: 0</span>'
                                    f'</div>', 
                                    unsafe_allow_html=True
                                )
                else:
                    st.success(f"Tidak ada penumpukan berkas melebihi durasi SOP di {kantah}.")
    else:
        st.info("Kolom wilayah/kantah tidak terdeteksi pada struktur data sheet.")

else:
    st.info("Tidak ada data pelacakan durasi prosedur berkas saat ini.")
st.markdown("<br><hr><br>", unsafe_allow_html=True)
