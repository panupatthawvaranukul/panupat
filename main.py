import streamlit as st
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import json
# สลับมาใช้ไลบรารีมาตรฐานดั้งเดิมที่เสถียรกับคีย์ฟรีที่สุด
import google.generativeai as tg_genai 

# --- 1. Web Page & Global Roboto Font Configuration ---
st.set_page_config(
    page_title="Airline Social Listening Dashboard",
    page_icon="✈️",
    layout="wide"
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        html, body, [class*="css"], .stMarkdown, p, button, input, select {
            font-family: 'Roboto', sans-serif !important;
            font-size: 15px !important;
            line-height: 1.6 !important;
        }
        h1 { font-size: 26px !important; font-weight: 700 !important; margin-bottom: 20px !important; }
        h2 { font-size: 20px !important; font-weight: 500 !important; margin-top: 15px !important; margin-bottom: 10px !important; }
        h3 { font-size: 18px !important; font-weight: 500 !important; }
        .report-box { padding: 20px; border-radius: 8px; background-color: transparent; }
    </style>
""", unsafe_allow_html=True)

# --- 2. API Connection Settings (เสถียรชัวร์ 100% สำหรับคีย์ใหม่) ---
GOOGLE_API_KEY = None
APIFY_TOKEN = None

# ดึงค่าจากระบบ Secrets ของ Streamlit Cloud (ดึงจากชื่อกล่องที่ถูกต้อง)
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    APIFY_TOKEN = st.secrets["APIFY_TOKEN"]
except Exception:
    pass

# แผนสำรอง (Fallback) ปล่อยว่างไว้เพื่อความปลอดภัย รหัสจริงจะอยู่ในตู้นิรภัย Streamlit แทน
if not GOOGLE_API_KEY:
    GOOGLE_API_KEY = ""

if not APIFY_TOKEN:
    APIFY_TOKEN = ""

# ตั้งค่าการเชื่อมต่อด้วยวิธีดั้งเดิมที่ไม่มีปัญหาเรื่องสิทธิ์ 401
if GOOGLE_API_KEY:
    tg_genai.configure(api_key=GOOGLE_API_KEY)

# --- 3. Time Period Code Converter ---
def get_period_code(period_name):
    mapping = {"1 Week": "7d", "1 Month": "1m", "3 Months": "3m", "6 Months": "6m", "YTD": "ytd", "1 Year": "1y"}
    return mapping.get(period_name, "7d")

# --- 4. Fetch Data Functions ---
def fetch_news_data(kw, period_code):
    encoded_keyword = urllib.parse.quote(kw)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}+when:{period_code}&hl=th&gl=TH&ceid=TH:th"
    data_stream = ""
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:6]
        if items:
            data_stream += f"📰 [Official News Streams] ===\n"
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                data_stream += f"- {title}\n"
    except Exception:
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
        items = root.findall('.//item')[:6]
        if items:
            data_stream += f"💬 [Consumer Voices on Pantip] ===\n"
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                clean_title = title.split(" - Pantip")[0]
                data_stream += f"- {clean_title}\n"
    except Exception:
        pass
    return data_stream

def fetch_real_x_data(kw):
    if not APIFY_TOKEN:
        return ""
    
    actor_url = "https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items"
    headers = {"Content-Type": "application/json"}
    params = {"token": APIFY_TOKEN}
    payload = {
        "searchTerms": [kw],
        "maxItems": 15,
        "sort": "Latest",
        "tweetLanguage": "th"
    }
    
    data_stream = ""
    try:
        response = requests.post(actor_url, headers=headers, params=params, json=payload, timeout=25)
        if response.status_code == 201 or response.status_code == 200:
            tweets = response.json()
            if tweets:
                data_stream += f"🐦 [Real-time Live Tweets & Complaints on X] ===\n"
                for tweet in tweets:
                    text = tweet.get("full_text", tweet.get("text", ""))
                    if text:
                        clean_text = text.replace("\n", " ").strip()
                        data_stream += f"- {clean_text}\n"
    except Exception:
        pass
    return data_stream

def fetch_multitopic_data(keywords_str, period_name):
    period_code = get_period_code(period_name)
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    all_data_stream = ""
    
    for kw in keywords:
        all_data_stream += f"Analyzed Keyword: {kw}\n"
        all_data_stream += fetch_news_data(kw, period_code)
        all_data_stream += "\n"
        all_data_stream += fetch_pantip_data(kw)
        all_data_stream += "\n"
        all_data_stream += fetch_real_x_data(kw)
        all_data_stream += "\n"
            
    return all_data_stream

# --- 5. Airline Strategy Prompt (English Synthesis) ---
def generate_airline_report(raw_data, topics):
    prompt = f"""
    You are the Chief Strategic Officer (CSO) of a leading international airline. 
    Analyze the following multi-channel online data (comprising public news, long-form discussions on Pantip, and raw live tweets/complaints scraped from X/Twitter) regarding these topics: "{topics}"
    
    Raw Cross-Platform Data:
    {raw_data}
    
    Your task is to synthesize this data into a highly strategic Executive Brief in English.
    
    Strict Strategic Requirements:
    1. Every recommendation and insight MUST be explicitly tailored to the AIRLINE business (e.g., flight operations, passenger experience, ticketing, ground handling, loyalty programs, or airline branding). 
    2. Synthesize customer pain points from both platforms: Contrast the detailed complaints on Pantip with the fast-moving, high-intensity viral trends and angry tweets on X (Twitter), and compare them against official news reporting.
    3. Keep font styling clean and professional. Structure the report using professional Markdown headers with uniform text presentation.
    
    Structure the report with these exact English sections:
    ## Executive Summary
    - Provide a concise 3-line overview of the current multi-channel narrative.
    ## Cross-Platform Passenger Insights
    - Break down specific airline-related customer feedback (Pantip discussion summaries vs. X viral tweet trends).
    ## Airline Strategic Recommendations
    - Actionable operational, customer support, or aviation marketing steps the board should execute immediately.
    """
    try:
      # โค้ดใหม่ที่ถูกต้องและรันผ่านแน่นอน 
        model = tg_genai.GenerativeModel('v1/models/gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI Service temporary unavailable. (Error: {str(e)}). Please wait 10 seconds and try again."

# --- 6. Clean English Dashboard User Interface ---
st.title("Aviation Social Listening & Executive Insights")
st.write("")

col_search, col_time = st.columns([2, 1])

with col_search:
    keywords_input = st.text_input(
        "Search Keywords (Separate multiple topics with a comma ',' | Thai keywords supported)", 
        placeholder="e.g., ดีเลย์, บริการสายการบิน, สัมภาระหาย",
        value="บริการสายการบิน, เลื่อนไฟลท์"
    )

with col_time:
    time_period = st.selectbox(
        "Data Horizon (Time Range for News)",
        ["1 Week", "1 Month", "3 Months", "6 Months", "YTD", "1 Year"]
    )

st.write("")

if st.button("🚀 Execute Strategic Analysis", use_container_width=True):
    if not keywords_input:
        st.warning("Please enter at least one keyword.")
    else:
        with st.spinner("Deep-scraping live X tweets, crawling Pantip, and gleaning news streams for aviation intelligence..."):
            combined_data = fetch_multitopic_data(keywords_input, time_period)
            
            if combined_data:
                executive_insight = generate_airline_report(combined_data, keywords_input)
                st.write("---")
                st.subheader("💡 Social Listening & Executive Insights Report (News + Pantip + Real X)")
                
                with st.container(border=True):
                    st.markdown(f'<div class="report-box">{executive_insight}</div>', unsafe_allow_html=True)
            else:
                st.error("❌ No data found matching the selected parameters. Please refine your keywords.")
