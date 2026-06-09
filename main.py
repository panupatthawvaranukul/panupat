import streamlit as st
import urllib.parse
import xml.etree.ElementTree as ET
import requests
from google import genai 

# --- 1. ตั้งค่าหน้าตาเว็บ (Clean & Minimal) ---
st.set_page_config(
    page_title="Social Listening & Executive Insights",
    page_icon="📊",
    layout="wide"
)

# --- 2. ตั้งค่า API Key และเชื่อมต่อสมองโปร (Gemini 2.5 Pro) ---
client = None
try:
    # ดึงค่าจากระบบ Secrets ของ Streamlit Cloud
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    client = genai.Client(
        api_key=GOOGLE_API_KEY,
        http_options={'api_version': 'v1alpha'}
    )
except Exception:
    # แผนสำรองกรณีรันในคอมพิวเตอร์ตัวเอง
    API_KEY_FALLBACK = "AIzaSyBcmnLrYMOTp6QjZSwOvXi4ig0Xitm41s0"
    if API_KEY_FALLBACK != "AIzaSyBcmnLrYMOTp6QjZSwOvXi4ig0Xitm41s0":
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

# --- 4. ฟังก์ชันดึงข้อมูล "ข่าวสารอย่างเป็นทางการ" ---
def fetch_news_data(kw, period_code):
    encoded_keyword = urllib.parse.quote(kw)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}+when:{period_code}&hl=th&gl=TH&ceid=TH:th"
    data_stream = ""
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:8]  # ดึง 8 ข่าวเด่น
        if items:
            data_stream += f"📰 [หัวข้อข่าวสารอย่างเป็นทางการ] ===\n"
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                data_stream += f"- {title}\n"
    except Exception:
        pass
    return data_stream

# --- 5. ฟังก์ชันดึงข้อมูล "กระแสสังคมและความคิดเห็นบน Pantip" ---
def fetch_pantip_data(kw):
    # เจาะจงดึงข้อมูลเฉพาะโดเมน pantip.com ผ่านระบบ RSS Search
    query = f"{kw} site:pantip.com"
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=th&gl=TH&ceid=TH:th"
    data_stream = ""
    try:
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        items = root.findall('.//item')[:8]  # ดึง 8 กระทู้เด่นที่มีการพูดคุย
        if items:
            data_stream += f"💬 [กระทู้พูดคุย เสียงบ่น และรีวิวบน Pantip] ===\n"
            for item in items:
                title = item.find('title').text if item.find('title') is not None else ""
                # ตัดคำสร้อยท้ายชื่อกระทู้ออกเพื่อความสะอาดของข้อมูล
                clean_title = title.split(" - Pantip")[0]
                data_stream += f"- {clean_title}\n"
    except Exception:
        pass
    return data_stream

# --- 6. ฟังก์ชันควบรวมมิติข้อมูลของทุกคีย์เวิร์ด ---
def fetch_multitopic_data(keywords_str, period_name):
    period_code = get_period_code(period_name)
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    all_data_stream = ""
    
    for kw in keywords:
        all_data_stream += f"====================================\n"
        all_data_stream += f"🔥 คีย์เวิร์ดวิเคราะห์: {kw}\n"
        all_data_stream += f"====================================\n"
        
        # รวบรวมข้อมูลจากทั้งท่อข่าวและท่อเว็บบอร์ด
        all_data_stream += fetch_news_data(kw, period_code)
        all_data_stream += "\n"
        all_data_stream += fetch_pantip_data(kw)
        all_data_stream += "\n"
            
    return all_data_stream

