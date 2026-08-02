import streamlit as st
import subprocess
import os
import shutil
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import time
import json
import random
from datetime import datetime
import imageio_ffmpeg
import pandas as pd
import streamlit as st

# 사이드바 상단에 도움말 섹션 구성
with st.sidebar:
    st.markdown("### 🛠️ HERTZ 시스템 메뉴")
    
    # 도움말 열기/닫기 (Expander 활용)
    with st.expander("📖 이용 가이드 & 매뉴얼", expanded=False):
        st.markdown("""
        **스마트폰에서 어플처럼 사용할 수 있습니다!!**
        - ios : 브라우저 하단 공유버튼 > 홈 화면 추가
        - Android : 브라우저 우측 상단 메뉴 > 앱 설치 또는 홈 화면 추가
        
        **1. 🎵 내 작업실**
        - 음원을 업로드하여 악기별로 세션을 분리하고 연습하세요. 저장도 된답니다.
        
        **2. 🎮 연습실 & 상점**
        - 타이머를 켜고 연습하면 크레딧이 적립됩니다. 또한 누적 연습 시간에 따라 칭호가 변합니다.\n
        - 크레딧은 round(30+관객수*0.05)C/연습 1min 으로 적립됩니다.\n
        - 관중 수는 장비 가치에 따라 늘어납니다.\n
        - 합주 중에도 개인 연습을 할 수 있습니다. 또한 연습실에서도 합주를 종료할 수 있습니다.\n
        - 상점에서는 크레딧과 합주 능력치(1ea/합주 30min)를 통해 장비를 구매할 수 있습니다.\n
        - 연습이 끝나면 꼭 연습을 종료해주세요!

        **3. 🎷 합주**
        - 팁 조합에서 생성된 팀으로 합주를 진행합니다.\n
        - 합주는 여러 팀이 동시에 진행할 수 있으나, 한 멤버가 두 팀에서 동시에 진행할 수는 없습니다.\n
        - 합주 중에는 모든 멤버가 무대 위에 올라갑니다. 야호!
        - 합주가 끝나면 꼭 합주를 종료해주세요!

        **4. 👥 부원 목록**
        - 활동 중인 부원 목록과 활동을 중단하거나, 탈퇴한 부원의 목록을 볼 수 있습니다.\n
        - 한 줄 소개와 장비로 자신의 프로필을 꾸밀 수 있습니다. 

        **5. 🤝 팀 조합**
        - 임원진은 팀 조합을 생성하고, 삭제할 수 있습니다. \n
        - 랜덤 팀 생성은 각 세션을 균형있게 배분해 조합합니다.\n
        - 임원진 직접 팀 편성은 5팀씩 생성할 수 있으며, 팀 이름과 멤버를 직접 정할 수 있습니다. 

        **6. 🎪 공연 관리**
        - 임원진은 공연을 추가하고, 팀 조합에서 만든 팀을 불러올 수 있습니다. 

        **7. 임원 관리**
        - 임원진은 멤버의 활동 상태 및 신규 멤버 추가가 가능합니다. 
        """)
        
    st.markdown("---") # 구분선
    
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
    ("김다혜", "화공생명에너지공학부", "26", "키보드", 0),
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

DEPARTMENT_LIST = sorted(list(set([item[1] for item in INITIAL_MEMBERS])))

COMMON_SHOP_ITEMS = {
    "모자": [
        {"id": "hat_1", "name": "🧢 기본 스냅백", "cost": 1000, "desc": "챙을 완전히 편 스냅백"},
        {"id": "hat_2", "name": "🎩 빈티지 페도라", "cost": 5000, "desc": "재즈와 인디 감성을 더해주는 페도라"},
        {"id": "hat_3", "name": "👑 락스타 실크 햇", "cost": 10000, "desc": "무대 위에서 눈에 띄는 화려한 모자"},
        {"id": "hat_4", "name": "🌟 다이아몬드 크라운", "cost": 20000, "desc": "왕관의 무게"}
    ],
    "옷": [
        {"id": "cloth_1", "name": "👕 무지 밴드 티셔츠", "cost": 1000, "desc": "교류/직류 라고 쓰여있다"},
        {"id": "cloth_2", "name": "🧥 데님 청자켓", "cost": 5000, "desc": "청춘과 록의 상징인 스타일리시한 청자켓"},
        {"id": "cloth_3", "name": "🔥 락스타 가죽 라이더 자켓", "cost": 10000, "desc": "그 시절 락스타들의 가죽 자켓"},
        {"id": "cloth_4", "name": "✨ HERTZ 바람막이", "cost": 20000, "desc": "교수님 착용 제품"}
    ],
    "신발": [
        {"id": "shoe_1", "name": "👟 편안한 단화 스니커즈", "cost": 1000, "desc": "연습실에서 신기 좋은 가벼운 스니커즈"},
        {"id": "shoe_2", "name": "🥾 컨버스 하이톱", "cost": 5000, "desc": "합주할 때 발목을 탄탄하게 잡아주는 하이탑"},
        {"id": "shoe_3", "name": "🥿 스터드 워커 부츠", "cost": 10000, "desc": "거친 매력을 더해주는 락커들의 부츠"},
        {"id": "shoe_4", "name": "💎 맨발의 청춘", "cost": 20000, "desc": "근본"}
    ],
    "장신구": [
        {"id": "acc_1", "name": "💍 써지컬 스틸 링", "cost": 1000, "desc": "심플하면서도 시크한 기본 반지"},
        {"id": "acc_2", "name": "⛓️ 메탈 체인 목걸이", "cost": 5000, "desc": "힙한 감성을 완성해주는 체인 목걸이"},
        {"id": "acc_3", "name": "🕶️ 메탈릭 선글라스", "cost": 10000, "desc": "김다니엘 접신"},
        {"id": "acc_4", "name": "💎 해골이 그려진 목걸이", "cost": 20000, "desc": "skrrr"}
    ],
    "MD": [
        {"id": "md_1", "name": "🎗️ HERTZ 기본 반다나", "cost": 1000, "desc": "땀을 닦거나 손목에 두르는 밴드 공식 MD"},
        {"id": "md_2", "name": "🧣 로고 자수 스포츠 타올", "cost": 5000, "desc": "격렬한 합주 후 땀 닦기 딱 좋은 타올"},
        {"id": "md_3", "name": "🎒 HERTZ 투어 백팩", "cost": 10000, "desc": "악보와 장비를 모두 담는 투어용 가방"},
        {"id": "md_4", "name": "🎟️ VIP 올패스 패스포트", "cost": 20000, "desc": "나도 하나만"}
    ]
}

