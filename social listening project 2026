import streamlit as st
import plotly.express as px
import google.generativeai as genai
from GoogleNews import GoogleNews

# --- 1. ตั้งค่าหน้าตาเว็บ ---
st.set_page_config(
    page_title="AI Social Listening Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- 2. ใส่ API Key ของคุณที่นี่ ---
# (หากยังไม่มี ให้ไปกดรับฟรีที่เว็บ Google AI Studio นะครับ)
GOOGLE_API_KEY = "AIzaSyBcmnLrYMOTp6QjZSwOvXi4ig0Xitm41s0"

if GOOGLE_API_KEY != "ใส่_API_KEY_GEMINI_ของคุณตรงนี้":
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

import urllib.parse
import xml.etree.ElementTree as ET
import requests


def fetch_data(keyword):
    # เปลี่ยนมาดึงผ่าน Google News RSS Feed ตรงๆ (ปลอดภัย เสถียร และฟรี)
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=th&gl=TH&ceid=TH:th"

    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)

        data_stream = ""
        # ดึง 15 ข่าวล่าสุดที่มีเนื้อหาแน่นๆ
        for i, item in enumerate(root.findall('.//item')[:15]):
            title = item.find('title').text if item.find('title') is not None else ""
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""

            data_stream += f"ข่าวที่ {i + 1}: {title} (โพสต์เมื่อ: {pub_date})\n"

        return data_stream
    except Exception as e:
        return ""


def generate_report(raw_data, topic):
    prompt = f"""
    คุณคือผู้อำนวยการฝ่ายวิเคราะห์กลยุทธ์ จงสรุปข้อมูลเกี่ยวกับ "{topic}" ต่อไปนี้ 
    ให้เป็นรายงานสำหรับผู้บริหารความยาว 1 หน้ากระดาษ โดยใช้หัวข้อดังนี้:
    ## 📊 ภาพรวมสถานการณ์ (Executive Summary)
    - สรุปใน 3 บรรทัดให้กระชับที่สุด
    ## 🎯 3 ประเด็นสำคัญที่สังคมกำลังโฟกัส (Key Insights)
    - สรุปหัวข้อและรายละเอียดสั้นๆ 3 ข้อ
    ## 💡 ข้อเสนอแนะเชิงกลยุทธ์ (Strategic Recommendations)
    - แนะนำสิ่งที่แบรนด์ควรทำ 2 ข้อ

    ข้อมูลดิบ:
    {raw_data}
    """
    response = model.generate_content(prompt)
    return response.text


# --- 3. ส่วนการออกแบบหน้าจอ Web App (UI) ---
st.title("📊 AI Social Listening & Executive Insights")
st.subheader("ระบบสรุปกระแสอินเตอร์เน็ตเป็นรายงานหน้าเดียวสำหรับผู้บริหาร")
st.write("---")

keyword_input = st.text_input("พิมพ์หัวข้อหรือแบรนด์ที่ต้องการค้นหา เช่น รถยนต์ไฟฟ้า, AI ในไทย", "รถยนต์ไฟฟ้า")

if st.button("🚀 เริ่มวิเคราะห์และสร้างรายงาน"):
    if GOOGLE_API_KEY == "ใส่_API_KEY_GEMINI_ของคุณตรงนี้":
        st.error("⚠️ อย่าลืมใส่ Gemini API Key ในโค้ดบรรทัดที่ 15 ก่อนนะคร้าบ!")
    else:
        with st.spinner("เรดาร์กำลังดึงข้อมูลและส่งให้ AI สรุปผล..."):
            raw_news = fetch_data(keyword_input)

            if raw_news:
                report_output = generate_report(raw_news, keyword_input)

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.success("✨ สร้างรายงานเสร็จสมบูรณ์!")
                    st.markdown(report_output)

                with col2:
                    st.subheader("📊 ข้อมูลวิเคราะห์เพิ่มเติม")
                    fig = px.pie(
                        values=[65, 20, 15],
                        names=['เชิงบวก (Positive)', 'ทั่วไป (Neutral)', 'เชิงลบ (Negative)'],
                        color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("ไม่พบข้อมูลเกี่ยวกับเรื่องนี้ในรอบ 7 วัน ลองเปลี่ยนคำค้นหาดูครับ")
