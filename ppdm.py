import streamlit as st
import pandas as pd
import plotly.graph_objects as go

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
    
    # Filter hanya berkas yang OVER SOP dan berada pada 4 jabatan target
    df_alert = df_strobo[(df_strobo['over_sop'] == True) & (df_strobo['kategori_clean'].notna())].copy()
    
    # Pastikan ketersediaan kolom daerah
    if 'kantah_kab' not in df_alert.columns:
        df_alert['kantah_kab'] = df_alert.get('kantah', 'Belum Terdata')

    if not df_alert.empty:
        # Gabungkan nomor dan tahun berkas untuk keperluan hover
        df_alert['nmr_thn'] = df_alert['nmr_berkas'].astype(str) + "/" + df_alert['thn_berkas'].astype(str)
        
        # 3. Grouping Data untuk Pembuatan Struktur Lampu Strobo
        # Dapatkan jumlah berkas dan daftar nomor berkas digabung dengan tag <br>
        df_chart = df_alert.groupby(['kantah_kab', 'kategori_clean']).agg(
            jumlah_berkas=('nmr_berkas', 'count'),
            daftar_berkas=('nmr_thn', lambda x: "<br>".join(x))
        ).reset_index()
        
        # 4. Skema Warna Seragam Global Berdasarkan Posisi Berkas (Workflow)
        warna_posisi = {
            "Kakan": "#dc2626",    # Merah Terang
            "Kasi SP": "#ea580c",  # Oranye Tua
            "Kasi PHP": "#eab308", # Kuning Strobo
            "Loket": "#2563eb"     # Biru Intelijen
        }
        
        # Pembuatan Grafis Bubble Strobo Matrix
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
                        size=df_sub['jumlah_berkas'] * 4 + 25, # Ukuran lingkaran membesar dinamis sesuai penumpukan
                        color=warna_posisi[posisi],
                        line=dict(width=3, color='#ffffff'),  # Border putih kontras agar mirip lampu
                        opacity=0.85
                    ),
                    text=df_sub['jumlah_berkas'], # Angka jumlah berkas tampil di dalam lampu
                    textposition="middle center",
                    textfont=dict(color="white", size=12, family="Arial Black"),
                    customdata=df_sub['daftar_berkas'],
                    hovertemplate=(
                        "<b>🏢 Kantah:</b> %{y}<br>"
                        "<b>📌 Posisi:</b> %{x}<br>"
                        "<b>🚨 Total Hambatan:</b> %{text} Berkas<br>"
                        "<br><b>📋 Daftar Berkas (No/Thn):</b><br>%{customdata}"
                        "<extra></extra>"
                    )
                ))
        
        # Mengatur Tata Letak Grafik Agar Muat di Satu Layar Penuh
        fig_strobo.update_layout(
            height=500,
            margin=dict(t=20, b=20, l=10, r=10),
            xaxis=dict(
                title=None, 
                type='category', 
                categoryorder='array', 
                categoryarray=kategori_target,
                tickfont=dict(size=13, fontweight='bold')
            ),
            yaxis=dict(title=None, autocastoptions=dict(autoorder='reversed')),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor="#f8fafc",
            paper_bgcolor="#ffffff"
        )
        
        # Tampilkan langsung ke Dashboard
        st.plotly_chart(fig_strobo, use_container_width=True, key="dashboard_lampu_strobo")
        
    else:
        st.success("🎉 Seluruh berkas di semua Kantah dalam posisi aman & sesuai durasi SOP.")
else:
    st.info("Tidak ada data pelacakan durasi prosedur berkas saat ini.")
