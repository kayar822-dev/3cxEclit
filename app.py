import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# Dashboard sayfa ayarları
st.set_page_config(page_title="3CX CSV Çağrı Analiz Paneli", page_icon="📞", layout="wide")

st.title("📞 3CX Tekilleştirilmiş Çağrı Analiz Paneli")
st.markdown("3CX panelinden dışarı aktardığınız **Çağrı Geçmişi (CSV)** dosyasını yükleyin. Aynı numaradan gelen mükerrer/spam aramalar filtrelenerek tekil çağrı olarak hesaplanacaktır.")

# --- SIDEBAR (YAN PANEL) FİLTRELERİ ---
st.sidebar.header("⚙️ Analiz Ayarları")
uploaded_file = st.sidebar.file_uploader("3CX Çağrı Raporu (CSV / Excel)", type=["csv", "xlsx"])
spam_threshold = st.sidebar.slider("Spam/Mükerrer Zaman Eşiği (Dakika)", min_value=1, max_value=60, value=10)

st.sidebar.info("Aynı numaradan bu süre içinde gelen ardışık aramalar tek bir çağrı sayılır.")

# Örnek Şablon Sağlama
if not uploaded_file:
    st.info("💡 Lütfen sol panelden bir 3CX Çağrı Raporu (CSV) yükleyin. Sisteminizin nasıl çalışacağını görmek için aşağıdaki örnek veriyi inceleyebilirsiniz.")
    
    # Test Verisi Simülasyonu
    now = datetime.now()
    data = {
        'CallerID': ['05321112233', '05321112233', '05321112233', '05449998877', '05449998877', '05552223344'],
        'CallTime': [now - timedelta(minutes=45), now - timedelta(minutes=43), now - timedelta(minutes=42), now - timedelta(minutes=30), now - timedelta(minutes=12), now - timedelta(minutes=5)],
        'Status': ['Missed', 'Missed', 'Answered', 'Missed', 'Answered', 'Answered']
    }
    df = pd.DataFrame(data)
else:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # Kolon isimlerini standartlaştırma (Kullanıcı sütun eşleme yapabilsin diye esneklik sağlıyoruz)
        st.sidebar.subheader("📊 Sütun Eşleştirme")
        all_cols = df.columns.tolist()
        
        caller_col = st.sidebar.selectbox("Arayan Numara (Caller ID) Sütunu", all_cols, index=0)
        time_col = st.sidebar.selectbox("Arama Zamanı (Call Time) Sütunu", all_cols, index=min(1, len(all_cols)-1))
        status_col = st.sidebar.selectbox("Çağrı Durumu (Status) Sütunu", all_cols, index=min(2, len(all_cols)-1))
        
        df = df.rename(columns={caller_col: 'CallerID', time_col: 'CallTime', status_col: 'Status'})
    except Exception as e:
        st.error(f"Dosya okunurken bir hata oluştu: {e}")
        st.stop()

# --- VERİ TEMİZLEME VE TEKİLLEŞTİRME MANTIĞI ---
if 'CallerID' in df.columns and 'CallTime' in df.columns and 'Status' in df.columns:
    try:
        df['CallTime'] = pd.to_datetime(df['CallTime'])
        df = df.sort_values(by=['CallerID', 'CallTime'])
        
        # İki çağrı arasındaki zaman farkını bul
        df['Time_Diff'] = df.groupby('CallerID')['CallTime'].diff()
        
        # Belirlenen filtreden kısa sürede gelen aramaları mükerrer (spam) işaretle
        df['Is_Spam_Duplicate'] = (df['Time_Diff'] < timedelta(minutes=spam_threshold)) & (df['Time_Diff'].notna())
        
        # Sadece orijinal (tekil) çağrıları filtrele
        clean_data = df[df['Is_Spam_Duplicate'] == False].copy()
        spam_count = df['Is_Spam_Duplicate'].sum()
        
        # --- KPI METRİKLERİ ---
        total_raw = len(df)
        total_clean = len(clean_data)
        
        # Durum değerlerini standartlaştırma veya içerik kontrolü
        # Yanıtlanan çağrıları içeren yaygın kelimeler: Answered, Yanıtlandı, Cevaplandı, Connected
        answered_mask = clean_data['Status'].astype(str).str.lower().str.contains('answer|yanıt|cevap|connect|✅|başarılı', na=False)
        answered_count = len(clean_data[answered_mask])
        missed_count = total_clean - answered_count
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Dökümdeki Toplam Çağrı", value=total_raw)
        with col2:
            st.metric(label="Filtrelenen Mükerrer/Spam", value=int(spam_count), delta=f"-{int(spam_count)}" if spam_count > 0 else None, delta_color="inverse")
        with col3:
            st.metric(label="Net Yanıtlanan (Tekil)", value=answered_count)
        with col4:
            st.metric(label="Net Kaçan Çağrı (Tekil)", value=missed_count, delta_color="inverse")
            
        st.markdown("---")
        
        # --- GRAFİKLER VE DETAYLAR ---
        left_col, right_col = st.columns(2)
        
        with left_col:
            st.subheader("📊 Çağrı Dağılım Oranı (Tekil)")
            status_df = pd.DataFrame({
                'Durum': ['Yanıtlanan', 'Kaçan'],
                'Adet': [answered_count, missed_count]
            })
            
            fig = px.pie(status_df, values='Adet', names='Durum', color='Durum',
                         color_discrete_map={'Yanıtlanan': '#2ecc71', 'Kaçan': '#e74c3c'},
                         hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
            
        with right_col:
            st.subheader("📋 Filtrelenmiş Çağrı Listesi")
            display_df = clean_data[['CallerID', 'CallTime', 'Status']].copy()
            display_df.columns = ['Telefon Numarası', 'Arama Zamanı', 'Durum']
            st.dataframe(display_df.sort_values(by='Arama Zamanı', ascending=False), use_container_width=True)
            
    except Exception as e:
        st.error(f"Veri işlenirken bir hata oluştu: {e}. Lütfen sütun seçimlerinin ve tarih formatının doğru olduğundan emin olun.")
else:
    st.warning("Uyumlu sütunlar bulunamadı. Lütfen sağ veya sol panelden doğru sütun eşleştirmelerini yapın.")
