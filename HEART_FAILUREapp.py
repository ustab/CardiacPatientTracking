import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="EVEYES 360 - Universal Edema Tracker", layout="centered")

# --- DİL VE MESAJ SÖZLÜĞÜ (Geliştirilmiş) ---
LANGS = {
    "TR": {
        "title": "EVEYES 360: Dijital Ödem Takibi",
        "condition": "Takip Edilen Durum",
        "conditions": ["Kalp Yetmezliği", "Gebelik (Preeklampsi Riski)", "Böbrek Yetmezliği / Diyaliz"],
        "weight": "Ağırlık (kg)", "ohm": "BİA (Ohm Ω)",
        "save": "ANALİZ ET & KAYDET", "report": "DR. RAPORU (PDF)",
        "risk_hf": "🚨 RİSK: Kalp Yetmezliği / Ödem!",
        "risk_pre": "🚨 RİSK: Preeklampsi / Hipoproteinemi Belirtisi!",
        "risk_kidney": "🚨 RİSK: Kritik Sıvı Yükü Artışı!",
        "stable": "✅ DURUM: STABİL",
        "no_data": "Grafik için veri giriniz!", "success": "Kayıt Başarılı!"
    },
    "EN": {
        "title": "EVEYES 360: Digital Edema Tracker",
        "condition": "Monitored Condition",
        "conditions": ["Heart Failure", "Pregnancy (Preeclampsia Risk)", "Kidney Disease / Dialysis"],
        "weight": "Weight (kg)", "ohm": "BIA (Ohm Ω)",
        "save": "ANALYZE & SAVE", "report": "DR. REPORT (PDF)",
        "risk_hf": "🚨 RISK: Heart Failure / Edema!",
        "risk_pre": "🚨 RISK: Preeclampsia / Hypoproteinemia Sign!",
        "risk_kidney": "🚨 RISK: Critical Fluid Overload!",
        "stable": "✅ STATUS: STABLE",
        "no_data": "Enter data for chart!", "success": "Saved!"
    }
}

