import streamlit as st
import urllib.parse
import xml.etree.ElementTree as ET
import requests
# เปลี่ยนมาใช้ไลบรารีมาตรฐานตัวใหม่ล่าสุดของ Google
from google import genai 

# --- 1. ตั้งค่าหน้าตาเว็บ (Clean & Minimal) ---
st.set_page_config(
    page_title="Social Listening & Executive Insights",
    page_icon="📊",
    layout="wide"
)

# --- 2. ตั้งค่า API Key และโมเดลระดับ Global ---
client = None

try:
    # ดึงค่าจากระบบ Secrets ของ Streamlit Cloud
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    
    # อัปเกรดการต่อท่อ: ใส่ตระกูล HttpOptions เพื่อบังคับระบบความปลอดภัยทางเครือข่าย
    from google.genai import types
    client = genai.Client(
        api_key=GOOGLE_API_KEY,
        http_options={'api_version': 'v1alpha'} # บังคับใช้ท่อเวอร์ชันสากลที่รองรับทุกพื้นที่
    )
except Exception:
    # หากรันในคอมตัวเอง สามารถเอารหัสใส่ตรงนี้ได้ครับ
    API_KEY_FALLBACK = "AIzaSyBcmnLrYMOTp6QjZSwOvXi4ig0Xitm41s0"
    if API_KEY_FALLBACK != "AIzaSyBcmnLrYMOTp6QjZSwOvXi4ig0Xitm41s0":
        from google.genai import types
        client = genai.Client(
            api_key=API_KEY_FALLBACK,
            http_options={'api_version': 'v1alpha'}
        )

# --- 3. ฟังก์ชันแปลงช่วงเวลาสำหรับ Google News ---
def get_period_code(period_name):
    mapping = {
        "1 สัปดาห์": "7d",
        "1 เดือน": "1m",
        "3 เดือน": "3m",
        "6 เดือน": "6m",
        "YTD": "ytd",
        "1 ปี": "1y"
    }
    return mapping.get(period_name, "7d")

# --- 4. ฟังก์ชันดึงข้อมูลจากหลายๆ คีย์เวิร์ด ---
def fetch_multitopic_data(keywords_str, period_name):
    period_code = get_period_code(period_name)
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    all_data_stream = ""
    
    for kw in keywords:
        encoded_keyword = urllib.parse.quote(kw)
        url = f"https://news.google.com/rss/search?q={encoded_keyword}+when:{period_code}&hl=th&gl=TH&ceid=TH:th"
        
        try:
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)
            items = root.findall('.//item')[:10]
            if items:
                all_data_stream += f"=== ข้อมูลสำหรับคีย์เวิร์ด: {kw} ===\n"
                for i, item in enumerate(items):
                    title = item.find('title').text if item.find('title') is not None else ""
                    all_data_stream += f"- {title}\n"
                all_data_stream += "\n"
        except Exception:
            continue
            
    return all_data_stream

# --- 5. ฟังก์ชันให้ Gemini สรุปแบบอิสระ ---
def generate_creative_report(raw_data, topics):
    prompt = f"""
    คุณคือผู้อำนวยการฝ่ายวิเคราะห์กลยุทธ์อัจฉริยะ 
    จงวิเคราะห์ข้อมูลดิบจากโลกออนไลน์เกี่ยวกับเรื่องต่อไปนี้: {topics}
    
    ข้อมูลดิบ:
    {raw_data}
    
    ข้อกำหนดในการเขียนรายงาน:
    - ไม่ต้องแบ่งสัดส่วนตามแพทเทิร์นล็อกตายตัวแบบเดิม
    - จงใช้ความเชี่ยวชาญของ Gemini สรุปเนื้อหาออกมาในรูปแบบที่คิดว่า 'มีประโยชน์ ทรงคุณค่า และช่วยให้ผู้บริหารตัดสินใจเชิงกลยุทธ์ได้ดีที่สุด' 
    - เขียนด้วยภาษาที่เฉียบคม เป็นมืออาชีพ กระชับ และน่าดึงดูด โดยใช้ Markdown ในการจัดหน้าให้สวยงามและอ่านง่ายที่สุด
    """
    
    try:
        # เปลี่ยนการส่งค่าพารามิเตอร์ให้เป็นรูปแบบ String ตรงๆ (รูปแบบนี้ปลอดภัยจาก ClientError ที่สุด)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        # หากระบบคลาวด์ยังดื้อแพ่ง ติดขัดสิทธิ์ API Key ตัวเดิม ให้ส่งข้อความแจ้งเตือนมาแทนหน้าจอพังสีแดง
        return f"⚠️ ระบบ AI ปฏิเสธการทำงานชั่วคราว (ข้อผิดพลาด: {str(e)}) แนะนำให้สร้าง API Key อันใหม่ที่เว็บ Google AI Studio แล้วนำมาเปลี่ยนในระบบ Secrets ครับ"

# --- 6. ออกแบบหน้าจอ Interface ตามรูปภาพเป๊ะๆ ---
st.title("Social Listening & Executive Insights")
st.write("")

col_search, col_time = st.columns([2, 1])

with col_search:
    # ตั้งชื่อตัวแปรหลักว่า keywords_input
    keywords_input = st.text_input(
        "ช่องค้นหาคีย์เวิร์ด (ใส่ได้หลายคำ คั่นด้วยเครื่องหมายจุลภาค , )", 
        placeholder="เช่น การท่องเที่ยว, วีซ่าฟรี, เที่ยวไทย",
        value="การท่องเที่ยว, วีซ่าฟรี"
    )

with col_time:
    time_period = st.selectbox(
        "เลือกช่วงเวลา",
        ["1 สัปดาห์", "1 เดือน", "3 เดือน", "6 เดือน", "YTD", "1 ปี"]
    )

st.write("")

if st.button("🚀 เริ่มวิเคราะห์ข้อมูล", use_container_width=True):
    if not keywords_input:
        st.warning("กรุณากรอกคีย์เวิร์ดอย่างน้อย 1 คำครับ")
    elif client is None:
        st.error("⚠️ ไม่สามารถเปิดใช้งานสมอง AI ได้เนื่องจากระบบหา API Key ไม่เจอ โปรดตรวจสอบความถูกต้องของระบบ Secrets อีกครั้งครับ")
    else:
        with st.spinner("ระบบกำลังรวบรวมมิติข้อมูลและให้ AI สรุปผลความรู้..."):
            # ดึงข้อมูลโดยส่งค่า keywords_input
            news_data = fetch_multitopic_data(keywords_input, time_period)
            
            if news_data:
                # ส่งค่า keywords_input (เช็กตัวแปรสะกดตรงกันเป๊ะ)
                executive_insight = generate_creative_report(news_data, keywords_input)
                
                st.write("---")
                st.subheader("💡 ช่องสรุป Social Listening & Insight")
                
                with st.container(border=True):
                    st.markdown(executive_insight)
            else:
                st.error("❌ ไม่พบข้อมูลข่าวสารในช่วงเวลาและคีย์เวิร์ดที่ระบุ ลองเปลี่ยนคำค้นหาดูนะครับ")