SESSION_GEAR_ITEMS = {
    "기타": [
        {"id": "g_1", "name": "🎸 입문용 통기타", "cost": 3000, "desc": "처음 튜닝을 배우며 코드를 잡던 추억의 기타"},
        {"id": "g_2", "name": "🎸 칩슨 & 휀다", "cost": 7000, "desc": "좌휀우칩"},
        {"id": "g_3", "name": "🎸 깁슨 & 펜더", "cost": 15000, "desc": "좌펜우깁"},
        {"id": "g_4", "name": "🎸 커스텀샵", "cost":30000, "desc": "장인이 한 땀 한 땀 영혼을 갈아 넣은 세상에 단 하나뿐인 기타"}
    ],
    "베이스": [
        {"id": "b_1", "name": "🎸 입문용 4현 베이스", "cost": 3000, "desc": "묵직한 저음의 세계로 입문하게 만드는 베이스"},
        {"id": "b_2", "name": "🎸 그루브한 베이스", "cost": 7000, "desc": "밴드의 든든한 뼈대를 받쳐주는 단단한 사운드"},
        {"id": "b_3", "name": "🎸 베이스 붐을 불러일으키는 베이스", "cost": 15000, "desc": "특유의 펀치감과 개성 넘치는 로큰롤 베이스"},
        {"id": "b_4", "name": "🎸 커스텀샵 액티브 5현 베이스", "cost": 30000, "desc": "드디어 소리가 들려..."}
    ],
    "보컬": [
        {"id": "v_1", "name": "🎤 가성비 다이나믹 마이크", "cost": 3000, "desc": "전 세계 합주실과 라이브 클럽의 국룰 마이크"},
        {"id": "v_2", "name": "🎤 무선 스테이지 마이크", "cost": 7000, "desc": "무대 위를 자유롭게 누비며 관객을 사로잡는 마이크"},
        {"id": "v_3", "name": "🎤 진공관 마이크", "cost": 15000, "desc": "숨소리 하나까지 예술로 만드는 최고급 스튜디오 마이크"},
        {"id": "v_4", "name": "🎤 커스텀 다이아몬드 스튜디오 마이크", "cost": 30000, "desc": "보컬리스트의 위엄을 상징하는 보석 박힌 마이크"}
    ],
    "드럼": [
        {"id": "d_1", "name": "🥁 연습용 스틱 & 패드 세트", "cost": 3000, "desc": "끊임없이 루디먼트를 연습하게 만드는 필수품"},
        {"id": "d_2", "name": "🥁 북 & 장구", "cost": 7000, "desc": "코리안 트래디셔널 드럼"},
        {"id": "d_3", "name": "🥁 그레치 & 타마", "cost": 15000, "desc": "프로 드러머들이 사랑하는 영롱한 타악기 브랜드"},
        {"id": "d_4", "name": "🥁 커스텀 풀 메탈 킷트", "cost": 30000, "desc": "우혁아 여기 더블페달 있다"}
    ],
    "키보드": [
        {"id": "k_1", "name": "🎹 61건반 가성비 신디사이저", "cost": 3000, "desc": "가볍게 들고 다니며 피아노와 패드 소리를 내는 건반"},
        {"id": "k_2", "name": "🎹 모티프 / 일렉트로", "cost": 7000, "desc": "합주실 무대를 꽉 채우는 따뜻한 건반 사운드"},
        {"id": "k_3", "name": "🎹 스테이지 레드 피아노", "cost": 15000, "desc": "건반 연주자들의 로망, 무대 위 강렬한 레드 감성"},
        {"id": "k_4", "name": "🎹 기아노", "cost": 30000, "desc": "건반도 프론트맨 할 수 있어"}
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
    conn = psycopg2.connect(st.secrets["DB_URL"])
    return conn

def init_db():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                student_id TEXT NOT NULL,
                session TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 0,
                inventory TEXT DEFAULT '',
                practice_minutes INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                bio TEXT DEFAULT '안녕하세요! 열심히 하겠습니다!',
                ensemble_stats INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_teams (
                id SERIAL PRIMARY KEY,
                team_name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS saved_team_members (
                id SERIAL PRIMARY KEY,
                team_id INTEGER NOT NULL REFERENCES saved_teams(id) ON DELETE CASCADE,
                member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                member_id INTEGER NOT NULL REFERENCES members(id),
                song_title TEXT NOT NULL,
                separated_dir TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performances (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_teams_map (
                id SERIAL PRIMARY KEY,
                performance_id INTEGER NOT NULL REFERENCES performances(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES saved_teams(id) ON DELETE CASCADE
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ensembles (
                id SERIAL PRIMARY KEY,
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
                    VALUES (%s, %s, %s, %s, %s, 0, '', 0, 1, '안녕하세요! 열심히 하겠습니다!', 0)
                ''', item)
            
        conn.commit()
        cursor.close()
    except Exception as e:
        st.error(f"데이터베이스 초기화 오류: {e}")
    finally:
        if conn is not None:
            conn.close()

@st.cache_resource
def run_init_db_once():
    init_db()
# --- Members Handlers ---

def verify_member(name, department, student_id, session):
    conn = get_db_connection()
    # 커서 생성 시 RealDictCursor를 반드시 지정해야 합니다.
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute('''
        SELECT * FROM members 
        WHERE name = %s AND department = %s AND student_id = %s AND session = %s AND is_active = 1
    ''', (name.strip(), department.strip(), str(student_id).strip(), session))
    
    member = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return dict(member) if member else None

def get_member_fresh(member_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM members WHERE id = %s", (member_id,))
    member = cursor.fetchone()
    conn.close()
    return dict(member) if member else None

def get_all_active_members():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM members WHERE is_active = 1 ORDER BY name ASC")
    members = cursor.fetchall()
    conn.close()
    return [dict(m) for m in members]

def get_all_members_including_inactive():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM members ORDER BY is_active DESC, name ASC")
    members = cursor.fetchall()
    conn.close()
    return [dict(m) for m in members]

def add_member(name, department, student_id, session, is_admin):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute('''
            INSERT INTO members (name, department, student_id, session, is_admin, credits, inventory, practice_minutes, is_active, bio, ensemble_stats)
            VALUES (%s, %s, %s, %s, %s, 0, '', 0, 1, '안녕하세요! 열심히 하겠습니다!', 0)
        ''', (name.strip(), department.strip(), str(student_id).strip(), session, 1 if is_admin else 0))
        conn.commit()
        return True, "부원이 성공적으로 추가되었습니다."
    except Exception as e:
        return False, f"오류 발생: {e}"
    finally:
        conn.close()

def update_member_admin(member_id, is_admin):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("UPDATE members SET is_admin = %s WHERE id = %s", (1 if is_admin else 0, member_id))
    conn.commit()
    conn.close()

def set_member_active_status(member_id, is_active):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("UPDATE members SET is_active = %s WHERE id = %s", (1 if is_active else 0, member_id))
    conn.commit()
    conn.close()

def update_member_bio(member_id, bio):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("UPDATE members SET bio = %s WHERE id = %s", (bio.strip(), member_id))
    conn.commit()
    conn.close()

def add_practice_time_and_credits(member_id, minutes, credits):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("UPDATE members SET practice_minutes = practice_minutes + %s, credits = credits + %s WHERE id = %s", (minutes, credits, member_id))
    conn.commit()
    conn.close()

def purchase_item_db(member_id, category_items, target_item_id, cost):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT credits, inventory, ensemble_stats FROM members WHERE id = %s", (member_id,))
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

    req_ensemble_stat = 0
    if target_idx == 1 : req_ensemble_stat = 1
    elif target_idx == 2 : req_ensemble_stat = 3
    elif target_idx == 3 : req_ensemble_stat = 5

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
    
    cursor.execute("UPDATE members SET credits = %s, inventory = %s, ensemble_stats = %s WHERE id = %s", 
                   (new_credits, new_inventory, new_ensemble_stats, member_id))
    conn.commit()
    conn.close()
    return True, f"구매가 완료되었습니다! ({cost} C 차감, ⚡ 합주 능력치 {req_ensemble_stat}개 차감)"

# --- Projects Handlers ---

def save_project(member_id, song_title, separated_dir):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO projects (member_id, song_title, separated_dir, created_at) VALUES (%s, %s, %s, %s)",
        (member_id, song_title, separated_dir, now)
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id

def get_member_projects(member_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM projects WHERE member_id = %s ORDER BY id DESC", (member_id,))
    projects = cursor.fetchall()
    conn.close()
    return [dict(p) for p in projects]

def delete_project(project_id, member_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT separated_dir FROM projects WHERE id = %s AND member_id = %s", (project_id, member_id))
    row = cursor.fetchone()
    if row and row['separated_dir'] and os.path.exists(row['separated_dir']):
        shutil.rmtree(row['separated_dir'], ignore_errors=True)
        
    cursor.execute("DELETE FROM projects WHERE id = %s AND member_id = %s", (project_id, member_id))
    conn.commit()
    conn.close()

# --- Saved Teams Handlers ---

def save_custom_team(team_name, member_ids):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO saved_teams (team_name, created_at) VALUES (%s, %s)", (team_name.strip(), now))
        team_id = cursor.lastrowid
        for m_id in member_ids:
            cursor.execute("INSERT INTO saved_team_members (team_id, member_id) VALUES (%s, %s)", (team_id, m_id))
        conn.commit()
        return True, "팀이 성공적으로 저장되었습니다."
    except sqlite3.IntegrityError:
        return False, f"이미 존재하는 팀 이름입니다: {team_name}"
    except Exception as e:
        return False, f"오류 발생: {e}"
    finally:
        conn.close()

def get_all_saved_teams():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM saved_teams ORDER BY id DESC")
    teams = cursor.fetchall()
    
    result = []
    for t in teams:
        cursor.execute('''
            SELECT m.id, m.name, m.department, m.session 
            FROM saved_team_members stm
            JOIN members m ON stm.member_id = m.id
            WHERE stm.team_id = %s
        ''', (t['id'],))
        members = cursor.fetchall()
        
        session_order = {"보컬": 1, "기타": 2, "베이스": 3, "드럼": 4, "키보드": 5}
        sorted_members = sorted([dict(m) for m in members], key=lambda x: (session_order.get(x['session'], 6), x['name']))
        
        result.append({
            "id": t['id'],
            "team_name": t['team_name'],
            "created_at": t['created_at'],
            "members": sorted_members
        })
    conn.close()
    return result

def delete_saved_team(team_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("DELETE FROM saved_teams WHERE id = %s", (team_id,))
    conn.commit()
    conn.close()

# --- Performances Handlers ---

def get_all_performances():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM performances ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_performance(title):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO performances (title, created_at) VALUES (%s, %s)", (title, now))
    perf_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return perf_id

def delete_performance(perf_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("DELETE FROM performances WHERE id = %s", (perf_id,))
    conn.commit()
    conn.close()

def get_performance_teams_new(perf_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute('''
        SELECT st.id, st.team_name 
        FROM performance_teams_map ptm
        JOIN saved_teams st ON ptm.team_id = st.id
        WHERE ptm.performance_id = %s
    ''', (perf_id,))
    teams = cursor.fetchall()
    
    result = []
    session_order = {"보컬": 1, "기타": 2, "베이스": 3, "드럼": 4, "키보드": 5}
    for t in teams:
        cursor.execute('''
            SELECT m.id, m.name, m.department, m.session 
            FROM saved_team_members stm
            JOIN members m ON stm.member_id = m.id
            WHERE stm.team_id = %s
        ''', (t['id'],))
        members = cursor.fetchall()
        sorted_members = sorted([dict(m) for m in members], key=lambda x: (session_order.get(x['session'], 6), x['name']))
        
        result.append({
            "team_id": t['id'],
            "team_name": t['team_name'],
            "members": sorted_members
        })
    conn.close()
    return result

def set_performance_teams(perf_id, team_ids):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("DELETE FROM performance_teams_map WHERE performance_id = %s", (perf_id,))
    for tid in team_ids:
        cursor.execute("INSERT INTO performance_teams_map (performance_id, team_id) VALUES (%s, %s)", (perf_id, tid))
    conn.commit()
    conn.close()

# --- Ensembles Handlers ---

def create_ensemble(name, team_name, member_ids):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    member_ids_str = ",".join(map(str, member_ids))
    cursor.execute('''
        INSERT INTO ensembles (name, team_name, member_ids, is_active, start_time, created_at)
        VALUES (%s, %s, %s, 0, 0, %s)
    ''', (name, team_name, member_ids_str, now))
    conn.commit()
    conn.close()

def get_all_ensembles():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM ensembles ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_ensemble_db(ensemble_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("DELETE FROM ensembles WHERE id = %s", (ensemble_id,))
    conn.commit()
    conn.close()

def start_ensemble_db(ensemble_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    now_ts = time.time()
    cursor.execute("UPDATE ensembles SET is_active = 1, start_time = %s WHERE id = %s", (now_ts, ensemble_id))
    conn.commit()
    conn.close()

def stop_ensemble_db(ensemble_id):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM ensembles WHERE id = %s", (ensemble_id,))
    ens = cursor.fetchone()
    
    if ens and ens['is_active'] == 1:
        start_t = ens['start_time']
        elapsed_sec = time.time() - start_t
        stats_earned = int(elapsed_sec // 1800)
        
        member_ids = [int(x.strip()) for x in ens['member_ids'].split(",") if x.strip()]
        
        if stats_earned > 0 and member_ids:
            for m_id in member_ids:
                cursor.execute("UPDATE members SET ensemble_stats = ensemble_stats + %s WHERE id = %s", (stats_earned, m_id))
                
        cursor.execute("UPDATE ensembles SET is_active = 0, start_time = 0 WHERE id = %s", (ensemble_id,))
        conn.commit()
        conn.close()
        return stats_earned, len(member_ids)
    
    conn.close()
    return 0, 0

def get_active_ensembles():
    """현재 활성화된(is_active == 1) 모든 합주 목록을 반환합니다."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM ensembles WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    
    active_list = []
    for row in rows:
        try:
            ens_id = row['id']
            name = row['name']
            team_name = row['team_name']
            member_ids = row['member_ids']
            is_active = row['is_active']
            start_time = row['start_time'] if 'start_time' in row.keys() else 0
        except (TypeError, AttributeError, KeyError):
            ens_id = row[0]
            name = row[1]
            team_name = row[2]
            member_ids = row[3]
            is_active = row[4]
            start_time = row[5] if len(row) > 5 else 0

        active_list.append({
            'id': ens_id,
            'name': name,
            'team_name': team_name,
            'member_ids': member_ids,
            'is_active': is_active,
            'start_time': start_time
        })
    return active_list

run_init_db_once()

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

# --- 세션 및 상태 관리 ---
if 'member' not in st.session_state or st.session_state['member'] is None:
    if "auto_login_id" in st.query_params:
        auto_uid = int(st.query_params["auto_login_id"])
        member_data = get_member_fresh(auto_uid)
        if member_data and member_data['is_active'] == 1:
            st.session_state['member'] = member_data
            st.session_state['view'] = 'dashboard'
    else:
        st.session_state['member'] = None

if 'view' not in st.session_state: st.session_state['view'] = 'dashboard'
if 'current_project' not in st.session_state: st.session_state['current_project'] = None
if 'is_practicing' not in st.session_state: st.session_state['is_practicing'] = False
if 'practice_start_time' not in st.session_state: st.session_state['practice_start_time'] = None

def handle_logout_or_stop():
    if st.session_state.get('is_practicing') and st.session_state.get('practice_start_time') and st.session_state.get('member'):
        elapsed_seconds = time.time() - st.session_state['practice_start_time']
        elapsed_minutes = int(elapsed_seconds // 60)
        if elapsed_minutes >= 1:
            earned = elapsed_minutes * 30
            add_practice_time_and_credits(st.session_state['member']['id'], elapsed_minutes, earned)
    st.session_state['is_practicing'] = False
    st.session_state['practice_start_time'] = None

# --- 알림 팝업(Dialog) 관리 ---
@st.dialog("🎉 개인 연습 정산 완료")
def practice_result_dialog(elapsed_minutes, earned):
    st.write(f"- **연습 시간**: {elapsed_minutes}분")
    st.write(f"- **획득 크레딧**: +{earned:,} C")
    if st.button("확인"):
        st.session_state['is_practicing'] = False
        st.session_state['practice_start_time'] = None
        st.rerun()

@st.dialog("🎉 합주 정산 완료")
def ensemble_result_dialog(ens_name, m_count, earned):
    st.write(f"- **합주 세션**: {ens_name}")
    st.write(f"- **참여 인원**: {m_count}명")
    st.write(f"- **획득 능력치**: 팀원 전원 각 +{earned}개 지급 완료!")
    if st.button("확인"):
        st.rerun()


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
    st.subheader("⚡ HERTZ 부원 로그인")
    with st.form("login_form"):
        input_name = st.text_input("이름")
        input_dept = st.selectbox("학과", DEPARTMENT_LIST + ["기타"])
        input_id = st.text_input("학번 두 자리 (예: 21, 23, 25 등)")
        input_session = st.selectbox("세션", ["보컬", "기타", "베이스", "드럼", "키보드"])
        submit_btn = st.form_submit_button("인증 및 입장하기 🚀", use_container_width=True)
        
        if submit_btn:
            member_data = verify_member(input_name, input_dept, input_id, input_session)
            if member_data:
                st.session_state['member'] = member_data
                st.session_state['view'] = 'dashboard'
                st.query_params["auto_login_id"] = str(member_data['id'])
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
            if "auto_login_id" in st.query_params:
                del st.query_params["auto_login_id"]
            st.rerun()

    base_tabs = ["🎵 내 작업실", "🎮 연습실 & 상점", "🎷 합주", "👥 부원 목록", "🤝 팀 조합", "🎪 공연 관리"]
    if member['is_admin'] == 1: base_tabs.append("⚙️ 임원 관리")

    selected_main_tab = st.radio("상단 메인 메뉴", base_tabs, horizontal=True, label_visibility="collapsed")

    all_possible_shop_items = []
    for items in COMMON_SHOP_ITEMS.values(): all_possible_shop_items.extend(items)
    for s_items in SESSION_GEAR_ITEMS.values(): all_possible_shop_items.extend(s_items)

    if selected_main_tab == "🎵 내 작업실":
        if st.session_state['view'] == 'dashboard':
            st.title("📂 내 연습 작업물 목록")
            projects = get_member_projects(member['id'])
            
            if not projects: st.info("저장된 곡이 없습니다. 아래 버튼을 눌러 합주곡을 추가해보세요!")
            else:
                for p in projects:
                    col_info, col_btn, col_del = st.columns([4, 1.5, 1])
                    with col_info: st.markdown(f"### 🎵 {p['song_title']}\n등록일: {p['created_at']}")
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
            if st.button("⬅️ 목록으로 돌아가기"): st.session_state['view'] = 'dashboard'; st.rerun()
            st.title("➕ 새 합주곡 추가")
            uploaded_file = st.file_uploader("오디오 파일 업로드", type=["mp3", "wav"])
            if uploaded_file and st.button("🚀 시작"):
                file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                with st.spinner("처리중..."):
                    try:
                        separated_dir = separate_audio(file_path, uploaded_file.name)
                        song_title = os.path.splitext(uploaded_file.name)[0]
                        pid = save_project(member['id'], song_title, separated_dir)
                        st.session_state['current_project'] = {"id": pid, "song_title": song_title, "separated_dir": separated_dir}
                        st.session_state['view'] = 'project_detail'
                        st.rerun()
                    except Exception as e: st.error(str(e))
        
        elif st.session_state['view'] == 'project_detail':
            if st.button("⬅️ 목록으로 돌아가기"): st.session_state['view'] = 'dashboard'; st.rerun()
            proj = st.session_state['current_project']
            st.title(f"🎵 {proj['song_title']}")
            all_stems = ["guitar", "vocals", "drums", "bass", "piano", "other"]
            cols = st.columns(3)
            selected_stems = [stem for i, stem in enumerate(all_stems) if cols[i%3].checkbox(stem.capitalize(), value=(stem != "guitar"))]
            speed = st.slider("재생 속도", 0.5, 2.0, 1.0, 0.01)
            start_time, end_time = st.columns(2)
            s_t = start_time.number_input("시작 초", 0, 0)
            e_t = end_time.number_input("종료 초", 0, 0)
            
            if selected_stems:
                with st.spinner("믹싱 중..."):
                    mix_path = process_mix(proj['separated_dir'], selected_stems, speed, s_t, e_t)
                if mix_path:
                    st.audio(mix_path)
                    with open(mix_path, "rb") as f: st.download_button("다운로드", f, file_name="mix.wav")

    elif selected_main_tab == "🎮 연습실 & 상점":
        st.title("🎮 HERTZ 연습실 & 상점")
        st.caption("실시간 타이머로 연습을 기록하고 크레딧을 모아 장비와 아이템을 구매해보세요!")

        sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎸 연습실 & 무대", "🛍️ 상점 & 인벤토리", "✏️ 내 한줄소개 설정"])

        inventory_str = member['inventory'] or ""
        my_items = [i.strip() for i in inventory_str.split(",") if i.strip()]
        user_practice_time = member['practice_minutes']
        user_title = get_title_by_practice_time(user_practice_time)

        active_ensembles = get_active_ensembles()

        with sub_tab1:
            st.subheader("연습실 & 무대")

            my_active_ensemble = None
            for ens in active_ensembles:
                ens_m_ids = [int(x.strip()) for x in ens['member_ids'].split(",") if x.strip()]
                if member['id'] in ens_m_ids and ens.get('is_active') == 1:
                    my_active_ensemble = ens
                    break

            render_members = []
            is_ensemble_mode = (my_active_ensemble is not None)

            if is_ensemble_mode:
                ens_m_ids = [int(x.strip()) for x in my_active_ensemble['member_ids'].split(",") if x.strip()]
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

            gear_text = " | ".join(equipped_display) if equipped_display else "합주실 장비 대여 중"
            audience_count = max(3, min(120, 3 + (total_credits // 200)))

            is_anim_playing = st.session_state['is_practicing'] or is_ensemble_mode

            st.write(f"**칭호:** {user_title} | **세션:** {member['session']} | **누적 연습 시간:** {user_practice_time}분 | **⚡ 합주 능력치:** {member.get('ensemble_stats', 0)}개")
            st.write(f"**착용 장비:** {gear_text} | **장비 총 가치:** {total_credits:,} C | **관중 수:** {audience_count}명")

            # Javascript로 타이머 계산을 넘기기 위한 변수들
            members_json = json.dumps(render_members, ensure_ascii=False)
            is_playing_str = "true" if is_anim_playing else "false"
            is_ensemble_mode_str = "true" if is_ensemble_mode else "false"
            is_practicing_str = "true" if (st.session_state['is_practicing'] and st.session_state['practice_start_time']) else "false"
            
            start_ts = 0
            ens_name = ""
            if is_ensemble_mode:
                start_ts = my_active_ensemble['start_time']
                ens_name = my_active_ensemble['name']
            elif st.session_state['is_practicing'] and st.session_state['practice_start_time']:
                start_ts = st.session_state['practice_start_time']
                
            stage_html = f"""
            <div style="text-align: center; background-color: #0d0d15; padding: 12px; border-radius: 10px; font-family: sans-serif;">
                <div id="timerStatus" style="color: #00FF66; font-weight: bold; font-size: 15px; margin-bottom: 8px;">타이머 상태 동기화 중...</div>
                <canvas id="stageCanvas" width="620" height="260" style="border:2px solid #2a2a3d; image-rendering: pixelated; border-radius: 8px;"></canvas>
            </div>

            <script>
            const canvas = document.getElementById('stageCanvas');
            const ctx = canvas.getContext('2d');
            
            const isPlaying = {is_playing_str};
            const audienceCount = {audience_count};
            const bandMembers = {members_json};
            
            const isEnsemble = {is_ensemble_mode_str};
            const isPracticing = {is_practicing_str};
            const startTimeTs = {start_ts};
            const ensName = "{ens_name}";

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
            
            function updateTimer() {{
                const statusDiv = document.getElementById('timerStatus');
                if (!statusDiv) return;
                
                if (isEnsemble && startTimeTs > 0) {{
                    const elapsed = Math.floor(Date.now() / 1000 - startTimeTs);
                    const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
                    const secs = String(elapsed % 60).padStart(2, '0');
                    statusDiv.innerText = `🎷 [소속 팀 합주 진행 중] '${{ensName}}': ${{mins}}분 ${{secs}}초 (30분당 능력치 1개 적립)`;
                }} else if (isPracticing && startTimeTs > 0) {{
                    const elapsed = Math.floor(Date.now() / 1000 - startTimeTs);
                    const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
                    const secs = String(elapsed % 60).padStart(2, '0');
                    statusDiv.innerText = `⏱️ [개인 연습 진행 중]: ${{mins}}분 ${{secs}}초`;
                }} else {{
                    statusDiv.innerText = "[타이머 대기 중 - 연습 시작 또는 합주 탭에서 합주를 시작하세요]";
                }}
            }}

            function render() {{
                updateTimer();
                
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

            st.iframe(src=stage_html, height=310)

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
                            st.rerun()
                        else:
                            bonus_credits = audience_count * 0.05
                            earned = int(round((elapsed_minutes * 30) + bonus_credits))

                            add_practice_time_and_credits(member['id'], elapsed_minutes, earned)
                            practice_result_dialog(elapsed_minutes, earned)
                else:
                    st.button("⏹️ 정지됨", disabled=True, use_container_width=True)

        with sub_tab2:
            st.subheader("🛍️ 밴드 장비 및 패션 상점")
            st.markdown(f"보유 크레딧: **{member['credits']} C** | 보유 합주 능력치: **⚡ {member.get('ensemble_stats', 0)}개**")
            st.info("💡 **상점 구매 조건:** 다음 단계 아이템을 얻기 위해선 이전 단계 아이템을 구매해야 하며, 크레딧과 합주 능력치는 연습과 합주로 얻을 수 있습니다. *'일단! 펜더를 사!'*")
            
            shop_tabs = st.tabs(["🧢 모자", "옷", "👟 신발", "💍 장신구", "🎗️ MD", "🎸 MULE"])
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

                            req_ensemble_stat = 0
                            if item['cost'] in (5000, 7000): req_ensemble_stat = 1
                            elif item['cost'] in (10000, 15000): req_ensemble_stat = 3
                            elif item['cost'] in (20000, 30000) : req_ensemble_stat = 5

                            req_text = f" + ⚡ 능력치 {req_ensemble_stat}개" if req_ensemble_stat > 0 else ""

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
                st.markdown("### 🎸 MULE")
                selected_gear_session = st.selectbox("조회할 악기 세션 선택", ["기타", "베이스", "보컬", "드럼", "키보드"])
                target_gear_list = SESSION_GEAR_ITEMS[selected_gear_session]
                
                g_cols = st.columns(2)
                for i, item in enumerate(target_gear_list):
                    with g_cols[i % 2]:
                        is_owned = item['id'] in my_items
                        can_buy = True
                        if i > 0 and target_gear_list[i - 1]['id'] not in my_items:
                            can_buy = False

                        req_ensemble_stat = 0
                        if item['cost'] in (5000, 7000): req_ensemble_stat = 1
                        elif item['cost'] in (10000, 15000): req_ensemble_stat = 3
                        elif item['cost'] in (20000, 30000) : req_ensemble_stat = 5


                        req_text = f" + ⚡ 능력치 {req_ensemble_stat}개" if req_ensemble_stat > 0 else ""

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
        
        active_ensembles = get_active_ensembles()

        st.subheader("➕ 새 합주 개설하기")

        saved_teams = get_all_saved_teams()
        
        if not saved_teams:
            st.warning("⚠️ 저장된 팀이 없습니다. 먼저 '🤝 팀 조합' 탭에서 팀을 생성하고 저장해주세요.")
        else:
            team_options = {t['team_name']: t for t in saved_teams}
            
            with st.form("create_ensemble_form"):
                ens_title = st.text_input("합주 이름 (예: 정기공연 1팀 합주, 주말 연습 등)")
                selected_team_name = st.selectbox("합주할 팀 선택", list(team_options.keys()))
                submit_ens = st.form_submit_button("합주 세션 등록하기", use_container_width=True)

                if submit_ens:
                    if ens_title.strip():
                        target_team = team_options[selected_team_name]
                        m_ids = [m['id'] for m in target_team['members']]
                        create_ensemble(ens_title.strip(), selected_team_name, m_ids)
                        st.success(f"합주 '{ens_title.strip()}' 세션이 새로 생성되었습니다!")
                        st.rerun()
                    else:
                        st.warning("합주 이름을 입력해주세요.")

        st.markdown("---")
        st.subheader("📋 개설된 합주 목록")
        
        ensembles = get_all_ensembles()
        if ensembles:
            for e in ensembles:
                ens_id = e['id']
                is_active = (e.get('is_active', 0) == 1)
                status = "🔴 [진행 중]" if is_active else "⚪ [대기 중]"
                
                if isinstance(e.get('member_ids'), str):
                    ens_member_ids = [int(x.strip()) for x in e['member_ids'].split(",") if x.strip()]
                else:
                    ens_member_ids = e.get('member_ids', [])

                st.markdown(f"**{e['name']}** {status}  \n배정 팀: {e['team_name']}")
                
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if not is_active:
                        if st.button("▶️ 합주 시작", key=f"start_{ens_id}", use_container_width=True):
                            conflict = False
                            for active in active_ensembles:
                                if active['id'] == ens_id:
                                    continue
                                if isinstance(active.get('member_ids'), str):
                                    active_m_ids = [int(x.strip()) for x in active['member_ids'].split(",") if x.strip()]
                                else:
                                    active_m_ids = active.get('member_ids', [])
                                    
                                if set(ens_member_ids) & set(active_m_ids):
                                    conflict = True
                                    break
                            
                            if conflict:
                                st.error("⚠️ 같은 시간대에 이미 합주 중인 멤버가 포함되어 있습니다.")
                            else:
                                start_ensemble_db(ens_id)
                                st.success(f"'{e['name']}' 합주가 시작되었습니다!")
                                st.rerun()
                    else:
                        st.button("진행 중 ⚡", key=f"running_{ens_id}", disabled=True, use_container_width=True)
                        
                with col_btn2:
                    if is_active:
                        if st.button("⏹️ 합주 종료", key=f"stop_{ens_id}", type="primary", use_container_width=True):
                            earned, m_count = stop_ensemble_db(ens_id)
                            ensemble_result_dialog(e['name'], m_count, earned)
                    else:
                        st.button("종료됨", key=f"stopped_{ens_id}", disabled=True, use_container_width=True)
                        
                with col_btn3:
                    if not is_active:
                        if st.button("🗑️ 팀 삭제", key=f"delete_{ens_id}", use_container_width=True):
                            if 'delete_ensemble_db' in globals():
                                delete_ensemble_db(ens_id)
                            st.warning(f"'{e['name']}' 합주 세션이 삭제되었습니다.")
                            st.rerun()
                    else:
                        st.button("삭제 불가 (진행중)", key=f"del_lock_{ens_id}", disabled=True, use_container_width=True)
                
                st.markdown("---")
        else:
            st.info("개설된 합주 목록이 없습니다.")

    elif selected_main_tab == "👥 부원 목록":
        st.title("👥 HERTZ 전체 부원 명단")
        all_members = get_all_members_including_inactive()
        
        col_f1, col_f2 = st.columns(2)
        filter_session = col_f1.selectbox("세션별 필터", ["전체"] + ["보컬", "기타", "베이스", "드럼", "키보드"])
        filter_dept = col_f2.selectbox("학과별 필터", ["전체"] + DEPARTMENT_LIST)
        
        filtered_members = all_members
        if filter_session != "전체":
            filtered_members = [m for m in filtered_members if m['session'] == filter_session]
        if filter_dept != "전체":
            filtered_members = [m for m in filtered_members if m['department'] == filter_dept]
            
        st.markdown(f"**총 부원 수:** {len(filtered_members)}명")
        st.markdown("---")
        
        for m in filtered_members:
            status_badge = "🟢 [활동 중]" if m['is_active'] == 1 else "🔴 [활동 휴식/중단]"
            admin_badge = "👑 임원" if m['is_admin'] == 1 else "🎵 부원"
            
            with st.expander(f"{m['name']} ({m['session']} / {m['department']}) - {admin_badge} {status_badge}"):
                st.write(f"- **학번:** {m['student_id']}학번")
                st.write(f"- **크레딧:** {m['credits']} C")
                st.write(f"- **합주 능력치:** ⚡ {m.get('ensemble_stats', 0)}개")
                st.write(f"- **누적 연습 시간:** {m.get('practice_minutes', 0)}분 ({get_title_by_practice_time(m.get('practice_minutes', 0))})")
                st.write(f"- **한줄 소개:** {m.get('bio', '')}")
                
                inv = m.get('inventory', "")
                if inv:
                    item_ids = [i.strip() for i in inv.split(",") if i.strip()]
                    equipped_names = []
                    
                    for i_id in item_ids:
                        # 전체 아이템 리스트에서 ID가 일치하는 아이템 검색
                        match_item = next((item for item in all_possible_shop_items if item['id'] == i_id), None)
                        if match_item:
                            equipped_names.append(match_item['name'])
                        else:
                            equipped_names.append(i_id) # 매칭되지 않는 경우 ID 그대로 출력
                    
                    display_text = ", ".join(equipped_names)
                    st.write(f"- **보유 장비/아이템:** {display_text}")

    elif selected_main_tab == "🤝 팀 조합":
        st.title("🤝 밴드 팀 조합 관리")
        main_team_tabs = st.tabs(["💡 팀 조합 생성", "📋 저장된 팀"])
        all_active_list = get_all_active_members()

        with main_team_tabs[0]:
            team_sub1, team_sub2 = st.tabs(["🎲 랜덤 팀 균형 조합", "✍️ 임원진 직접 팀 편성"])
            
            with team_sub1:
                num_teams_rand = st.number_input("생성할 팀 수", min_value=1, max_value=10, value=2, key="rand_team_count")
                if st.button("🎲 세션 균형 자동 배분 실행", type="primary"):
                    session_dict = {}
                    for m in all_active_list:
                        s = m['session']
                        if s not in session_dict: session_dict[s] = []
                        session_dict[s].append(m)
                    
                    for s in session_dict: random.shuffle(session_dict[s])
                    teams_result = {f"생성팀 {i+1}": [] for i in range(num_teams_rand)}
                    
                    for s, members_list in session_dict.items():
                        for idx, m in enumerate(members_list):
                            teams_result[f"생성팀 {(idx % num_teams_rand) + 1}"].append(m)
                    
                    st.session_state['random_teams'] = teams_result

                if 'random_teams' in st.session_state and st.session_state['random_teams']:
                    for t_idx, (t_name, members_list) in enumerate(st.session_state['random_teams'].items()):
                        st.markdown(f"### 🎸 {t_name} 구성안")
                        for m in members_list:
                            st.write(f"- {m['name']} (`{m['session']}` / {m['department']})")
                        
                        col1, col2 = st.columns([3, 1])
                        input_name = col1.text_input("팀 이름 지정", key=f"rand_name_{t_idx}")
                        if col2.button("💾 저장하기", key=f"rand_save_{t_idx}"):
                            if input_name.strip():
                                m_ids = [m['id'] for m in members_list]
                                success, msg = save_custom_team(input_name, m_ids)
                                if success: 
                                    st.success(msg)
                                    st.rerun()
                                else: 
                                    st.error(msg)
                            else:
                                st.warning("저장할 팀 이름을 입력하세요.")
                        st.markdown("---")

            with team_sub2:
                st.subheader("임원진 수동 팀 편성 (최대 5팀 동시 등록)")
                if member['is_admin'] == 0:
                    st.warning("⚠️ 임원진 권한이 없어 팀을 저장할 수 없습니다.")
                
                num_manual_teams = st.number_input("동시에 생성할 팀 수", min_value=1, max_value=5, value=1, key="num_manual_teams_input")
                
                session_order = {"보컬": 1, "기타": 2, "베이스": 3, "드럼": 4, "키보드": 5}
                sorted_active_list = sorted(all_active_list, key=lambda x: (session_order.get(x['session'], 6), x['name']))
                member_options = {f"{m['name']} ({m['session']} / {m['department']})": m['id'] for m in sorted_active_list}
                
                manual_team_configs = []
                for i in range(int(num_manual_teams)):
                    st.markdown(f"#### 팀 {i+1} 설정")
                    t_name = st.text_input(f"팀 이름 #{i+1}", key=f"manual_tname_{i}")
                    t_members = st.multiselect(f"팀원 선택 #{i+1}", list(member_options.keys()), key=f"manual_tmembers_{i}")
                    manual_team_configs.append({"name": t_name, "members": t_members})
                    st.markdown("---")
                
                if st.button("💾 팀 저장", type="primary", disabled=(member['is_admin'] == 0)):
                    success_count = 0
                    error_msgs = []
                    
                    for cfg in manual_team_configs:
                        t_name = cfg["name"].strip()
                        labels = cfg["members"]
                        if t_name and labels:
                            m_ids = [member_options[lbl] for lbl in labels]
                            success, msg = save_custom_team(t_name, m_ids)
                            if success:
                                success_count += 1
                            else:
                                error_msgs.append(f"[{t_name}]: {msg}")
                        elif t_name or labels:
                            error_msgs.append(f"[{t_name or '이름 없음'}]: 팀 이름과 팀원을 모두 지정해주세요.")
                            
                    if success_count > 0:
                        st.success(f"총 {success_count}개의 팀이 성공적으로 저장되었습니다!")
                    for em in error_msgs:
                        st.error(em)
                    if success_count > 0:
                        st.rerun()

        with main_team_tabs[1]:
            st.subheader("📋 저장된 팀 목록")
            saved_teams = get_all_saved_teams()
            if not saved_teams:
                st.info("현재 저장된 팀이 없습니다.")
            else:
                for t in saved_teams:
                    with st.expander(f"🎸 {t['team_name']} (팀원 {len(t['members'])}명) - 생성일: {t['created_at']}"):
                        for m in t['members']:
                            st.write(f"- {m['name']} (`{m['session']}` / {m['department']})")
                        if member['is_admin'] == 1:
                            if st.button("🗑️ 팀 삭제", key=f"del_saved_{t['id']}"):
                                delete_saved_team(t['id'])
                                st.rerun()

    elif selected_main_tab == "🎪 공연 관리":
        st.title("🎪 공연별 참여 팀 관리")
        performances = get_all_performances()

        if member['is_admin'] == 1:
            with st.form("new_perf_form"):
                perf_title = st.text_input("새 공연 이름")
                if st.form_submit_button("공연 추가"):
                    if perf_title.strip():
                        create_performance(perf_title.strip())
                        st.success("생성되었습니다.")
                        st.rerun()
            st.markdown("---")

        if not performances:
            st.info("등록된 공연이 없습니다.")
        else:
            saved_teams = get_all_saved_teams()
            team_options = {t['team_name']: t['id'] for t in saved_teams}

            for p in performances:
                with st.container():
                    st.markdown(f"### 🎪 {p['title']}")
                    perf_teams = get_performance_teams_new(p['id'])

                    if perf_teams:
                        for pt in perf_teams:
                            with st.expander(f"🎸 팀: {pt['team_name']} (참가 인원 {len(pt['members'])}명)"):
                                for m in pt['members']:
                                    st.write(f"- {m['name']} (`{m['session']}` / {m['department']})")
                    else:
                        st.caption("현재 배정된 팀이 없습니다.")

                    if member['is_admin'] == 1:
                        with st.expander(f"⚙️ '{p['title']}' 팀 배정 관리"):
                            current_team_names = [pt['team_name'] for pt in perf_teams]
                            
                            selected_teams = st.multiselect(
                                "이 공연에 참가할 팀을 저장된 팀 목록에서 선택하세요",
                                list(team_options.keys()),
                                default=current_team_names,
                                key=f"perf_teams_{p['id']}"
                            )

                            if st.button(f"💾 공연 팀 배정 확정", key=f"save_perf_{p['id']}"):
                                selected_ids = [team_options[tname] for tname in selected_teams]
                                set_performance_teams(p['id'], selected_ids)
                                st.success("적용되었습니다.")
                                st.rerun()

                        if st.button(f"🗑️ 공연 전체 삭제", key=f"del_perf_{p['id']}"):
                            delete_performance(p['id'])
                            st.rerun()
                st.markdown("---")

    elif selected_main_tab == "⚙️ 임원 관리" and member['is_admin'] == 1:
        st.title("⚙️ HERTZ 임원진 전용 관리")
        admin_sub_tab1, admin_sub_tab2 = st.tabs(["👤 부원 추가 및 권한 관리", "🔄 부원 활동 상태 관리"])
        
        all_members_list = get_all_members_including_inactive()
        
        with admin_sub_tab1:
            st.subheader("➕ 새 부원 직접 등록")
            with st.form("add_member_form"):
                new_name = st.text_input("이름")
        
                # 1. 학과 셀렉트박스
                new_dept = st.selectbox("학과", DEPARTMENT_LIST + ["기타"], key="add_dept")
        
                # 2. '기타'를 선택했을 때 보여줄 직접 입력 텍스트 박스 추가
                custom_dept_input = st.text_input("학과 직접 입력 ('기타' 선택 시에만 적용)")
        
                new_sid = st.text_input("학번 두 자리 (예: 24)")
                new_sess = st.selectbox("세션", ["보컬", "기타", "베이스", "드럼", "키보드"], key="add_sess")
                new_is_admin = st.checkbox("임원진 권한 부여")   
                submitted = st.form_submit_button("부원 등록하기", use_container_width=True)
                
                if submitted:
                    if not new_name.strip() or not new_sid.strip():
                        st.error("이름과 학번을 모두 입력해주세요.")
                    else:
                        # '기타'를 선택했다면 직접 입력한 텍스트를 최종 학과로 지정
                        if new_dept == "기타":
                            final_dept = custom_dept_input.strip()
                            if not final_dept:
                                final_dept = "기타" # 직접 입력조차 비어있다면 기본값 설정
                        else:
                            final_dept = new_dept
                      
                        try:
                            conn = sqlite3.connect("hertz_app_data.db")  # 사용 중인 DB 파일명에 맞게 수정
                            cursor = conn.cursor()
                            cursor.execute(
                                """
                                INSERT INTO members (name, student_id, department, session, is_admin) 
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (new_name, new_sid, final_dept, new_sess, 1 if new_is_admin else 0)
                            )
                            conn.commit()
                            conn.close()
                
                            st.success(f"등록 완료! (이름: {new_name}, 학과: {final_dept})")
                            st.rerun()  # 화면을 새로고침하여 목록에 즉시 반영되도록 함
                        except Exception as e:
                            st.error(f"데이터베이스 저장 중 오류가 발생했습니다: {e}")

            st.markdown("---")
            st.subheader("👑 임원 권한 부여 및 회수")
            for m in all_members_list:
                col_m1, col_m2, col_m3 = st.columns([3, 2, 1])
                col_m1.markdown(f"**{m['name']}** (`{m['session']}` / {m['department']})")
                is_currently_admin = (m['is_admin'] == 1)
                new_admin_state = col_m2.checkbox("임원진", value=is_currently_admin, key=f"admin_chk_{m['id']}")
                
                if new_admin_state != is_currently_admin:
                    update_member_admin(m['id'], new_admin_state)
                    st.success(f"{m['name']} 님의 임원 권한이 변경되었습니다.")
                    st.rerun()

        with admin_sub_tab2:
            st.subheader("🔄 부원 활동 상태 관리 (휴학/탈퇴 등)")
            for m in all_members_list:
                col_a1, col_a2 = st.columns([3, 1])
                is_active_state = (m['is_active'] == 1)
                status_text = "🟢 활동 중" if is_active_state else "🔴 활동 중단/휴식"
                col_a1.markdown(f"**{m['name']}** ({m['session']} / {m['department']}) - {status_text}")
                
                new_active_state = col_a2.toggle("활동 여부", value=is_active_state, key=f"active_tog_{m['id']}")
                if new_active_state != is_active_state:
                    set_member_active_status(m['id'], new_active_state)
                    st.rerun()
