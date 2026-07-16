import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =========================================================================
# --- MODEL MONITORING LAMPU STROBO SOP (DIBAWAH PROFIL & GRAFIK PERSIL) ---
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
        # Fallback jika nama kolom sedikit berbeda, misalnya 'kantah'
        df_alert['kantah_kab'] = df_alert.get('kantah', 'Unknown')

    # =====================================================================
    # PENDEKATAN SATU LAYAR: MATRIKS REKAPITULASI TOTAL OVER SOP PER KANTAH
    # =====================================================================
    st.markdown("### 📊 Ringkasan Eksekutif (Dashboard Matriks)")
    
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
    
    # Menampilkan tabel interaktif yang muat di satu layar
    st.dataframe(
        df_matrix.style.background_gradient(cmap='Reds', subset=kategori_target)
                       .format("{:,}"),
        use_container_width=True
    )
    
    st.markdown("---")
    st.markdown("### 🔍 Detail Distribusi Visual per Kantah")

    # Ambil list seluruh kantah unik dari data awal (agar kantah yang 'Aman' tetap muncul)
    semua_kantah = sorted(df_pros_filtered['kantah_kab'].dropna().unique())

    # Menggunakan container expander horizontal agar hemat space layar
    for kantah in semua_kantah:
        df_kantah = df_alert[df_alert['kantah_kab'] == kantah]
        total_kantah_over = len(df_kantah)
        
        # Penamaan status header kantah
        if total_kantah_over > 0:
            header_text = f"🏢 {kantah.upper()} 🔴 ({total_kantah_over} Berkas Over SOP)"
        else:
            header_text = f"🏢 {kantah.upper()} 🟢 (Semua Berkas Aman/Sesuai SOP)"
            
        with st.expander(header_text, expanded=(total_kantah_over > 0)):
            if total_kantah_over > 0:
                # Tampilkan mini kolom untuk 4 Jabatan di dalam masing-masing Kantah
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
                            # Opsional: Jika ingin melihat nomor berkasnya via text kecil
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
                st.success(f"Mantap! Tidak ada penumpukan berkas melebihi durasi SOP di {kantah}.")

else:
    st.info("Tidak ada data pelacakan durasi prosedur berkas saat ini.")
st.markdown("<br><hr><br>", unsafe_allow_html=True)