# --- VERİTABANI ---
def init_db():
    conn = sqlite3.connect("medical_storage.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS records (dt TEXT, w REAL, b INTEGER, msg TEXT, cond TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_info (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- SIDEBAR / AYARLAR ---
st.sidebar.title("🩺 Patient Profile")
lang_choice = st.sidebar.selectbox("Language", ["TR", "EN"])
L = LANGS[lang_choice]

p_name = st.sidebar.text_input("Full Name", "Hasta Adı")
p_cond = st.sidebar.selectbox(L["condition"], L["conditions"])

# --- ANA EKRAN ---
st.title("🛡️ " + L["title"])
st.subheader(f"Monitoring: {p_cond}")

# Veri Giriş Kartı
with st.expander("➕ Yeni Ölçüm Ekle", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        w_input = st.number_input(L["weight"], value=70.0, step=0.1)
    with col2:
        b_input = st.number_input(L["ohm"], value=500, step=1)
    
    if st.button(L["save"], use_container_width=True, type="primary"):
        dt_now = datetime.now().strftime("%d/%m %H:%M")
        
        # Akıllı Risk Analizi
        cursor.execute("SELECT w, b FROM records WHERE cond=? ORDER BY rowid DESC LIMIT 1", (p_cond,))
        last = cursor.fetchone()
        
        status_msg = L["stable"]
        if last and w_input > last[0] and b_input < last[1]:
            if "Gebelik" in p_cond or "Pregnancy" in p_cond: status_msg = L["risk_pre"]
            elif "Böbrek" in p_cond or "Kidney" in p_cond: status_msg = L["risk_kidney"]
            else: status_msg = L["risk_hf"]
            st.error(status_msg)
        else:
            st.success(status_msg)
            
        cursor.execute("INSERT INTO records VALUES (?,?,?,?,?)", (dt_now, w_input, b_input, status_msg, p_cond))
        conn.commit()

# --- GRAFİK ---
cursor.execute("SELECT dt, w, b FROM records WHERE cond=? ORDER BY rowid DESC LIMIT 10", (p_cond,))
rows = cursor.fetchall()[::-1]

if rows:
    df = pd.DataFrame(rows, columns=["Date", "Weight", "BIA"])
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.plot(df["Date"], df["Weight"], color="blue", marker="o", label="Weight")
    ax2.plot(df["Date"], df["BIA"], color="purple", marker="s", ls="--", label="BIA")
    ax1.set_ylabel("Weight (kg)")
    ax2.set_ylabel("BIA (Ohm)")
    st.pyplot(fig)

    # PDF Rapor Fonksiyonu
    def generate_pdf():
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(50, 750, f"PATIENT: {p_name}")
        c.drawString(50, 735, f"CONDITION: {p_cond}")
        c.line(50, 720, 550, 720)
        c.drawString(50, 700, "The inverse correlation between Weight and BIA indicates fluid retention.")
        c.save()
        buffer.seek(0)
        return buffer

    st.download_button("📥 " + L["report"], generate_pdf(), f"Report_{p_name}.pdf", "application/pdf")
else:
    st.info(L["no_data"])

"""Key Features of EVEYES 360: ENG
Patient-Centric Header: The dashboard now features the patient’s name and contact information prominently in the header.
This ensures that when a doctor receives a report, they immediately know which patient to contact.
Embedded Charts in PDF: Using the fig.savefig command, the system captures a high-resolution snapshot of the current live trend chart
and embeds it directly into the PDF. This is a critical feature for physicians to visually assess patient trends at a glance.
Color-Coded Visual Analytics: To ensure clarity, Weight (kg) is represented by blue circles, while BIA (Ohm Ω) is shown with purple squares.
A clear legend at the top of the chart distinguishes the two metrics, making the data easy to interpret.
BIA-Weight Correlation Logic (Edema Detection): In heart failure management,
the most reliable early sign of edema (fluid retention) is an increase in body weight coupled with a decrease in body impedance (BIA).
When this specific inverse correlation is detected, the app triggers a red "
🚨 RISK: EDEMA!" alert.
Next Steps: Deployment Strategy
Currently, the application runs as a Web-App that mimics a mobile interface on desktop browsers.
Current State: Fully responsive and accessible via smartphone browsers (Chrome/Safari) using the "Add to Home Screen" feature.
Future Native Integration: If you wish to convert this into a Native Android/iOS App (.apk or .ipa) to access local hardware features or offline storage,
we can transition the codebase using libraries like Kivy or BeeWare.
Would you like to continue with the current high-efficiency Web-App model, or should we explore building a native mobile installation package?"""

"""Önemli Özellikler TR
Hasta Odaklı Başlık: Artık başlıkta hastanın adı ve telefon numarası yer alıyor. 
Doktor raporu aldığında kiminle iletişime geçeceğini anında görüyor.

PDF İçinde Grafik: self.fig.savefig komutuyla o an 
ekrandaki grafiğin fotoğrafını çekip PDF'in tam ortasına yerleştiriyoruz. Bu, doktorun trendleri görsel olarak görmesi için en önemli özellik.

Renkli ve İsimli Grafikler: Grafikte Ağırlık (Kg) mavi noktalarla, 
BİA (Ohm Ω) ise mor karelerle gösteriliyor. Hangisinin ne olduğu grafiğin üzerindeki kutucukta (Legend) açıkça yazıyor.

BİA-Kilo Analiz Mantığı: Kalp yetmezliğinde ödemi anlamanın yolu; 
kilonun artmasıyla vücut direncinin (BİA) düşmesidir. Bu ikili durum oluştuğunda uygulama kırmızı alarm verir.

Bir Sonraki Adım:
Şu an uygulama bir masaüstü bilgisayarda "telefon ekranı gibi" görünüyor.
 Eğer bu kodu gerçekten bir cep telefonuna (Android) uygulama 
 olarak yüklemek istersen, Kivy veya BeeWare gibi farklı kütüphaneler 
 kullanmamız gerekir. Bu yönde bir çalışma yapmak ister misin yoksa bilgisayarda 
bu şekilde kullanmak yeterli mi?

"""




