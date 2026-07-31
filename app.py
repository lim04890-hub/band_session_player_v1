import streamlit as st
import streamlit.components.v1 as components
import subprocess
import os
import shutil
import sys
import sqlite3
import uuid
import time
import json
from datetime import datetime
import imageio_ffmpeg

# 디렉토리 및 DB 설정
UPLOAD_DIR = "uploaded_audio"
OUTPUT_DIR = "separated_audio"
PROCESSED_DIR = "processed_audio"
DB_FILE = "hertz_app_data.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 페이지 설정 및 HERTZ 맞춤형 CSS
st.set_page_config(page_title="HERTZ Session Master", page_icon="🎸", layout="centered")

st.markdown("""
    <style>
    .stApp {
        background-color: #0b0b0b;
        color: #e0e0e0;
    }
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .hertz-header {
        background: linear-gradient(90deg, #1a1a1a 0%, #2b0505 100%);
        padding: 20px;
        border-radius: 10px;
        border-left: 6px solid #FF2222;
        margin-bottom: 25px;
    }
    .stButton>button {
        background-color: #FF2222;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #cc1b1b;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# 초기 부원 명단 데이터 
INITIAL_MEMBERS = [
    ("강대현", "전기전자공학부", "25", "기타", 0),
    ("강준", "전기전자공학부", "23", "베이스", 0),
    ("권도영", "컴퓨터공학부", "24", "보컬", 0),
    ("권찬우", "항공우주모빌리티공학과", "25", "베이스", 0),
    ("김다혜", "화화생명에너지학부", "26", "키보드", 0),
    ("김마루", "컴퓨터공학부", "24", "기타", 0),
    ("김민재", "전기전자공학부", "25", "기타", 0),
    ("김서윤", "환경보건과학과", "25", "드럼", 0),
    ("김수민", "화학공학부", "23", "베이스", 0),
    ("김준홍", "화학공학부", "23", "기타", 1),
    ("남성진", "화학공학부", "23", "기타", 0),
    ("노시영", "생물공학과", "25", "드럼", 0),
    ("박서진", "전기전자공학부", "25", "보컬", 0),
    ("박유찬", "항공우주모빌리티공학과", "25", "키보드", 0),
    ("박주용", "재료공학과", "23", "기타", 0),
    ("박현준", "산업공학과", "26", "보컬", 0),
    ("백찬민", "사회환경공학부", "24", "드럼", 0),
    ("변지우", "생물공학과", "24", "기타", 1),
    ("변지은", "화학공학부", "22", "기타", 1),
    ("손예원", "행정학과", "22", "보컬", 1),
    ("송종민", "전기전자공학부", "21", "기타", 0),
    ("심재형", "산림조경전공 (항공우주모빌리티공학과)", "25", "기타", 0),
    ("유병욱", "화학공학부", "23", "기타", 0),
    ("유선호", "화학공학부", "23", "키보드", 0),
    ("유시아", "사회환경공학부", "24", "보컬", 0),
    ("이승원", "생물공학과", "21", "키보드", 0),
    ("임승우", "화학공학부", "23", "기타", 0),
    ("임형준", "공과대학자유전공학부", "26", "기타", 0),
    ("장호준", "생물공학과", "25", "드럼", 0),
    ("정지호", "전기전자공학부", "23", "기타", 0),
    ("조제희", "기계항공공학부", "20", "보컬", 0),
    ("조혜성", "기계로봇자동차공학부", "26", "키보드", 0),
    ("천현승", "일어교육과", "21", "보컬", 0),
    ("최아현", "동물자원과학과", "22", "보컬", 1),
    ("최우혁", "항공우주모빌리티공학과", "26", "드럼", 0),
    ("최준호", "전기전자공학과", "26", "기타", 0),
    ("최준희", "전기전자공학부", "21", "베이스", 0),
    ("하은지", "전기전자공학부", "23", "드럼", 0),
    ("한호림", "전기전지공학부", "26", "베이스", 0),
    ("허승범", "전기전자공학부", "23", "보컬", 1)
]

# 공통 장착 아이템 카테고리별 정의
COMMON_SHOP_ITEMS = {
    "모자": [
        {"id": "hat_1", "name": "🧢 기본 스냅백", "cost": 1000, "desc": "챙을 완전히 편 스냅백"},
        {"id": "hat_2", "name": "🎩 빈티지 페도라", "cost": 3000, "desc": "재즈와 인디 감성을 더해주는 페도라"},
        {"id": "hat_3", "name": "👑 락스타 실크 햇", "cost": 5000, "desc": "무대 위에서 눈에 띄는 화려한 모자"},
        {"id": "hat_4", "name": "🌟 다이아몬드 크라운", "cost": 10000, "desc": "왕관의 무게"}
    ],
    "옷": [
        {"id": "cloth_1", "name": "👕 무지 밴드 티셔츠", "cost": 1000, "desc": "교류/직류 라고 쓰여있다"},
        {"id": "cloth_2", "name": "🧥 데님 청자켓", "cost": 3000, "desc": "청춘과 록의 상징인 스타일리시한 청자켓"},
        {"id": "cloth_3", "name": "🔥 락스타 가죽 라이더 자켓", "cost": 5000, "desc": "그 시절 락스타들의 가죽 자켓"},
        {"id": "cloth_4", "name": "✨ HERTZ 바람막이", "cost": 10000, "desc": "교수님 착용 제품"}
    ],
    "신발": [
        {"id": "shoe_1", "name": "👟 편안한 단화 스니커즈", "cost": 1000, "desc": "연습실에서 신기 좋은 가벼운 스니커즈"},
        {"id": "shoe_2", "name": "🥾 컨버스 하이톱", "cost": 3000, "desc": "합주할 때 발목을 탄탄하게 잡아주는 하이탑"},
        {"id": "shoe_3", "name": "🥿 스터드 워커 부츠", "cost": 5000, "desc": "거친 매력을 더해주는 락커들의 부츠"},
        {"id": "shoe_4", "name": "💎 맨발의 청춘", "cost": 10000, "desc": "근본"}
    ],
    "장신구": [
        {"id": "acc_1", "name": "💍 써지컬 스틸 링", "cost": 1000, "desc": "심플하면서도 시크한 기본 반지"},
        {"id": "acc_2", "name": "⛓️ 메탈 체인 목걸이", "cost": 3000, "desc": "힙한 감성을 완성해주는 체인 목걸이"},
        {"id": "acc_3", "name": "🕶️ 메탈릭 선글라스", "cost": 5000, "desc": "김다니엘 접신"},
        {"id": "acc_4", "name": "💎 해골이 그려진 목걸이", "cost": 10000, "desc": "skrrr"}
    ],
    "MD": [
        {"id": "md_1", "name": "🎗️ HERTZ 기본 반다나", "cost": 1000, "desc": "땀을 닦거나 손목에 두르는 밴드 공식 MD"},
        {"id": "md_2", "name": "🧣 로고 자수 스포츠 타올", "cost": 3000, "desc": "격렬한 합주 후 땀 닦기 딱 좋은 타올"},
        {"id": "md_3", "name": "🎒 HERTZ 투어 백팩", "cost": 5000, "desc": "악보와 장비를 모두 담는 투어용 가방"},
        {"id": "md_4", "name": "🎟️ VIP 올패스 패스포트", "cost": 10000, "desc": "나도 하나만"}
    ]
}

# 세션별 악기 아이템 정의
SESSION_GEAR_ITEMS = {
    "기타": [
        {"id": "g_1", "name": "🎸 입문용 통기타", "cost": 1000, "desc": "처음 튜닝을 배우며 코드를 잡던 추억의 기타"},
        {"id": "g_2", "name": "🎸 칩슨 & 휀다", "cost": 3000, "desc": "좌휀우칩"},
        {"id": "g_3", "name": "🎸 깁슨 & 펜더", "cost": 5000, "desc": "좌펜우깁"},
        {"id": "g_4", "name": "🎸 커스텀샵", "cost": 10000, "desc": "장인이 한 땀 한 땀 영혼을 갈아 넣은 세상에 단 하나뿐인 기타"}
    ],
    "베이스": [
        {"id": "b_1", "name": "🎸 입문용 4현 베이스", "cost": 1000, "desc": "묵직한 저음의 세계로 입문하게 만드는 베이스"},
        {"id": "b_2", "name": "🎸 그루브한 베이스", "cost": 3000, "desc": "밴드의 든든한 뼈대를 받쳐주는 단단한 사운드"},
        {"id": "b_3", "name": "🎸 베이스 붐을 불러일으키는 베이스", "cost": 5000, "desc": "특유의 펀치감과 개성 넘치는 로큰롤 베이스"},
        {"id": "b_4", "name": "🎸 커스텀샵 액티브 5현 베이스", "cost": 10000, "desc": "드디어 소리가 들려..."}
    ],
    "보컬": [
        {"id": "v_1", "name": "🎤 가성비 다이나믹 마이크", "cost": 1000, "desc": "전 세계 합주실과 라이브 클럽의 국룰 마이크"},
        {"id": "v_2", "name": "🎤 무선 스테이지 마이크", "cost": 3000, "desc": "무대 위를 자유롭게 누비며 관객을 사로잡는 마이크"},
        {"id": "v_3", "name": "🎤 진공관 마이크", "cost": 5000, "desc": "숨소리 하나까지 예술로 만드는 최고급 스튜디오 마이크"},
        {"id": "v_4", "name": "🎤 커스텀 다이아몬드 스튜디오 마이크", "cost": 10000, "desc": "보컬리스트의 위엄을 상징하는 보석 박힌 마이크"}
    ],
    "드럼": [
        {"id": "d_1", "name": "🥁 연습용 스틱 & 패드 세트", "cost": 1000, "desc": "끊임없이 루디먼트를 연습하게 만드는 필수품"},
        {"id": "d_2", "name": "🥁 북 & 장구", "cost": 3000, "desc": "코리안 트래디셔널 드럼"},
        {"id": "d_3", "name": "🥁 그레치 & 타마", "cost": 5000, "desc": "프로 드러머들이 사랑하는 영롱한 타악기 브랜드"},
        {"id": "d_4", "name": "🥁 커스텀 풀 메탈 킷트", "cost": 10000, "desc": "우혁아 여기 더블페달 있다"}
    ],
    "키보드": [
        {"id": "k_1", "name": "🎹 61건반 가성비 신디사이저", "cost": 1000, "desc": "가볍게 들고 다니며 피아노와 패드 소리를 내는 건반"},
        {"id": "k_2", "name": "🎹 모티프 / 일렉트로", "cost": 3000, "desc": "합주실 무대를 꽉 채우는 따뜻한 건반 사운드"},
        {"id": "k_3", "name": "🎹 스테이지 레드 피아노", "cost": 5000, "desc": "건반 연주자들의 로망, 무대 위 강렬한 레드 감성"},
        {"id": "k_4", "name": "🎹 기아노", "cost": 10000, "desc": "건반도 프론트맨 할 수 있어"}
    ]
}

def get_title_by_practice_time(minutes):
    if minutes >= 1000:
        return "🏆 전설의 HERTZ 마스터"
    elif minutes >= 500:
        return "🔥 무대를 찢어놓는 락스타"
    elif minutes >= 200:
        return "🎸 합주실 고인물"
    elif minutes >= 50:
        return "🎵 연습하는 밴드 키즈"
    else:
        return "🌱 풋풋한 뉴비"

# --- 데이터베이스 설정 ---

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                student_id TEXT NOT NULL,
                session TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 0,
                inventory TEXT DEFAULT '',
                practice_minutes INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                bio TEXT DEFAULT '안녕하세요! HERTZ 밴드 활동 열심히 하겠습니다!',
                ensemble_stats INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute("PRAGMA table_info(members)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'credits' not in columns:
            cursor.execute("ALTER TABLE members ADD COLUMN credits INTEGER DEFAULT 0")
        if 'inventory' not in columns:
            cursor.execute("ALTER TABLE members ADD COLUMN inventory TEXT DEFAULT ''")
        if 'practice_minutes' not in columns:
            cursor.execute("ALTER TABLE members ADD COLUMN practice_minutes INTEGER DEFAULT 0")
        if 'is_active' not in columns:
            cursor.execute("ALTER TABLE members ADD COLUMN is_active INTEGER DEFAULT 1")
        if 'bio' not in columns:
            cursor.execute("ALTER TABLE members ADD COLUMN bio TEXT DEFAULT '안녕하세요! HERTZ 밴드 활동 열심히 하겠습니다!'")
        if 'ensemble_stats' not in columns:
            cursor.execute("ALTER TABLE members ADD COLUMN ensemble_stats INTEGER DEFAULT 0")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                song_title TEXT NOT NULL,
                separated_dir TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (member_id) REFERENCES members (id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                performance_id INTEGER NOT NULL,
                team_name TEXT NOT NULL,
                member_id INTEGER NOT NULL,
                FOREIGN KEY (performance_id) REFERENCES performances (id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ensembles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                team_name TEXT NOT NULL,
                member_ids TEXT NOT NULL,
                is_active INTEGER DEFAULT 0,
                start_time REAL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute("SELECT COUNT(*) FROM members")
        if cursor.fetchone()[0] == 0:
            for item in INITIAL_MEMBERS:
                cursor.execute('''
                    INSERT INTO members (name, department, student_id, session, is_admin, credits, inventory, practice_minutes, is_active, bio, ensemble_stats)
                    VALUES (?, ?, ?, ?, ?, 0, '', 0, 1, '안녕하세요! HERTZ 밴드 활동 열심히 하겠습니다!', 0)
                ''', item)
            
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"데이터베이스 초기화 오류: {e}")

def verify_member(name, department, student_id, session):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM members 
        WHERE name = ? AND department = ? AND student_id = ? AND session = ? AND is_active = 1
    ''', (name.strip(), department.strip(), str(student_id).strip(), session))
    member = cursor.fetchone()
    conn.close()
    return dict(member) if member else None

def get_member_fresh(member_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    member = cursor.fetchone()
    conn.close()
    return dict(member) if member else None

def get_all_active_members():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE is_active = 1 ORDER BY name ASC")
    members = cursor.fetchall()
    conn.close()
    return [dict(m) for m in members]

def get_all_members_including_inactive():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members ORDER BY is_active DESC, name ASC")
    members = cursor.fetchall()
    conn.close()
    return [dict(m) for m in members]

def add_member(name, department, student_id, session, is_admin):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO members (name, department, student_id, session, is_admin, credits, inventory, practice_minutes, is_active, bio, ensemble_stats)
            VALUES (?, ?, ?, ?, ?, 0, '', 0, 1, '안녕하세요! HERTZ 밴드 활동 열심히 하겠습니다!', 0)
        ''', (name.strip(), department.strip(), str(student_id).strip(), session, 1 if is_admin else 0))
        conn.commit()
        return True, "부원이 성공적으로 추가되었습니다."
    except Exception as e:
        return False, f"오류 발생: {e}"
    finally:
        conn.close()

def update_member_admin(member_id, is_admin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, member_id))
    conn.commit()
    conn.close()

def set_member_active_status(member_id, is_active):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET is_active = ? WHERE id = ?", (1 if is_active else 0, member_id))
    conn.commit()
    conn.close()

def update_member_bio(member_id, bio):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET bio = ? WHERE id = ?", (bio.strip(), member_id))
    conn.commit()
    conn.close()

def add_practice_time_and_credits(member_id, minutes, credits):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET practice_minutes = practice_minutes + ?, credits = credits + ? WHERE id = ?", (minutes, credits, member_id))
    conn.commit()
    conn.close()

def purchase_item_db(member_id, category_items, target_item_id, cost):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT credits, inventory, ensemble_stats FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "부원 정보를 찾을 수 없습니다."
    
    row_dict = dict(row)
    current_credits = row_dict.get('credits', 0)
    inventory = row_dict.get('inventory', "") or ""
    current_ensemble_stats = row_dict.get('ensemble_stats', 0) or 0
    items_list = [i.strip() for i in inventory.split(",") if i.strip()]
    
    if target_item_id in items_list:
        conn.close()
        return False, "이미 보유한 아이템입니다."
        
    target_idx = -1
    for idx, item in enumerate(category_items):
        if item['id'] == target_item_id:
            target_idx = idx
            break
            
    if target_idx > 0:
        prev_item_id = category_items[target_idx - 1]['id']
        if prev_item_id not in items_list:
            conn.close()
            return False, f"이전 단계 아이템인 [{category_items[target_idx - 1]['name']}]을(를) 먼저 구매해야 합니다!"

    # 합주 능력치 필요 조건 및 소모량 계산
    req_ensemble_stat = 0
    if cost == 3000:
        req_ensemble_stat = 1
    elif cost == 5000:
        req_ensemble_stat = 3
    elif cost >= 10000:
        req_ensemble_stat = 5

    if current_credits < cost and current_ensemble_stats < req_ensemble_stat:
        conn.close()
        return False, f"크레딧({cost} C)과 합주 능력치({req_ensemble_stat}개)가 모두 부족합니다."
    elif current_credits < cost:
        conn.close()
        return False, f"크레딧이 부족합니다. (필요: {cost} C / 보유: {current_credits} C)"
    elif current_ensemble_stats < req_ensemble_stat:
        conn.close()
        return False, f"합주 능력치가 부족합니다. (필요: ⚡ {req_ensemble_stat}개 / 보유: ⚡ {current_ensemble_stats}개)"

    items_list.append(target_item_id)
    new_inventory = ",".join(items_list)
    new_credits = current_credits - cost
    new_ensemble_stats = current_ensemble_stats - req_ensemble_stat
    
    cursor.execute("UPDATE members SET credits = ?, inventory = ?, ensemble_stats = ? WHERE id = ?", 
                   (new_credits, new_inventory, new_ensemble_stats, member_id))
    conn.commit()
    conn.close()
    return True, f"구매가 완료되었습니다! ({cost} C 차감, ⚡ 합주 능력치 {req_ensemble_stat}개 차감)"

def save_project(member_id, song_title, separated_dir):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO projects (member_id, song_title, separated_dir, created_at) VALUES (?, ?, ?, ?)",
        (member_id, song_title, separated_dir, now)
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id

def get_member_projects(member_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE member_id = ? ORDER BY id DESC", (member_id,))
    projects = cursor.fetchall()
    conn.close()
    return [dict(p) for p in projects]

def delete_project(project_id, member_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT separated_dir FROM projects WHERE id = ? AND member_id = ?", (project_id, member_id))
    row = cursor.fetchone()
    if row and row['separated_dir'] and os.path.exists(row['separated_dir']):
        shutil.rmtree(row['separated_dir'], ignore_errors=True)
        
    cursor.execute("DELETE FROM projects WHERE id = ? AND member_id = ?", (project_id, member_id))
    conn.commit()
    conn.close()

def get_all_performances():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM performances ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_performance(title):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO performances (title, created_at) VALUES (?, ?)", (title, now))
    perf_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return perf_id

def delete_performance(perf_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM performances WHERE id = ?", (perf_id,))
    cursor.execute("DELETE FROM performance_teams WHERE performance_id = ?", (perf_id,))
    conn.commit()
    conn.close()

def save_performance_teams(perf_id, team_dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM performance_teams WHERE performance_id = ?", (perf_id,))
    for team_name, m_ids in team_dict.items():
        for m_id in m_ids:
            cursor.execute("INSERT INTO performance_teams (performance_id, team_name, member_id) VALUES (?, ?, ?)",
                           (perf_id, team_name, m_id))
    conn.commit()
    conn.close()

def get_performance_teams(perf_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT pt.team_name, m.id as member_id, m.name, m.department, m.student_id, m.session 
        FROM performance_teams pt
        JOIN members m ON pt.member_id = m.id
        WHERE pt.performance_id = ?
    ''', (perf_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_distinct_teams():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT pt.team_name, p.title as perf_title
        FROM performance_teams pt
        JOIN performances p ON pt.performance_id = p.id
    ''')
    teams = cursor.fetchall()
    conn.close()
    return [dict(t) for t in teams]

def get_members_by_team(team_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.id, m.name, m.department, m.session, m.inventory, m.bio
        FROM performance_teams pt
        JOIN members m ON pt.member_id = m.id
        WHERE pt.team_name = ?
    ''', (team_name,))
    members = cursor.fetchall()
    conn.close()
    return [dict(m) for m in members]

# --- 합주 DB 핸들러 ---

def create_ensemble(name, team_name, member_ids):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    member_ids_str = ",".join(map(str, member_ids))
    cursor.execute('''
        INSERT INTO ensembles (name, team_name, member_ids, is_active, start_time, created_at)
        VALUES (?, ?, ?, 0, 0, ?)
    ''', (name, team_name, member_ids_str, now))
    conn.commit()
    conn.close()

def get_all_ensembles():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ensembles ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def start_ensemble_db(ensemble_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_ts = time.time()
    cursor.execute("UPDATE ensembles SET is_active = 0")
    cursor.execute("UPDATE ensembles SET is_active = 1, start_time = ? WHERE id = ?", (now_ts, ensemble_id))
    conn.commit()
    conn.close()

def stop_ensemble_db(ensemble_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ensembles WHERE id = ?", (ensemble_id,))
    ens = cursor.fetchone()
    
    if ens and ens['is_active'] == 1:
        start_t = ens['start_time']
        elapsed_sec = time.time() - start_t
        stats_earned = int(elapsed_sec // 1800) # 30분(1800초)당 1 능력치
        
        member_ids = [int(x.strip()) for x in ens['member_ids'].split(",") if x.strip()]
        
        if stats_earned > 0 and member_ids:
            for m_id in member_ids:
                cursor.execute("UPDATE members SET ensemble_stats = ensemble_stats + ? WHERE id = ?", (stats_earned, m_id))
                
        cursor.execute("UPDATE ensembles SET is_active = 0, start_time = 0 WHERE id = ?", (ensemble_id,))
        conn.commit()
        conn.close()
        return stats_earned, len(member_ids)
    
    conn.close()
    return 0, 0

def get_active_ensemble():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ensembles WHERE is_active = 1 LIMIT 1")
    ens = cursor.fetchone()
    conn.close()
    return dict(ens) if ens else None

init_db()

# --- 오디오 처리 로직 ---

def separate_audio(file_path, filename):
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "2"
    
    command = [
        sys.executable,
        "-m", "demucs",
        "-d", "cpu",
        "-n", "htdemucs_6s",
        "--out", OUTPUT_DIR,
        file_path
    ]
    
    result = subprocess.run(command, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Demucs 실행 실패: {result.stderr}")
        
    base_name = os.path.splitext(filename)[0]
    target_dir = os.path.join(OUTPUT_DIR, "htdemucs_6s", base_name)
    
    if not os.path.exists(target_dir):
        raise FileNotFoundError(f"분리된 결과 폴더를 찾을 수 없습니다: {target_dir}")
        
    return target_dir

def process_mix(separated_dir, selected_stems, speed, start_sec, end_sec):
    if not selected_stems or not separated_dir or not os.path.exists(separated_dir):
        return None

    input_files = []
    for stem in selected_stems:
        stem_path = os.path.join(separated_dir, f"{stem}.wav")
        if os.path.exists(stem_path):
            input_files.append(stem_path)

    if not input_files:
        return None

    unique_id = str(uuid.uuid4())[:8]
    output_path = os.path.join(PROCESSED_DIR, f"mix_{unique_id}.wav")
    
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg_exe = "ffmpeg"

    command = [ffmpeg_exe, "-y"]

    if end_sec > start_sec:
        command.extend(["-ss", str(start_sec), "-to", str(end_sec)])

    for f in input_files:
        command.extend(["-i", f])

    filter_complex = []
    num_inputs = len(input_files)

    if num_inputs > 1:
        filter_complex.append(f"amix=inputs={num_inputs}:duration=longest:dropout_transition=0")

    if speed != 1.0:
        filter_complex.append(f"atempo={speed}")

    if filter_complex:
        command.extend(["-filter_complex", ",".join(filter_complex)])

    command.append(output_path)
    
    try:
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except Exception as e:
        st.error(f"오디오 믹싱 처리 중 오류 발생: {e}")
        return None


# --- 세션 상태 관리 ---
if 'member' not in st.session_state:
    st.session_state['member'] = None
if 'view' not in st.session_state:
    st.session_state['view'] = 'dashboard'
if 'current_project' not in st.session_state:
    st.session_state['current_project'] = None

# 타이머 및 연습 세션 상태 관리
if 'is_practicing' not in st.session_state:
    st.session_state['is_practicing'] = False
if 'practice_start_time' not in st.session_state:
    st.session_state['practice_start_time'] = None

def handle_logout_or_stop():
    if st.session_state.get('is_practicing') and st.session_state.get('practice_start_time') and st.session_state.get('member'):
        elapsed_seconds = time.time() - st.session_state['practice_start_time']
        elapsed_minutes = int(elapsed_seconds // 60)
        if elapsed_minutes >= 1:
            earned = elapsed_minutes * 30
            add_practice_time_and_credits(st.session_state['member']['id'], elapsed_minutes, earned)
    st.session_state['is_practicing'] = False
    st.session_state['practice_start_time'] = None


# --- UI 레이아웃 ---

st.markdown("""
    <div class="hertz-header">
        <h1 style="margin:0; font-size: 26px;">🎸 건국대학교 공과대학 밴드 HERTZ</h1>
        <p style="margin:5px 0 0 0; color: #ff8888; font-size: 14px;">
            Official Instagram: <a href="https://instagram.com/ku.hertz" target="_blank" style="color: #ff9999;">@ku.hertz</a> | 세션 커스텀 연습 플레이어
        </p>
    </div>
""", unsafe_allow_html=True)

if st.session_state['member'] is None:
    st.subheader("⚡ HERTZ 부원 인증 로그인")
    st.caption("등록된 명단(이름, 학과, 학번, 세션)과 일치해야 로그인이 가능합니다.")
    
    with st.form("login_form"):
        input_name = st.text_input("이름")
        input_dept = st.text_input("학과 (예: 전기전자공학부, 컴퓨터공학부 등)")
        input_id = st.text_input("학번 두 자리 (예: 21, 23, 25 등)")
        input_session = st.selectbox("세션", ["보컬", "기타", "베이스", "드럼", "키보드"])
        
        submit_btn = st.form_submit_button("인증 및 입장하기 🚀", use_container_width=True)
        
        if submit_btn:
            member_data = verify_member(input_name, input_dept, input_id, input_session)
            if member_data:
                st.session_state['member'] = member_data
                st.session_state['view'] = 'dashboard'
                st.success("인증 성공!")
                st.rerun()
            else:
                st.error("❌ 등록된 HERTZ 부원 정보와 일치하지 않거나 활동이 중단된 계정입니다.")

else:
    current_mem_id = st.session_state['member']['id']
    latest_member_info = get_member_fresh(current_mem_id)
    if latest_member_info:
        st.session_state['member'] = latest_member_info
    member = st.session_state['member']

    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        admin_badge = "👑 [임원진]" if member['is_admin'] == 1 else "🎵 [부원]"
        practicing_indicator = " 🔴 [개인 연습 중]" if st.session_state['is_practicing'] else ""
        st.markdown(f"{admin_badge} **{member['name']}** 님 (`{member['department']}` / {member['student_id']}학번 / `{member['session']}`) | 💰 **{member['credits']} C** | ⚡ **합주 능력치: {member.get('ensemble_stats', 0)}개**{practicing_indicator}")
    with top_col2:
        if st.button("로그아웃"):
            handle_logout_or_stop()
            st.session_state['member'] = None
            st.session_state['view'] = 'dashboard'
            st.session_state['current_project'] = None
            st.rerun()

    base_tabs = ["🎵 내 작업실", "🎮 연습실 & 상점", "🎷 합주","\n(임원진 전용)" "👥 부원 목록", "🤝 팀", "🎪 공연 관리"]
    if member['is_admin'] == 1:
        base_tabs.append("⚙️ 임원 관리")

    selected_main_tab = st.radio("상단 메인 메뉴", base_tabs, horizontal=True, label_visibility="collapsed")

    all_possible_shop_items = []
    for cat, items in COMMON_SHOP_ITEMS.items():
        all_possible_shop_items.extend(items)
    for s_name, s_items in SESSION_GEAR_ITEMS.items():
        all_possible_shop_items.extend(s_items)

    if selected_main_tab == "🎵 내 작업실":
        if st.session_state['view'] == 'dashboard':
            st.title("📂 내 연습 작업물 목록")
            projects = get_member_projects(member['id'])
            
            if not projects:
                st.info("저장된 곡이 없습니다. 아래 버튼을 눌러 합주곡을 추가해보세요!")
            else:
                for p in projects:
                    with st.container():
                        col_info, col_btn, col_del = st.columns([4, 1.5, 1])
                        with col_info:
                            st.markdown(f"### 🎵 {p['song_title']}")
                            st.caption(f"등록일: {p['created_at']}")
                        with col_btn:
                            if st.button("플레이어 열기 ▶️", key=f"open_{p['id']}", use_container_width=True):
                                st.session_state['current_project'] = dict(p)
                                st.session_state['view'] = 'project_detail'
                                st.rerun()
                        with col_del:
                            if st.button("삭제 🗑️", key=f"del_{p['id']}", use_container_width=True):
                                delete_project(p['id'], member['id'])
                                st.rerun()
                        st.markdown("---")

            if st.button("➕ 새 합주곡 세션 분리하기", type="primary", use_container_width=True):
                st.session_state['view'] = 'new_project'
                st.rerun()

        elif st.session_state['view'] == 'new_project':
            if st.button("⬅️ 목록으로 돌아가기"):
                st.session_state['view'] = 'dashboard'
                st.rerun()

            st.title("➕ 새 합주곡 추가")
            uploaded_file = st.file_uploader("합주 연습용 오디오 파일 업로드 (MP3, WAV)", type=["mp3", "wav"])
            
            if uploaded_file is not None:
                file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if st.button("🚀 AI 세션 분리 및 저장 시작", type="primary", use_container_width=True):
                    with st.spinner("AI가 곡의 6개 세션을 분리하는 중입니다...(수 분 소요됨)"):
                        try:
                            separated_dir = separate_audio(file_path, uploaded_file.name)
                            song_title = os.path.splitext(uploaded_file.name)[0]
                            project_id = save_project(member['id'], song_title, separated_dir)
                            
                            st.success("세션 분리 완료!")
                            st.session_state['current_project'] = {
                                "id": project_id,
                                "song_title": song_title,
                                "separated_dir": separated_dir
                            }
                            st.session_state['view'] = 'project_detail'
                            st.rerun()
                        except Exception as e:
                            st.error(f"오류 발생: {e}")

        elif st.session_state['view'] == 'project_detail':
            if st.button("⬅️ 목록으로 돌아가기"):
                st.session_state['view'] = 'dashboard'
                st.rerun()

            project = st.session_state['current_project']
            separated_dir = project['separated_dir']

            st.title(f"🎵 {project['song_title']}")
            st.subheader("🎛️ HERTZ 세션 커스텀 믹서")

            all_stems = ["guitar", "vocals", "drums", "bass", "piano", "other"]
            stem_labels = {
                "guitar": "🎸 Guitar", "vocals": "🎤 Vocals", "drums": "🥁 Drums",
                "bass": "🎸 Bass", "piano": "🎹 Piano", "other": "🎶 Other"
            }

            cols = st.columns(3)
            selected_stems = []
            for idx, stem in enumerate(all_stems):
                col = cols[idx % 3]
                default_val = True if stem != "guitar" else False
                if col.checkbox(stem_labels[stem], value=default_val, key=f"chk_p_{stem}"):
                    selected_stems.append(stem)

            st.markdown("#### ⚡ 재생 및 연습 옵션")
            col_spd, col_s, col_e = st.columns([1, 1, 1])
            with col_spd:
                speed = st.slider("재생 속도", 0.5, 2.0, 1.0, 0.01)
            with col_s:
                start_time = st.number_input("시작 구간 (초)", min_value=0, value=0)
            with col_e:
                end_time = st.number_input("종료 구간 (초, 0은 끝까지)", min_value=0, value=0)

            st.markdown("---")

            if selected_stems:
                with st.spinner("커스텀 트랙 믹싱 중..."):
                    mixed_audio_path = process_mix(separated_dir, selected_stems, speed, start_time, end_time)

                if mixed_audio_path and os.path.exists(mixed_audio_path):
                    st.subheader("▶️ 커스텀 합주 트랙 재생")
                    st.audio(mixed_audio_path, format="audio/wav")

                    with open(mixed_audio_path, "rb") as f:
                        st.download_button(
                            label=f"📥 연습용 음원 다운로드 ({len(selected_stems)}개 세션)",
                            data=f,
                            file_name=f"{project['song_title']}_HERTZ_mix.wav",
                            mime="audio/wav",
                            type="primary",
                            use_container_width=True
                        )
            else:
                st.info("하나 이상의 스템을 선택하면 플레이어가 활성화됩니다.")

    elif selected_main_tab == "🎮 연습실 & 상점":
        st.title("🎮 HERTZ 아케이드 연습실 & 상점")
        st.caption("실시간 타이머로 연습을 기록하고 크레딧을 모아 캐릭터에 장비와 아이템을 순서대로 장착해보세요!")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎸 연습 세션실 & 무대", "🛍️ 확장 상점 & 인벤토리", "✏️ 내 한줄소개 설정"])

        inventory_str = member['inventory'] or ""
        my_items = [i.strip() for i in inventory_str.split(",") if i.strip()]
        user_practice_time = member['practice_minutes']
        user_title = get_title_by_practice_time(user_practice_time)

        # 활성 합주 체크
        active_ens = get_active_ensemble()

        with sub_tab1:
            st.subheader("무대 위 캐릭터 공연 애니메이션 & 타이머")

            # 활성 합주가 진행 중인 경우, 해당 팀 멤버들 전원을 무대에 렌더링
            render_members = []
            if active_ens and active_ens['is_active'] == 1:
                ens_m_ids = [int(x.strip()) for x in active_ens['member_ids'].split(",") if x.strip()]
                for mid in ens_m_ids:
                    mobj = get_member_fresh(mid)
                    if mobj:
                        render_members.append({
                            "name": mobj['name'],
                            "session": mobj['session'],
                            "inventory": [i.strip() for i in (mobj['inventory'] or "").split(",") if i.strip()]
                        })
            else:
                render_members.append({
                    "name": member['name'],
                    "session": member['session'],
                    "inventory": my_items
                })

            equipped_display = []
            total_credits = 0

            for mi in my_items:
                match_obj = next((item for item in all_possible_shop_items if item['id'] == mi), None)
                if match_obj:
                    equipped_display.append(match_obj['name'])
                    item_cost = match_obj.get('cost', 1000)
                    total_credits += item_cost

            gear_text = " | ".join(equipped_display) if equipped_display else "기본 장비 착용 중"
            audience_count = max(3, min(120, 3 + (total_credits // 200)))

            # 타이머 상태 계산
            is_ensemble_mode = (active_ens and active_ens['is_active'] == 1)
            is_anim_playing = st.session_state['is_practicing'] or is_ensemble_mode

            if is_ensemble_mode:
                ens_elapsed = int(time.time() - active_ens['start_time'])
                mins = ens_elapsed // 60
                secs = ens_elapsed % 60
                timer_html_status = f"🎷 [팀 합주 진행 중] '{active_ens['name']}': {mins:02d}분 {secs:02d}초 (30분당 능력치 1개 적립)"
            elif st.session_state['is_practicing'] and st.session_state['practice_start_time']:
                current_elapsed_seconds = int(time.time() - st.session_state['practice_start_time'])
                mins = current_elapsed_seconds // 60
                secs = current_elapsed_seconds % 60
                timer_html_status = f"⏱️ [개인 연습 진행 중]: {mins:02d}분 {secs:02d}초"
            else:
                timer_html_status = "[타이머 대기 중 - 연습 시작 또는 합주 탭에서 합주를 시작하세요]"

            st.write(f"**칭호:** {user_title} | **본래 세션:** {member['session']} | **누적 연습 시간:** {user_practice_time}분 | **⚡ 합주 능력치:** {member.get('ensemble_stats', 0)}개")
            st.write(f"**착용 장비:** {gear_text} | **장비 총 가치:** {total_credits:,} C | **관중 수:** {audience_count}명")

            # JavaScript에 넘길 부원 정보 JSON 구조 생성
            members_json = json.dumps(render_members, ensure_ascii=False)
            is_playing_str = "true" if is_anim_playing else "false"

            stage_html = f"""
            <div style="text-align: center; background-color: #0d0d15; padding: 12px; border-radius: 10px; font-family: sans-serif;">
                <div style="color: #00FF66; font-weight: bold; font-size: 15px; margin-bottom: 8px;">{timer_html_status}</div>
                <canvas id="stageCanvas" width="620" height="260" style="border:2px solid #2a2a3d; image-rendering: pixelated; border-radius: 8px;"></canvas>
            </div>

            <script>
            const canvas = document.getElementById('stageCanvas');
            const ctx = canvas.getContext('2d');
            
            const isPlaying = {is_playing_str};
            const audienceCount = {audience_count};
            const bandMembers = {members_json};

            let frame = 0;

            const crowd = [];
            for (let i = 0; i < audienceCount; i++) {{
                crowd.push({{
                    x: Math.random() * (canvas.width - 20) + 10,
                    y: canvas.height - 18 + Math.random() * 10,
                    height: 12 + Math.random() * 6,
                    color: ['#4A5568', '#718096', '#A0AEC0', '#ED8936', '#9F7AEA', '#48BB78'][Math.floor(Math.random() * 6)],
                    offset: Math.random() * Math.PI * 2
                }});
            }}

            function render() {{
                ctx.fillStyle = '#0a0a16';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                if (isPlaying) {{
                    const hue1 = (frame * 2) % 360;
                    const hue2 = (frame * 2 + 120) % 360;
                    
                    ctx.fillStyle = `hsla(${{hue1}}, 80%, 50%, 0.12)`;
                    ctx.beginPath();
                    ctx.moveTo(80, 0); ctx.lineTo(0, canvas.height - 60); ctx.lineTo(220, canvas.height - 60);
                    ctx.fill();

                    ctx.fillStyle = `hsla(${{hue2}}, 80%, 50%, 0.12)`;
                    ctx.beginPath();
                    ctx.moveTo(canvas.width - 80, 0); ctx.lineTo(canvas.width - 220, canvas.height - 60); ctx.lineTo(canvas.width, canvas.height - 60);
                    ctx.fill();
                }}

                ctx.fillStyle = '#161625';
                ctx.fillRect(0, canvas.height - 70, canvas.width, 40);
                ctx.fillStyle = '#FF2222';
                ctx.fillRect(0, canvas.height - 70, canvas.width, 2);

                drawAmplifiers();

                const numMembers = bandMembers.length;
                const spacing = canvas.width / (numMembers + 1);

                bandMembers.forEach((m, idx) => {{
                    const cx = spacing * (idx + 1);
                    drawPixelCharacter(cx, m);
                }});

                drawAudience();

                frame++;
                requestAnimationFrame(render);
            }}

            function drawAmplifiers() {{
                ctx.fillStyle = '#1f1f2e';
                ctx.fillRect(20, canvas.height - 120, 28, 50);
                ctx.fillRect(canvas.width - 48, canvas.height - 120, 28, 50);
                
                ctx.fillStyle = '#3a3a52';
                ctx.beginPath();
                ctx.arc(34, canvas.height - 105, 5, 0, Math.PI * 2);
                ctx.arc(34, canvas.height - 85, 5, 0, Math.PI * 2);
                ctx.arc(canvas.width - 34, canvas.height - 105, 5, 0, Math.PI * 2);
                ctx.arc(canvas.width - 34, canvas.height - 85, 5, 0, Math.PI * 2);
                ctx.fill();
            }}

            function drawPixelCharacter(cx, mData) {{
                let cy = canvas.height - 110;
                const bounce = isPlaying ? Math.sin(frame * 0.2 + cx) * 3 : 0;
                cy += bounce;

                // 머리
                ctx.fillStyle = '#ffe0bd';
                ctx.fillRect(cx - 8, cy - 24, 16, 16);

                // 눈
                ctx.fillStyle = '#111';
                ctx.fillRect(cx - 5, cy - 18, 3, 3);
                ctx.fillRect(cx + 2, cy - 18, 3, 3);

                // 머리카락
                ctx.fillStyle = '#3a2e2b';
                ctx.fillRect(cx - 9, cy - 27, 18, 6);

                // 이름 표시
                ctx.fillStyle = '#ffffff';
                ctx.font = '10px sans-serif';
                ctx.textAlign = 'center';
                ctx.fillText(mData.name, cx, cy - 32);

                // 상의 & 하의
                ctx.fillStyle = '#0f3460';
                ctx.fillRect(cx - 7, cy - 8, 14, 16);
                ctx.fillStyle = '#16213e';
                ctx.fillRect(cx - 6, cy + 8, 5, 12);
                ctx.fillRect(cx + 1, cy + 8, 5, 12);

                drawInstrument(cx, cy, mData.session);
            }}

            function drawInstrument(cx, cy, sessionType) {{
                ctx.save();
                if (sessionType === "기타" || sessionType === "베이스") {{
                    ctx.fillStyle = sessionType === "기타" ? '#FF2222' : '#00fff5';
                    ctx.fillRect(cx - 12, cy - 2, 10, 8);
                    ctx.fillStyle = '#8d5524';
                    ctx.fillRect(cx - 3, cy - 0, 18, 3);
                }} else if (sessionType === "드럼") {{
                    ctx.fillStyle = '#f5abc9';
                    ctx.beginPath();
                    ctx.arc(cx, cy + 8, 10, 0, Math.PI * 2);
                    ctx.fill();
                }} else if (sessionType === "키보드") {{
                    ctx.fillStyle = '#ffffff';
                    ctx.fillRect(cx - 14, cy + 2, 28, 6);
                }} else if (sessionType === "보컬") {{
                    ctx.fillStyle = '#aaaaaa';
                    ctx.fillRect(cx + 6, cy - 12, 2, 20);
                    ctx.fillStyle = '#FF2222';
                    ctx.fillRect(cx + 4, cy - 16, 6, 6);
                }}
                ctx.restore();
            }}

            function drawAudience() {{
                crowd.forEach((p) => {{
                    const jump = isPlaying ? Math.abs(Math.sin(frame * 0.25 + p.offset)) * 7 : 0;
                    const drawY = p.y - jump;

                    ctx.fillStyle = p.color;
                    ctx.fillRect(p.x, drawY, 8, p.height);
                    ctx.fillRect(p.x + 1, drawY - 6, 6, 6);
                }});
            }}

            render();
            </script>
            """

            components.html(stage_html, height=310)

            col_t_btn1, col_t_btn2 = st.columns(2)
            with col_t_btn1:
                if not st.session_state['is_practicing']:
                    if st.button("🔴 개인 연습 시작", use_container_width=True, type="primary"):
                        st.session_state['is_practicing'] = True
                        st.session_state['practice_start_time'] = time.time()
                        st.rerun()
                else:
                    st.button("🔴 연습 진행 중...", disabled=True, use_container_width=True)

            with col_t_btn2:
                if st.session_state['is_practicing']:
                    if st.button("⏹️ 연습 종료 및 크레딧 정산", use_container_width=True, type="primary"):
                        elapsed_seconds = time.time() - st.session_state['practice_start_time']
                        elapsed_minutes = int(elapsed_seconds // 60)
                        if elapsed_minutes < 1:
                            st.warning("⚠️ 1분 이상 연습해야 크레딧이 적립됩니다.")
                            st.session_state['is_practicing'] = False
                            st.session_state['practice_start_time'] = None
                        else:
                            earned = elapsed_minutes * 30
                            add_practice_time_and_credits(member['id'], elapsed_minutes, earned)
                            st.success(f"🎉 연습 종료! {elapsed_minutes}분 동안 연습하여 **{earned} 크레딧**을 획득했습니다!")
                            st.session_state['is_practicing'] = False
                            st.session_state['practice_start_time'] = None
                        st.rerun()
                else:
                    st.button("⏹️ 정지됨", disabled=True, use_container_width=True)

            if st.session_state['is_practicing'] or is_ensemble_mode:
                time.sleep(1)
                st.rerun()

        with sub_tab2:
            st.subheader("🛍️ 밴드 장비 및 패션 상점")
            st.markdown(f"보유 크레딧: **{member['credits']} C** | 보유 합주 능력치: **⚡ {member.get('ensemble_stats', 0)}개**")
            st.info("💡 **상점 구매 조건:** 아이템 구매 시 해당 단계의 크레딧과 합주 능력치가 함께 소모됩니다.\n(3,000 C = 능력치 1개 소모 | 5,000 C = 3개 소모 | 10,000 C = 5개 소모)")
            
            shop_tabs = st.tabs(["🧢 모자", "옷", "👟 신발", "💍 장신구", "🎗️ MD", "🎸 세션별 악기 장비"])
            categories = ["모자", "옷", "신발", "장신구", "MD"]

            for idx, cat_name in enumerate(categories):
                with shop_tabs[idx]:
                    st.markdown(f"### 🛒 {cat_name} 컬렉션")
                    c_items = COMMON_SHOP_ITEMS[cat_name]
                    scols = st.columns(2)
                    for i, item in enumerate(c_items):
                        with scols[i % 2]:
                            is_owned = item['id'] in my_items
                            can_buy = True
                            if i > 0 and c_items[i - 1]['id'] not in my_items:
                                can_buy = False

                            req_stat = 0
                            if item['cost'] == 3000: req_stat = 1
                            elif item['cost'] == 5000: req_stat = 3
                            elif item['cost'] >= 10000: req_stat = 5

                            req_text = f" + ⚡ 능력치 {req_stat}개" if req_stat > 0 else ""

                            st.markdown(f"""
                                <div style="background: #151515; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px;">
                                    <h4>{item['name']}</h4>
                                    <p style="color: #ccc; font-size: 13px; margin: 5px 0;">{item['desc']}</p>
                                    <p style="color: #FF2222; font-weight: bold; margin: 5px 0;">소모 재화: {item['cost']} C{req_text}</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if is_owned:
                                st.button("보유 중 ✅", key=f"owned_{item['id']}", disabled=True, use_container_width=True)
                            elif not can_buy:
                                st.button("잠김 🔒 (이전 단계 필요)", key=f"lock_{item['id']}", disabled=True, use_container_width=True)
                            else:
                                if st.button("구매하기 💳", key=f"buy_{item['id']}", use_container_width=True):
                                    success, msg = purchase_item_db(member['id'], c_items, item['id'], item['cost'])
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)

            with shop_tabs[5]:
                st.markdown("### 🎸 세션별 악기 및 장비 상점")
                selected_gear_session = st.selectbox("조회할 악기 세션 선택", ["기타", "베이스", "보컬", "드럼", "키보드"])
                target_gear_list = SESSION_GEAR_ITEMS[selected_gear_session]
                
                g_cols = st.columns(2)
                for i, item in enumerate(target_gear_list):
                    with g_cols[i % 2]:
                        is_owned = item['id'] in my_items
                        can_buy = True
                        if i > 0 and target_gear_list[i - 1]['id'] not in my_items:
                            can_buy = False

                        req_stat = 0
                        if item['cost'] == 3000: req_stat = 1
                        elif item['cost'] == 5000: req_stat = 3
                        elif item['cost'] >= 10000: req_stat = 5

                        req_text = f" + ⚡ 능력치 {req_stat}개" if req_stat > 0 else ""

                        st.markdown(f"""
                            <div style="background: #151515; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px;">
                                <h4>{item['name']}</h4>
                                <p style="color: #ccc; font-size: 13px; margin: 5px 0;">{item['desc']}</p>
                                <p style="color: #FF2222; font-weight: bold; margin: 5px 0;">소모 재화: {item['cost']} C{req_text}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if is_owned:
                            st.button("보유 중 ✅", key=f"owned_{item['id']}", disabled=True, use_container_width=True)
                        elif not can_buy:
                            st.button("잠김 🔒 (이전 단계 필요)", key=f"lock_{item['id']}", disabled=True, use_container_width=True)
                        else:
                            if st.button("구매하기 💳", key=f"buy_{item['id']}", use_container_width=True):
                                success, msg = purchase_item_db(member['id'], target_gear_list, item['id'], item['cost'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

            st.markdown("---")
            st.subheader("🎒 내 장비 인벤토리")
            if my_items:
                for mi in my_items:
                    match_item = next((item for item in all_possible_shop_items if item['id'] == mi), None)
                    if match_item:
                        st.markdown(f"- ✅ **{match_item['name']}**")
            else:
                st.info("보유한 아이템이 없습니다.")

        with sub_tab3:
            st.subheader("✏️ 한줄소개 수정")
            with st.form("bio_form"):
                new_bio_input = st.text_input("한줄소개 입력", value=member.get('bio', ''))
                bio_submit = st.form_submit_button("저장하기", use_container_width=True)
                if bio_submit:
                    update_member_bio(member['id'], new_bio_input)
                    st.success("업데이트되었습니다!")
                    st.rerun()

    elif selected_main_tab == "🎷 합주":
        st.title("🎷 HERTZ 팀 합주실")
        st.caption("팀 조합에서 생성된 팀을 선택하여 합주 세션을 개설하고 진행하세요! 30분당 모든 팀원에게 ⚡ 합주 능력치 1개가 적립됩니다.")

        active_ens = get_active_ensemble()

        if active_ens and active_ens['is_active'] == 1:
            st.markdown(f"""
                <div style="background: #2b0505; border: 2px solid #FF2222; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: #00FF66;">🔴 현재 합주 진행 중: {active_ens['name']}</h3>
                    <p style="margin: 5px 0 0 0; color: #ccc;">배정 팀: <b>{active_ens['team_name']}</b></p>
                </div>
            """, unsafe_allow_html=True)

            if st.button("⏹️ 현재 합주 종료 및 능력치 정산", type="primary", use_container_width=True):
                earned_stat, m_count = stop_ensemble_db(active_ens['id'])
                st.success(f"🎉 합주가 종료되었습니다! 팀원 {m_count}명 전원에게 합주 능력치 **+{earned_stat}개**가 지급되었습니다.")
                st.rerun()

        st.markdown("---")
        st.subheader("➕ 새 합주 개설하기")

        distinct_teams = get_all_distinct_teams()

        if not distinct_teams:
            st.warning("⚠️ 선택 가능한 팀이 없습니다. 먼저 '🎪 공연 관리' 또는 '🤝 팀 조합' 탭에서 팀을 등록해주세요.")
        else:
            team_options = [f"{t['team_name']} ({t['perf_title']})" for t in distinct_teams]
            
            with st.form("create_ensemble_form"):
                ens_title = st.text_input("합주 이름 (예: 정기공연 1팀 합주, 주말 연습 등)")
                selected_team_str = st.selectbox("합주할 팀 선택", team_options)
                
                submit_ens = st.form_submit_button("합주 세션 등록하기", use_container_width=True)

                if submit_ens:
                    if ens_title.strip():
                        target_team_name = selected_team_str.split(" (")[0]
                        team_mems = get_members_by_team(target_team_name)
                        
                        if not team_mems:
                            st.error("선택한 팀에 소속된 부원이 없습니다.")
                        else:
                            m_ids = [m['id'] for m in team_mems]
                            create_ensemble(ens_title.strip(), target_team_name, m_ids)
                            st.success(f"합주 '{ens_title.strip()}' 세션이 새로 생성되었습니다!")
                            st.rerun()
                    else:
                        st.warning("합주 이름을 입력해주세요.")

        st.markdown("---")
        st.subheader("📋 개설된 합주 목록")
        ensembles = get_all_ensembles()

        if not ensembles:
            st.info("개설된 합주 목록이 없습니다.")
        else:
            for e in ensembles:
                with st.container():
                    col_e1, col_e2 = st.columns([3, 1])
                    with col_e1:
                        status_str = "🔴 [진행 중]" if e['is_active'] == 1 else "⚪ [대기 중]"
                        st.markdown(f"### {e['name']} {status_str}")
                        st.caption(f"배정 팀: **{e['team_name']}** | 생성일: {e['created_at']}")
                    with col_e2:
                        if e['is_active'] == 0:
                            if st.button("▶️ 합주 시작", key=f"start_ens_{e['id']}", use_container_width=True, type="primary"):
                                start_ensemble_db(e['id'])
                                st.success("합주가 시작되었습니다! 연습실&상점 탭 무대에서 팀원 전체 연주 모습을 확인할 수 있습니다.")
                                st.rerun()
                        else:
                            st.button("🔴 진행 중", key=f"active_ens_btn_{e['id']}", disabled=True, use_container_width=True)
                    st.markdown("---")

    elif selected_main_tab == "👥 부원 목록 및 아바타":
        st.title("👥 HERTZ 전체 부원 및 아바타 갤러리")
        filter_opt = st.radio("조회 범위 선택", ["활동 중인 부원만", "전체 명단"], horizontal=True)
        
        display_members = get_all_active_members() if filter_opt == "활동 중인 부원만" else get_all_members_including_inactive()

        for m in display_members:
            m_items = [i.strip() for i in (m.get('inventory') or "").split(",") if i.strip()]
            m_time = m.get('practice_minutes', 0)
            m_title = get_title_by_practice_time(m_time)
            m_bio = m.get('bio') or "안녕하세요!"
            m_stats = m.get('ensemble_stats', 0)
            
            session_emojis = {"기타": "🎸💥", "베이스": "🎸🔥", "보컬": "🎤✨", "드럼": "🥁💥", "키보드": "🎹🎶"}
            m_icon = session_emojis.get(m.get('session'), "🎶")

            m_gear_names = []
            for mi in m_items:
                match_obj = next((item for item in all_possible_shop_items if item['id'] == mi), None)
                if match_obj: m_gear_names.append(match_obj['name'])
            m_gear_str = " | ".join(m_gear_names) if m_gear_names else "기본 장비 착용 중"

            status_badge = "🟢 활동 중" if m.get('is_active') == 1 else "⚪ [탈퇴/보존]"
            admin_icon = "👑 " if m.get('is_admin') == 1 else ""

            st.markdown(f"""
                <div style="background: #141414; padding: 20px; border-radius: 10px; border: 1px solid #333; margin-bottom: 15px;">
                    <h3 style="margin-top:0;">{admin_icon}{m['name']} <span style="font-size: 14px; color: #888;">({m['department']} / {m['student_id']}학번 / {m['session']})</span> {status_badge}</h3>
                    <p style="color: #ff6666; font-size: 14px; margin: 5px 0;"><b>칭호:</b> {m_title} | 연습시간: <b>{m_time}분</b> | ⚡ 합주 능력치: <b>{m_stats}개</b></p>
                    <p style="font-style: italic; color: #ddd; background: #202020; padding: 6px 12px; border-radius: 6px; display: inline-block; margin: 5px 0;">"{m_bio}"</p>
                    <p style="font-size: 32px; margin: 10px 0;">{m_icon}</p>
                    <p style="color: #aaa; font-size: 13px; margin: 0;"><b>착용 장비:</b> {m_gear_str}</p>
                </div>
            """, unsafe_allow_html=True)

    elif selected_main_tab == "🤝 팀 조합":
        st.title("🤝 밴드 팀 조합 관리")
        team_sub1, team_sub2 = st.tabs(["🎲 랜덤 팀 균형 조합", "✍️ 임원진 직접 팀 편성"])
        all_active_list = get_all_active_members()

        with team_sub1:
            st.subheader("세션 균형 무작위 팀 배치")
            num_teams_rand = st.number_input("생성할 팀 수", min_value=1, max_value=10, value=2, key="rand_team_count")
            
            if st.button("🎲 세션 균형 자동 배분 실행", type="primary"):
                import random
                session_dict = {}
                for m in all_active_list:
                    s = m['session']
                    if s not in session_dict: session_dict[s] = []
                    session_dict[s].append(m)
                
                for s in session_dict: random.shuffle(session_dict[s])
                teams_result = {f"팀 {i+1}": [] for i in range(num_teams_rand)}
                
                for s, members in session_dict.items():
                    for idx, m in enumerate(members):
                        teams_result[f"팀 {(idx % num_teams_rand) + 1}"].append(m)
                
                st.success("팀 편성이 완료되었습니다!")
                for t_name, members in teams_result.items():
                    st.markdown(f"### 🎸 {t_name}")
                    for m in members:
                        st.write(f"- {m['name']} (`{m['session']}` / {m['department']})")
                    st.markdown("---")

        with team_sub2:
            st.subheader("임원진 직접 팀 지정 편성")
            if member['is_admin'] == 0:
                st.warning("⚠️ 직접 팀 편성은 임원진 권한 부원만 저장할 수 있습니다.")

            manual_num_teams = st.number_input("편성할 팀 수 설정", min_value=1, max_value=10, value=2, key="manual_team_count")
            for t_idx in range(manual_num_teams):
                t_name = f"팀 {t_idx + 1}"
                with st.expander(f"📌 {t_name} 멤버 구성"):
                    for m in all_active_list:
                        st.checkbox(f"{m['name']} ({m['session']} / {m['department']})", key=f"t_{t_idx}_m_{m['id']}")

    elif selected_main_tab == "🎪 공연 관리":
        st.title("🎪 공연별 팀 세팅 관리")
        performances = get_all_performances()

        with st.expander("➕ 새 공연 생성하기 (임원진 전용)"):
            with st.form("new_perf_form"):
                perf_title_input = st.text_input("공연 이름")
                perf_submit = st.form_submit_button("공연 추가")
                if perf_submit:
                    if perf_title_input.strip() and member['is_admin'] == 1:
                        create_performance(perf_title_input.strip())
                        st.success(f"'{perf_title_input.strip()}' 공연이 생성되었습니다!")
                        st.rerun()

        st.markdown("---")
        if not performances:
            st.info("등록된 공연이 없습니다.")
        else:
            all_active_list = get_all_active_members()
            for p in performances:
                with st.container():
                    st.markdown(f"### 🎪 {p['title']}")
                    p_teams_rows = get_performance_teams(p['id'])
                    
                    perf_teams_dict = {}
                    for row in p_teams_rows:
                        tname = row['team_name']
                        if tname not in perf_teams_dict: perf_teams_dict[tname] = []
                        perf_teams_dict[tname].append(row)

                    if perf_teams_dict:
                        for tname, members in perf_teams_dict.items():
                            st.markdown(f"**🔹 {tname}**")
                            for m in members:
                                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;- {m['name']} (`{m['session']}` / {m['department']})")

                    if member['is_admin'] == 1:
                        with st.expander(f"⚙️ '{p['title']}' 팀 편집 및 배정"):
                            edit_num_teams = st.number_input("팀 수", min_value=1, max_value=5, value=2, key=f"edit_perf_cnt_{p['id']}")
                            current_perf_team_dict = {}
                            for et_idx in range(edit_num_teams):
                                et_name = f"팀 {et_idx + 1}"
                                et_selected_ids = []
                                for m in all_active_list:
                                    is_already_in = any(row['team_name'] == et_name and row['member_id'] == m['id'] for row in p_teams_rows)
                                    if st.checkbox(f"{m['name']} ({m['session']})", value=is_already_in, key=f"perf_{p['id']}_t_{et_idx}_m_{m['id']}"):
                                        et_selected_ids.append(m['id'])
                                current_perf_team_dict[et_name] = et_selected_ids

                            if st.button(f"💾 팀 구성 저장", key=f"save_perf_btn_{p['id']}"):
                                save_performance_teams(p['id'], current_perf_team_dict)
                                st.success("저장되었습니다!")
                                st.rerun()

                        if st.button(f"🗑️ 공연 삭제", key=f"del_perf_{p['id']}"):
                            delete_performance(p['id'])
                            st.rerun()
                    st.markdown("---")

    elif selected_main_tab == "⚙️ 임원 관리" and member['is_admin'] == 1:
        st.title("⚙️ HERTZ 멤버 및 권한 관리 (임원 전용)")
        tab_add, tab_manage = st.tabs(["➕ 부원 추가", "📋 부원 목록 관리"])
        
        with tab_add:
            with st.form("add_member_form"):
                new_name = st.text_input("이름")
                new_dept = st.text_input("학과")
                new_id = st.text_input("학번 두 자리")
                new_session = st.selectbox("세션", ["보컬", "기타", "베이스", "드럼", "키보드"], key="add_session")
                new_is_admin = st.checkbox("임원진 권한 부여")
                
                add_submit = st.form_submit_button("부원 추가하기", use_container_width=True)
                if add_submit and new_name.strip() and new_dept.strip() and new_id.strip():
                    success, msg = add_member(new_name, new_dept, new_id, new_session, new_is_admin)
                    if success:
                        st.success(msg)
                        st.rerun()

        with tab_manage:
            all_members_full = get_all_members_including_inactive()
            for m in all_members_full:
                with st.container():
                    col_info, col_admin, col_active = st.columns([2.5, 1.2, 1.3])
                    with col_info:
                        st.markdown(f"**{m['name']}** ({m['department']} / {m['student_id']}학번 / `{m['session']}`)")
                    with col_admin:
                        new_admin = st.checkbox("임원진", value=bool(m['is_admin']), key=f"admin_chk_{m['id']}")
                        if new_admin != bool(m['is_admin']):
                            update_member_admin(m['id'], new_admin)
                            st.rerun()
                    with col_active:
                        new_active = st.checkbox("활동 중", value=bool(m['is_active']), key=f"active_chk_{m['id']}")
                        if new_active != bool(m['is_active']):
                            set_member_active_status(m['id'], new_active)
                            st.rerun()
                    st.markdown("---")
