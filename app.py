import streamlit as st
import subprocess
import os
import shutil
import sys
import sqlite3
import uuid
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

# 페이지 설정 및 HERTZ 맞춤형 CSS (블랙 & 레드 컨셉)
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

# 초기 부원 명단 데이터 (본인 계정 강대현 임원진 1 설정 포함)
INITIAL_MEMBERS = [
    ("강대현", "전기전자공학부", "25", "기타", 1),
    ("강준", "전기전자공학부", "23", "베이스", 0),
    ("권도영", "컴퓨터공학부", "24", "보컬", 0),
    ("권찬우", "항공우주모빌리티공학과", "25", "베이스", 0),
    ("김다혜", "화공생명에너지학부", "26", "키보드", 0),
    ("김마루", "컴퓨터공학부", "24", "기타", 0),
    ("김민재", "전기전자공학부", "25", "기타", 0),
    ("김서윤", "환경보건과학과", "25", "드럼", 0),
    ("김수민", "화학공학부", "23", "베이스", 0),
    ("김준홍", "화학공학부", "23", "기타", 0),
    ("남성진", "화학공학부", "23", "기타", 0),
    ("노시영", "생물공학과", "25", "드럼", 0),
    ("박서진", "전기전자공학부", "25", "보컬", 0),
    ("박유찬", "항공우주모빌리티공학과", "25", "키보드", 0),
    ("박주용", "재료공학과", "23", "기타", 0),
    ("박현준", "산업공학과", "26", "보컬", 0),
    ("백찬민", "사회환경공학부", "24", "드럼", 0),
    ("변지우", "생물공학과", "24", "기타", 0),
    ("변지은", "화학공학부", "22", "기타", 0),
    ("손예원", "행정학과", "22", "보컬", 0),
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
    ("최아현", "동물자원과학과", "22", "보컬", 0),
    ("최우혁", "항공우주모빌리티공학과", "26", "드럼", 0),
    ("최준호", "전기전자공학과", "26", "기타", 0),
    ("최준희", "전기전자공학부", "21", "베이스", 0),
    ("하은지", "전기전자공학부", "23", "드럼", 0),
    ("한호림", "전기전지공학부", "26", "베이스", 0),
    ("허승범", "전기전자공학부", "23", "보컬", 0)
]

