import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# Sayfa Ayarları
st.set_page_config(page_title="3CX Gelişmiş Personel & Çağrı Analizi", page_icon="📞", layout="wide")

st.title("📞 3CX Gelişmiş Analiz ve Personel Takip Paneli")
st.markdown("CSV dosyasını yükleyin; spamları temizleyelim ve personel performansını raporlayalım.")

# --- SIDEBAR FİLTRELERİ ---
st.sidebar.header("⚙️ Analiz Ayarları")
uploaded_file = st.sidebar.file_uploader("3CX Çağrı Raporu (CSV / Excel)", type=["csv", "xlsx"])
spam_threshold = st.sidebar.slider("Spam Zaman Eşiği (Dakika)", 1, 60, 10)

if not uploaded_file:
    st.info("💡 Lütfen sol panelden 3CX CSV dosyasını yükleyin.")
    st.stop()

# --- VERİ YÜKLEME ---
try:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    st.sidebar.subheader("📊 Sütun Eşleştirme")
    all_cols = df.columns.tolist()
    
    # Sütunları seçtiriyoruz (3CX dökümündeki isimlere göre)
    caller_col = st.sidebar.selectbox("Arayan Numara (Caller ID)", all_cols, index=0)
    time_col = st.sidebar.selectbox("Arama Zamanı", all_cols, index=min(1, len(all_cols)-1))
    status_col = st.sidebar.selectbox("Durum (Status)", all_cols, index=min(2, len(all_cols)-1))
    agent_col = st.sidebar.selectbox("Yanıtlayan/Dahili (Agent/To)", all_cols, index=min(3, len(all_cols)-1))

    df = df.rename(columns={caller_col: 'CallerID', time_col: 'CallTime', status_col: 'Status', agent_col: 'Agent'})
    df['CallTime'] = pd.to_datetime(df['CallTime'])
except Exception as e:
    st.error(f"Hata: {e}")
    st.stop()

# --- TEKİLLEŞTİRME MANTIĞI ---
df = df.sort_values(by=['CallerID', 'CallTime'])
df['Time_Diff'] = df.groupby('CallerID')['CallTime'].diff()
df['Is_Spam_Duplicate'] = (df['Time_Diff'] < timedelta(minutes=spam_threshold)) & (df['Time_Diff'].notna())

# Filtrelenmiş veri (Spamsız)
clean_data = df[df['Is_Spam_Duplicate'] == False].copy()

# --- PERSONEL ANALİZİ ---
# Yanıtlananlar ✅
answered_mask = clean_data['Status'].astype(str).str.lower().str.contains('answer|yanıt|cevap|connect|✅', na=False)
answered_calls = clean_data[answered_mask]

# Cevapsızlar ❌
missed_calls = clean_data[~answered_mask]

# KPI'lar
total_clean = len(clean_data)
total_answered = len(answered_calls)
total_missed = len(missed_calls)

col1, col2, col3 = st.columns(3)
col1.metric("Toplam Tekil Çağrı", total_clean)
col2.metric("Toplam Yanıtlanan", total_answered)
col3.metric("Toplam Kaçan (Net)", total_missed, delta_color="inverse")

st.markdown("---")

# --- PERSONEL TABLOSU ---
st.subheader("👨‍💼 Personel Performans Karnesi")

# Yanıtlananları agent bazlı say
agent_stats = answered_calls['Agent'].value_counts().reset_index()
agent_stats.columns = ['Personel (Dahili)', 'Yanıtlanan Çağrı']

# Cevapsızları agent bazlı say (Eğer dökümde kimin kaçırdığı bilgisi varsa)
missed_stats = missed_calls['Agent'].value_counts().reset_index()
missed_stats.columns = ['Personel (Dahili)', 'Kaçırılan Çağrı']

# Tabloları birleştir
performance_df = pd.merge(agent_stats, missed_stats, on='Personel (Dahili)', how='outer').fillna(0)
performance_df['Toplam Yük'] = performance_df['Yanıtlanan Çağrı'] + performance_df['Kaçırılan Çağrı']
performance_df['Başarı %'] = (performance_df['Yanıtlanan Çağrı'] / performance_df['Toplam Yük'] * 100).round(1)

st.dataframe(performance_df.sort_values(by='Yanıtlanan Çağrı', ascending=False), use_container_width=True)

# --- GRAFİKLER ---
c1, c2 = st.columns(2)
with c1:
    fig_agent = px.bar(performance_df, x='Personel (Dahili)', y='Yanıtlanan Çağrı', title="En Çok Çağrı Yanıtlayanlar", color='Yanıtlanan Çağrı', color_continuous_scale='Viridis')
    st.plotly_chart(fig_agent, use_container_width=True)
with c2:
    fig_pie = px.pie(clean_data, names='Status', title="Genel Yanıtlanma Oranı", hole=0.4)
    st.plotly_chart(fig_pie, use_container_width=True)
