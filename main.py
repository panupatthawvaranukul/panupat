import streamlit as st
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import json

# --- [1] การตั้งค่าหน้าเว็บ & ฟอนต์สำหรับภาษาไทยและอังกฤษ ---
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
            line-height: 1.6 !important;
        }
        h1 { font-size: 26px !important; font-weight: 700 !important; margin-bottom: 20px !important; }
        h2 { font-size: 20px !important; font-weight: 500 !important; margin-top: 15px !important; margin-bottom: 10px !important; }
        .report-box { padding: 20px; border-radius: 8px; background-color: transparent; }
    </style>
""", unsafe_allow_html=True)

# --- [2] การเชื่อมต่อ Secrets ปลอดภัยหลังบ้าน ---
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")

# --- [3] ฟังก์ชันแปลงช่วงเวลาสำหรับ Google News ---
def get_period_code(period_name):
    mapping = {"1 Week": "7d", "1 Month": "1m", "3 Months": "3m", "6 Months": "6m", "1 Year": "1y"}
    return mapping.get(period_name, "7d")

# --- [4] ฟังก์ชันการดึงข้อมูล Blended Data ---
def fetch_news_data(kw, period_code):
    encoded_keyword = urllib.parse.quote(kw)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}+when:{period_code}&hl=th&gl=TH&ceid=TH:th"
    data_stream = ""
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:6]
        if items:
            data_stream += f"📰 [Google News Streams Regarding: {kw}]\n"
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                data_stream += f"- {title}\n"
    except:
        pass
    return data_stream

def fetch_pantip_data(kw):
    query = f"{kw} site:pantip.com"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=th&gl=TH&ceid=TH:th"
    data_stream = ""
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:8]
        if items:
            data_stream += f"💬 [Consumer Voices on Pantip Regarding: {kw}]\n"
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                clean_title = title.split(" - Pantip")[0]
                data_stream += f"- {clean_title}\n"
    except:
        pass
    return data_stream

def fetch_multitopic_data(keywords_str, period_name):
    period_code = get_period_code(period_name)
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    all_data_stream = ""
    for kw in keywords:
        all_data_stream += f"=== Target Keyword: {kw} ===\n"
        all_data_stream += fetch_news_data(kw, period_code) + "\n"
        all_data_stream += fetch_pantip_data(kw) + "\n"
        all_data_stream += "---------------------------------------\n\n"
    return all_data_stream

# --- [5] ฟังก์ชันสังเคราะห์รายงานด้วย REST API (แก้บั๊ก 404/v1beta ค้างถาวร) ---
def generate_airline_report(raw_data, topics):
    if not GOOGLE_API_KEY:
        return "⚠️ Missing GOOGLE_API_KEY. Please configure it in Streamlit Secrets."
        
    prompt = f"""
    You are the Chief Strategic Officer (CSO) of a leading international airline.
    Analyze the following blended online intelligence data (comprising official public Google News reports and organic consumer discussions from Pantip forums) regarding these topics: "{topics}"
    
    Blended Raw Data:
    {raw_data}
    
    Your task is to synthesize this cross-platform data into a high-level strategic Executive Brief in English.
    
    Strict Strategic Requirements:
    1. Tailor every single insight to the AIRLINE ecosystem (e.g., fleet operations, passenger service, ground handling, ticketing, crisis PR, or brand reputation).
    2. Juxtapose media coverage against ground-level consumer feedback: Contrast how mainstream Google News reports these topics versus what real passengers are complaining about or praising on Pantip.
    3. Structure the report using clean, uniform Markdown headers.
    
    Structure the report with these exact English sections:
    ## Executive Summary
    - Provide a concise 3-line overview of the multi-channel narrative and prevailing sentiment.
    ## Blended Media & Pantip Passenger Insights
    - Detailed breakdown of specific customer pain points, recurring flight/service complaints, or public praise found in the data.
    ## Airline Strategic Recommendations
    - Actionable operational modifications, customer service protocols, or aviation marketing steps the board should execute immediately.
    """
    
    # 📌 สูตรลับปี 2026: ใช้ Endpoint ท่อตรง v1beta + บังคับชื่อโมเดลรุ่นเจาะจง gemini-1.5-flash-latest
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            res_json = response.json()
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"⚠️ Google API Error ({response.status_code}): {response.text}"
    except Exception as e:
        return f"⚠️ Connection Failed: {str(e)}"

# --- [6] ส่วนแสดงผลหน้าจอผู้ใช้งาน (User Interface) ---
st.title("Aviation Social Listening & Executive Insights")
st.write("Blended Intelligence Dashboard: Google News Streams + Pantip Community Forums")

col_search, col_time = st.columns([2, 1])

with col_search:
    keywords_input = st.text_input(
        "Search Keywords (Separate multiple topics with a comma ',' | Thai keywords supported)", 
        value="บริการสายการบิน, เลื่อนไฟลท์"
    )

with col_time:
    time_period = st.selectbox(
        "Data Horizon (Time Range for Google News)",
        ["1 Week", "1 Month", "3 Months", "6 Months", "1 Year"]
    )

st.write("")

if st.button("🚀 Execute Strategic Analysis", use_container_width=True):
    if not keywords_input:
        st.warning("Please enter at least one keyword.")
    else:
        with st.spinner("Harvesting Google News streams and crawling Pantip forums for blended aviation intelligence..."):
            combined_data = fetch_multitopic_data(keywords_input, time_period)
            
            if combined_data.strip():
                executive_insight = generate_airline_report(combined_data, keywords_input)
                st.write("---")
                st.subheader("💡 Blended Social Listening Report (Google News + Pantip)")
                
                with st.container(border=True):
                    st.markdown(f'<div class="report-box">{executive_insight}</div>', unsafe_allow_html=True)
            else:
                st.error("❌ No data found on Google News or Pantip matching the selected parameters.")