# 공통 장착 아이템 카테고리별 정의 (모자, 옷, 신발, 장신구, MD)
COMMON_SHOP_ITEMS = {
    "모자": [
        {"id": "hat_1", "name": "🧢 기본 스냅백", "cost": 1000, "desc": "어느 룩에나 잘 어울리는 무난한 스냅백"},
        {"id": "hat_2", "name": "🎩 빈티지 페도라", "cost": 3000, "desc": "재즈와 인디 감성을 더해주는 페도라"},
        {"id": "hat_3", "name": "👑 락스타 실크 햇", "cost": 5000, "desc": "무대 위에서 눈에 띄는 화려한 모자"},
        {"id": "hat_4", "name": "🌟 다이아몬드 크라운", "cost": 10000, "desc": "최고급 보석이 박힌 황제의 왕관"}
    ],
    "옷": [
        {"id": "cloth_1", "name": "👕 무지 밴드 티셔츠", "cost": 1000, "desc": "땀 흡수가 잘 되는 심플한 연습용 티셔츠"},
        {"id": "cloth_2", "name": "🧥 데님 청자켓", "cost": 3000, "desc": "청춘과 록의 상징인 스타일리시한 청자켓"},
        {"id": "cloth_3", "name": "🔥 락스타 가죽 라이더 자켓", "cost": 5000, "desc": "묵직한 카리스마를 뿜어내는 가죽 자켓"},
        {"id": "cloth_4", "name": "✨ 골드 벨벳 투피스", "cost": 10000, "desc": "럭셔리함의 극치를 보여주는 무대 의상"}
    ],
    "신발": [
        {"id": "shoe_1", "name": "👟 편안한 단화 스니커즈", "cost": 1000, "desc": "연습실에서 신기 좋은 가벼운 스니커즈"},
        {"id": "shoe_2", "name": "🥾 컨버스 하이톱", "cost": 3000, "desc": "합주할 때 발목을 탄탄하게 잡아주는 하이탑"},
        {"id": "shoe_3", "name": "🥿 스터드 워커 부츠", "cost": 5000, "desc": "거친 매력을 더해주는 락커들의 부츠"},
        {"id": "shoe_4", "name": "💎 다이아몬드 스니커즈", "cost": 10000, "desc": "한 걸음마다 반짝이는 최고급 한정판 슈즈"}
    ],
    "장신구": [
        {"id": "acc_1", "name": "💍 써지컬 스틸 링", "cost": 1000, "desc": "심플하면서도 시크한 기본 반지"},
        {"id": "acc_2", "name": "⛓️ 메탈 체인 목걸이", "cost": 3000, "desc": "힙한 감성을 완성해주는 체인 목걸이"},
        {"id": "acc_3", "name": "🕶️ 메탈릭 선글라스", "cost": 5000, "desc": "조명을 완벽하게 차단하는 락스타 선글라스"},
        {"id": "acc_4", "name": "💎 플래티넘 락스타 체인", "cost": 10000, "desc": "재력과 멋을 동시에 과시하는 순은 체인"}
    ],
    "MD": [
        {"id": "md_1", "name": "🎗️ HERTZ 기본 반다나", "cost": 1000, "desc": "땀을 닦거나 손목에 두르는 밴드 공식 MD"},
        {"id": "md_2", "name": "🧣 로고 자수 스포츠 타올", "cost": 3000, "desc": "격렬한 합주 후 땀 닦기 딱 좋은 타올"},
        {"id": "md_3", "name": "🎒 HERTZ 투어 백팩", "cost": 5000, "desc": "악보와 장비를 모두 담는 투어용 가방"},
        {"id": "md_4", "name": "🎟️ VIP 올패스 패스포트", "cost": 10000, "desc": "모든 공연장 백스테이지를 프리패스하는 목걸이"}
    ]
}

