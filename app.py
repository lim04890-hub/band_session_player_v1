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

# 초기 부원 명단 데이터 (최초 실행 시 DB가 비어있을 때 자동 삽입용)
INITIAL_MEMBERS = [
    ("강대현", "전기전자공학부", "25", "기타", 0),
    ("강준", "전기전자공학부", "23", "베이스", 0),
    ("권도영", "컴퓨터공학부", "24", "보컬", 0),
    ("권찬우", "항공우주모빌리티공학과", "25", "베이스", 0),
    ("김다혜", "화공생명에너지학부", "26", "키보드", 0),
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
        
        # 1. members 테이블 (is_admin: 0=일반부원, 1=임원진)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                student_id TEXT NOT NULL,
                session TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        
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
        
        # 초기 데이터 삽입 (테이블이 비어있을 때만)
        cursor.execute("SELECT COUNT(*) FROM members")
        if cursor.fetchone()[0] == 0:
            cursor.executemany('''
                INSERT INTO members (name, department, student_id, session, is_admin)
                VALUES (?, ?, ?, ?, ?)
            ''', INITIAL_MEMBERS)
            
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
            INSERT INTO members (name, department, student_id, session, is_admin)
            VALUES (?, ?, ?, ?, ?)
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
                st.error("❌ 등록된 HERTZ 부원 정보와 일치하지 않습니다. 정보를 다시 확인해주세요.")

else:
    member = st.session_state['member']
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        admin_badge = "👑 [임원진]" if member['is_admin'] == 1 else "🎵 [부원]"
        st.markdown(f"{admin_badge} **{member['name']}** 님 (`{member['department']}` / {member['student_id']}학번 / `{member['session']}`)")
    with top_col2:
        if st.button("로그아웃"):
            st.session_state['member'] = None
            st.session_state['view'] = 'dashboard'
            st.session_state['current_project'] = None
            st.rerun()

    # 상단 네비게이션 탭 (임원진인 경우 멤버 관리 탭 추가)
    if member['is_admin'] == 1:
        tab_choice = st.radio("메뉴 선택", ["🎵 내 작업실", "👥 멤버 관리"], horizontal=True, label_visibility="collapsed")
    else:
        tab_choice = "🎵 내 작업실"

    if tab_choice == "🎵 내 작업실":
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

    elif tab_choice == "👥 멤버 관리":
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
                        # 임원진 권한 체크박스 토글
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
