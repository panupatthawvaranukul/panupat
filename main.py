import streamlit as st
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import google.generativeai as genai

# --- 1. Web Page & Global Font Configuration ---
st.set_page_config(
    page_title="Airline Social Listening Dashboard",
    page_icon="✈️",
    layout="wide"
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght=300;400;500;700&display=swap');
        html, body, [class*="css"], .stMarkdown, p, button, input, select {
            font-family: 'Roboto', sans-serif !important;
            font-size: 15px !important;
        }
        .report-box { padding: 20px; border-radius: 8px; background-color: transparent; }
    </style>
""", unsafe_allow_html=True)

# --- 2. API Connection Settings (ดึงค่าจาก Secrets นิรภัยดั้งเดิม) ---
GOOGLE_API_KEY = None
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except Exception:
    pass

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# --- 3. Fetch Pantip Data Only (ท่อดั้งเดิมที่เสถียรที่สุด) ---
def fetch_pantip_data(kw):
    query = f"{kw} site:pantip.com"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=th&gl=TH&ceid=TH:th"
    data_stream = ""
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:10]
        if items:
            data_stream += f"💬 [Consumer Voices on Pantip Regarding: {kw}] ===\n"
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                clean_title = title.split(" - Pantip")[0]
                data_stream += f"- {clean_title}\n"
    except Exception:
        pass
    return data_stream

# --- 4. Generate Report Using Classic Stable Model ---
def generate_airline_report(raw_data, topics):
    if not GOOGLE_API_KEY:
        return "⚠️ Missing GOOGLE_API_KEY. Please configure it in Streamlit Secrets."
        
    prompt = f"""
    You are the Chief Strategic Officer (CSO) of a leading international airline.
    Analyze the following public discussions from Pantip forums regarding these topics: "{topics}"
    
    Raw Pantip Data:
    {raw_data}
    
    Synthesize this data into a strategic Executive Brief in English with these exact sections:
    ## Executive Summary
    - Provide a concise 3-line overview of customer sentiment on Pantip.
    ## Pantip Passenger Insights
    - Detailed breakdown of specific customer complaints, flight issues, or appreciation.
    ## Airline Strategic Recommendations
    - Actionable steps the airline board should execute immediately.
    """
    
    try:
        # ย้อนกลับมาใช้ตัวพิมพ์ชื่อรุ่นแบบคลาสสิกดั้งเดิมที่ Google ไม่มีวันบล็อก
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ Strategy Synthesis Failed: {str(e)}"

# --- 5. Classic Minimalist User Interface ---
st.title("Aviation Social Listening & Executive Insights")
st.write("Focused Intelligence from Pantip Community Forums")

keywords_input = st.st.text_input(
    "Search Keywords (Separate multiple topics with a comma ',' | Thai keywords supported)", 
    value="บริการสายการบิน, เลื่อนไฟลท์"
)

st.write("")

if st.button("🚀 Execute Strategic Analysis", use_container_width=True):
    if not keywords_input:
        st.warning("Please enter a keyword.")
    else:
        with st.spinner("Crawling Pantip forums for customer intelligence..."):
            combined_data = ""
            keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
            for kw in keywords:
                combined_data += fetch_pantip_data(kw) + "\n"
                
            if combined_data.strip():
                executive_insight = generate_airline_report(combined_data, keywords_input)
                st.write("---")
                st.subheader("💡 Executive Insights Report (Pantip Only)")
                
                with st.container(border=True):
                    st.markdown(f'<div class="report-box">{executive_insight}</div>', unsafe_allow_html=True)
            else:
                st.error("❌ No discussions found on Pantip matching the selected parameters.")