# 세션별 악기 아이템 정의 (보컬, 기타, 베이스, 드럼, 키보드)
SESSION_GEAR_ITEMS = {
    "기타": [
        {"id": "g_1", "name": "🎸 입문용 통기타 (스콰이어급)", "cost": 1000, "desc": "처음 튜닝을 배우며 코트를 잡던 추억의 기타"},
        {"id": "g_2", "name": "🎸 그럴듯한 일렉기타 (에피폰 스탠다드)", "cost": 3000, "desc": "합주실에서 험버커 사운드를 뿜어내는 든든한 녀석"},
        {"id": "g_3", "name": "🎸 칩슨 & 휀다 (오리지널 미국산)", "cost": 5000, "desc": "기타 키즈들의 로망, 명불허전 전설의 브랜드"},
        {"id": "g_4", "name": "🎸 마스터빌드 커스텀샵", "cost": 10000, "desc": "장인이 한 땀 한 땀 영혼을 갈아 넣은 세상에 단 하나뿐인 기타"}
    ],
    "베이스": [
        {"id": "b_1", "name": "🎸 입문용 4현 베이스 (스콰이어)", "cost": 1000, "desc": "묵직한 저음의 세계로 입문하게 만드는 베이스"},
        {"id": "b_2", "name": "🎸 그루브한 베이스 (멕시칸 펜더)", "cost": 3000, "desc": "밴드의 든든한 뼈대를 받쳐주는 단단한 사운드"},
        {"id": "b_3", "name": "🎸 뮤직맨 & Rickenbacker", "cost": 5000, "desc": "특유의 펀치감과 개성 넘치는 로큰롤 베이스"},
        {"id": "b_4", "name": "🎸 커스텀샵 액티브 5현 베이스", "cost": 10000, "desc": "무대 밑바닥까지 진동을 때려 박는 하이엔드 베이스"}
    ],
    "보컬": [
        {"id": "v_1", "name": "🎤 가성비 다이나믹 마이크 (슈어 SM58급)", "cost": 1000, "desc": "전 세계 합주실과 라이브 클럽의 국룰 마이크"},
        {"id": "v_2", "name": "🎤 무선 스테이지 마이크", "cost": 3000, "desc": "무대 위를 자유롭게 누비며 관객을 사로잡는 마이크"},
        {"id": "v_3", "name": "🎤 노이만 진공관 마이크", "cost": 5000, "desc": "숨소리 하나까지 예술로 만드는 최고급 스튜디오 마이크"},
        {"id": "v_4", "name": "🎤 커스텀 다이아몬드 스튜디오 마이크", "cost": 10000, "desc": "보컬리스트의 위엄을 상징하는 보석 박힌 마이크"}
    ],
    "드럼": [
        {"id": "d_1", "name": "🥁 연습용 스틱 & 패드 세트", "cost": 1000, "desc": "끊임없이 루디먼트를 연습하게 만드는 필수품"},
        {"id": "d_2", "name": "🥁 펄 스탠다드 스네어 드럼", "cost": 3000, "desc": "귀를 찢는 타격감으로 곡의 리드미컬함을 살리는 스네어"},
        {"id": "d_3", "name": "🥁 야마하 녹턴 & 타마 스타클래식", "cost": 5000, "desc": "프로 드러머들이 사랑하는 영롱한 타악기 브랜드"},
        {"id": "d_4", "name": "🥁 커스텀 풀 메탈 킷트", "cost": 10000, "desc": "무대를 폭발시키는 압도적인 스케일의 드럼 세트"}
    ],
    "키보드": [
        {"id": "k_1", "name": "🎹 61건반 가성비 신디사이저", "cost": 1000, "desc": "가볍게 들고 다니며 피아노와 패드 소리를 내는 건반"},
        {"id": "k_2", "name": "🎹 야마하 모티프 / 노드 일렉트로", "cost": 3000, "desc": "합주실 무대를 꽉 채우는 따뜻한 건반 사운드"},
        {"id": "k_3", "name": "🎹 노드 스테이지 레드 피아노", "cost": 5000, "desc": "건반 연주자들의 로망, 무대 위 강렬한 레드 감성"},
        {"id": "k_4", "name": "🎹 그랜드 커스텀 신디사이저", "cost": 10000, "desc": "화려한 오케스트라 패드와 신스 사운드를 지배하는 장비"}
    ]
}

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
        
        # 1. members 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                student_id TEXT NOT NULL,
                session TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                credits INTEGER DEFAULT 0,
                inventory TEXT DEFAULT ''
            )
        ''')
        
        # 기존 테이블에 누락된 컬럼이 있을 경우 안전하게 추가 (마이그레이션)
        cursor.execute("PRAGMA table_info(members)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'credits' not in columns:
            cursor.execute("ALTER TABLE members ADD COLUMN credits INTEGER DEFAULT 0")
        if 'inventory' not in columns:
            cursor.execute("ALTER TABLE members ADD COLUMN inventory TEXT DEFAULT ''")
        
        # 2. projects 테이블
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

        # 3. performances 테이블 (공연 관리)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        # 4. performance_teams 테이블 (공연별 팀 및 멤버 매핑)
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
        
        # 초기 데이터 삽입 (테이블이 비어있을 때만)
        cursor.execute("SELECT COUNT(*) FROM members")
        if cursor.fetchone()[0] == 0:
            for item in INITIAL_MEMBERS:
                cursor.execute('''
                    INSERT INTO members (name, department, student_id, session, is_admin, credits, inventory)
                    VALUES (?, ?, ?, ?, ?, 0, '')
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
        WHERE name = ? AND department = ? AND student_id = ? AND session = ?
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

def get_all_members():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members ORDER BY name ASC")
    members = cursor.fetchall()
    conn.close()
    return members

def add_member(name, department, student_id, session, is_admin):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO members (name, department, student_id, session, is_admin, credits, inventory)
            VALUES (?, ?, ?, ?, ?, 0, '')
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

