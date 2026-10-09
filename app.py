# ==============================================================================
# 🌶️ ฟ้าใสตำนัว (Fahsai Tum Nua) - ระบบสั่งอาหารโต๊ะ & จอครัวอัจฉริยะ (Smart POS)
# ==============================================================================
# โครงสร้างการทำงานของโปรแกรม:
# 1. 🗄️ ฐานข้อมูล SQLite (restaurant.db): บันทึกเมนูอาหาร, โต๊ะ, ออเดอร์ และใบเสร็จ
# 2. 🪑 จัดการโต๊ะอาหาร & QR-Code: เพิ่ม/ลบโต๊ะ สร้าง QR-Code อัตโนมัติ และเคลียร์โต๊ะ
# 3. 🍳 จอครัว & เคาน์เตอร์คิดเงิน (KDS): แสดงออเดอร์สด อัปเดตทุก 3 วินาที พร้อมเสียงเตือน
# 4. 🏆 เมนูขายดี: จัดอันดับเมนูยอดนิยม ยอดขายรวม และสรุปตามหมวดหมู่อาหาร
# 5. 📱 ฝั่งลูกค้า: สแกน QR Code เข้ามาสั่งอาหาร จัดการตะกร้า และติดตามสถานะแบบเรียลไทม์
# ==============================================================================

# --- ไลบรารีที่จำเป็นสำหรับระบบ ---
import streamlit as st                      # เฟรมเวิร์กหลักสำหรับสร้างเว็บแอปพลิเคชัน
import streamlit.components.v1 as components # ใช้สำหรับแทรก HTML/JS เช่น หน้าต่างพิมพ์ใบเสร็จ
import sqlite3                             # ระบบจัดการฐานข้อมูลในตัวเครื่อง (ไม่ต้องลงเซิร์ฟเวอร์แยก)
import os                                  # จัดการไฟล์และพาธของระบบปฏิบัติการ
import base64                              # เข้ารหัสไฟล์รูปภาพและเสียงเป็นข้อความ Base64
import wave                                # สร้างและจัดการไฟล์เสียงแบบคลื่นเสียง WAV
import struct                              # แปลงข้อมูลตัวเลขเป็นไบนารีสำหรับไฟล์เสียง
import math                                # ฟังก์ชันคณิตศาสตร์ (ใช้คำนวณคลื่นเสียงกระดิ่ง)
import io                                  # จัดการข้อมูลในหน่วยความจำ RAM (In-Memory Buffer)
from datetime import datetime, timedelta, timezone # จัดการวันและเวลา
from urllib.parse import quote             # เข้ารหัส URL สำหรับสร้างภาพ QR Code

# --- ตั้งค่าเวลาประเทศไทย (UTC+7 / Asia/Bangkok) ---
# เนื่องจากเซิร์ฟเวอร์ Cloud (เช่น Streamlit Cloud) มักตั้งเวลาเป็น UTC (ช้ากว่าไทย 7 ชม.)
# เราจึงล็อกเขตเวลาให้เป็น UTC+7 โดยตรง เพื่อให้เวลาในระบบตรงกับเวลาจริงในประเทศไทยเสมอ
TH_TZ = timezone(timedelta(hours=7))

def get_thai_now():
    """ฟังก์ชันคืนค่าวันและเวลาปัจจุบันของประเทศไทย (UTC+7)"""
    return datetime.now(TH_TZ)

# --- ตั้งค่าหน้าเว็บ Streamlit เบื้องต้น ---
st.set_page_config(
    page_title="ฟ้าใสตำนัว",               # ชื่อที่จะแสดงบนแท็บของเบราว์เซอร์
    page_icon="🌶️",                         # ไอคอน Favicon ของแท็บเว็บ
    layout="wide",                          # ใช้พื้นที่หน้าจอแบบเต็มความกว้าง (Wide mode)
    initial_sidebar_state="collapsed"       # ซ่อนแถบเมนูด้านข้างเริ่มต้น เพื่อให้ดูเหมือน App มือถือ
)

# --- CSS อัจฉริยะ ปรับหน้าตาให้สวยงาม รองรับทั้ง มือถือ (iOS/Android), แท็บเล็ต, iPad และ คอมพิวเตอร์ ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');

/* บังคับใช้ฟอนต์ Prompt โดยไม่ทับไอคอน Material Symbols ของ Streamlit */
html, body, p, input, select, textarea {
    font-family: 'Prompt', sans-serif !important;
}

.stMarkdown, .stButton > button {
    font-family: 'Prompt', sans-serif !important;
}

/* คืนค่าฟอนต์ไอคอน Material Symbols เพื่อไม่ให้กลายเป็นตัวหนังสือคำว่า expand_less ทับบนปุ่ม */
[data-testid="stIconMaterial"], 
[class*="material-symbols"], 
[class*="material-icons"] {
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    font-style: normal !important;
}

/* ซ่อนไอคอนลูกศร expand_less/expand_more ในปุ่ม popover ไม่ให้บังข้อความ */
div[data-testid="stPopover"] > button [data-testid="stIconMaterial"] {
    display: none !important;
}

div[data-testid="stPopover"] > button {
    font-family: 'Prompt', sans-serif !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    min-height: 44px !important;
    font-weight: 600 !important;
}

/* ปรับระยะขอบหน้าจอให้พอดีกับมือถือ */
@media (max-width: 640px) {
    .main .block-container {
        padding: 0.75rem 0.5rem 3rem 0.5rem !important;
    }
    h1 { font-size: 1.8rem !important; }
    h2 { font-size: 1.35rem !important; }
    h3 { font-size: 1.15rem !important; }
}

@media (min-width: 641px) and (max-width: 1024px) {
    .main .block-container {
        padding: 1.5rem 1.25rem 3rem 1.25rem !important;
    }
}

/* ปุ่มกดขนาดใหญ่ สัมผัสง่ายสำหรับนิ้วมือบนสมาร์ตโฟน (Touch-friendly 44px+) */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    min-height: 44px !important;
    font-size: 14px !important;
    transition: all 0.15s ease !important;
}

.stButton > button:active {
    transform: scale(0.96) !important;
}

/* ปุ่ม Primary โดดเด่นด้วยสีส้มไล่เฉด */
button[kind="primary"] {
    background: linear-gradient(135deg, #ea580c 0%, #dc2626 100%) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(234, 88, 12, 0.35) !important;
}

/* การ์ดรายการอาหารมนโค้ง สวยงาม มีมิติ */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    border: 1px solid #fed7aa !important;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04) !important;
    background: #ffffff !important;
    padding: 10px !important;
}

/* รูปภาพอาหารตัดมุมโค้งสวยงาม */
img {
    border-radius: 14px !important;
    object-fit: cover !important;
}

/* 🔶 ปุ่มเลือกหมวดหมู่อาหาร ให้เป็นปุ่มทรงเหลี่ยมชัดเจน (Crisp Rectangular Category Buttons) */
div[data-testid="stPills"], div[data-testid="stRadio"] {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
    margin: 4px 0 14px 0 !important;
}
div[data-testid="stPills"] > div, div[data-testid="stRadio"] > div[role="radiogroup"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    justify-content: center !important;
    width: 100% !important;
}

/* สไตล์สำหรับ st.pills */
div[data-testid="stPills"] button {
    border-radius: 4px !important; /* ปรับเป็นทรงเหลี่ยมชัดเจน */
    border: 2px solid #ea580c !important;
    background-color: #ffffff !important;
    color: #431407 !important;
    padding: 8px 18px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.15s ease-in-out !important;
}
div[data-testid="stPills"] button:hover {
    background-color: #ffedd5 !important;
    border-color: #c2410c !important;
}
div[data-testid="stPills"] button[aria-selected="true"],
div[data-testid="stPills"] button[data-checked="true"] {
    background-color: #ea580c !important;
    color: #ffffff !important;
    border-color: #9a3412 !important;
    box-shadow: 0 4px 10px rgba(234, 88, 12, 0.35) !important;
}

