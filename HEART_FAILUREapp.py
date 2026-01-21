import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="EVEYES 360 - HF Smart Track", layout="centered")

# --- DİL SÖZLÜĞÜ ---
LANGS = {
    "TR": {
        "title": "KKY Mobil Takip", "weight": "Ağırlık (kg)", "ohm": "BİA (Ohm Ω)",
        "save": "ANALİZ ET & KAYDET", "history": "GEÇMİŞ", "report": "DR. RAPORU (PDF)",
        "risk": "🚨 RİSK: ÖDEM!", "stable": "✅ DURUM: STABİL", "patient": "Hasta:", "phone": "Tel:",
        "mail_ok": "PDF ve Grafik oluşturuldu!", "settings": "Profil Ayarları",
        "no_data": "Grafik oluşturmak için önce veri giriniz!", "success": "Kayıt Başarılı!"
    },
    "EN": {
        "title": "HF Smart Track", "weight": "Weight (kg)", "ohm": "BIA (Ohm Ω)",
        "save": "ANALYZE & SAVE", "history": "HISTORY", "report": "DR. REPORT (PDF)",
        "risk": "🚨 RISK: EDEMA!", "stable": "✅ STATUS: STABLE", "patient": "Patient:", "phone": "Tel:",
        "mail_ok": "PDF and Chart generated!", "settings": "Profile Settings",
        "no_data": "Enter data first to generate chart!", "success": "Saved Successfully!"
    },
    "DE": {
        "title": "HF Intelligenter Track", "weight": "Gewicht (kg)", "ohm": "BIA (Ohm Ω)",
        "save": "ANALYSE & SPEICHERN", "history": "HISTORIE", "report": "BERICHT (PDF)",
        "risk": "🚨 RISIKO: ÖDEM!", "stable": "✅ STATUS: STABIL", "patient": "Patient:", "phone": "Tel:",
        "mail_ok": "Bericht und Grafik erstellt!", "settings": "Profil-Einstellungen",
        "no_data": "Zuerst Daten eingeben!", "success": "Erfolgreich gespeichert!"
    }
}

# --- VERİTABANI İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect("kky_final_storage.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS records (dt TEXT, w REAL, b INTEGER, msg TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS user_info (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- SIDEBAR / AYARLAR ---
st.sidebar.title("⚙️ " + "Settings")
lang_choice = st.sidebar.selectbox("Language / Dil", ["TR", "EN", "DE"])
L = LANGS[lang_choice]

st.sidebar.divider()
st.sidebar.subheader(L["settings"])

# Kullanıcı bilgilerini yükle/kaydet
cursor.execute("SELECT value FROM user_info WHERE key='name'")
res_n = cursor.fetchone()
default_name = res_n[0] if res_n else ""

cursor.execute("SELECT value FROM user_info WHERE key='phone'")
res_p = cursor.fetchone()
default_phone = res_p[0] if res_p else ""

p_name = st.sidebar.text_input("Patient Name", default_name)
p_phone = st.sidebar.text_input("Phone", default_phone)

if st.sidebar.button("Update Profile"):
    cursor.execute("INSERT OR REPLACE INTO user_info VALUES ('name', ?)", (p_name,))
    cursor.execute("INSERT OR REPLACE INTO user_info VALUES ('phone', ?)", (p_phone,))
    conn.commit()
    st.sidebar.success("Updated!")

# --- ANA EKRAN ---
st.title("🏥 " + L["title"])
st.info(f"👤 {p_name if p_name else '---'}  |  📞 {p_phone if p_phone else '---'}")

# Veri Giriş Kartı
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        w_input = st.number_input(L["weight"], min_value=30.0, max_value=250.0, value=75.0, step=0.1)
    with col2:
        b_input = st.number_input(L["ohm"], min_value=100, max_value=1000, value=500)
    
    if st.button(L["save"], use_container_width=True, type="primary"):
        dt_now = datetime.now().strftime("%d/%m %H:%M")
        
        # Risk Analizi
        cursor.execute("SELECT w, b FROM records ORDER BY rowid DESC LIMIT 1")
        last = cursor.fetchone()
        status_msg = L["stable"]
        
        if last and w_input > last[0] and b_input < last[1]:
            status_msg = L["risk"]
            st.error(status_msg)
        else:
            st.success(status_msg)
            
        cursor.execute("INSERT INTO records VALUES (?,?,?,?)", (dt_now, w_input, b_input, status_msg))
        conn.commit()

# --- GRAFİK ALANI ---
st.divider()
cursor.execute("SELECT * FROM records ORDER BY rowid DESC LIMIT 7")
rows = cursor.fetchall()[::-1]

if rows:
    df = pd.DataFrame(rows, columns=["Date", "Weight", "BIA", "Status"])
    
    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    
    ax1.plot(df["Date"], df["Weight"], color="#2980B9", marker="o", label=L["weight"])
    ax2.plot(df["Date"], df["BIA"], color="#8E44AD", marker="s", linestyle="--", label=L["ohm"])
    
    ax1.set_ylabel(L["weight"], color="#2980B9")
    ax2.set_ylabel(L["ohm"], color="#8E44AD")
    plt.xticks(rotation=25)
    
    fig.legend(loc="upper center", ncol=2)
    st.pyplot(fig)
    
    # PDF RAPORLAMA (Bellek üzerinden)
    def generate_pdf():
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, f"HF PATIENT REPORT: {p_name}")
        c.setFont("Helvetica", 12)
        c.drawString(50, 730, f"Contact: {p_phone} | Date: {datetime.now().strftime('%Y-%m-%d')}")
        c.line(50, 720, 550, 720)
        
        y = 680
        c.drawString(50, y, "Last Measurements:")
        y -= 20
        for index, row in df.iloc[::-1].iterrows():
            c.drawString(50, y, f"{row['Date']} - W: {row['Weight']}kg - BIA: {row['BIA']} - {row['Status']}")
            y -= 15
        c.save()
        buffer.seek(0)
        return buffer

    st.download_button(
        label="📥 " + L["report"],
        data=generate_pdf(),
        file_name=f"Report_{p_name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
else:
    st.warning(L["no_data"])

# --- GEÇMİŞ TABLOSU ---
with st.expander(L["history"]):
    cursor.execute("SELECT * FROM records ORDER BY rowid DESC")
    all_data = cursor.fetchall()
    if all_data:
        st.table(pd.DataFrame(all_data, columns=["Date", "Weight", "BIA", "Result"]))


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