def delete_member(member_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()

def add_credits_to_member(member_id, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET credits = credits + ? WHERE id = ?", (amount, member_id))
    conn.commit()
    conn.close()

def purchase_item_db(member_id, item_id, cost):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT credits, inventory FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "부원 정보를 찾을 수 없습니다."
    
    current_credits = row['credits']
    inventory = row['inventory'] or ""
    items_list = [i.strip() for i in inventory.split(",") if i.strip()]
    
    if item_id in items_list:
        conn.close()
        return False, "이미 보유한 아이템입니다."
        
    if current_credits < cost:
        conn.close()
        return False, "크레딧이 부족합니다."
        
    items_list.append(item_id)
    new_inventory = ",".join(items_list)
    new_credits = current_credits - cost
    
    cursor.execute("UPDATE members SET credits = ?, inventory = ? WHERE id = ?", (new_credits, new_inventory, member_id))
    conn.commit()
    conn.close()
    return True, "구매가 완료되었습니다!"

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
    return projects

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

# 공연 및 팀 관련 함수
def get_all_performances():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM performances ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

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
    return rows

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


# --- UI 레이아웃 ---

st.markdown("""
    <div class="hertz-header">
        <h1 style="margin:0; font-size: 26px;">🎸 건국대학교 공과대학 밴드 HERTZ</h1>
        <p style="margin:5px 0 0 0; color: #ff8888; font-size: 14px;">
            Official Instagram: <a href="https://instagram.com/ku.hertz" target="_blank" style="color: #ff9999;">@ku.hertz</a> | 세션 커스텀 연습 플레이어 & 게이미피케이션
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
                st.error("❌ 등록된 HERTZ 부원 정보와 일치하지 않습니다. 정보를 다시 확인해주세요.")

else:
    # 최신 회원 정보 동기화
    current_mem_id = st.session_state['member']['id']
    latest_member_info = get_member_fresh(current_mem_id)
    if latest_member_info:
        st.session_state['member'] = latest_member_info
    member = st.session_state['member']

    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        admin_badge = "👑 [임원진]" if member['is_admin'] == 1 else "🎵 [부원]"
        st.markdown(f"{admin_badge} **{member['name']}** 님 (`{member['department']}` / {member['student_id']}학번 / `{member['session']}`) | 💰 **{member['credits']} 크레딧**")
    with top_col2:
        if st.button("로그아웃"):
            st.session_state['member'] = None
            st.session_state['view'] = 'dashboard'
            st.session_state['current_project'] = None
            st.rerun()

    # 네비게이션 탭 설정 (임원진 여부에 따른 탭 구성)
    base_tabs = ["🎵 내 작업실", "🎮 연습 & 상점", "🤝 팀 조합", "🎪 공연 관리"]
    if member['is_admin'] == 1:
        base_tabs.append("👥 멤버 관리")

    selected_main_tab = st.radio("상단 메인 메뉴", base_tabs, horizontal=True, label_visibility="collapsed")

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
                    with st.spinner("AI가 곡의 6개 세션(기타, 보컬, 드럼, 베이스, 피아노, 기타 등)을 분리하는 중입니다..."):
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
                speed = st.slider("재생 속도 (카피 연습용)", 0.5, 2.0, 1.0, 0.1)
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
                            label=f"📥 조합된 연습용 음원 다운로드 ({len(selected_stems)}개 세션 조합)",
                            data=f,
                            file_name=f"{project['song_title']}_HERTZ_mix.wav",
                            mime="audio/wav",
                            type="primary",
                            use_container_width=True
                        )
            else:
                st.info("하나 이상의 스템을 선택하면 플레이어가 활성화됩니다.")

            st.markdown("---")
            st.subheader("📂 개별 원본 스템 다운로드")
            dl_cols = st.columns(3)
            for idx, stem in enumerate(all_stems):
                stem_path = os.path.join(separated_dir, f"{stem}.wav")
                if os.path.exists(stem_path):
                    with dl_cols[idx % 3]:
                        with open(stem_path, "rb") as f:
                            st.download_button(
                                label=f"{stem_labels[stem]} 다운로드",
                                data=f,
                                file_name=f"{project['song_title']}_{stem}.wav",
                                mime="audio/wav",
                                use_container_width=True,
                                key=f"dl_det_{stem}"
                            )

    elif selected_main_tab == "🎮 연습 & 상점":
        st.title("🎮 HERTZ 아케이드 연습실 & 상점")
        st.caption("연습을 완료하고 크레딧을 모아 캐릭터 아바타에 장비와 아이템을 장착해보세요! (1분당 30 크레딧)")

        sub_tab1, sub_tab2 = st.tabs(["🎸 연습 세션실 & 아바타", "🛍️ 확장 상점 & 인벤토리"])

        inventory_str = member['inventory'] or ""
        my_items = [i.strip() for i in inventory_str.split(",") if i.strip()]

        with sub_tab1:
            st.subheader("무대 위 캐릭터 스튜디오")
            
            user_session = member['session']
            session_emojis = {
                "기타": "🎸💥 [열정적으로 기타 솔로 연주 중!]",
                "베이스": "🎸🔥 [그루브한 베이스 라인 연주 중!]",
                "보컬": "🎤✨ [스탠딩 마이크를 잡고 열창 중!]",
                "드럼": "🥁💥 [파워풀하게 드럼 스틱을 흔드는 중!]",
                "키보드": "🎹🎶 [화려한 신디사이저 연주 중!]"
            }
            current_animation = session_emojis.get(user_session, "🎶 [음악에 맞춰 연주 중!]")
            
            # 장착 중인 아이템 실시간 반영 시각화
            equipped_display = []
            all_possible_shop_items = []
            for cat, items in COMMON_SHOP_ITEMS.items():
                all_possible_shop_items.extend(items)
            for s_name, s_items in SESSION_GEAR_ITEMS.items():
                all_possible_shop_items.extend(s_items)

            for mi in my_items:
                match_obj = next((item for item in all_possible_shop_items if item['id'] == mi), None)
                if match_obj:
                    equipped_display.append(match_obj['name'])

            gear_text = " | ".join(equipped_display) if equipped_display else "기본 장비 착용 중"

            st.markdown(f"""
                <div style="background-color: #161616; padding: 25px; border-radius: 12px; text-align: center; border: 2px dashed #FF2222; margin-bottom: 20px;">
                    <h2 style="color: #FF2222; margin: 0;">STAGE LIVE</h2>
                    <p style="font-size: 20px; margin: 10px 0; color: #fff;">{current_animation}</p>
                    <p style="color: #aaa; font-size: 14px;">본래 세션: <b>{user_session}</b></p>
                    <hr style="border-color: #333; margin: 15px 0;">
                    <p style="color: #ff9999; font-size: 15px; margin: 0;">✨ <b>착용 중인 장비:</b> {gear_text}</p>
                </div>
            """, unsafe_allow_html=True)

            col_timer1, col_timer2 = st.columns(2)
            with col_timer1:
                practice_minutes = st.number_input("연습한 시간 (분 단위 입력)", min_value=1, max_value=300, value=1, step=1)
            with col_timer2:
                st.write("")
                st.write("")
                earn_btn = st.button("🏁 연습 완료 및 크레딧 정산받기", type="primary", use_container_width=True)

            if earn_btn:
                earned = practice_minutes * 30
                add_credits_to_member(member['id'], earned)
                st.success(f"🎉 연습 완료! {practice_minutes}분 동안 연습하여 **{earned} 크레딧**을 획득했습니다!")
                st.rerun()

        with sub_tab2:
            st.subheader("🛍️ 밴드 장비 및 패션 상점")
            st.markdown(f"현재 보유 크레딧: **{member['credits']} 크레딧**")
            
            # 카테고리별 탭 분류 (모자, 옷, 신발, 장신구, MD + 악기)
            shop_tabs = st.tabs(["🧢 모자", "👕 옷", "👟 신발", "💍 장신구", "🎗️ MD", "🎸 세션별 악기 장비"])

            # 1. 공통 아이템 탭 렌더링
            categories = ["모자", "옷", "신발", "장신구", "MD"]
            for idx, cat_name in enumerate(categories):
                with shop_tabs[idx]:
                    st.markdown(f"### 🛒 {cat_name} 컬렉션 (가격: 1000 / 3000 / 5000 / 10000)")
                    c_items = COMMON_SHOP_ITEMS[cat_name]
                    
                    scols = st.columns(2)
                    for i, item in enumerate(c_items):
                        with scols[i % 2]:
                            is_owned = item['id'] in my_items
                            st.markdown(f"""
                                <div style="background: #151515; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px;">
                                    <h4>{item['name']}</h4>
                                    <p style="color: #ccc; font-size: 13px; margin: 5px 0;">{item['desc']}</p>
                                    <p style="color: #FF2222; font-weight: bold; margin: 5px 0;">가격: {item['cost']} 크레딧</p>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if is_owned:
                                st.button("보유 중 ✅", key=f"owned_{item['id']}", disabled=True, use_container_width=True)
                            else:
                                if st.button("구매하기 💳", key=f"buy_{item['id']}", use_container_width=True):
                                    success, msg = purchase_item_db(member['id'], item['id'], item['cost'])
                                    if success:
                                        st.success(msg)
                                        st.rerun()
                                    else:
                                        st.error(msg)

            # 2. 세션별 악기 장비 탭 렌더링 (모든 세션 장비 구매 가능)
            with shop_tabs[5]:
                st.markdown("### 🎸 세션별 악기 및 장비 상점")
                st.caption("보컬이라도 기타나 건반 등 다른 세션의 장비를 자유롭게 구매하여 장착할 수 있습니다!")
                
                selected_gear_session = st.selectbox("조회할 악기 세션 선택", ["기타", "베이스", "보컬", "드럼", "키보드"])
                target_gear_list = SESSION_GEAR_ITEMS[selected_gear_session]
                
                g_cols = st.columns(2)
                for i, item in enumerate(target_gear_list):
                    with g_cols[i % 2]:
                        is_owned = item['id'] in my_items
                        st.markdown(f"""
                            <div style="background: #151515; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 10px;">
                                <h4>{item['name']}</h4>
                                <p style="color: #ccc; font-size: 13px; margin: 5px 0;">{item['desc']}</p>
                                <p style="color: #FF2222; font-weight: bold; margin: 5px 0;">가격: {item['cost']} 크레딧</p>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        if is_owned:
                            st.button("보유 중 ✅", key=f"owned_{item['id']}", disabled=True, use_container_width=True)
                        else:
                            if st.button("구매하기 💳", key=f"buy_{item['id']}", use_container_width=True):
                                success, msg = purchase_item_db(member['id'], item['id'], item['cost'])
                                if success:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

            st.markdown("---")
            st.subheader("🎒 내 장비 장식함 (인벤토리)")
            if my_items:
                for mi in my_items:
                    match_item = next((item for item in all_possible_shop_items if item['id'] == mi), None)
                    if match_item:
                        st.markdown(f"- ✅ **{match_item['name']}** (장착 완료)")
            else:
                st.info("아직 구매한 아이템이 없습니다. 상점에서 마음에 드는 장비를 구매해보세요!")

    elif selected_main_tab == "🤝 팀 조합":
        st.title("🤝 밴드 팀 조합 관리")
        st.caption("공연이나 합주를 위한 팀을 자동으로 무작위 조합하거나 임원진이 직접 구성할 수 있습니다.")

        team_sub1, team_sub2 = st.tabs(["🎲 랜덤 팀 균형 조합", "✍️ 임원진 직접 팀 편성"])
        all_members_list = get_all_members()

        with team_sub1:
            st.subheader("세션 균형 무작위 팀 배치")
            num_teams_rand = st.number_input("생성할 팀 수", min_value=1, max_value=10, value=2, key="rand_team_count")
            
            if st.button("🎲 랜덤 팀 자동 배분 실행", type="primary"):
                import random
                shuffled_members = list(all_members_list)
                random.shuffle(shuffled_members)
                
                teams_result = {f"팀 {i+1}": [] for i in range(num_teams_rand)}
                for idx, m in enumerate(shuffled_members):
                    t_key = f"팀 {(idx % num_teams_rand) + 1}"
                    teams_result[t_key].append(m)
                
                st.success("랜덤 팀 편성이 완료되었습니다!")
                for t_name, members in teams_result.items():
                    st.markdown(f"### 🎸 {t_name}")
                    for m in members:
                        st.write(f"- {m['name']} (`{m['session']}` / {m['department']})")
                    st.markdown("---")

        with team_sub2:
            st.subheader("임원진 직접 팀 지정 편성")
            if member['is_admin'] == 0:
                st.warning("⚠️ 직접 팀 편성은 임원진 권한 부원만 저장할 수 있습니다. (조회 및 시뮬레이션은 가능합니다)")

            manual_num_teams = st.number_input("편성할 팀 수 설정", min_value=1, max_value=10, value=2, key="manual_team_count")
            
            manual_team_allocation = {}
            for t_idx in range(manual_num_teams):
                t_name = f"팀 {t_idx + 1}"
                with st.expander(f"📌 {t_name} 멤버 구성"):
                    selected_m_ids = []
                    for m in all_members_list:
                        chk = st.checkbox(f"{m['name']} ({m['session']} / {m['department']})", key=f"t_{t_idx}_m_{m['id']}")
                        if chk:
                            selected_m_ids.append(m['id'])
                    manual_team_allocation[t_name] = selected_m_ids

            if st.button("💾 구성한 팀 저장하기", type="primary"):
                if member['is_admin'] == 1:
                    st.success("팀 구성 데이터가 준비되었습니다. '공연 관리' 탭에서 공연별로 팀을 확정 등록할 수 있습니다!")
                else:
                    st.error("임원진 권한이 필요합니다.")

    elif selected_main_tab == "🎪 공연 관리":
        st.title("🎪 공연별 팀 세팅 관리")
        st.caption("여러 개의 공연을 생성하고, 공연마다 서로 다른 팀 조합을 완벽하게 분리하여 관리하세요.")

        performances = get_all_performances()

        with st.expander("➕ 새 공연 생성하기 (임원진 전용)"):
            with st.form("new_perf_form"):
                perf_title_input = st.text_input("공연 이름 (예: 2026 정기 공연, 버스킹 등)")
                perf_submit = st.form_submit_button("공연 추가")
                if perf_submit:
                    if perf_title_input.strip():
                        if member['is_admin'] == 1:
                            create_performance(perf_title_input.strip())
                            st.success(f"'{perf_title_input.strip()}' 공연이 생성되었습니다!")
                            st.rerun()
                        else:
                            st.error("임원진 권한만 공연을 생성할 수 있습니다.")
                    else:
                        st.warning("공연 이름을 입력해주세요.")

        st.markdown("---")
        st.subheader("📋 등록된 공연 목록 및 팀 현황")

        if not performances:
            st.info("등록된 공연이 없습니다. 위에서 새 공연을 생성해보세요.")
        else:
            all_members_list = get_all_members()
            for p in performances:
                with st.container():
                    st.markdown(f"### 🎪 {p['title']}")
                    st.caption(f"생성일: {p['created_at']}")
                    
                    p_teams_rows = get_performance_teams(p['id'])
                    
                    perf_teams_dict = {}
                    for row in p_teams_rows:
                        tname = row['team_name']
                        if tname not in perf_teams_dict:
                            perf_teams_dict[tname] = []
                        perf_teams_dict[tname].append(row)

                    if perf_teams_dict:
                        for tname, members in perf_teams_dict.items():
                            st.markdown(f"**🔹 {tname}**")
                            for m in members:
                                st.write(f"&nbsp;&nbsp;&nbsp;&nbsp;- {m['name']} (`{m['session']}` / {m['department']})")
                    else:
                        st.info("이 공연에 편성된 팀이 아직 없습니다.")

                    if member['is_admin'] == 1:
                        with st.expander(f"⚙️ '{p['title']}' 팀 편집 및 배정"):
                            edit_num_teams = st.number_input("이 공연의 팀 수", min_value=1, max_value=5, value=2, key=f"edit_perf_cnt_{p['id']}")
                            
                            current_perf_team_dict = {}
                            for et_idx in range(edit_num_teams):
                                et_name = f"팀 {et_idx + 1}"
                                st.markdown(f"**{et_name} 멤버 선택**")
                                et_selected_ids = []
                                for m in all_members_list:
                                    chk_key = f"perf_{p['id']}_t_{et_idx}_m_{m['id']}"
                                    is_already_in = any(row['team_name'] == et_name and row['member_id'] == m['id'] for row in p_teams_rows)
                                    if st.checkbox(f"{m['name']} ({m['session']})", value=is_already_in, key=chk_key):
                                        et_selected_ids.append(m['id'])
                                current_perf_team_dict[et_name] = et_selected_ids

                            if st.button(f"💾 '{p['title']}' 팀 구성 저장", key=f"save_perf_btn_{p['id']}"):
                                save_performance_teams(p['id'], current_perf_team_dict)
                                st.success("공연 팀 구성이 성공적으로 저장되었습니다!")
                                st.rerun()

                        if st.button(f"🗑️ 공연 삭제", key=f"del_perf_{p['id']}"):
                            delete_performance(p['id'])
                            st.success("공연이 삭제되었습니다.")
                            st.rerun()

                    st.markdown("---")

    elif selected_main_tab == "👥 멤버 관리" and member['is_admin'] == 1:
        st.title("👥 HERTZ 멤버 및 권한 관리")
        st.caption("임원진 권한으로 부원을 추가/삭제하고 임원진 권한을 부여할 수 있습니다.")
        
        tab_add, tab_manage = st.tabs(["➕ 부원 추가", "📋 부원 목록 및 삭제/권한 설정"])
        
        with tab_add:
            st.subheader("신규 부원 등록")
            with st.form("add_member_form"):
                new_name = st.text_input("이름")
                new_dept = st.text_input("학과")
                new_id = st.text_input("학번 두 자리 (예: 25)")
                new_session = st.selectbox("세션", ["보컬", "기타", "베이스", "드럼", "키보드"], key="add_session")
                new_is_admin = st.checkbox("임원진 권한 부여")
                
                add_submit = st.form_submit_button("부원 추가하기", use_container_width=True)
                if add_submit:
                    if new_name.strip() and new_dept.strip() and new_id.strip():
                        success, msg = add_member(new_name, new_dept, new_id, new_session, new_is_admin)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("모든 필드를 올바르게 입력해주세요.")

        with tab_manage:
            st.subheader("등록된 부원 관리")
            members = get_all_members()
            
            for m in members:
                with st.container():
                    col_info, col_admin, col_del = st.columns([3, 1.5, 1])
                    with col_info:
                        role_icon = "👑" if m['is_admin'] == 1 else "👤"
                        st.markdown(f"{role_icon} **{m['name']}** ({m['department']} / {m['student_id']}학번 / `{m['session']}`)")
                    with col_admin:
                        current_admin_status = bool(m['is_admin'])
                        new_admin_status = st.checkbox("임원진", value=current_admin_status, key=f"admin_chk_{m['id']}")
                        if new_admin_status != current_admin_status:
                            update_member_admin(m['id'], new_admin_status)
                            st.rerun()
                    with col_del:
                        if st.button("삭제", key=f"del_mem_{m['id']}", use_container_width=True):
                            delete_member(m['id'])
                            st.success(f"{m['name']} 부원이 삭제되었습니다.")
                            st.rerun()
                    st.markdown("---")
