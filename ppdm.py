import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================================================================
# 1. KONEKSI & LOAD DATA DARI GOOGLE SHEETS
# =========================================================================
sheet_id = st.secrets.get("sheet_id", st.secrets.get("SHEET_ID", None))
gid = "1447858691"

if sheet_id is None:
    st.error("❌ 'id sheet' belum ditemukan di Streamlit Secrets. Pastikan nama key di secrets sesuai (misal: sheet_id = 'YOUR_ID').")
    st.stop()

sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

@st.cache_data(ttl=300)
def load_data_from_sheets(url):
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"⚠️ Gagal mengambil data dari Google Sheets: {e}")
        return pd.DataFrame()

df_source = load_data_from_sheets(sheet_url)

if df_source.empty:
    st.warning("Data kosong atau gagal dimuat. Periksa kembali konfigurasi ID Sheet dan koneksi internet Anda.")
    st.stop()

df_pros_filtered = df_source.copy()


# =========================================================================
# --- MODEL MONITORING LAMPU STROBO SOP (DIBAWAH PROFIL & GRAFIK PERSIL) ---
# =========================================================================
st.subheader("🚨 Monitoring Lampu Strobo: Berkas Melebihi Durasi SOP")

if not df_pros_filtered.empty:
    df_strobo = df_pros_filtered.copy()
    
    # 1. Parsing Tanggal & Kalkulasi Batas Toleransi SOP
    df_strobo['tgl_mulai'] = pd.to_datetime(df_strobo['tgl_mulai'], errors='coerce')
    df_strobo['durasi'] = pd.to_numeric(df_strobo['durasi'], errors='coerce').fillna(0)
    df_strobo['batas_sop'] = df_strobo['tgl_mulai'] + pd.to_timedelta(df_strobo['durasi'], unit='D')
    
    # Deteksi Over SOP
    waktu_sekarang = pd.Timestamp.now()
    df_strobo['over_sop'] = df_strobo['batas_sop'] < waktu_sekarang
    
    # 2. Pemetaan Posisi Berkas ke 4 Kategori Target
    kategori_target = ["Kakan", "Kasi SP", "Kasi PHP", "Loket"]
    
    def cek_kategori(posisi):
        pos_clean = str(posisi).strip().lower()
        if "kakan" in pos_clean: return "Kakan"
        if "sp" in pos_clean: return "Kasi SP"
        if "php" in pos_clean: return "Kasi PHP"
        if "loket" in pos_clean: return "Loket"
        return None
        
    df_strobo['kategori_clean'] = df_strobo['posisi_berkas'].apply(cek_kategori)
    
    # Filter berkas yang OVER SOP & masuk 4 kategori target
    df_alert = df_strobo[(df_strobo['over_sop'] == True) & (df_strobo['kategori_clean'].notna())].copy()
    
    # Pastikan ketersediaan kolom daerah
    if 'kantah_kab' not in df_alert.columns:
        df_alert['kantah_kab'] = df_alert.get('kantah', 'Belum Terdata')

    if not df_alert.empty:
        # Gabungkan nomor dan tahun berkas untuk hover
        df_alert['nmr_thn'] = df_alert['nmr_berkas'].astype(str) + "/" + df_alert['thn_berkas'].astype(str)
        
        # Grouping untuk grafik bubble strobo matrix
        df_chart = df_alert.groupby(['kantah_kab', 'kategori_clean']).agg(
            jumlah_berkas=('nmr_berkas', 'count'),
            daftar_berkas=('nmr_thn', lambda x: "<br>".join(x))
        ).reset_index()
        
        # Skema warna seragam global per posisi berkas
        warna_posisi = {
            "Kakan": "#dc2626",    # Merah Terang
            "Kasi SP": "#ea580c",  # Oranye Tua
            "Kasi PHP": "#eab308", # Kuning Strobo
            "Loket": "#2563eb"     # Biru
        }
        
        fig_strobo = go.Figure()
        
        for posisi in kategori_target:
            df_sub = df_chart[df_chart['kategori_clean'] == posisi]
            if not df_sub.empty:
                fig_strobo.add_trace(go.Scatter(
                    x=df_sub['kategori_clean'],
                    y=df_sub['kantah_kab'],
                    mode='markers+text',
                    name=posisi,
                    marker=dict(
                        size=df_sub['jumlah_berkas'] * 4 + 25, 
                        color=warna_posisi[posisi],
                        line=dict(width=2, color='#ffffff'),
                        opacity=0.85
                    ),
                    text=df_sub['jumlah_berkas'], 
                    textposition="middle center",
                    textfont=dict(color="white", size=11, family="Arial Black"),
                    customdata=df_sub['daftar_berkas'],
                    hovertemplate=(
                        "<b>🏢 Kantah:</b> %{y}<br>"
                        "<b>📌 Posisi:</b> %{x}<br>"
                        "<b>🚨 Total Hambatan:</b> %{text} Berkas<br>"
                        "<br><b>📋 Daftar Berkas (No/Thn):</b><br>%{customdata}"
                        "<extra></extra>"
                    )
                ))
        
        fig_strobo.update_layout(
            height=450,
            margin=dict(t=20, b=20, l=10, r=10),
            xaxis=dict(
                title=None, 
                type='category', 
                categoryorder='array', 
                categoryarray=kategori_target,
                tickfont=dict(size=12, fontweight='bold')
            ),
            yaxis=dict(title=None, autocastoptions=dict(autoorder='reversed')),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#f8fafc",
            paper_bgcolor="#ffffff"
        )
        
        st.plotly_chart(fig_strobo, use_container_width=True, key="dashboard_lampu_strobo")
        
    else:
        st.success("🎉 Seluruh berkas di semua Kantah dalam posisi aman & sesuai durasi SOP.")

    # =====================================================================
    # PENDEKATAN SATU LAYAR: MATRIKS REKAPITULASI TOTAL OVER SOP PER KANTAH
    # =====================================================================
    st.markdown("### 📊 Ringkasan Eksekutif (Dashboard Matriks)")
    
    if not df_alert.empty:
        df_matrix = df_alert.groupby(['kantah_kab', 'kategori_clean']).size().unstack(fill_value=0)
        
        for kat in kategori_target:
            if kat not in df_matrix.columns:
                df_matrix[kat] = 0
                
        df_matrix = df_matrix[kategori_target]
        df_matrix['TOTAL OVER SOP'] = df_matrix.sum(axis=1)
        df_matrix = df_matrix.sort_values(by='TOTAL OVER SOP', ascending=False)
        
        try:
            st.dataframe(
                df_matrix.style.background_gradient(cmap='Reds', subset=kategori_target)
                               .format("{:,}"),
                use_container_width=True
            )
        except ImportError:
            st.dataframe(df_matrix, use_container_width=True)
            st.caption("💡 *Tips: Tambahkan 'jinja2' di requirements.txt untuk gradasi warna tabel.*")
            
    else:
        st.success("🎉 Luar biasa! Seluruh berkas di semua Kantah dalam posisi aman & sesuai durasi SOP.")
    
    st.markdown("---")
    st.markdown("### 🔍 Detail Distribusi Visual per Kantah")

    kolom_kantah_induk = 'kantah_kab' if 'kantah_kab' in df_pros_filtered.columns else ('kantah' if 'kantah' in df_pros_filtered.columns else None)
    
    if kolom_kantah_induk:
        semua_kantah = sorted(df_pros_filtered[kolom_kantah_induk].dropna().unique())
        
        for kantah in semua_kantah:
            df_kantah = df_alert[df_alert['kantah_kab'] == kantah]
            total_kantah_over = len(df_kantah)
            
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