# --- 7. ฟังก์ชันส่งข้อมูลให้สมองระดับโปร (Gemini 2.5 Pro) ตกผลึกขั้นสูง ---
def generate_creative_report(raw_data, topics):
    prompt = f"""
    คุณคือผู้อำนวยการฝ่ายวิเคราะห์กลยุทธ์และอินไซต์อัจฉริยะ (Chief Insights Officer) 
    จงทำหน้าที่วิเคราะห์เชิงลึก (Deep Reasoning) จากข้อมูลดิบที่เรดาร์กวาดมาได้ในหัวข้อต่อไปนี้: {topics}
    
    ข้อมูลดิบที่รวบรวมได้ (แบ่งเป็นฝั่งข่าวสารหลัก และฝั่งความคิดเห็นดิบของผู้บริโภคบนเว็บบอร์ด Pantip):
    {raw_data}
    
    ข้อกำหนดในการเขียนรายงานระดับผู้บริหาร (Executive Brief):
    1. จงทำการวิเคราะห์เปรียบเทียบความสอดคล้องหรือความขัดแย้ง ระหว่าง "สิ่งที่สื่อมวลชนนำเสนอ (Fact)" กับ "สิ่งที่ผู้บริโภคตัวจริงเข้าไปพูดคุย/รีวิว/บ่น บน Pantip (Feeling)" 
    2. ใช้ความฉลาดระดับสูงของคุณในการตกผลึกเนื้อหา ออกมาในรูปแบบที่ไม่ล็อกแพทเทิร์นตายตัว แต่เป็นรูปแบบที่ 'มีประโยชน์ คมคาย และชี้เป้าโอกาสทางธุรกิจหรือวิกฤตที่ต้องเฝ้าระวัง' ได้ชัดเจนที่สุด
    3. เรียบเรียงด้วยภาษาธุรกิจที่เฉียบคม เป็นมืออาชีพ กระชับ โดยใช้ Markdown ในการจัดหัวข้อ ตัวหนา หรือตาราง เพื่อให้อ่านง่าย คลีน และสวยงามที่สุด
    """
    
    try:
        # อัปเกรดเป็น gemini-2.5-pro เพื่อการวิเคราะห์ที่ลึกซึ้งและเฉียบคมยิ่งขึ้น
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"⚠️ เซิร์ฟเวอร์ AI หนาแน่นเกินไปชั่วคราว (ข้อผิดพลาด: {str(e)}) แนะนำให้รอประมาณ 10 วินาทีแล้วกดปุ่มวิเคราะห์ใหม่อีกครั้งครับ"

# --- 8. ส่วนการแสดงผลบนหน้าจอ Interface (Clean UI) ---
st.title("Social Listening & Executive Insights")
st.write("")

# จัดวางช่องกรอกและดรอปดาวน์ให้อยู่แถวเดียวกันตามดีไซน์ที่ต้องการ
col_search, col_time = st.columns([2, 1])

with col_search:
    keywords_input = st.text_input(
        "ช่องค้นหาคีย์เวิร์ด (ใส่ได้หลายคำ คั่นด้วยเครื่องหมายจุลภาค , )", 
        placeholder="เช่น การท่องเที่ยว, วีซ่าฟรี, รถยนต์ไฟฟ้า",
        value="การท่องเที่ยว, วีซ่าฟรี"
    )

with col_time:
    time_period = st.selectbox(
        "เลือกช่วงเวลาของข้อมูลข่าว",
        ["1 สัปดาห์", "1 เดือน", "3 เดือน", "6 เดือน", "YTD", "1 ปี"]
    )

st.write("")

# ปุ่มรันดีไซน์กว้างเต็มผืนคลีนๆ
if st.button("🚀 เริ่มวิเคราะห์ข้อมูล", use_container_width=True):
    if not keywords_input:
        st.warning("กรุณากรอกคีย์เวิร์ดอย่างน้อย 1 คำครับ")
    elif client is None:
        st.error("⚠️ ไม่สามารถเปิดใช้งานสมอง AI ได้เนื่องจากระบบหา API Key ไม่เจอ โปรดตรวจสอบความถูกต้องของระบบ Secrets อีกครั้งครับ")
    else:
        with st.spinner("ระบบกำลังเจาะลึกข้อมูลข่าวสารและขุดกระแสความคิดเห็นจาก Pantip ส่งให้ Gemini 2.5 Pro ประมวลผล..."):
            # สั่งการดึงข้อมูล
            combined_data = fetch_multitopic_data(keywords_input, time_period)
            
            if combined_data:
                # สั่งการวิเคราะห์ด้วยโมเดลตัวโปร
                executive_insight = generate_creative_report(combined_data, keywords_input)
                
                st.write("---")
                st.subheader("💡 ช่องสรุป Social Listening & Insight (News + Pantip)")
                
                # แสดงผลในกล่อง Minimal ผืนใหญ่เต็มหน้าจอ
                with st.container(border=True):
                    st.markdown(executive_insight)
            else:
                st.error("❌ ไม่พบข้อมูลข่าวสารหรือกระทู้ใดๆ ในหัวข้อและช่วงเวลาที่ระบุ ลองปรับเปลี่ยนคำค้นหาดูนะครับ")