/* สไตล์ fallback สำหรับ stRadio โดยไม่ปิดกั้นการคลิก */
div[data-testid="stRadio"] label[data-baseweb="radio"] {
    border-radius: 4px !important;
    border: 2px solid #ea580c !important;
    background-color: #ffffff !important;
    padding: 8px 18px !important;
    cursor: pointer !important;
    margin: 0 !important;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.15s ease-in-out !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
    background-color: #ffedd5 !important;
    border-color: #c2410c !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] svg {
    display: none !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] input {
    opacity: 0 !important;
    position: absolute !important;
    width: 0 !important;
    height: 0 !important;
    pointer-events: none !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"] p,
div[data-testid="stRadio"] label[data-baseweb="radio"] span,
div[data-testid="stRadio"] label[data-baseweb="radio"] div {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #431407 !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked),
div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] {
    background-color: #ea580c !important;
    border: 2px solid #9a3412 !important;
    box-shadow: 0 4px 10px rgba(234, 88, 12, 0.35) !important;
}
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span,
div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) div,
div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] p,
div[data-testid="stRadio"] label[data-baseweb="radio"][aria-checked="true"] span {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* ซ่อนแถบเมนูที่ไม่จำเป็นของ Streamlit เพื่อประสบการณ์แบบ App แท้ */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 🗄️ การจัดการฐานข้อมูล SQLite (Database Setup)
# ==============================================================================
# ระบบใช้ SQLite ซึ่งเก็บข้อมูลทั้งหมดไว้ในไฟล์เดียวชื่อ "restaurant.db"
# ข้อดี: เบา รวดเร็ว พกพาง่าย ไม่ต้องติดตั้ง Database Server เพิ่มเติม

DB_NAME = "restaurant.db"

def init_db():
    """
    ฟังก์ชันสร้างตารางฐานข้อมูลที่จำเป็น (ถ้ายังไม่มี) 
    และบันทึกข้อมูลเมนูอาหารเริ่มต้นของร้านฟ้าใสตำนัว
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1. ตารางเมนูอาหาร (menu_items)
    # เก็บชื่ออาหาร หมวดหมู่ ราคา ต้นทุน รูปภาพ และคำอธิบาย
    c.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,          -- ชื่อเมนูอาหาร (ห้ามซ้ำ)
            category TEXT NOT NULL,             -- หมวดหมู่อาหาร (เช่น ส้มตำ, ย่าง, ต้ม)
            price REAL NOT NULL,                -- ราคาขาย (บาท)
            cost REAL DEFAULT 0,                -- ต้นทุนวัตถุดิบ (บาท)
            image TEXT,                         -- URL รูปภาพอาหาร
            description TEXT                    -- คำอธิบายความอร่อย/จุดเด่น
        )
    ''')

    # 2. ตารางโต๊ะอาหารในร้าน (tables)
    # เก็บหมายเลขโต๊ะ ชื่อโต๊ะ และสถานะ (ว่าง/มีลูกค้า)
    # *หมายเหตุ: ค่าเริ่มต้นไม่มีโต๊ะ โดยเจ้าของร้านสามารถกดเพิ่ม/ลบโต๊ะได้เองตามต้องการ
    c.execute('''
        CREATE TABLE IF NOT EXISTS tables (
            id INTEGER PRIMARY KEY,
            table_number INTEGER NOT NULL UNIQUE, -- หมายเลขโต๊ะ เช่น 1, 2, 3
            name TEXT,                            -- ชื่อเรียกโต๊ะ เช่น "โต๊ะที่ 1", "ซุ้มริมน้ำ 2"
            status TEXT DEFAULT 'available'       -- สถานะโต๊ะ
        )
    ''')

    # 3. ตารางออเดอร์/บิลหลัก (orders)
    # เก็บรหัสบิล โต๊ะที่สั่ง สถานะบิล ยอดเงินรวม และวันเวลาที่สั่ง
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_id INTEGER NOT NULL,          -- หมายเลขโต๊ะที่สั่ง
            status TEXT NOT NULL DEFAULT 'pending', -- สถานะบิล: pending -> accepted -> cooked -> served -> paid -> archived
            total_price REAL NOT NULL,          -- ยอดเงินรวมทั้งสิ้นของบิล (บาท)
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- วันและเวลาที่สั่งอาหาร
        )
    ''')

    # 4. ตารางรายการอาหารย่อยในแต่ละบิล (order_items)
    # เก็บว่าในบิลนั้นๆ สั่งอาหารจานใดบ้าง จำนวนกี่จาน ราคา และสถานะการปรุงแต่ละจาน
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,          -- เชื่อมกับ orders.id
            item_name TEXT NOT NULL,            -- ชื่อเมนูอาหารที่สั่ง
            price REAL NOT NULL,                -- ราคาต่อหน่วย ณ ตอนที่สั่ง
            cost REAL DEFAULT 0,                -- ต้นทุนต่อหน่วย
            quantity INTEGER NOT NULL,          -- จำนวนจานที่สั่ง
            note TEXT,                          -- โน้ตเพิ่มเติม เช่น เผ็ดน้อย, ไม่ใส่ชูรส
            status TEXT DEFAULT 'pending'       -- สถานะแต่ละจาน: pending(กำลังปรุง) -> cooked(ปรุงเสร็จ) -> served(เสิร์ฟแล้ว)
        )
    ''')

    # 5. ตารางสมาชิกสะสมแต้ม (members)
    # เก็บข้อมูลสมาชิก: ชื่อ, นามสกุล, หมายเลขโทรศัพท์ และคะแนนสะสม
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,           -- ชื่อสมาชิก
            last_name TEXT NOT NULL,            -- นามสกุล
            phone TEXT NOT NULL UNIQUE,         -- หมายเลขโทรศัพท์ (ห้ามซ้ำ)
            points INTEGER DEFAULT 0,           -- คะแนนสะสม
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- วันเวลาที่สมัครสมาชิก
        )
    ''')

    # ตรวจสอบและอัปเกรดคอลัมน์ status ในตาราง order_items แบบอัตโนมัติ (Backward Compatibility)
    c.execute("PRAGMA table_info(order_items)")
    existing_cols = [col[1] for col in c.fetchall()]
    if 'status' not in existing_cols:
        c.execute("ALTER TABLE order_items ADD COLUMN status TEXT DEFAULT 'pending'")
    c.execute("UPDATE order_items SET status = 'pending' WHERE status IS NULL")

    # ตรวจสอบและอัปเกรดคอลัมน์ระบบสมาชิกและส่วนลดในตาราง orders แบบอัตโนมัติ
    c.execute("PRAGMA table_info(orders)")
    order_cols = [col[1] for col in c.fetchall()]
    if 'subtotal' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN subtotal REAL DEFAULT 0")
    if 'discount' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN discount REAL DEFAULT 0")
    if 'points_used' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN points_used INTEGER DEFAULT 0")
    if 'points_earned' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN points_earned INTEGER DEFAULT 0")
    if 'member_phone' not in order_cols:
        c.execute("ALTER TABLE orders ADD COLUMN member_phone TEXT DEFAULT NULL")

    # บันทึกชุดเมนูอาหารทั้งหมดของร้าน "ฟ้าใสตำนัว" (10 หมวดหมู่ 131 เมนูแซ่บ)
    fahsai_menu = [
        # --- 1. หมวด "ตำนัว" ---
        ("ตำไทย", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "รสเปรี้ยวหวานกลมกล่อม ถั่วคั่วใหม่ กุ้งแห้งเกรดเอ"),
        ("ตำไทยไข่เค็ม", "ตำนัว", 60, 22, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ตำไทยครบรส ท็อปไข่เค็มเต็มใบ มันนัวเข้ากัน"),
        ("ตำไทยปู", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ตำไทยรสเด็ด ใส่ปูดองเค็มสะอาด นัวกลมกล่อม"),
        ("ตำไทยปูปลาร้า", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=600&q=80", "ตำไทยผสมน้ำปลาร้าต้มสุกสูตรเด็ด แซ่บนัวลงตัว"),
        ("ตำปูปลาร้า", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=600&q=80", "เส้นมะละกอกรอบ ปลาร้าต้มสุกนัวเข้มข้น รสอีสานแท้"),
        ("ตำปลาร้า", "ตำนัว", 45, 15, "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=600&q=80", "ปลาร้านัวกลิ่นหอม รสแซ่บจัดจ้าน ซดน้ำส้มตำฟิน"),
        ("ตำปู", "ตำนัว", 45, 15, "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=600&q=80", "ตำปูเค็มสะอาด รสเปรี้ยวเผ็ดเค็มกำลังดี"),
        ("ตำซั่ว", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=600&q=80", "ตำปลาร้าใส่เส้นขนมจีนนุ่มลื่น แคบหมูกรอบ"),
        ("ตำแตง", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80", "แตงกวาสดกรอบฉ่ำน้ำ คลุกเคล้าน้ำปลาร้าแซ่บนัว"),
        ("ตำถั่ว", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80", "ถั่วฝักยาวกรุบกรอบ ตำพริกแห้งและปลาร้าเข้มข้น"),
        ("ตำมะม่วง", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "มะม่วงเปรี้ยวกำลังดี ตำใส่น้ำปลาร้า แซ่บจี๊ดถึงใจ"),
        ("ตำข้าวโพด", "ตำนัว", 60, 22, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "ข้าวโพดหวานเม็ดเต่ง ตำคลุกน้ำยำรสแซ่บกลมกล่อม"),
        ("ตำข้าวโพดไข่เค็ม", "ตำนัว", 70, 26, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "ข้าวโพดหวานมัน ท็อปไข่เค็มชิ้นโต นัวฟิน"),
        ("ตำแครอท", "ตำนัว", 50, 18, "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80", "เส้นแครอทส้มสดกรอบ ตำรสจัดจ้านเพื่อสุขภาพ"),
        ("ตำถาด", "ตำนัว", 159, 60, "https://images.unsplash.com/photo-1603133872878-684f208fb84b?auto=format&fit=crop&w=600&q=80", "ตำถาดไซส์ใหญ่ เครื่องแน่น หมูยอ แคบหมู ไข่ต้ม ผักครบ"),
        ("ตำทะเล", "ตำนัว", 120, 48, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "กุ้ง ปลาหมึก หอยแครงสดลวก คลุกเคล้าน้ำส้มตำแซ่บ"),
        ("ตำกุ้งสด", "ตำนัว", 100, 40, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "กุ้งสดเนื้อเด้งหวานฉ่ำ เคล้าน้ำปลาร้านัวถึงใจ"),
        ("ตำกุ้งสุก", "ตำนัว", 100, 40, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "กุ้งลวกสุกพอดีเนื้อหวานเด้ง ตำรสเปรี้ยวเผ็ดกลมกล่อม"),
        ("ตำหอยแครง", "ตำนัว", 100, 40, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "หอยแครงสดลวกสะดุ้ง เนื้อหวานกรุบ ตำแซ่บนัว"),
        ("ตำปูม้า", "ตำนัว", 120, 50, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "ปูม้าสดเนื้อแน่นฉ่ำหวาน ตำรสจัดจ้านแซ่บสะท้าน"),
        ("ตำปูม้าปลาร้า", "ตำนัว", 120, 50, "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=600&q=80", "ปูม้าสดผสานน้ำปลาร้าต้มสุกสูตรพิเศษ นัวถึงเครื่อง"),
        ("ตำรวมทะเล", "ตำนัว", 150, 60, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "ยกทะเลมาไว้ในครก กุ้ง หมึก ปูม้า หอยแครง จัดเต็ม"),

        # --- 2. หมวด "ตำแซ่บ" ---
        ("ตำเหลาทะเล", "ตำแซ่บ", 140, 55, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "เกาเหลาไม่ใส่เส้นมะละกอ ทะเลเน้นๆ น้ำยำแซ่บจี๊ด"),
        ("ตำเหลาหมูยอ", "ตำแซ่บ", 80, 30, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "หมูยออุบลอย่างดีหั่นชิ้นหนา คลุกน้ำยำรสเด็ด"),
        ("ตำเหลาหอยแครง", "ตำแซ่บ", 120, 48, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "หอยแครงลวกไซส์พอดีคำ ตำเหลารสแซ่บซดน้ำนัว"),
        ("ตำเหลากุ้งสด", "ตำแซ่บ", 120, 48, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "กุ้งสดตัวโตเนื้อเด้ง ตำเหลาน้ำปลาร้าเข้มข้น"),
        ("ตำเหลากุ้งสุก", "ตำแซ่บ", 120, 48, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "กุ้งลวกสุกเนื้อเด้งหวาน คลุกน้ำส้มตำรสแซ่บ"),
        ("ตำเหลาปูม้า", "ตำแซ่บ", 140, 55, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "ปูม้าสดเนื้อแน่น ตำเหลาไม่ใส่เส้น เน้นเนื้อปูเต็มคำ"),
        ("ตำเกาเหลากุ้งสด", "ตำแซ่บ", 120, 48, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "เกาเหลากุ้งสดน้ำปลาร้า แซ่บจี๊ดพริกสด"),
        ("ตำเกาเหลาทะเล", "ตำแซ่บ", 140, 55, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "เกาเหลารวมมิตรทะเล กุ้ง หมึก หอย แซ่บถึงทรวง"),
        ("ตำแซลมอน", "ตำแซ่บ", 150, 65, "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=600&q=80", "แซลมอนสดนำเข้าเกรดซาชิมิ ตำน้ำยำรสเด็ดเข้มข้น"),
        ("ตำแซลมอนกุ้งสด", "ตำแซ่บ", 160, 70, "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=600&q=80", "แซลมอนเนื้อนุ่มและกุ้งสดเด้ง คู่หูความแซ่บ"),
        ("ตำแซลมอนปูม้า", "ตำแซ่บ", 170, 75, "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=600&q=80", "คอมโบสุดหรู แซลมอนสดและปูม้าเนื้อหวาน"),
        ("ตำหมูยอ", "ตำแซ่บ", 60, 24, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "หมูยอเนื้อแน่นหอมพริกไทย ตำคลุกน้ำส้มตำนัว"),
        ("ตำไส้กรอก", "ตำแซ่บ", 60, 24, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ไส้กรอกไก่หนังกรอบ ตำรสเผ็ดเปรี้ยวหวาน"),
        ("ตำเล็บมือนาง", "ตำแซ่บ", 70, 28, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "เล็บมือนางกรุบกรอบ เคี้ยวเพลิน รสแซ่บสะใจ"),
        ("ตำขนมจีน", "ตำแซ่บ", 50, 18, "https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=600&q=80", "เส้นขนมจีนนุ่มลื่น คลุกน้ำปลาร้าต้มสุกและพริกสด"),
        ("ตำมาม่า", "ตำแซ่บ", 60, 22, "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=600&q=80", "เส้นมาม่าลวกเหนียวนุ่ม ตำรสจัดจ้านเครื่องแน่น"),
        ("ตำเส้นแก้ว", "ตำแซ่บ", 60, 22, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "เส้นแก้วกรุบกรอบ แคลอรีต่ำ ตำรสแซ่บนัว"),

        # --- 3. หมวด "เพิ่มท็อปปิ้ง" ---
        ("ไข่เค็ม", "เพิ่มท็อปปิ้ง", 15, 6, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ไข่เค็มไชยา มันนัวเต็มใบ"),
        ("ไข่เยี่ยวม้า", "เพิ่มท็อปปิ้ง", 20, 8, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ไข่เยี่ยวม้าเนื้อเด้ง ทานคู่ส้มตำ"),
        ("หมูยอ", "เพิ่มท็อปปิ้ง", 25, 10, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "หมูยออุบลแท้ ลวกพร้อมทาน"),
        ("แคบหมู (ท็อปปิ้ง)", "เพิ่มท็อปปิ้ง", 20, 7, "https://images.unsplash.com/photo-1541529086526-db283c563270?auto=format&fit=crop&w=600&q=80", "แคบหมูกรอบไม่อมน้ำมัน"),
        ("กุ้งสด", "เพิ่มท็อปปิ้ง", 40, 18, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "กุ้งสดแกะเปลือกเนื้อหวานเด้ง"),
        ("กุ้งสุก", "เพิ่มท็อปปิ้ง", 40, 18, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "กุ้งลวกสุกเนื้อเด้งหวาน"),
        ("ปูม้า", "เพิ่มท็อปปิ้ง", 50, 22, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "ปูม้าสดเนื้อแน่นฉ่ำ"),
        ("หอยแครง", "เพิ่มท็อปปิ้ง", 40, 18, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "หอยแครงลวกสุกสะดุ้ง"),
        ("เล็บมือนาง", "เพิ่มท็อปปิ้ง", 30, 12, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "เล็บมือนางต้มสุกกรุบกรอบ"),
        ("ไส้กรอก", "เพิ่มท็อปปิ้ง", 25, 10, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ไส้กรอกไก่ลวกหั่นชิ้น"),
        ("แซลมอน", "เพิ่มท็อปปิ้ง", 60, 28, "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=600&q=80", "แซลมอนสดหั่นเต๋าพร้อมทาน"),
        ("ขนมจีน (ท็อปปิ้ง)", "เพิ่มท็อปปิ้ง", 15, 5, "https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=600&q=80", "เส้นขนมจีนสดแป้งหมัก 1 จับ"),
        ("มาม่า", "เพิ่มท็อปปิ้ง", 15, 5, "https://images.unsplash.com/photo-1569058242253-92a9c755a0ec?auto=format&fit=crop&w=600&q=80", "เส้นมาม่าลวกพร้อมทาน"),
        ("เส้นแก้ว", "เพิ่มท็อปปิ้ง", 20, 8, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "เส้นแก้วกรุบกรอบ"),
        ("ข้าวโพด", "เพิ่มท็อปปิ้ง", 20, 7, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "ข้าวโพดหวานต้มสุกฝาน"),

        # --- 4. หมวด "เมนูทอด" ---
        ("ไก่ทอด", "เมนูทอด", 60, 24, "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=600&q=80", "ไก่ทอดกรอบนอกนุ่มใน หอมกระเทียมพริกไทย"),
        ("ปีกไก่ทอด", "เมนูทอด", 70, 28, "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?auto=format&fit=crop&w=600&q=80", "ปีกไก่ทอดกรอบสีทอง ไม่อมน้ำมัน"),
        ("น่องไก่ทอด", "เมนูทอด", 70, 28, "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=600&q=80", "น่องไก่หมักเครื่องเทศ ทอดกรอบฉ่ำเนื้อใน"),
        ("ปีกไก่ทอดน้ำปลา", "เมนูทอด", 80, 32, "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?auto=format&fit=crop&w=600&q=80", "หมักน้ำปลาแท้อย่างดี หอมกรอบเค็มนิดๆ กลมกล่อม"),
        ("หมูทอด", "เมนูทอด", 70, 28, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "หมูหมักสูตรโบราณ ทอดร้อนๆ ทานคู่ข้าวเหนียว"),
        ("หมูแดดเดียว", "เมนูทอด", 80, 32, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "หมูแดดเดียวเนื้อนุ่มเคี้ยวเพลิน รสกลมกล่อม"),
        ("เนื้อแดดเดียว", "เมนูทอด", 90, 38, "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80", "เนื้อวัวคัดพิเศษ หมักสมุนไพรตากแดด ทอดหอมกรุ่น"),
        ("คอหมูทอด", "เมนูทอด", 80, 32, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "คอหมูแทรกมันทอดกรอบนอกนุ่มใน น้ำจิ้มแจ่ว"),
        ("สามชั้นทอดน้ำปลา", "เมนูทอด", 80, 32, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "หมูสามชั้นหนังกรอบเนื้อฉ่ำ คลุกน้ำปลาทอดหอมเตะจมูก"),
        ("เอ็นไก่ทอด", "เมนูทอด", 80, 32, "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?auto=format&fit=crop&w=600&q=80", "เอ็นข้อไก่คลุกงาทอด กรุบกรอบเคี้ยวมัน"),
        ("หนังไก่ทอด", "เมนูทอด", 60, 22, "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?auto=format&fit=crop&w=600&q=80", "หนังไก่ทอดกรอบสีทอง ไม่อมน้ำมัน ทานเพลิน"),
        ("ไส้กรอกทอด", "เมนูทอด", 50, 18, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ไส้กรอกแดงในตำนาน ทอดกรอบพองจิ้มน้ำจิ้ม"),
        ("ลูกชิ้นทอด", "เมนูทอด", 50, 18, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ลูกชิ้นหมูและเนื้อทอดรวม เสิร์ฟพร้อมน้ำจิ้มมะขาม"),
        ("หมูยอทอด", "เมนูทอด", 60, 24, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "หมูยออุบลทอดสีทอง ผิวนอกตึงเนื้อในนุ่ม"),
        ("แหนมทอด", "เมนูทอด", 70, 28, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "แหนมหมูรสเปรี้ยวกำลังดี ทอดหอมเสิร์ฟคู่พริกขิง"),

        # --- 5. หมวด "เมนูย่าง" ---
        ("คอหมูย่าง", "เมนูย่าง", 90, 36, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "คอหมูแท้แทรกมัน ย่างเตาถ่านหอมกรุ่น น้ำจิ้มแจ่วเด็ด"),
        ("ไก่ย่าง", "เมนูย่าง", 80, 32, "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=600&q=80", "ไก่หมักสมุนไพรไทย ย่างหนังกรอบเนื้อนุ่มฉ่ำ"),
        ("ปีกไก่ย่าง", "เมนูย่าง", 70, 28, "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?auto=format&fit=crop&w=600&q=80", "ปีกไก่เสียบไม้ย่างเตาถ่าน หอมกระเทียมพริกไทย"),
        ("เนื้อย่าง", "เมนูย่าง", 100, 42, "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80", "เนื้อโคขุนคัดพิเศษ ย่างระดับมีเดียม น้ำจิ้มแจ่วขม/เปรี้ยว"),
        ("หมูย่าง", "เมนูย่าง", 80, 32, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "หมูหมักนุ่มย่างไฟอ่อน หอมกรุ่นละมุนลิ้น"),
        ("ไส้ย่าง", "เมนูย่าง", 80, 32, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "ไส้อ่อนล้างสะอาดไม่ขม ย่างเกรียมกำลังดี จิ้มแจ่ว"),
        ("ตับย่าง", "เมนูย่าง", 70, 26, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "ตับหมักเครื่องเทศเสียบไม้ย่าง ไม่แห้งกระด้าง"),
        ("ตับหมูย่าง", "เมนูย่าง", 70, 26, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "ตับหมูสดใหม่ย่างไฟหอมหวาน นุ่มละมุน"),
        ("เสือร้องไห้", "เมนูย่าง", 120, 50, "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80", "เนื้อติดมันย่างเตาถ่านในตำนาน กลิ่นหอมเย้ายวนใจ"),
        ("หมูสามชั้นย่าง", "เมนูย่าง", 90, 36, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "สามชั้นย่างเกรียมหนังกรุบ มันหอมฉ่ำ"),
        ("ไส้กรอกอีสานย่าง", "เมนูย่าง", 70, 28, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "ไส้กรอกอีสานเปรี้ยวกำลังดี ย่างเตาถ่านหนังกรอบ"),

        # --- 6. หมวด "เมนูลาบ / น้ำตก" ---
        ("ลาบหมู", "เมนูลาบ / น้ำตก", 70, 28, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "หมูสับคลุกข้าวคั่วใหม่ พริกป่น มะนาวสด หอมสะระแหน่"),
        ("ลาบไก่", "เมนูลาบ / น้ำตก", 70, 28, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "เนื้อไก่สับนุ่ม คลุกเคล้าเครื่องลาบอีสานแท้"),
        ("ลาบเนื้อ", "เมนูลาบ / น้ำตก", 80, 34, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "เนื้อวัวสับคลุกเครื่องลาบรสจัดจ้าน เลือกสุก/ดิบได้"),
        ("ลาบปลาดุก", "เมนูลาบ / น้ำตก", 70, 28, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "ปลาดุกย่างแกะเนื้อสับ คลุกข้าวคั่วสมุนไพรหอมกรุ่น"),
        ("ลาบทะเล", "เมนูลาบ / น้ำตก", 120, 50, "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=600&q=80", "กุ้ง หมึก ลวกสะดุ้ง คลุกเครื่องลาบแซ่บจี๊ดจ๊าด"),
        ("ลาบวุ้นเส้น", "เมนูลาบ / น้ำตก", 80, 32, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "วุ้นเส้นเหนียวนุ่มคลุกหมูสับและเครื่องลาบรสเข้ม"),
        ("ลาบหมูทอด", "เมนูลาบ / น้ำตก", 80, 32, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "ลาบหมูปั้นก้อนทอดกรอบนอกนุ่มใน หอมเครื่องเทศ"),
        ("น้ำตกหมู", "เมนูลาบ / น้ำตก", 80, 32, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "เนื้อหมูย่างนุ่มฉ่ำ คลุกน้ำยำน้ำตกรสแซ่วกลมกล่อม"),
        ("น้ำตกเนื้อ", "เมนูลาบ / น้ำตก", 90, 38, "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80", "เนื้อย่างติดมันหั่นชิ้น ปรุงน้ำตกรสแซ่บหอมข้าวคั่ว"),
        ("น้ำตกคอหมูย่าง", "เมนูลาบ / น้ำตก", 90, 38, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "คอหมูย่างฉ่ำๆ คลุกเครื่องน้ำตกอีสานแท้ สุดยอดเมนู"),
        ("ตับหวาน", "เมนูลาบ / น้ำตก", 80, 30, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "ตับหมูลวกสุกกำลังดีเนื้อหวานฉ่ำ คลุกข้าวคั่วรสแซ่บ"),
        ("ซกเล็ก", "เมนูลาบ / น้ำตก", 90, 38, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "เมนูอีสานแท้รสเด็ด เครื่องเทศสมุนไพรครบครัน"),
        ("ก้อยหมู", "เมนูลาบ / น้ำตก", 80, 32, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "ก้อยหมูรสแซ่บจัดจ้าน ถึงเครื่องสมุนไพรพื้นบ้าน"),
        ("ก้อยเนื้อ", "เมนูลาบ / น้ำตก", 90, 38, "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?auto=format&fit=crop&w=600&q=80", "ก้อยเนื้อวัวสดคลุกพริกป่นข้าวคั่ว เลือกขม/เปรี้ยวได้"),

        # --- 7. หมวด "เมนูอีสาน" ---
        ("ต้มแซ่บกระดูกอ่อน", "เมนูอีสาน", 100, 40, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "กระดูกหมูอ่อนเคี่ยวเปื่อยนุ่ม ซุปสมุนไพรเปรี้ยวเผ็ดร้อน"),
        ("ต้มแซ่บหมู", "เมนูอีสาน", 90, 36, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "เนื้อหมูนุ่ม ซุปต้มยำสมุนไพรไทย ซดคล่องคอ"),
        ("ต้มแซ่บเนื้อ", "เมนูอีสาน", 100, 42, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "เนื้อวัวตุ๋นยาจีนและสมุนไพร ซุปเปรี้ยวเผ็ดแซ่บสะใจ"),
        ("ต้มแซ่บเอ็นแก้ว", "เมนูอีสาน", 110, 45, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "เอ็นแก้วตุ๋นจนนุ่มเด้งดึ๋ง ซุปต้มแซ่บร้อนๆ"),
        ("ต้มแซ่บเครื่องใน", "เมนูอีสาน", 100, 40, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "เครื่องในวัว/หมูล้างสะอาด เปื่อยไม่คาว ซุปแซ่บ"),
        ("แกงอ่อมหมู", "เมนูอีสาน", 90, 36, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "แกงอ่อมผักชีลาวและผักอีสาน น้ำปลาร้าขลุกขลิก"),
        ("แกงอ่อมเนื้อ", "เมนูอีสาน", 100, 42, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "เนื้อวัวนุ่ม แกงอ่อมสมุนไพรกลิ่นหอมฟุ้ง"),
        ("แกงอ่อมไก่", "เมนูอีสาน", 90, 36, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "ไก่บ้านสับแกงอ่อมผักรวม รสเข้มข้นกลมกล่อม"),
        ("แกงเห็ด", "เมนูอีสาน", 80, 30, "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=600&q=80", "เห็ดหลากชนิดต้มน้ำใบย่านาง รสหวานธรรมชาติเพื่อสุขภาพ"),
        ("ซุปหน่อไม้", "เมนูอีสาน", 60, 22, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "หน่อไม้ขูดเส้นปรุงน้ำใบย่านาง คลุกข้าวคั่วหอมๆ"),
        ("ไส้กรอกอีสาน", "เมนูอีสาน", 70, 26, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "ไส้กรอกหมูเปรี้ยวกลมกล่อม เสิร์ฟพร้อมพริกขิงกะหล่ำ"),
        ("แจ่วฮ้อน", "เมนูอีสาน", 199, 80, "https://images.unsplash.com/photo-1541832676-9b763b0239ab?auto=format&fit=crop&w=600&q=80", "ชุดหม้อไฟแจ่วฮ้อนอีสาน ซุปสมุนไพรเข้มข้น ชุดหมูและผักครบ"),

        # --- 8. หมวด "ข้าว / เส้น" ---
        ("ข้าวเหนียว", "ข้าว / เส้น", 15, 5, "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?auto=format&fit=crop&w=600&q=80", "ข้าวเหนียวเขี้ยวงูนึ่งร้อนๆ นุ่มเม็ดเรียวยาว"),
        ("ข้าวสวย", "ข้าว / เส้น", 15, 5, "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?auto=format&fit=crop&w=600&q=80", "ข้าวหอมมะลิหุงนุ่ม หอมกรุ่น"),
        ("ขนมจีน", "ข้าว / เส้น", 15, 5, "https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=600&q=80", "เส้นขนมจีนสดแป้งหมัก นุ่มลื่น ทานคู่ส้มตำ"),
        ("ข้าวเหนียวหมูทอด", "ข้าว / เส้น", 60, 24, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "เซ็ตอิ่มคุ้ม ข้าวเหนียวนุ่มคู่หมูทอดสูตรเด็ด"),
        ("ข้าวเหนียวไก่ทอด", "ข้าว / เส้น", 60, 24, "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=600&q=80", "เซ็ตข้าวเหนียวกับไก่ทอดกรอบ หอมเจียวโรยหน้า"),
        ("ข้าวคอหมูย่าง", "ข้าว / เส้น", 70, 28, "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80", "ข้าวสวยร้อนๆ โปะคอหมูย่างฉ่ำๆ พร้อมน้ำจิ้มแจ่ว"),
        ("ข้าวน้ำตกหมู", "ข้าว / เส้น", 70, 28, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "ข้าวราดน้ำตกหมูรสแซ่บ จัดจ้านถึงใจ"),
        ("ข้าวลาบหมู", "ข้าว / เส้น", 70, 28, "https://images.unsplash.com/photo-1548943487-a2e4e43b4853?auto=format&fit=crop&w=600&q=80", "ข้าวสวยร้อนๆ ราดลาบหมูสับหอมข้าวคั่ว"),

        # --- 9. หมวด "เครื่องเคียง" ---
        ("ผักสด", "เครื่องเคียง", 15, 5, "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80", "ชุดผักสดรวม สะอาด กรอบ ดับเผ็ดได้ดี"),
        ("กะหล่ำปลี", "เครื่องเคียง", 15, 5, "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80", "กะหล่ำปลีสดแช่เย็นกรอบ หวานฉ่ำ"),
        ("ถั่วฝักยาว", "เครื่องเคียง", 15, 5, "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80", "ถั่วฝักยาวสดคัดพิเศษ กรุบกรอบ"),
        ("แตงกวา", "เครื่องเคียง", 15, 5, "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80", "แตงกวาสดหั่นชิ้น แช่เย็นชื่นใจ"),
        ("แคบหมู", "เครื่องเคียง", 20, 7, "https://images.unsplash.com/photo-1541529086526-db283c563270?auto=format&fit=crop&w=600&q=80", "แคบหมูไร้มันกรอบโบราณ ทานคู่ส้มตำ"),
        ("ข้าวเกรียบ", "เครื่องเคียง", 20, 7, "https://images.unsplash.com/photo-1541529086526-db283c563270?auto=format&fit=crop&w=600&q=80", "ข้าวเกรียบกุ้งทอดกรอบ แผ่นใหญ่เคี้ยวเพลิน"),
        ("ไข่ต้ม", "เครื่องเคียง", 10, 4, "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "ไข่ไก่ต้มสุกกำลังดี 1 ฟอง"),

        # --- 10. หมวด "เครื่องดื่ม" ---
        ("น้ำเปล่า", "เครื่องดื่ม", 15, 6, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=600&q=80", "น้ำดื่มบริสุทธิ์ขวดเย็นชื่นใจ"),
        ("น้ำแข็ง", "เครื่องดื่ม", 10, 3, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=600&q=80", "น้ำแข็งหลอดสะอาดใส่กระติก/แก้ว"),
        ("น้ำอัดลม", "เครื่องดื่ม", 25, 12, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=600&q=80", "โคล่า/น้ำอัดลมกระป๋องเย็นซ่าสดชื่น"),
        ("น้ำแดง", "เครื่องดื่ม", 25, 10, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=600&q=80", "น้ำหวานกลิ่นสละ หอมหวานเย็นชื่นใจ"),
        ("น้ำเขียว", "เครื่องดื่ม", 25, 10, "https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=600&q=80", "น้ำหวานกลิ่นครีมโซดา สดชื่นดับกระหาย"),
        ("ชามะนาว", "เครื่องดื่ม", 35, 12, "https://images.unsplash.com/photo-1558857563-b371033873b8?auto=format&fit=crop&w=600&q=80", "ชาดำแท้ผสมน้ำมะนาวคั้นสด เปรี้ยวหวานลงตัว"),
        ("ชาเย็น", "เครื่องดื่ม", 35, 12, "https://images.unsplash.com/photo-1558857563-b371033873b8?auto=format&fit=crop&w=600&q=80", "ชาไทยแท้สูตรโบราณ หอมมันนมสดแท้ ดับเผ็ด"),
        ("น้ำเก๊กฮวย", "เครื่องดื่ม", 30, 10, "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80", "เก๊กฮวยต้มสมุนไพรแท้ หวานน้อยหอมสดชื่น"),
        ("น้ำกระเจี๊ยบ", "เครื่องดื่ม", 30, 10, "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80", "กระเจี๊ยบแดงต้มสด เปรี้ยวอมหวานชุ่มคอ"),
        ("น้ำลำไย", "เครื่องดื่ม", 35, 12, "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80", "น้ำลำไยเนื้อแน่น หวานหอมกลมกล่อม")
    ]
    
    # อัปเดตรายการอาหารให้ตรงกับชุดเมนูล่าสุด
    c.execute('DELETE FROM menu_items')
    c.executemany('INSERT OR REPLACE INTO menu_items (name, category, price, cost, image, description) VALUES (?, ?, ?, ?, ?, ?)', fahsai_menu)

    conn.commit()
    conn.close()


# เรียกใช้งานเพื่อเตรียมฐานข้อมูลพร้อมใช้งานทันทีที่เริ่มโปรแกรม
init_db()

# ==============================================================================
# 🔀 ตรวจสอบโหมดการแสดงผล (Admin หรือ ลูกค้า) ผ่าน URL Parameter
# ==============================================================================
# ตัวอย่าง:
# - หน้าจัดการหลังร้าน: https://domain/?mode=admin
# - หน้าร้าน/ลูกค้าสั่งอาหาร: https://domain/?table=1
params = st.query_params
is_admin_mode = (params.get("mode", "") == "admin")

# ที่อยู่ไฟล์รูปภาพโลโก้ของร้านฟ้าใสตำนัว
logo_path = "static/img/logo.png"


# ==============================================================================
# 🛠️ ฟังก์ชันช่วยเหลือ (Utility / Helper Functions)
# ==============================================================================

def get_base64_image(image_path):
    """
    แปลงไฟล์รูปภาพ (เช่น PNG/JPG) เป็นข้อความ Base64
    ประโยชน์: ช่วยให้แทรกภาพลงในแท็ก HTML <img> ได้โดยตรง 
    ทำให้หน้าเว็บโหลดภาพขึ้นมาทันที ไม่ติดปัญหา Path หรือ CORS
    """
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

@st.cache_data
def get_bell_sound_b64():
    """
    สังเคราะห์คลื่นเสียงกระดิ่งเตือน (Chime) ความถี่คู่ 784Hz และ 1046.5Hz ขึ้นมาใน RAM
    แล้วบันทึกเป็น WAV ในหน่วยความจำโดยตรง
    ประโยชน์:
    - ไม่ต้องโหลดไฟล์เสียง MP3/WAV จากภายนอก
    - ใช้ @st.cache_data เพื่อสร้างคลื่นเสียงเพียงครั้งเดียว แล้วเก็บแคชไว้ใช้งานซ้ำ
    """
    sample_rate = 22050
    duration = 0.85
    n_samples = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(n_samples):
            t = i / sample_rate
            decay = math.exp(-4.2 * t)
            v1 = math.sin(2 * math.pi * 784.0 * t)
            v2 = math.sin(2 * math.pi * 1046.5 * t) if t > 0.08 else 0
            sample = int(32767 * 0.45 * (v1 * 0.55 + v2 * 0.45) * decay)
            wav_file.writeframes(struct.pack('<h', sample))
    return base64.b64encode(buf.getvalue()).decode()

def play_order_sound():
    """
    สั่งเล่นเสียงกระดิ่งเตือนในเบราว์เซอร์อัตโนมัติ (Autoplay)
    เมื่อมีออเดอร์ใหม่ที่ลูกค้าเพิ่งสั่งเข้ามาในห้องครัว
    """
    sound_b64 = get_bell_sound_b64()
    audio_html = f'''
    <audio autoplay style="display:none;">
        <source src="data:audio/wav;base64,{sound_b64}" type="audio/wav">
    </audio>
    <script>
    try {{
        const snd = new Audio("data:audio/wav;base64,{sound_b64}");
        snd.play().catch(e => {{ console.log("Audio waiting for gesture:", e); }});
    }} catch(e) {{}}
    </script>
    '''
    st.markdown(audio_html, unsafe_allow_html=True)


# ==============================================================================
# 📌 ฟังก์ชันแสดง Footer เครดิตผู้พัฒนาระบบ
# ==============================================================================
def render_app_footer():
    """แสดง Footer เครดิตผู้พัฒนาระบบด้านล่างสุดของหน้าจอ จัดกึ่งกลาง"""
    st.write("---")
    footer_html = """
    <div style="text-align: center; margin-top: 25px; margin-bottom: 25px; padding: 15px 10px; color: #4b5563; line-height: 1.8;">
        <div style="font-weight: 700; color: #c2410c; font-size: 1.05rem;">ระบบสั่งอาหารโต๊ะผ่าน QR Code</div>
        <div style="color: #374151; font-weight: 500;">พัฒนา โดย นางสาวชญาดา สิงหวัฒน์</div>
        <div style="color: #6b7280; font-size: 0.95rem;">อีเมล์ : chayada.sing@kkumail.com &nbsp;&nbsp;&nbsp;&nbsp; โทรศัพท์ : 093-773-4851</div>
    </div>
    """
    st.markdown(footer_html, unsafe_allow_html=True)


# ==============================================================================
# 🧾 ฟังก์ชันสร้างใบเสร็จรับเงินอย่างย่อ (HTML / Print / PDF)
# ==============================================================================
def get_payment_qr_base64():
    """ดึงรูปภาพ QR ธนาคาร/พร้อมเพย์ (payment.jpg) จากโฟลเดอร์ static มาแปลงเป็น Base64 สำหรับแสดงในใบเสร็จ HTML"""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "static", "img", "payment.jpg"),
        os.path.join(os.path.dirname(__file__), "static", "payment.jpg"),
        os.path.join("static", "img", "payment.jpg"),
        os.path.join("static", "payment.jpg"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            try:
                with open(p, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass
    return ""


def generate_receipt_html(order_id, table_id, items, total_price, order_time, subtotal=None, discount=0, points_used=0, points_earned=0, member_phone=None, member_name=None, remaining_points=None):
    total_qty = sum(item[1] for item in items)
    if subtotal is None or subtotal <= 0:
        subtotal = total_price + discount
    vat_included = round(total_price * 7 / 107, 2)
    before_vat = round(total_price - vat_included, 2)
    
    # แปลงภาพ QR ธนาคาร (payment.jpg) เป็น Base64 เพื่อฝังลงในใบเสร็จ
    qr_b64 = get_payment_qr_base64()
    if qr_b64:
        qr_payment_html = f"""
        <div class="dashed"></div>
        <div class="text-center" style="margin: 8px 0;">
            <div style="font-size: 13px; font-weight: bold; color: #1e3a8a; margin-bottom: 2px;">
                📲 สแกน QR เพื่อชำระเงิน
            </div>
            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">
                (PromptPay / สแกนผ่านแอปธนาคาร)
            </div>
            <div style="display: flex; justify-content: center; align-items: center; margin: 4px 0;">
                <img src="data:image/jpeg;base64,{qr_b64}" 
                     style="width: 175px; max-width: 90%; height: auto; border: 1.5px solid #cbd5e1; border-radius: 8px; padding: 4px; background: #fff; box-shadow: 0 2px 6px rgba(0,0,0,0.06);" 
                     alt="QR ธนาคารชำระเงิน" />
            </div>
            <div style="font-size: 12px; color: #1e293b; margin-top: 5px;">
                ยอดที่ต้องชำระ: <strong style="color: #c2410c; font-size: 14px;">฿{int(total_price):,}</strong>
            </div>
        </div>
        """
    else:
        qr_payment_html = ""
    
    items_rows_html = ""
    for idx, item in enumerate(items, 1):
        iname = item[0]
        iqty = item[1]
        iprice = item[2]
        line_total = int(iqty * iprice)
        items_rows_html += f"""
        <tr>
            <td style="padding: 4px 0; text-align: left; font-size: 13px;">{idx}. {iname}</td>
            <td style="padding: 4px 0; text-align: center; font-size: 13px;">{iqty}</td>
            <td style="padding: 4px 0; text-align: right; font-size: 13px;">{int(iprice)}</td>
            <td style="padding: 4px 0; text-align: right; font-size: 13px; font-weight: bold;">{line_total:,}</td>
        </tr>
        """
        
    # ข้อมูลสมาชิกสะสมแต้มในใบเสร็จ
    member_info_html = ""
    if member_phone:
        pts_used_txt = f"<div>• ใช้คะแนนแลกส่วนลด: <strong>{points_used}</strong> แต้ม (-฿{int(discount):,})</div>" if points_used > 0 else ""
        rem_pts_txt = f"<div>• คะแนนสะสมคงเหลือ: <strong style='color: #ea580c;'>{remaining_points}</strong> แต้ม</div>" if remaining_points is not None else ""
        member_info_html = f"""
        <div class="dashed"></div>
        <div style="font-size: 11.5px; background: #fff7ed; padding: 6px 8px; border-radius: 5px; border: 1px dashed #fdba74; margin-top: 4px;">
            <div style="font-weight: bold; color: #c2410c;">💎 ข้อมูลสมาชิกสะสมแต้ม</div>
            <div>ลูกค้า: <strong>{member_name or 'สมาชิก'}</strong> ({member_phone})</div>
            {pts_used_txt}
            <div>• ได้รับคะแนนบิลนี้: <strong style="color: #16a34a;">+{points_earned}</strong> แต้ม (ทุก 100บ. = 1 แต้ม)</div>
            {rem_pts_txt}
        </div>
        """

    # แถวส่วนลดในตาราง
    discount_row_html = ""
    if discount > 0:
        discount_row_html = f"""
        <tr style="color: #16a34a; font-weight: bold;">
            <td>ส่วนลดจากคะแนน ({points_used} แต้ม):</td>
            <td class="text-right">-฿{int(discount):,}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="th">
    <head>
    <meta charset="UTF-8">
    <title>ใบเสร็จรับเงินอย่างย่อ #{order_id}</title>
    <style>
        @page {{
            size: 80mm auto;
            margin: 3mm;
        }}
        @media print {{
            body {{
                margin: 0 !important;
                padding: 4px !important;
                width: 76mm !important;
                box-shadow: none !important;
                border: none !important;
            }}
            .no-print {{
                display: none !important;
            }}
            img {{
                max-width: 48mm !important;
            }}
        }}
        body {{
            font-family: 'Sarabun', 'Segoe UI', Tahoma, monospace, sans-serif;
            color: #111;
            background: #fff;
            width: 290px;
            margin: 4px auto;
            padding: 14px 10px;
            font-size: 13px;
            line-height: 1.38;
            border: 1px dashed #bbb;
            border-radius: 6px;
            box-sizing: border-box;
        }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .bold {{ font-weight: bold; }}
        .dashed {{
            border-top: 1px dashed #777;
            margin: 8px 0;
        }}
        .double-line {{
            border-top: 2px solid #222;
            margin: 8px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            border-bottom: 1px dashed #777;
            padding: 4px 0;
            font-size: 12px;
        }}
        .btn-print {{
            background: #ea580c;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
            transition: background 0.2s;
        }}
        .btn-print:hover {{
            background: #c2410c;
        }}
    </style>
    </head>
    <body>
        <div class="no-print" style="margin-bottom: 12px;">
            <button class="btn-print" onclick="window.print()">🖨️ สั่งพิมพ์ใบเสร็จ / บันทึกเป็น PDF</button>
        </div>
        
        <div class="text-center">
            <div style="font-size: 18px; font-weight: bold; color: #c2410c;">🌶️ ฟ้าใสตำนัว</div>
            <div style="font-size: 11px; color: #444;">(FAHSAI TUM NUA)</div>
            <div style="font-size: 12px; margin-top: 3px; font-weight: bold;">ใบเสร็จรับเงิน / ใบกำกับภาษีอย่างย่อ</div>
            <div style="font-size: 11px; color: #666;">โทร. 093-773-4851 • ยินดีให้บริการ</div>
        </div>
        
        <div class="dashed"></div>
        
        <div style="display: flex; justify-content: space-between; font-size: 12px;">
            <span><strong>โต๊ะที่:</strong> โต๊ะที่ {table_id}</span>
            <span><strong>บิลเลขที่:</strong> #{order_id}</span>
        </div>
        <div style="font-size: 12px; color: #444;">
            <strong>วันที่-เวลา:</strong> {order_time}
        </div>
        
        <div class="dashed"></div>
        
        <table>
            <thead>
                <tr>
                    <th style="text-align: left;">รายการอาหาร</th>
                    <th style="text-align: center; width: 32px;">จน.</th>
                    <th style="text-align: right; width: 45px;">ราคา</th>
                    <th style="text-align: right; width: 50px;">รวม</th>
                </tr>
            </thead>
            <tbody>
                {items_rows_html}
            </tbody>
        </table>
        
        <div class="dashed"></div>
        
        <table style="font-size: 12.5px;">
            <tr>
                <td>จำนวนรวม:</td>
                <td class="text-right bold">{total_qty} จาน</td>
            </tr>
            <tr>
                <td>ยอดรวมสินค้า:</td>
                <td class="text-right bold">฿{int(subtotal):,}</td>
            </tr>
            {discount_row_html}
            <tr>
                <td>มูลค่าก่อนภาษี:</td>
                <td class="text-right">฿{before_vat:,.2f}</td>
            </tr>
            <tr>
                <td>ภาษีมูลค่าเพิ่ม (VAT 7% รวมแล้ว):</td>
                <td class="text-right">฿{vat_included:,.2f}</td>
            </tr>
            <tr style="font-size: 15px; font-weight: bold; color: #c2410c;">
                <td style="padding-top: 5px;">ยอดจ่ายจริง (TOTAL):</td>
                <td class="text-right" style="padding-top: 5px;">฿{int(total_price):,}</td>
            </tr>
        </table>
        
        {member_info_html}
        
        {qr_payment_html}
        
        <div class="double-line"></div>
        
        <div class="text-center" style="font-size: 11px; color: #444;">
            <div>ชำระโดย: เงินสด / โอนเงินผ่าน QR ธนาคาร</div>
            <div style="margin-top: 4px; font-weight: bold; color: #111;">ขอบพระคุณที่มาอุดหนุนค่ะ 🙏</div>
            <div>โอกาสหน้าเชิญใหม่นะคะ แซ่บนัวทุกจาน!</div>
        </div>
    </body>
    </html>
    """
    return html

def render_receipt_box(oid, conn):
    c = conn.cursor()
    c.execute("""
        SELECT table_id, total_price, created_at, status,
               COALESCE(subtotal, total_price), COALESCE(discount, 0),
               COALESCE(points_used, 0), COALESCE(points_earned, 0),
               member_phone
        FROM orders WHERE id = ?
    """, (oid,))
    row = c.fetchone()
    if not row:
        st.session_state['active_receipt_oid'] = None
        return
    t_id, total, otime, st_code, subtotal, discount, pts_used, pts_earned, m_phone = row
    c.execute("SELECT item_name, quantity, price FROM order_items WHERE order_id = ?", (oid,))
    items = c.fetchall()
    
    m_name = None
    rem_pts = None
    if m_phone:
        c.execute("SELECT first_name, last_name, points FROM members WHERE phone = ?", (m_phone,))
        m_row = c.fetchone()
        if m_row:
            m_name = f"{m_row[0]} {m_row[1]}"
            rem_pts = m_row[2]

    receipt_html = generate_receipt_html(
        oid, t_id, items, total, otime,
        subtotal=subtotal, discount=discount,
        points_used=pts_used, points_earned=pts_earned,
        member_phone=m_phone, member_name=m_name,
        remaining_points=rem_pts
    )
    
    with st.container(border=True):
        st.markdown(f"### 🧾 ใบเสร็จรับเงินอย่างย่อ — โต๊ะที่ {t_id} (บิล #{oid})")
        st.caption("สามารถกดปุ่ม **🖨️ สั่งพิมพ์ใบเสร็จ / บันทึกเป็น PDF** ด้านล่างนี้ หรือดาวน์โหลดไฟล์ได้ทันทีค่ะ")
        
        components.html(receipt_html, height=750, scrolling=True)
        
        # ส่วนแสดง/ผูกข้อมูลสมาชิกที่เคาน์เตอร์คิดเงิน
        if st_code != 'paid':
            if m_phone:
                st.info(f"💎 สมาชิก: **{m_name}** ({m_phone}) | ใช้แลกส่วนลด: **{pts_used}** แต้ม (-฿{int(discount):,}) | ได้รับแต้มบิลนี้: **+{pts_earned}** แต้ม")
            else:
                with st.expander("💎 เพิ่มสมาชิกสะสมแต้มสำหรับบิลนี้ (ที่เคาน์เตอร์)", expanded=False):
                    c_ph_in, c_ph_btn = st.columns([3, 1.2])
                    with c_ph_in:
                        attach_phone = st.text_input("เบอร์โทรศัพท์ลูกค้า:", key=f"attach_ph_input_{oid}", placeholder="เช่น 0937734851")
                    with c_ph_btn:
                        st.write("")
                        attach_btn = st.button("🔗 บันทึกเบอร์", key=f"btn_attach_ph_{oid}", use_container_width=True)
                    if attach_btn and attach_phone.strip():
                        cl_ph = attach_phone.strip().replace("-", "").replace(" ", "")
                        c.execute("SELECT id, first_name, last_name, points FROM members WHERE phone = ?", (cl_ph,))
                        m_f = c.fetchone()
                        if m_f:
                            pts_to_earn = int(total // 100)
                            c.execute("UPDATE orders SET member_phone = ?, points_earned = ? WHERE id = ?", (cl_ph, pts_to_earn, oid))
                            conn.commit()
                            st.success(f"ผูกสมาชิก คุณ {m_f[1]} {m_f[2]} (แต้มปัจจุบัน: {m_f[3]}) สำเร็จ!")
                            st.rerun()
                        else:
                            st.warning("ไม่พบเบอร์นี้ในระบบสมาชิกค่ะ สามารถสมัครสมาชิกใหม่ได้ที่แท็บ '👥 ประวัติลูกค้า' นะคะ")

        rc1, rc2, rc3 = st.columns([1.5, 1.5, 1])
        with rc1:
            st.download_button(
                label="💾 ดาวน์โหลดไฟล์ใบเสร็จ (.html)",
                data=receipt_html,
                file_name=f"receipt_table{t_id}_order{oid}.html",
                mime="text/html",
                use_container_width=True,
                key=f"dl_receipt_file_{oid}"
            )
        with rc2:
            if st_code != 'paid':
                if st.button("💵 ยืนยันรับเงิน (ปิดบิล)", key=f"pay_confirm_btn_{oid}", type="primary", use_container_width=True):
                    c.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (oid,))
                    # อัปเดตคะแนนสะสมของสมาชิก
                    if m_phone:
                        net_pts_change = pts_earned - pts_used
                        c.execute("UPDATE members SET points = MAX(0, points + ?) WHERE phone = ?", (net_pts_change, m_phone))
                    conn.commit()
                    st.session_state['active_receipt_oid'] = None
                    st.toast(f"ปิดบิลโต๊ะ {t_id} เรียบร้อยแล้วค่ะ!", icon="✅")
                    st.rerun()
            else:
                st.info("✅ บิลนี้ชำระเงินเรียบร้อยแล้ว")
        with rc3:
            if st.button("❌ ปิดหน้าต่างใบเสร็จ", key=f"close_receipt_btn_{oid}", use_container_width=True):
                st.session_state['active_receipt_oid'] = None
                st.rerun()

# ==============================================================================
# 🍳 จอครัว & เคาน์เตอร์คิดเงิน (Fragment ทำงานอัตโนมัติทุก 3 วินาที)
# ==============================================================================
@st.fragment(run_every=3)
def render_pos_dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # ตรวจจับออเดอร์ใหม่สถานะ pending ที่เพิ่งเข้ามา
    c.execute("SELECT MAX(id) FROM orders WHERE status = 'pending'")
    row_max = c.fetchone()
    cur_max = row_max[0] if (row_max and row_max[0]) else 0
    
    if 'last_seen_pending_id' not in st.session_state:
        st.session_state['last_seen_pending_id'] = cur_max
    elif cur_max > st.session_state['last_seen_pending_id']:
        st.session_state['last_seen_pending_id'] = cur_max
        play_order_sound()
        st.toast(f"🔔 มีออเดอร์ใหม่ #{cur_max} เข้ามาในครัวแล้วค่ะ!", icon="🛎️")
        st.warning(f"🔔 **มีออเดอร์ใหม่ #{cur_max} เพิ่งส่งเข้ามาในครัว!** กำลังรอให้เตรียมอาหาร")

    # แถบแสดงสถานะอัปเดตสดแบบเรียลไทม์
    top_c1, top_c2 = st.columns([3, 1])
    with top_c1:
        st.markdown(f"**⚡ สถานะระบบ:** :green[**● เชื่อมต่อสด • อัปเดตออเดอร์อัตโนมัติทุก 3 วินาที**] <span style='color: #64748b; font-size: 0.85rem;'>(เวลาปัจจุบัน: {get_thai_now().strftime('%H:%M:%S')})</span>", unsafe_allow_html=True)
    with top_c2:
        if st.button("🔔 ทดสอบเสียงกระดิ่ง", key="btn_test_sound", use_container_width=True):
            play_order_sound()
            st.toast("ทดสอบเสียงกระดิ่งเตือนออเดอร์แล้ว 🔔", icon="🛎️")

    c.execute("SELECT COALESCE(SUM(total_price), 0), COUNT(*) FROM orders WHERE status IN ('paid', 'archived')")
    revenue, paid_cnt = c.fetchone()
    c.execute("SELECT COUNT(*), COUNT(DISTINCT table_id) FROM orders WHERE status NOT IN ('paid', 'archived')")
    active_cnt, active_tables = c.fetchone()
    
    # Responsive Metrics
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("💰 ยอดขายรวม", f"฿{int(revenue):,}")
    s2.metric("🍳 กำลังปรุง/เสิร์ฟ", f"{active_cnt} บิล")
    s3.metric("🪑 นั่งทาน", f"{active_tables} โต๊ะ")
    s4.metric("✅ เช็คบิลแล้ว", f"{paid_cnt} บิล")
    
    st.write("---")
    
    # หากมีการกดเช็คบิล/ดูใบเสร็จ ให้แสดงกล่องใบเสร็จอย่างย่อด้านบนสุด
    active_rec_id = st.session_state.get('active_receipt_oid')
    if active_rec_id:
        render_receipt_box(active_rec_id, conn)
        st.write("---")

    c.execute('''
        SELECT id, table_id, status, total_price, created_at 
        FROM orders 
        WHERE status NOT IN ('paid', 'archived')
        ORDER BY 
            CASE status 
                WHEN 'pending' THEN 1 
                WHEN 'accepted' THEN 2 
                WHEN 'cooked' THEN 3 
                WHEN 'served' THEN 4 
            END, id ASC
    ''')
    orders_to_manage = c.fetchall()
    
    if not orders_to_manage:
        st.success("🎉 ไม่มีออเดอร์ค้างในครัว น้องฟ้าใสพร้อมรับออเดอร์ใหม่เสมอค่ะ 🌶️")
    else:
        grid_cols = st.columns(3)
        for idx, (oid, t_id, st_code, total, otime) in enumerate(orders_to_manage):
            with grid_cols[idx % 3]:
                with st.container(border=True):
                    h1, h2 = st.columns([2, 1])
                    h1.markdown(f"### โต๊ะที่ {t_id}")
                    h2.caption(f"#{oid}")
                    st.caption(f"เวลาสั่ง: {otime}")
                    
                    c.execute("""
                        SELECT oi.id, oi.item_name, oi.quantity, oi.note, oi.price, COALESCE(oi.status, 'pending'), mi.image
                        FROM order_items oi
                        LEFT JOIN menu_items mi ON oi.item_name = mi.name
                        WHERE oi.order_id = ?
                    """, (oid,))
                    items_in_order = c.fetchall()
                    
                    total_items = len(items_in_order)
                    served_items = sum(1 for it in items_in_order if it[5] == 'served')
                    cooked_items = sum(1 for it in items_in_order if it[5] == 'cooked')
                    all_items_served = (total_items > 0) and (served_items == total_items)
                    
                    st.markdown("**📋 รายการอาหารในบิล:**")
                    for oi_id, iname, iqty, inote, iprice, istatus, dish_img in items_in_order:
                        with st.container(border=True):
                            it_c1, it_c2 = st.columns([1.1, 2.3])
                            with it_c1:
                                if dish_img:
                                    st.image(dish_img, use_container_width=True)
                                else:
                                    st.markdown("<div style='font-size: 2.2rem; text-align: center; line-height: 60px;'>🍲</div>", unsafe_allow_html=True)
                            with it_c2:
                                st.markdown(f"**{iname}** <span style='color: #ea580c; font-weight: bold;'>x{iqty}</span>", unsafe_allow_html=True)
                                st.caption(f"฿{int(iprice * iqty):,}")
                                if inote:
                                    st.caption(f"⚠️ {inote}")
                                
                                if istatus == 'pending':
                                    st.markdown("<span style='background: #fff7ed; color: #c2410c; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #fdba74;'>⏳ กำลังปรุง</span>", unsafe_allow_html=True)
                                elif istatus == 'cooked':
                                    st.markdown("<span style='background: #f3e8ff; color: #7e22ce; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #d8b4fe;'>🍳 เสร็จแล้ว</span>", unsafe_allow_html=True)
                                elif istatus == 'served':
                                    st.markdown("<span style='background: #f0fdf4; color: #15803d; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; border: 1px solid #86efac;'>✅ เสิร์ฟแล้ว</span>", unsafe_allow_html=True)
                            
                            # ปุ่มเปลี่ยนสถานะแต่ละเมนู: เสร็จแล้ว / นำเสิร์ฟแล้ว
                            act_c1, act_c2 = st.columns(2)
                            if istatus == 'pending':
                                with act_c1:
                                    if st.button("🍳 เสร็จ", key=f"btn_ck_{oi_id}", use_container_width=True, help="เปลี่ยนสถานะเป็นปรุงเสร็จแล้ว"):
                                        c.execute("UPDATE order_items SET status = 'cooked' WHERE id = ?", (oi_id,))
                                        c.execute("UPDATE orders SET status = 'cooked' WHERE id = ? AND status IN ('pending', 'accepted')", (oid,))
                                        conn.commit()
                                        st.rerun()
                                with act_c2:
                                    if st.button("🍽️ เสิร์ฟ", key=f"btn_sv_{oi_id}", type="primary", use_container_width=True, help="เปลี่ยนสถานะเป็นนำเสิร์ฟแล้ว"):
                                        c.execute("UPDATE order_items SET status = 'served' WHERE id = ?", (oi_id,))
                                        c.execute("SELECT COUNT(*) FROM order_items WHERE order_id = ? AND status != 'served'", (oid,))
                                        if c.fetchone()[0] == 0:
                                            c.execute("UPDATE orders SET status = 'served' WHERE id = ?", (oid,))
                                        else:
                                            c.execute("UPDATE orders SET status = 'cooked' WHERE id = ?", (oid,))
                                        conn.commit()
                                        st.rerun()
                            elif istatus == 'cooked':
                                with act_c1:
                                    st.caption("รอพนักงานยกเสิร์ฟ")
                                with act_c2:
                                    if st.button("🍽️ เสิร์ฟ", key=f"btn_sv_{oi_id}", type="primary", use_container_width=True, help="เปลี่ยนสถานะเป็นนำเสิร์ฟแล้ว"):
                                        c.execute("UPDATE order_items SET status = 'served' WHERE id = ?", (oi_id,))
                                        c.execute("SELECT COUNT(*) FROM order_items WHERE order_id = ? AND status != 'served'", (oid,))
                                        if c.fetchone()[0] == 0:
                                            c.execute("UPDATE orders SET status = 'served' WHERE id = ?", (oid,))
                                        conn.commit()
                                        st.rerun()
                            elif istatus == 'served':
                                with act_c1:
                                    st.write("")
                                with act_c2:
                                    if st.button("↩️ ยกเลิก", key=f"btn_un_{oi_id}", use_container_width=True, help="ย้อนกลับเป็นกำลังปรุง"):
                                        c.execute("UPDATE order_items SET status = 'pending' WHERE id = ?", (oi_id,))
                                        c.execute("UPDATE orders SET status = 'cooked' WHERE id = ?", (oid,))
                                        conn.commit()
                                        st.rerun()
                    
                    # ปุ่มทางลัด: เสิร์ฟทุกเมนูพร้อมกัน
                    if not all_items_served:
                        if st.button("⚡ เสิร์ฟทุกเมนูทันที", key=f"btn_all_srv_{oid}", use_container_width=True):
                            c.execute("UPDATE order_items SET status = 'served' WHERE order_id = ?", (oid,))
                            c.execute("UPDATE orders SET status = 'served' WHERE id = ?", (oid,))
                            conn.commit()
                            st.toast(f"เสิร์ฟอาหารโต๊ะ {t_id} ครบทุกเมนูแล้วค่ะ!", icon="🍽️")
                            st.rerun()

                    st.write("---")
                    st.markdown(f"**ยอดรวม: <span style='color: #ea580c; font-size: 1.15rem; font-weight: bold;'>฿{int(total):,}</span>**", unsafe_allow_html=True)
                    
                    # Requirement: เช็คบิลได้เฉพาะเมื่อเสิร์ฟครบทุกเมนูแล้วเท่านั้น
                    if not all_items_served:
                        st.warning(f"⚠️ เสิร์ฟแล้ว {served_items}/{total_items} เมนู (ปุ่มเช็คบิลจะเปิดเมื่อเสิร์ฟครบ)")
                        st.button(f"🧾 เช็คบิลโต๊ะ {t_id} (รอเสิร์ฟครบ)", key=f"btn_bill_{oid}", disabled=True, use_container_width=True)
                    else:
                        st.success(f"🍽️ เสิร์ฟครบ {served_items}/{total_items} เมนูแล้ว พร้อมเช็คบิลค่ะ!")
                        if st.button(f"🧾 เช็คบิล & ออกใบเสร็จอย่างย่อ (โต๊ะ {t_id})", key=f"btn_bill_{oid}", type="primary", use_container_width=True):
                            st.session_state['active_receipt_oid'] = oid
                            st.rerun()

                    # ปุ่มเคลียร์โต๊ะรับลูกค้าใหม่
                    st.write("")
                    if st.button(f"🧹 เคลียร์โต๊ะ {t_id}", key=f"adm_clr_{oid}", use_container_width=True, help="ล้างสถานะเพื่อรับลูกค้าใหม่"):
                        c.execute("UPDATE orders SET status = 'archived' WHERE table_id = ?", (t_id,))
                        conn.commit()
                        st.toast(f"เคลียร์โต๊ะ {t_id} เรียบร้อยแล้ว โต๊ะพร้อมรับลูกค้าใหม่!", icon="✨")
                        st.rerun()

    # Expander: ประวัติบิลที่ชำระแล้ววันนี้
    st.write("---")
    with st.expander("📜 ประวัติบิลที่ชำระแล้ววันนี้ (ดู/พิมพ์ใบเสร็จย้อนหลัง)", expanded=False):
        c.execute("""
            SELECT id, table_id, total_price, created_at, status 
            FROM orders 
            WHERE status IN ('paid', 'archived')
            ORDER BY id DESC LIMIT 15
        """)
        past_orders = c.fetchall()
        if not past_orders:
            st.info("ยังไม่มีบิลที่ชำระแล้วในวันนี้ค่ะ")
        else:
            for p_id, p_tid, p_tot, p_time, p_st in past_orders:
                st_p_col1, st_p_col2, st_p_col3 = st.columns([2, 1.5, 1.5])
                st_p_col1.markdown(f"**บิล #{p_id}** — โต๊ะที่ {p_tid} (เวลา: {p_time})")
                st_p_col2.markdown(f"**฿{int(p_tot):,}**")
                with st_p_col3:
                    if st.button("🧾 พิมพ์ใบเสร็จ", key=f"btn_reprint_{p_id}", use_container_width=True):
                        st.session_state['active_receipt_oid'] = p_id
                        st.rerun()
                        
    conn.close()

# ==============================================================================
# 🔴 ฝั่งร้านค้า (เคาน์เตอร์ & ครัว & เมนูขายดี) -> https://.../?mode=admin
# ==============================================================================
# หน้านี้สำหรับพนักงานและเจ้าของร้าน โดยเข้าใช้งานผ่านการเติม ?mode=admin ท้าย URL
# ประกอบด้วย 3 แท็บหลัก:
# 1. จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (พร้อมสร้าง QR Code)
# 2. จอครัว & เคาน์เตอร์คิดเงิน (KDS)
# 3. อันดับเมนูขายดี
if is_admin_mode:
    # Header ปรับขนาดภาพโลโก้ให้ใหญ่ขึ้น สวยงาม คมชัด จัดกลางอย่างลงตัว
    logo_b64 = get_base64_image(logo_path)
    if logo_b64:
        logo_html = f'''<div style="text-align: center; margin-bottom: 8px;">
            <img src="data:image/png;base64,{logo_b64}" 
                 style="width: 145px; height: 145px; object-fit: cover; border-radius: 50%; box-shadow: 0 6px 20px rgba(234, 88, 12, 0.32); border: 4px solid #ffedd5; display: inline-block;" 
                 alt="โลโก้ฟ้าใสตำนัว" />
        </div>'''
    elif os.path.exists(logo_path):
        logo_html = f'<div style="text-align: center; margin-bottom: 8px;"><img src="{logo_path}" style="width: 145px; height: 145px; object-fit: cover; border-radius: 50%; border: 4px solid #ffedd5; box-shadow: 0 6px 20px rgba(234, 88, 12, 0.32); display: inline-block;" alt="โลโก้ฟ้าใสตำนัว" /></div>'
    else:
        logo_html = '<div style="text-align: center; font-size: 75px; margin-bottom: 4px;">🌶️</div>'

    header_html = f'''
    {logo_html}
    <h1 style="text-align: center; color: #c2410c; font-weight: 800; font-size: 2.3rem; margin: 4px 0 2px 0; line-height: 1.2;">
        ฟ้าใสตำนัว (ระบบจัดการหลังร้าน)
    </h1>
    <p style="text-align: center; color: #78716c; font-size: 1.05rem; margin: 0 0 14px 0;">
        👨‍🍳 หน้าจอเคาน์เตอร์คิดเงิน • ครัวปรุงอาหาร • อันดับเมนูขายดี
    </p>
    '''
    st.markdown(header_html, unsafe_allow_html=True)

    st.write("---")

    # แยก 4 แท็บสำหรับจัดการหลังร้าน
    tab_tbl, tab_pos, tab_rep, tab_mem = st.tabs([
        "🪑 จัดการโต๊ะอาหาร & เคลียร์โต๊ะ", 
        "🍳 จอครัว & เคาน์เตอร์คิดเงิน", 
        "🏆 เมนูขายดี",
        "👥 ประวัติลูกค้า"
    ])


    # --------------------------------------------------------------------------
    # แท็บที่ 1: 🪑 จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (พร้อมสร้าง QR-Code)
    # --------------------------------------------------------------------------
    with tab_tbl:
        st.subheader("🪑 จัดการโต๊ะอาหาร & เคลียร์โต๊ะ (พร้อมสร้าง QR-Code)")
        st.caption("เพิ่มหรือลบโต๊ะอาหารในร้าน สร้าง QR-Code ติดโต๊ะให้ลูกค้าสแกนสั่งอาหาร และกดล้างสถานะโต๊ะเพื่อรับลูกค้ารายใหม่")
        
        conn_tb = sqlite3.connect(DB_NAME)
        c_tb = conn_tb.cursor()
        
        # ดึงรายชื่อโต๊ะทั้งหมด พร้อมนับจำนวนออเดอร์ค้าง (active_orders) และบิลที่จ่ายเงินแล้วรอเคลียร์ (paid_orders)
        # ใช้ LEFT JOIN เพื่อให้โต๊ะที่ยังไม่มีออเดอร์ยังคงแสดงผลขึ้นมาได้
        c_tb.execute("""
            SELECT t.table_number, t.name,
                   COUNT(CASE WHEN o.status NOT IN ('paid', 'archived') THEN 1 END) as active_orders,
                   COUNT(CASE WHEN o.status = 'paid' THEN 1 END) as paid_orders
            FROM tables t
            LEFT JOIN orders o ON t.table_number = o.table_id
            GROUP BY t.table_number
            ORDER BY t.table_number ASC
        """)
        table_statuses = c_tb.fetchall()

        existing_nums = [r[0] for r in table_statuses]
        
        # ลิงก์ร้านสำหรับสร้าง QR-Code อัตโนมัติ
        base_url_for_qr = "https://fahsai-tumnua-xwwixnezbpyxzpwvkvhad3.streamlit.app"

        # ส่วนที่ 1: เมนู เพิ่ม / ลบ โต๊ะอาหารในร้าน
        st.markdown("### ⚙️ 1. เพิ่ม / ลบ โต๊ะอาหารในร้าน")
        t_c1, t_c2 = st.columns(2)
        
        with t_c1:
            with st.container(border=True):
                st.markdown("#### ➕ เพิ่มโต๊ะใหม่")
                st.caption("เมื่อเพิ่มแล้ว ระบบจะสร้าง QR-Code และลิงก์สั่งอาหารของโต๊ะนั้นให้ทันที")
                next_t_num = (max(existing_nums) + 1) if existing_nums else 1
                new_t_num = st.number_input("หมายเลขโต๊ะที่จะเพิ่ม:", min_value=1, max_value=999, value=next_t_num, step=1, key="add_t_num_input")
                new_t_name = st.text_input("ชื่อเรียกโต๊ะ:", value=f"โต๊ะที่ {new_t_num}", key="add_t_name_input")
                
                if st.button("➕ ยืนยันเพิ่มโต๊ะและสร้าง QR-Code", key="btn_add_new_table", type="primary", use_container_width=True):
                    if new_t_num in existing_nums:
                        st.error(f"หมายเลขโต๊ะ {new_t_num} มีอยู่ในระบบแล้วค่ะ")
                    else:
                        c_tb.execute("INSERT INTO tables (table_number, name) VALUES (?, ?)", (new_t_num, new_t_name))
                        conn_tb.commit()
                        st.success(f"เพิ่ม '{new_t_name}' สำเร็จ พร้อมเปิดใช้งาน QR-Code เรียบร้อยแล้วค่ะ! 🎉")
                        st.rerun()

        with t_c2:
            with st.container(border=True):
                st.markdown("#### 🗑️ ลบโต๊ะอาหาร")
                st.caption("ลบโต๊ะที่ไม่ใช้งานออกจากระบบ")
                if existing_nums:
                    table_options = [f"โต๊ะที่ {r[0]} ({r[1]})" for r in table_statuses]
                    table_to_del_str = st.selectbox("เลือกโต๊ะที่ต้องการลบ:", table_options, key="select_del_t")
                    del_t_num = int(table_to_del_str.split(" ")[1])
                    
                    if st.button(f"🗑️ ยืนยันลบโต๊ะที่ {del_t_num}", key="btn_del_table", use_container_width=True):
                        c_tb.execute("DELETE FROM tables WHERE table_number = ?", (del_t_num,))
                        conn_tb.commit()
                        st.warning(f"ลบโต๊ะที่ {del_t_num} ออกจากระบบเรียบร้อยแล้ว")
                        st.rerun()
                else:
                    st.info("ปัจจุบันยังไม่มีโต๊ะอาหารในระบบ")
        
        st.write("---")

        # ส่วนที่ 2: รายการโต๊ะอาหาร & QR-Code สั่งอาหาร & เคลียร์สถานะโต๊ะ
        st.markdown("### 📱 2. รายการโต๊ะอาหาร & QR-Code สั่งอาหาร & ล้างสถานะโต๊ะ")
        
        if not table_statuses:
            st.info("ℹ️ **ขณะนี้ยังไม่มีโต๊ะอาหารในร้าน** (ค่าเริ่มต้น 0 โต๊ะ)\n\n👉 สามารถเพิ่มโต๊ะใหม่ได้ที่แบบฟอร์ม **'➕ เพิ่มโต๊ะใหม่'** ด้านบนค่ะ เมื่อเพิ่มแล้ว QR-Code สำหรับติดโต๊ะและระบบสั่งอาหารจะแสดงที่นี่ทันที ✨")
        else:
            total_tbls = len(table_statuses)
            busy_tbls = sum(1 for r in table_statuses if (r[2] > 0 or r[3] > 0))
            free_tbls = total_tbls - busy_tbls
            
            # สรุปภาพรวมของโต๊ะ
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("🪑 โต๊ะอาหารทั้งหมด", f"{total_tbls} โต๊ะ")
            col_m2.metric("🟢 โต๊ะว่างพร้อมรับลูกค้า", f"{free_tbls} โต๊ะ")
            col_m3.metric("🟠 มีลูกค้า / รอเคลียร์", f"{busy_tbls} โต๊ะ")

            # ปุ่มล้างทุกโต๊ะที่เช็คบิลแล้วพร้อมกัน
            total_paid_orders = sum(r[3] for r in table_statuses)
            if total_paid_orders > 0:
                if st.button("🧹 ล้างสถานะทุกโต๊ะที่เช็คบิลแล้วพร้อมกันทั้งหมด", type="primary", use_container_width=True):
                    c_tb.execute("UPDATE orders SET status = 'archived' WHERE status = 'paid'")
                    conn_tb.commit()
                    st.toast("ล้างสถานะทุกโต๊ะที่เช็คบิลแล้วเรียบร้อย!", icon="✨")
                    st.rerun()
                st.write("")

            st.caption("💡 แนะนำ: พิมพ์หรือเปิดภาพ **QR-Code** ด้านล่างนี้ไปติดไว้ที่โต๊ะอาหาร ลูกค้าสแกนเพื่อเปิดเมนูสั่งอาหารได้ทันที")
            
            clr_cols = st.columns(3)
            for idx, (t_no, t_name, act_cnt, paid_cnt) in enumerate(table_statuses):
                with clr_cols[idx % 3]:
                    with st.container(border=True):
                        # หัวการ์ดโต๊ะ
                        st.markdown(f"#### 🪑 {t_name}")
                        st.caption(f"หมายเลขโต๊ะ: #{t_no}")
                        
                        # สถานะโต๊ะ
                        if act_cnt > 0:
                            st.markdown(f"สถานะ: :orange[**มีออเดอร์ค้าง {act_cnt} บิล (กำลังทำ/รอเสิร์ฟ)**]")
                        elif paid_cnt > 0:
                            st.markdown(f"สถานะ: :blue[**เช็คบิลแล้ว {paid_cnt} บิล (รอเคลียร์โต๊ะ)**]")
                        else:
                            st.markdown(f"สถานะ: :green[**โต๊ะว่าง (พร้อมรับลูกค้า)**]")

                        # ลิงก์สำหรับลูกค้าโต๊ะนี้
                        cust_table_url = f"{base_url_for_qr}/?table={t_no}"
                        qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={quote(cust_table_url)}&margin=10"
                        
                        # แสดงภาพ QR Code
                        st.image(qr_image_url, caption=f"QR-Code สั่งอาหาร {t_name}", use_container_width=True)
                        
                        # ลิงก์ตรงเปิดหน้าสั่งอาหาร
                        st.markdown(f"""
                        <div style="text-align: center; margin-bottom: 8px;">
                            <a href="{cust_table_url}" target="_blank" style="display: inline-block; background: #fff7ed; color: #ea580c; border: 1.5px solid #fdba74; padding: 4px 12px; border-radius: 6px; font-weight: 600; text-decoration: none; font-size: 0.85rem;">
                                🔗 เปิดหน้าสั่งอาหารโต๊ะนี้ (ทดสอบ)
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # ปุ่มล้างสถานะโต๊ะเพื่อรับลูกค้าใหม่
                        btn_type = "primary" if (paid_cnt > 0 or act_cnt > 0) else "secondary"
                        if st.button(f"🧹 ล้างสถานะโต๊ะ {t_no} (รับลูกค้าใหม่)", key=f"btn_clr_tbl_{t_no}", use_container_width=True, type=btn_type):
                            c_tb.execute("UPDATE orders SET status = 'archived' WHERE table_id = ?", (t_no,))
                            conn_tb.commit()
                            st.toast(f"ล้างสถานะ '{t_name}' เรียบร้อยแล้ว โต๊ะพร้อมรับลูกค้าใหม่!", icon="✨")
                            st.rerun()

                        # ปุ่มลบโต๊ะ
                        with st.popover(f"🗑️ ลบ {t_name}"):
                            st.markdown(f"ยืนยันการลบ **{t_name}** ออกจากระบบ?")
                            if st.button(f"ยืนยันลบโต๊ะ {t_no}", key=f"btn_pop_del_{t_no}", type="primary", use_container_width=True):
                                c_tb.execute("DELETE FROM tables WHERE table_number = ?", (t_no,))
                                conn_tb.commit()
                                st.warning(f"ลบ {t_name} เรียบร้อยแล้วค่ะ")
                                st.rerun()

        conn_tb.close()

    # --------------------------------------------------------------------------
    # แท็บที่ 2: 🍳 จอครัว & เคาน์เตอร์คิดเงิน (Kitchen POS Dashboard)
    # --------------------------------------------------------------------------
    with tab_pos:
        # เรียกใช้ฟังก์ชัน fragment ที่รีเฟรชออเดอร์อัตโนมัติทุก 3 วินาที
        render_pos_dashboard()

    # --------------------------------------------------------------------------
    # แท็บที่ 3: 🏆 อันดับเมนูขายดี (Best Selling Menus Dashboard)
    # --------------------------------------------------------------------------
    with tab_rep:
        st.subheader("🏆 อันดับเมนูขายดี (Best Selling Menus)")
        st.caption("จัดอันดับเมนูยอดนิยมของฟ้าใสตำนัว ตามจำนวนจานและยอดขายรวม")
        
        conn_bs = sqlite3.connect(DB_NAME)
        c_bs = conn_bs.cursor()

        
        # ตัวกรองช่วงเวลาและการเรียงลำดับ
        c_f1, c_f2 = st.columns([1.5, 2])
        with c_f1:
            filter_period = st.pills("📅 ช่วงเวลา:", ["ทั้งหมด", "วันนี้"], default="ทั้งหมด", key="pills_period_filter")
        with c_f2:
            sort_by = st.pills("📊 จัดอันดับตาม:", ["จำนวนจานที่ขายได้ (จาน)", "ยอดขายรวม (บาท)"], default="จำนวนจานที่ขายได้ (จาน)", key="pills_sort_filter")

        thai_today_str = get_thai_now().strftime('%Y-%m-%d')
        date_sql = f"AND DATE(o.created_at) = '{thai_today_str}'" if filter_period == "วันนี้" else ""
        order_sql = "total_qty DESC, total_sales DESC" if "จำนวนจาน" in sort_by else "total_sales DESC, total_qty DESC"
        
        c_bs.execute(f'''
            SELECT 
                oi.item_name,
                COALESCE(mi.category, 'ทั่วไป') as category,
                COALESCE(mi.image, '') as image,
                COALESCE(mi.price, oi.price) as unit_price,
                SUM(oi.quantity) as total_qty,
                SUM(oi.quantity * oi.price) as total_sales
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            LEFT JOIN menu_items mi ON oi.item_name = mi.name
            WHERE o.status != 'cancelled' {date_sql}
            GROUP BY oi.item_name
            ORDER BY {order_sql}
        ''')
        best_sellers = c_bs.fetchall()
        
        if not best_sellers:
            st.info("ยังไม่มีข้อมูลการขายในช่วงเวลานี้ค่ะ")
        else:
            total_sold_all = sum(r[4] for r in best_sellers)
            total_revenue_all = sum(r[5] for r in best_sellers)
            top_seller = best_sellers[0]
            
            # สถิติภาพรวมด้านบน
            m1, m2, m3 = st.columns(3)
            m1.metric("🍲 จำนวนอาหารที่ขายได้รวม", f"{total_sold_all:,} จาน")
            m2.metric("💰 ยอดขายรวม", f"฿{int(total_revenue_all):,}")
            m3.metric("👑 เมนูขายดีอันดับ 1", f"{top_seller[0]}", f"{top_seller[4]} จาน (฿{int(top_seller[5]):,})")
            
            st.write("---")
            
            # 3 อันดับแรก (Podium Top 3)
            st.markdown("### 🥇🥈🥉 3 อันดับเมนูยอดนิยมสูงสุด")
            podium_cols = st.columns(min(3, len(best_sellers)))
            medals = ["🥇 อันดับ 1 (แชมป์)", "🥈 อันดับ 2", "🥉 อันดับ 3"]
            badge_bg = ["#fef3c7", "#f1f5f9", "#ffedd5"]
            badge_border = ["#f59e0b", "#94a3b8", "#f97316"]
            
            for p_idx in range(min(3, len(best_sellers))):
                p_name, p_cat, p_img, p_price, p_qty, p_sales = best_sellers[p_idx]
                with podium_cols[p_idx]:
                    with st.container(border=True):
                        st.markdown(f"<div style='background: {badge_bg[p_idx]}; border: 1.5px solid {badge_border[p_idx]}; border-radius: 6px; padding: 4px 8px; text-align: center; font-weight: bold; font-size: 1rem; margin-bottom: 8px;'>{medals[p_idx]}</div>", unsafe_allow_html=True)
                        if p_img:
                            st.image(p_img, use_container_width=True)
                        st.markdown(f"**{p_name}**")
                        st.caption(f"หมวดหมู่: {p_cat}")
                        st.markdown(f"🔥 ขายได้: <span style='color: #ea580c; font-size: 1.25rem; font-weight: bold;'>{p_qty} จาน</span>", unsafe_allow_html=True)
                        st.markdown(f"💵 รวมเงิน: **฿{int(p_sales):,}**")

            st.write("---")
            
            # ตารางจัดอันดับทั้งหมด
            st.markdown("### 📋 ตารางจัดอันดับเมนูขายดีทั้งหมด")
            max_qty = best_sellers[0][4] if best_sellers and best_sellers[0][4] > 0 else 1
            
            for rank, (iname, icat, iimg, iprice, iqty, isales) in enumerate(best_sellers, 1):
                with st.container(border=True):
                    rc1, rc2, rc3, rc4 = st.columns([0.8, 1.2, 3, 2])
                    with rc1:
                        if rank == 1:
                            r_badge = "🥇 #1"
                        elif rank == 2:
                            r_badge = "🥈 #2"
                        elif rank == 3:
                            r_badge = "🥉 #3"
                        else:
                            r_badge = f"#{rank}"
                        st.markdown(f"<div style='font-size: 1.3rem; font-weight: 800; line-height: 60px; text-align: center; color: #ea580c;'>{r_badge}</div>", unsafe_allow_html=True)
                    with rc2:
                        if iimg:
                            st.image(iimg, use_container_width=True)
                        else:
                            st.markdown("<div style='font-size: 2.2rem; text-align: center; line-height: 60px;'>🍲</div>", unsafe_allow_html=True)
                    with rc3:
                        st.markdown(f"**{iname}**")
                        st.caption(f"หมวด: {icat} • ราคา ฿{int(iprice)}/จาน")
                        pct_of_top = min(1.0, float(iqty) / float(max_qty))
                        st.progress(pct_of_top)
                    with rc4:
                        st.markdown(f"<div style='text-align: right;'><span style='font-size: 1.25rem; font-weight: bold; color: #ea580c;'>{iqty} จาน</span><br><span style='font-size: 0.95rem; color: #555;'>฿{int(isales):,}</span></div>", unsafe_allow_html=True)

            # สรุปยอดขายแยกตามหมวดหมู่อาหาร
            st.write("---")
            st.markdown("### 📊 สรุปยอดขายแยกตามหมวดหมู่อาหาร")
            c_bs.execute(f'''
                SELECT 
                    COALESCE(mi.category, 'ทั่วไป') as category,
                    SUM(oi.quantity) as cat_qty,
                    SUM(oi.quantity * oi.price) as cat_sales
                FROM order_items oi
                JOIN orders o ON oi.order_id = o.id
                LEFT JOIN menu_items mi ON oi.item_name = mi.name
                WHERE o.status != 'cancelled' {date_sql}
                GROUP BY mi.category
                ORDER BY cat_qty DESC
            ''')
            cat_summary = c_bs.fetchall()
            if cat_summary:
                cat_cols = st.columns(min(len(cat_summary), 4))
                for c_idx, (cname, cqty, csales) in enumerate(cat_summary):
                    with cat_cols[c_idx % len(cat_cols)]:
                        with st.container(border=True):
                            st.markdown(f"**{cname}**")
                            st.markdown(f"🔥 ขายได้: **{cqty} จาน**")
                            st.caption(f"ยอดรวม: ฿{int(csales):,}")
        conn_bs.close()

    # --------------------------------------------------------------------------
    # แท็บที่ 4: 👥 ประวัติลูกค้า (Customer History & Loyalty Members)
    # --------------------------------------------------------------------------
    with tab_mem:
        st.subheader("👥 ประวัติลูกค้า & ระบบสมาชิกสะสมแต้ม")
        st.caption("ดูข้อมูลสมาชิก จัดการคะแนนสะสม เรียงลำดับจากคะแนนมากไปน้อย และสมัครสมาชิกใหม่หน้าร้าน")
        
        conn_mem = sqlite3.connect(DB_NAME)
        c_mem = conn_mem.cursor()

        # ฟอร์มสมัครสมาชิกลูกค้าใหม่ (ที่เคาน์เตอร์)
        with st.expander("➕ สมัครสมาชิกลูกค้าใหม่ (ที่เคาน์เตอร์)", expanded=False):
            st.markdown("##### กรอกข้อมูลสมาชิกลูกค้า")
            st.caption("ข้อมูลที่ใช้: ชื่อ, นามสกุล และหมายเลขโทรศัพท์")
            mf_c1, mf_c2, mf_c3 = st.columns(3)
            with mf_c1:
                adm_fname = st.text_input("ชื่อ:", key="adm_reg_fname", placeholder="ชื่อจริง")
            with mf_c2:
                adm_lname = st.text_input("นามสกุล:", key="adm_reg_lname", placeholder="นามสกุล")
            with mf_c3:
                adm_phone = st.text_input("หมายเลขโทรศัพท์:", key="adm_reg_phone", placeholder="เช่น 0937734851")
                
            if st.button("➕ บันทึกข้อมูลสมาชิก", key="btn_adm_save_member", type="primary", use_container_width=True):
                cl_adm_ph = adm_phone.strip().replace("-", "").replace(" ", "")
                if not adm_fname.strip() or not adm_lname.strip() or not cl_adm_ph:
                    st.error("กรุณากรอกข้อมูล ชื่อ นามสกุล และหมายเลขโทรศัพท์ให้ครบถ้วนค่ะ")
                else:
                    c_mem.execute("SELECT id FROM members WHERE phone = ?", (cl_adm_ph,))
                    if c_mem.fetchone():
                        st.error(f"หมายเลขโทรศัพท์ {cl_adm_ph} มีอยู่ในระบบสมาชิกแล้วค่ะ")
                    else:
                        reg_now = get_thai_now().strftime('%Y-%m-%d %H:%M:%S')
                        c_mem.execute(
                            "INSERT INTO members (first_name, last_name, phone, points, created_at) VALUES (?, ?, ?, 0, ?)",
                            (adm_fname.strip(), adm_lname.strip(), cl_adm_ph, reg_now)
                        )
                        conn_mem.commit()
                        st.success(f"บันทึกสมาชิก 'คุณ {adm_fname} {adm_lname}' เรียบร้อยแล้วค่ะ! 🎉")
                        st.rerun()

        st.write("---")

        # ช่องค้นหาลูกค้า
        search_kw = st.text_input("🔍 ค้นหาลูกค้า (ชื่อ, นามสกุล หรือ เบอร์โทรศัพท์):", placeholder="พิมพ์คำค้นหา...", key="mem_search_input")
        kw_pattern = f"%{search_kw.strip()}%"

        # ดึงรายชื่อลูกค้า เรียงตามคะแนนสะสมจากมากไปน้อย (ORDER BY points DESC)
        c_mem.execute("""
            SELECT 
                m.id, 
                m.first_name, 
                m.last_name, 
                m.phone, 
                m.points, 
                m.created_at,
                COUNT(DISTINCT CASE WHEN o.status = 'paid' THEN o.id END) as paid_orders,
                COALESCE(SUM(CASE WHEN o.status = 'paid' THEN o.total_price ELSE 0 END), 0) as total_spent
            FROM members m
            LEFT JOIN orders o ON m.phone = o.member_phone
            WHERE (m.first_name LIKE ? OR m.last_name LIKE ? OR m.phone LIKE ?)
            GROUP BY m.id
            ORDER BY m.points DESC, total_spent DESC, m.id ASC
        """, (kw_pattern, kw_pattern, kw_pattern))
        members_list = c_mem.fetchall()

        # สถิติภาพรวมสมาชิก
        c_mem.execute("SELECT COUNT(*), COALESCE(SUM(points), 0) FROM members")
        tot_m_cnt, tot_pts_sum = c_mem.fetchone()

        sm1, sm2, sm3 = st.columns(3)
        sm1.metric("👥 สมาชิกทั้งหมด", f"{tot_m_cnt} คน")
        sm2.metric("⭐ คะแนนสะสมรวมทั้งระบบ", f"{tot_pts_sum:,} แต้ม")
        top_member_txt = f"{members_list[0][1]} {members_list[0][2]} ({members_list[0][4]} แต้ม)" if members_list else "-"
        sm3.metric("🥇 แชมป์แต้มสูงสุด", top_member_txt)

        st.markdown(f"### 📋 รายชื่อสมาชิกลูกค้า (เรียงตามคะแนนสะสมมากที่สุด)")
        st.caption("กฎคะแนน: ทุก ๆ 100 บาท (ยอดสุทธิ) ได้รับ 1 คะแนน | 10 คะแนน แลกส่วนลด 25 บาท")

        if not members_list:
            if search_kw:
                st.warning(f"ไม่พบข้อมูลสมาชิกที่ตรงกับคำค้นหา '{search_kw}'")
            else:
                st.info("ขณะนี้ยังไม่มีข้อมูลสมาชิกลูกค้าในระบบ สามารถกด **'➕ สมัครสมาชิกลูกค้าใหม่'** ด้านบนได้เลยค่ะ")
        else:
            for idx, (mid, fname, lname, phone, pts, reg_date, order_cnt, spent) in enumerate(members_list, 1):
                # ตราอันดับคะแนน
                if idx == 1:
                    badge = "🥇 อันดับ 1"
                elif idx == 2:
                    badge = "🥈 อันดับ 2"
                elif idx == 3:
                    badge = "🥉 อันดับ 3"
                else:
                    badge = f"#{idx}"

                with st.container(border=True):
                    mc1, mc2, mc3, mc4 = st.columns([1.2, 3.5, 2.5, 2.5])
                    with mc1:
                        st.markdown(f"<div style='font-size: 1.15rem; font-weight: 700; color: #ea580c; text-align: center; line-height: 40px;'>{badge}</div>", unsafe_allow_html=True)
                    with mc2:
                        st.markdown(f"**คุณ{fname} {lname}**")
                        st.caption(f"📞 เบอร์โทร: **{phone}** • สมัครเมื่อ: {reg_date[:10] if reg_date else '-'}")
                    with mc3:
                        st.markdown(f"⭐ คะแนนสะสม: <span style='font-size: 1.25rem; font-weight: 800; color: #ea580c;'>{pts:,}</span> แต้ม", unsafe_allow_html=True)
                        discount_avail = (pts // 10) * 25
                        st.caption(f"แลกส่วนลดได้สูงสุด: **฿{discount_avail:,}**")
                    with mc4:
                        st.markdown(f"🍽️ มาทาน: **{order_cnt} ครั้ง**")
                        st.caption(f"ยอดซื้อสะสม: **฿{int(spent):,}**")

        conn_mem.close()

    # Footer ล่างสุดสำหรับหน้าระบบจัดการหลังร้าน (?mode=admin)
    render_app_footer()

# ==============================================================================
# 🟢 ฝั่งลูกค้าสั่งอาหารที่โต๊ะ (Customer Menu & Ordering View)
# ==============================================================================
# ทำงานเมื่อลูกค้าสแกน QR Code เข้ามา เช่น https://domain/?table=1
# หน้าที่หลัก:
# 1. ตรวจสอบหมายเลขโต๊ะจาก URL Query Parameter (?table=N)
# 2. แสดงรายการอาหารแยกตามหมวดหมู่ พร้อมรูปภาพและราคา
# 3. จัดการตะกร้าสินค้าแบบเรียลไทม์ (บันทึกใน st.session_state)
# 4. บันทึกคำสั่งซื้อเข้าห้องครัว (บันทึกลงตาราง orders และ order_items)
# 5. ติดตามสถานะอาหารแบบเรียลไทม์ (Auto-refresh ทุก 3 วินาที)
else:
    table_from_param = params.get("table", None)
    conn_chk = sqlite3.connect(DB_NAME)
    c_chk = conn_chk.cursor()
    c_chk.execute("SELECT table_number, name FROM tables ORDER BY table_number ASC")
    valid_tables_data = c_chk.fetchall()
    conn_chk.close()
    
    valid_tables = [row[0] for row in valid_tables_data]
    table_names_map = {row[0]: row[1] for row in valid_tables_data}

    # Header โลโก้ลูกค้า: จัดกลางเสมอ สวยงาม ชัดเจน รองรับทุกขนาดหน้าจอ
    logo_b64 = get_base64_image(logo_path)
    if logo_b64:
        logo_html = f'''<div style="text-align: center; margin-bottom: 6px;">
            <img src="data:image/png;base64,{logo_b64}" 
                 style="width: 105px; height: 105px; object-fit: cover; border-radius: 50%; box-shadow: 0 4px 16px rgba(234, 88, 12, 0.28); display: inline-block; border: 3px solid #ffedd5;" 
                 alt="โลโก้ฟ้าใสตำนัว" />
        </div>'''
    else:
        logo_html = '<div style="text-align: center; font-size: 55px; margin-bottom: 4px;">🌶️</div>'

    # กรณีทางร้านยังไม่ได้เปิดโต๊ะใดๆ (0 โต๊ะเริ่มต้น)
    if not valid_tables:
        header_html = f'''
        {logo_html}
        <h1 style="text-align: center; color: #c2410c; font-weight: 800; font-size: 2.25rem; margin: 2px 0 0 0; letter-spacing: -0.5px; line-height: 1.2;">
            ฟ้าใสตำนัว
        </h1>
        <p style="text-align: center; color: #78716c; font-size: 0.95rem; margin: 0 0 10px 0;">
            ส้มตำ ยำ ลาบ ย่าง แซ่บนัว สดใหม่ทุกครก 🌶️
        </p>
        '''
        st.markdown(header_html, unsafe_allow_html=True)
        st.write("---")
        st.warning("⚠️ ขณะนี้ทางร้านยังไม่ได้เปิดโต๊ะอาหารในระบบ")
        st.info("กรุณาติดต่อพนักงานที่เคาน์เตอร์ หรือเปิดโต๊ะในระบบหลังร้านก่อนนะคะ 🌶️")
        st.markdown("<div style='text-align: center; margin-top: 15px;'><a href='?mode=admin' style='color: #ea580c; text-decoration: none; font-weight: bold;'>⚙️ ไปที่ระบบจัดการหลังร้าน</a></div>", unsafe_allow_html=True)
        st.stop()
        valid_tables = [1]

    # กำหนดหมายเลขโต๊ะปัจจุบัน (หาก URL ไม่ได้ระบุ ให้เลือกโต๊ะแรกในระบบ)
    current_table_num = None
    if table_from_param is not None:
        try:
            p_val = int(table_from_param)
            if p_val in valid_tables:
                current_table_num = p_val
        except:
            pass
            
    if current_table_num is None:
        current_table_num = valid_tables[0]
        
    current_table_name = table_names_map.get(current_table_num, f"โต๊ะที่ {current_table_num}")

    header_html = f'''
    {logo_html}
    <h1 style="text-align: center; color: #c2410c; font-weight: 800; font-size: 2.25rem; margin: 2px 0 0 0; letter-spacing: -0.5px; line-height: 1.2;">
        ฟ้าใสตำนัว
    </h1>
    <p style="text-align: center; color: #78716c; font-size: 0.95rem; margin: 0 0 10px 0;">
        ส้มตำ ยำ ลาบ ย่าง แซ่บนัว สดใหม่ทุกครก 🌶️
    </p>
    <div style="text-align: center; margin: 6px 0 16px 0;">
        <div style="display: inline-block; background: linear-gradient(135deg, #ea580c, #c2410c); color: white; padding: 7px 30px; border-radius: 6px; font-size: 1.3rem; font-weight: 700; box-shadow: 0 4px 12px rgba(234, 88, 12, 0.35); letter-spacing: 0.5px;">
            🪑 {current_table_name}
        </div>
    </div>
    '''
    st.markdown(header_html, unsafe_allow_html=True)
    st.write("---")

    # ==========================================================================
    # 💎 ระบบสมาชิกสะสมแต้ม (ไม่บังคับ)
    # ==========================================================================
    mem_tbl_key = f"member_phone_table_{current_table_num}"
    cust_phone_val = st.session_state.get(mem_tbl_key, "")

    with st.container(border=True):
        st.markdown("#### 💎 สมาชิกสะสมแต้ม (ไม่บังคับ)")
        st.caption("กรอกเบอร์โทรศัพท์เพื่อสะสมแต้ม (ทุก 100 บาทสุทธิ = 1 คะแนน) และแลกส่วนลด (10 คะแนน = 25 บาท)")
        
        c_mph_in, c_mph_btn = st.columns([3, 1.2])
        with c_mph_in:
            in_phone = st.text_input(
                "หมายเลขโทรศัพท์:", 
                value=cust_phone_val, 
                placeholder="เช่น 0937734851 (ไม่บังคับ)", 
                key=f"input_cust_phone_{current_table_num}"
            )
        with c_mph_btn:
            st.write("")
            btn_chk_mem = st.button("🔍 ตรวจสอบ", key=f"btn_chk_mem_{current_table_num}", use_container_width=True)

        cl_phone = in_phone.strip().replace("-", "").replace(" ", "")
        
        current_member_data = None
        if cl_phone:
            conn_m = sqlite3.connect(DB_NAME)
            c_m = conn_m.cursor()
            c_m.execute("SELECT id, first_name, last_name, phone, points FROM members WHERE phone = ?", (cl_phone,))
            m_row = c_m.fetchone()
            if m_row:
                current_member_data = {
                    'id': m_row[0],
                    'first_name': m_row[1],
                    'last_name': m_row[2],
                    'phone': m_row[3],
                    'points': m_row[4]
                }
                st.session_state[mem_tbl_key] = cl_phone
                st.session_state[f'member_obj_{current_table_num}'] = current_member_data
                
                st.success(f"👤 ยินดีต้อนรับ **คุณ{m_row[1]} {m_row[2]}** | ⭐ แต้มสะสมปัจจุบัน: **{m_row[4]:,}** คะแนน")
                if m_row[4] >= 10:
                    max_d = (m_row[4] // 10) * 25
                    st.caption(f"🎁 คุณมีสิทธิ์ใช้คะแนนแลกส่วนลดได้สูงสุด **฿{max_d:,}** (ชุดละ 10 คะแนน = 25 บาท เลือกใช้ได้ในตะกร้าอาหารค่ะ)")
                else:
                    st.caption(f"💡 สะสมเพิ่มอีก **{10 - m_row[4]}** คะแนน เพื่อแลกรับส่วนลด 25 บาทค่ะ")
            else:
                st.info(f"ℹ️ ยังไม่พบเบอร์ `{cl_phone}` ในระบบสมาชิก สมัครสมาชิกฟรีเพื่อเริ่มสะสมแต้มได้เลยค่ะ ✨")
                with st.expander("📝 สมัครสมาชิกใหม่ทันที (ง่ายๆ แค่กรอกชื่อ-นามสกุล)", expanded=True):
                    reg_c1, reg_c2 = st.columns(2)
                    with reg_c1:
                        reg_fname = st.text_input("ชื่อ:", key=f"reg_fname_t_{current_table_num}", placeholder="ระบุชื่อจริง")
                    with reg_c2:
                        reg_lname = st.text_input("นามสกุล:", key=f"reg_lname_t_{current_table_num}", placeholder="ระบุนามสกุล")
                        
                    if st.button("✨ ยืนยันสมัครสมาชิก", key=f"btn_reg_mem_t_{current_table_num}", type="primary", use_container_width=True):
                        if not reg_fname.strip() or not reg_lname.strip():
                            st.error("กรุณากรอกชื่อและนามสกุลให้ครบถ้วนค่ะ")
                        else:
                            try:
                                reg_time = get_thai_now().strftime('%Y-%m-%d %H:%M:%S')
                                c_m.execute(
                                    "INSERT INTO members (first_name, last_name, phone, points, created_at) VALUES (?, ?, ?, 0, ?)",
                                    (reg_fname.strip(), reg_lname.strip(), cl_phone, reg_time)
                                )
                                conn_m.commit()
                                current_member_data = {
                                    'id': c_m.lastrowid,
                                    'first_name': reg_fname.strip(),
                                    'last_name': reg_lname.strip(),
                                    'phone': cl_phone,
                                    'points': 0
                                }
                                st.session_state[mem_tbl_key] = cl_phone
                                st.session_state[f'member_obj_{current_table_num}'] = current_member_data
                                st.success(f"🎉 สมัครสมาชิกสำเร็จ! ยินดีต้อนรับคุณ {reg_fname} {reg_lname} เริ่มสะสมแต้มได้ทันทีค่ะ")
                                st.rerun()
                            except Exception as e:
                                st.error(f"เกิดข้อผิดพลาด: {e}")
            conn_m.close()
        else:
            st.session_state[mem_tbl_key] = ""
            st.session_state[f'member_obj_{current_table_num}'] = None

    current_member = st.session_state.get(f'member_obj_{current_table_num}')

    # ==========================================================================
    # 🛒 ฟังก์ชันจัดการตะกร้าสินค้า (Cart Callbacks)
    # ==========================================================================
    # เก็บข้อมูลใน st.session_state.cart เพื่อไม่ให้หายเวลากดเพิ่ม/ลดรายการ
    # โครงสร้าง: { 'ชื่ออาหาร': {'price': ราคา, 'qty': จำนวน, 'note': โน้ตพิเศษ} }

    def add_to_cart_item(item_name, item_price):
        """เพิ่มจำนวนอาหารในตะกร้า (+1) หรือเพิ่มรายการใหม่ลงตะกร้า"""
        if 'cart' not in st.session_state:
            st.session_state.cart = {}
        if item_name in st.session_state.cart:
            st.session_state.cart[item_name]['qty'] += 1
        else:
            st.session_state.cart[item_name] = {'price': item_price, 'qty': 1, 'note': ''}

    def dec_from_cart_item(item_name):
        """ลดจำนวนอาหารในตะกร้า (-1) หากเหลือ 0 จะลบรายการออกอัตโนมัติ"""
        if 'cart' in st.session_state and item_name in st.session_state.cart:
            if st.session_state.cart[item_name]['qty'] > 1:
                st.session_state.cart[item_name]['qty'] -= 1
            else:
                del st.session_state.cart[item_name]

    def del_from_cart_item(item_name):
        """ลบรายการอาหารชิ้นนั้นออกจากตะกร้าทันที"""
        if 'cart' in st.session_state and item_name in st.session_state.cart:
            del st.session_state.cart[item_name]

    if 'cart' not in st.session_state:
        st.session_state.cart = {}


    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        SELECT id, name, category, price, image, description 
        FROM menu_items 
        ORDER BY 
            CASE category 
                WHEN 'ตำนัว' THEN 1 
                WHEN 'ตำแซ่บ' THEN 2 
                WHEN 'เมนูทอด' THEN 3 
                WHEN 'เมนูย่าง' THEN 4 
                WHEN 'เมนูลาบ / น้ำตก' THEN 5 
                WHEN 'เมนูอีสาน' THEN 6 
                WHEN 'ข้าว / เส้น' THEN 7 
                WHEN 'เพิ่มท็อปปิ้ง' THEN 8 
                WHEN 'เครื่องเคียง' THEN 9 
                WHEN 'เครื่องดื่ม' THEN 10 
                ELSE 11 
            END, id ASC
    ''')
    all_menus = c.fetchall()
    
    cat_order_list = [
        "ตำนัว", 
        "ตำแซ่บ", 
        "เมนูทอด", 
        "เมนูย่าง", 
        "เมนูลาบ / น้ำตก", 
        "เมนูอีสาน", 
        "ข้าว / เส้น", 
        "เพิ่มท็อปปิ้ง", 
        "เครื่องเคียง", 
        "เครื่องดื่ม"
    ]

    available_cats = list(set(m[2] for m in all_menus))
    categories = [cat for cat in cat_order_list if cat in available_cats]
    for cat in available_cats:
        if cat not in categories:
            categories.append(cat)
    
    st.markdown("<p style='text-align: center; font-weight: 600; color: #44403c; margin-bottom: 4px; font-size: 1.05rem;'>🍽️ เลือกหมวดหมู่อาหาร</p>", unsafe_allow_html=True)
    sel_cat = st.pills("เลือกหมวดหมู่อาหาร:", ["ทั้งหมด"] + categories, default="ทั้งหมด", key="pills_cat_sel", label_visibility="collapsed")
    if not sel_cat:
        sel_cat = "ทั้งหมด"
    
    # คำนวณยอดตะกร้า
    total_cart_qty = sum(item['qty'] for item in st.session_state.cart.values())
    total_cart_sum = sum(item['price'] * item['qty'] for item in st.session_state.cart.values())

    # แถบตะกร้าอาหาร เพื่อให้ลูกค้าสั่งและแก้ไขรายการได้สะดวก
    if total_cart_qty > 0:
        with st.container(border=True):
            st.markdown(f"<div style='text-align: center; font-size: 1.15rem; font-weight: 700; color: #1c1917; margin-bottom: 8px;'>🛒 ในตะกร้า: <span style='color: #ea580c;'>{total_cart_qty} รายการ</span> | รวม <span style='color: #ea580c;'>฿{int(total_cart_sum):,}</span></div>", unsafe_allow_html=True)
            with st.popover("👀 ดูตะกร้า & ยืนยันสั่งอาหาร", use_container_width=True):
                st.markdown(f"### 🛒 ตะกร้าอาหาร (โต๊ะ {current_table_num})")
                for item_name, data in list(st.session_state.cart.items()):
                    subtotal = data['price'] * data['qty']
                    with st.container():
                        st.markdown(f"**{item_name}** • <span style='color: #ea580c; font-weight: 600;'>฿{int(data['price'])} / จาน</span>", unsafe_allow_html=True)
                        
                        # แถวปุ่มปรับจำนวน: ➖ | ตัวเลขจำนวน | ➕ | 🗑️ ลบ
                        c_minus, c_num, c_plus, c_del = st.columns([1, 1.2, 1, 1.2])
                        with c_minus:
                            st.button("➖", key=f"cart_dec_{item_name}", on_click=dec_from_cart_item, args=(item_name,), use_container_width=True)
                        with c_num:
                            st.markdown(f"<div style='text-align: center; font-size: 1.25rem; font-weight: 700; line-height: 42px; background: #fff7ed; border-radius: 6px; border: 1.5px solid #fdba74; color: #c2410c;'>{data['qty']}</div>", unsafe_allow_html=True)
                        with c_plus:
                            st.button("➕", key=f"cart_inc_{item_name}", on_click=add_to_cart_item, args=(item_name, data['price']), use_container_width=True)
                        with c_del:
                            st.button("🗑️ ลบ", key=f"cart_rem_{item_name}", on_click=del_from_cart_item, args=(item_name,), use_container_width=True)
                                
                        st.caption(f"รวมย่อย: ฿{int(subtotal):,}")
                        note = st.text_input("โน้ตพิเศษ (เช่น เผ็ดน้อย/ไม่ใส่ชูรส):", value=data['note'], key=f"cart_note_{item_name}", placeholder="ระบุความต้องการ...")
                        st.session_state.cart[item_name]['note'] = note
                        st.write("---")
                
                discount_val = 0
                points_used_val = 0
                
                if current_member:
                    m_pts = current_member['points']
                    # กฎ:
                    # 1. ทุก ๆ 10 คะแนน สามารถแลกเป็นส่วนลด 25 บาท
                    # 2. ผู้ใช้ต้องแลกเป็นจำนวนชุดของ 10 คะแนนเท่านั้น (10, 20, 30...)
                    # 3. ส่วนลดที่ได้รับต้องไม่เกินยอดราคาที่ต้องชำระจริง
                    max_sets_by_pts = m_pts // 10
                    max_sets_by_bill = int(total_cart_sum // 25)
                    max_sets = min(max_sets_by_pts, max_sets_by_bill)
                    
                    if max_sets >= 1:
                        st.markdown("---")
                        st.markdown("##### 🎁 ใช้คะแนนสะสมแลกส่วนลด")
                        st.caption(f"แต้มสะสมที่คุณมี: **{m_pts:,}** คะแนน (แลกได้ชุดละ 10 คะแนน = 25 บาท)")
                        
                        redeem_options = [s * 10 for s in range(max_sets + 1)]
                        sel_pts_to_use = st.selectbox(
                            "เลือกจำนวนคะแนนที่ต้องการใช้แลกส่วนลด:",
                            options=redeem_options,
                            format_func=lambda x: "ไม่ใช้คะแนน" if x == 0 else f"ใช้ {x} คะแนน (ส่วนลด ฿{(x // 10) * 25:,})",
                            key=f"sel_redeem_pts_{current_table_num}"
                        )
                        points_used_val = sel_pts_to_use
                        discount_val = (sel_pts_to_use // 10) * 25
                    elif m_pts > 0:
                        st.caption(f"⭐ คุณมีคะแนนสะสม **{m_pts}** คะแนน (สะสมครบ 10 คะแนนเพื่อแลกส่วนลด 25 บาท)")
                
                net_cart_sum = max(0, total_cart_sum - discount_val)
                points_to_earn = int(net_cart_sum // 100)
                
                st.write("---")
                st.markdown(f"**ยอดรวมสินค้า:** ฿{int(total_cart_sum):,}")
                if discount_val > 0:
                    st.markdown(f"**ส่วนลดจากคะแนน ({points_used_val} แต้ม):** :green[-฿{int(discount_val):,}]")
                st.markdown(f"#### ยอดชำระสุทธิ: <span style='color: #ea580c;'>฿{int(net_cart_sum):,}</span>", unsafe_allow_html=True)
                
                if current_member:
                    st.caption(f"✨ เมื่อชำระบิลนี้ คุณจะได้รับแต้มสะสมเพิ่ม: **+{points_to_earn}** คะแนน (ทุก 100 บาท = 1 คะแนน)")
                
                if st.button("🚀 ยืนยันส่งออเดอร์เข้าครัว", type="primary", use_container_width=True):
                    order_time_th = get_thai_now().strftime('%Y-%m-%d %H:%M:%S')
                    m_phone_to_save = current_member['phone'] if current_member else None
                    c.execute("""
                        INSERT INTO orders (table_id, status, subtotal, discount, total_price, points_used, points_earned, member_phone, created_at) 
                        VALUES (?, 'pending', ?, ?, ?, ?, ?, ?, ?)
                    """, (current_table_num, total_cart_sum, discount_val, net_cart_sum, points_used_val, points_to_earn, m_phone_to_save, order_time_th))
                    new_order_id = c.lastrowid
                    for iname, idata in st.session_state.cart.items():
                        c.execute("INSERT INTO order_items (order_id, item_name, price, quantity, note, status) VALUES (?, ?, ?, ?, ?, 'pending')", (new_order_id, iname, idata['price'], idata['qty'], idata['note']))
                    conn.commit()
                    st.session_state.cart = {}
                    st.success(f"🎉 ส่งออเดอร์ #{new_order_id} เรียบร้อยแล้วค่ะ!")
                    st.rerun()

    # แสดงรายการเมนูอาหาร แถวการ์ดแนวนอน (กดได้ทุกรายการ พร้อม Stepper ➖/➕ บนการ์ดโดยตรง)
    filtered_menus = all_menus if sel_cat == "ทั้งหมด" else [m for m in all_menus if m[2] == sel_cat]
    
    for m_id, name, cat, price, img, desc in filtered_menus:
        with st.container(border=True):
            mc_img, mc_info, mc_btn = st.columns([1.2, 3.2, 1.6])
            with mc_img:
                st.image(img, use_container_width=True)
            with mc_info:
                st.markdown(f"**{name}**")
                st.caption(desc)
                st.markdown(f"<span style='color: #ea580c; font-weight: bold; font-size: 1.15rem;'>฿{int(price)}</span>", unsafe_allow_html=True)
            with mc_btn:
                cur_qty = st.session_state.cart.get(name, {}).get('qty', 0)
                if cur_qty == 0:
                    st.button("➕ เพิ่ม", key=f"btn_add_menu_{m_id}", on_click=add_to_cart_item, args=(name, price), use_container_width=True)
                else:
                    c_m, c_q, c_p = st.columns([1, 1, 1])
                    with c_m:
                        st.button("➖", key=f"btn_dec_card_{m_id}", on_click=dec_from_cart_item, args=(name,), use_container_width=True)
                    with c_q:
                        st.markdown(f"<div style='text-align: center; font-weight: 700; line-height: 42px; color: #ea580c; font-size: 1.15rem;'>{cur_qty}</div>", unsafe_allow_html=True)
                    with c_p:
                        st.button("➕", key=f"btn_inc_card_{m_id}", on_click=add_to_cart_item, args=(name, price), use_container_width=True, type="primary")

    # ==========================================================================
    # 📋 ระบบติดตามสถานะอาหารของโต๊ะนี้ (Live Order Tracking Fragment)
    # ==========================================================================
    # ใช้ @st.fragment(run_every=3) เพื่อให้อัปเดตสถานะแบบเรียลไทม์ทุก 3 วินาที
    # ลูกค้าจะเห็น Progress Bar ขยับตามขั้นตอน:
    # ⏳ รอร้านรับออเดอร์ (25%) -> 🍳 ครัวกำลังปรุง (45%) -> 🍲 กำลังทยอยเสิร์ฟ (75%) -> 🍽️ เสิร์ฟครบแล้ว (100%)
    st.write("---")
    
    @st.fragment(run_every=3)
    def render_table_order_tracking(table_num):
        """แสดงรายการอาหารที่โต๊ะนี้สั่ง พร้อมแถบความคืบหน้าแบบ Real-time"""
        conn_trk = sqlite3.connect(DB_NAME)
        c_trk = conn_trk.cursor()
        
        # ดึงออเดอร์ล่าสุดของโต๊ะนี้ที่ไม่ใช่ archived (ที่ยังทานอยู่ หรือเพิ่งเช็คบิล)
        c_trk.execute("""
            SELECT id, status, total_price, created_at 
            FROM orders 
            WHERE table_id = ? AND status != 'archived'
            ORDER BY id DESC LIMIT 5
        """, (table_num,))
        cur_orders = c_trk.fetchall()
        
        col_t_title, col_t_btn = st.columns([3, 1])
        with col_t_title:
            st.markdown(f"#### 📋 ติดตามสถานะอาหาร โต๊ะที่ {table_num} (เรียลไทม์ ⚡)")
            st.caption("ระบบจะอัปเดตสถานะอัตโนมัติทุก 3 วินาทีเมื่อครัวเปลี่ยนขั้นตอน")
        with col_t_btn:
            if st.button("🔄 รีเฟรช", key=f"btn_ref_table_{table_num}", use_container_width=True):
                st.rerun()


        if not cur_orders:
            st.info("ยังไม่มีรายการอาหารที่สั่งในขณะนี้ค่ะ สามารถเลือกเมนูแซ่บๆ ด้านบนแล้วส่งเข้าครัวได้เลยนะคะ 🌶️")
        else:
            st_map = {
                'pending': ('⏳ รอร้านรับออเดอร์', 'orange', 0.25, 'กำลังส่งออเดอร์เข้าจอครัว...'),
                'accepted': ('🍳 ครัวกำลังปรุงอาหาร', 'blue', 0.50, 'แม่ครัวกำลังตั้งกระทะ ปรุงสดใหม่ค่ะ'),
                'cooked': ('🍲 ปรุงเสร็จ กำลังทยอยเสิร์ฟ', 'purple', 0.75, 'อาหารปรุงเสร็จแล้ว พนักงานกำลังยกไปเสิร์ฟค่ะ'),
                'served': ('🍽️ เสิร์ฟถึงโต๊ะครบแล้ว', 'green', 1.0, 'เสิร์ฟครบทุกเมนูแล้ว ทานให้อร่อยแซ่บนัวนะคะ!'),
                'paid': ('✅ เช็คบิลเรียบร้อยแล้ว', 'gray', 1.0, 'ขอบคุณที่มาอุดหนุนฟ้าใสตำนัวนะคะ 🙏')
            }
            for oid, status, total, otime in cur_orders:
                c_trk.execute("SELECT item_name, quantity, note, COALESCE(status, 'pending') FROM order_items WHERE order_id = ?", (oid,))
                order_items_trk = c_trk.fetchall()
                
                total_it = len(order_items_trk)
                served_it = sum(1 for it in order_items_trk if it[3] == 'served')
                
                if status == 'paid':
                    prog_val = 1.0
                    label, color, _, desc_status = st_map['paid']
                elif status == 'served' or (total_it > 0 and served_it == total_it):
                    prog_val = 1.0
                    label, color, _, desc_status = st_map['served']
                elif served_it > 0:
                    prog_val = 0.5 + 0.4 * (served_it / total_it)
                    label, color, _, desc_status = (f'🍲 กำลังทยอยเสิร์ฟ ({served_it}/{total_it})', 'purple', prog_val, 'พนักงานกำลังยกอาหารมาเสิร์ฟที่โต๊ะค่ะ')
                elif status == 'cooked':
                    prog_val = 0.65
                    label, color, _, desc_status = st_map['cooked']
                elif status == 'accepted':
                    prog_val = 0.45
                    label, color, _, desc_status = st_map['accepted']
                else:
                    prog_val = 0.25
                    label, color, _, desc_status = st_map['pending']

                with st.container(border=True):
                    c_oh1, c_oh2 = st.columns([3, 1])
                    with c_oh1:
                        st.markdown(f"**ออเดอร์ #{oid}** — <span style='font-size: 1.05rem; font-weight: bold;'>:{color}[{label}]</span>", unsafe_allow_html=True)
                        st.caption(f"⚡ {desc_status} • สั่งเมื่อ {otime}")
                    with c_oh2:
                        st.markdown(f"<div style='text-align: right; font-weight: bold; font-size: 1.1rem; color: #ea580c;'>฿{int(total):,}</div>", unsafe_allow_html=True)
                    
                    st.progress(prog_val)
                    
                    with st.expander("🔍 ดูรายการอาหาร & สถานะแต่ละจานในบิลนี้", expanded=(status != 'paid')):
                        for iname, iqty, inote, ist in order_items_trk:
                            note_text = f" *(โน้ต: {inote})*" if inote else ""
                            if ist == 'served':
                                st_badge = ":green[**[✅ เสิร์ฟแล้ว]**]"
                            elif ist == 'cooked':
                                st_badge = ":purple[**[🍳 ปรุงเสร็จแล้ว]**]"
                            else:
                                st_badge = ":orange[**[⏳ กำลังปรุง]**]"
                            st.markdown(f"• **{iname}** x{iqty}{note_text} — {st_badge}")
                    
                    # ตัวเลือกให้ลูกค้าสแกนจ่ายเงินผ่าน QR ธนาคารได้สะดวกจากที่โต๊ะ
                    if status != 'paid':
                        with st.expander("📲 สแกน QR ชำระเงิน (PromptPay / ธนาคาร)", expanded=(status == 'served')):
                            p_img = "static/payment.jpg" if os.path.exists("static/payment.jpg") else "static/img/payment.jpg"
                            if os.path.exists(p_img):
                                st.image(p_img, caption=f"สแกนชำระเงินยอด ฿{int(total):,} (บิล #{oid})", width=220)
                                st.caption("💡 เมื่อสแกนชำระเงินเรียบร้อยแล้ว แจ้งพนักงานเพื่อเช็คบิลได้เลยนะคะ 🙏")
            conn_trk.close()

    render_table_order_tracking(current_table_num)
    conn.close()

    # Footer ล่างสุดสำหรับฝั่งลูกค้า
    render_app_footer()
