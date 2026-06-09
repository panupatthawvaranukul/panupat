import streamlit as st
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from google import genai 

# --- 1. Web Page & Global Roboto Font Configuration ---
st.set_page_config(
    page_title="Airline Social Listening Dashboard",
    page_icon="✈️",
    layout="wide"
)

# Inject CSS to import and apply Google's signature 'Roboto' font
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
        
        /* Apply Roboto across all UI elements with strict consistency */
        html, body, [class*="css"], .stMarkdown, p, button, input, select {
            font-family: 'Roboto', sans-serif !important;
            font-size: 15px !important;
            line-height: 1.6 !important;
        }
        /* Standarized professional headers */
        h1 { font-size: 26px !important; font-weight: 700 !important; margin-bottom: 20px !important; }
        h2 { font-size: 20px !important; font-weight: 500 !important; margin-top: 15px !important; margin-bottom: 10px !important; }
        h3 { font-size: 18px !important; font-weight: 500 !important; }
        
        .report-box {
            padding: 20px;
            border-radius: 8px;
            background-color: transparent;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. API Connection Settings ---
client = None
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    client = genai.Client(
        api_key=GOOGLE_API_KEY,
        http_options={'api_version': 'v1alpha'}
    )
except Exception:
    API_KEY_FALLBACK = "AIzaSyBcmnLrYMOTp6QjZSwOvXi4ig0Xitm41s0"
    if API_KEY_FALLBACK != "AIzaSyBcmnLrYMOTp6QjZSwOvXi4ig0Xitm41s0":
        client = genai.Client(
            api_key=API_KEY_FALLBACK,
            http_options={'api_version': 'v1alpha'}
        )

# --- 3. Time Period Code Converter ---
def get_period_code(period_name):
    mapping = {
        "1 Week": "7d",
        "1 Month": "1m",
        "3 Months": "3m",
        "6 Months": "6m",
        "YTD": "ytd",
        "1 Year": "1y"
    }
    return mapping.get(period_name, "7d")

# --- 4. Fetch Data Functions (Multi-Channel Scraping) ---

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

def fetch_x_data(kw):
    # ดึงข้อมูลกระแสเรียลไทม์บน X (Twitter) ผ่านท่อค้นหาเปิดพิเศษแบบไร้ API Key
    query = f"{kw} (lang:th)"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}+site:x.com&hl=th&gl=TH&ceid=TH:th"
    data_stream = ""
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:6]
        if items:
            data_stream += f"🐦 [Real-time Tweets & Viral Concerns on X] ===\n"
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                # ทำความสะอาดข้อมูลข้อความทวีต
                clean_tweet = title.split(" / X")[0].split("on Twitter:")[0].strip()
                if clean_tweet:
                    data_stream += f"- {clean_tweet}\n"
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
        all_data_stream += fetch_x_data(kw)
        all_data_stream += "\n"
            
    return all_data_stream

# --- 5. Airline Strategy Prompt (English Synthesis) ---
def generate_airline_report(raw_data, topics):
    prompt = f"""
    You are the Chief Strategic Officer (CSO) of a leading international airline. 
    Analyze the following multi-channel online data (comprising public news, long-form discussions on Pantip, and short viral tweets/complaints on X/Twitter) regarding these topics: "{topics}"
    
    Raw Cross-Platform Data:
    {raw_data}
    
    Your task is to synthesize this data into a highly strategic Executive Brief in English.
    
    Strict Strategic Requirements:
    1. Every recommendation and insight MUST be explicitly tailored to the AIRLINE business (e.g., flight operations, passenger experience, ticketing, ground handling, loyalty programs, or airline branding). 
    2. Synthesize customer pain points from both platforms: Contrast the detailed complaints on Pantip with the fast-moving, high-intensity viral trends on X (Twitter), and compare them against official news reporting.
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
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
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
    elif client is None:
        st.error("⚠️ AI engine connection failed. Please check your Secrets configuration for GOOGLE_API_KEY.")
    else:
        with st.spinner("Gleaning news streams, scraping Pantip discussions, and capturing X trends for aviation intelligence..."):
            combined_data = fetch_multitopic_data(keywords_input, time_period)
            
            if combined_data:
                executive_insight = generate_airline_report(combined_data, keywords_input)
                
                st.write("---")
                st.subheader("💡 Social Listening & Executive Insights Report (News + Pantip + X)")
                
                with st.container(border=True):
                    st.markdown(f'<div class="report-box">{executive_insight}</div>', unsafe_allow_html=True)
            else:
                st.error("❌ No data found matching the selected parameters. Please refine your keywords.")
