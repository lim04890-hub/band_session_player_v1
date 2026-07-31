import streamlit as st
import subprocess
import os
import shutil
import sys
import sqlite3
import hashlib
import uuid
from datetime import datetime
import imageio_ffmpeg
import yt_dlp

# 디렉토리 및 DB 설정
UPLOAD_DIR = "uploaded_audio"
OUTPUT_DIR = "separated_audio"
PROCESSED_DIR = "processed_audio"
DB_FILE = "app_data.db"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

st.set_page_config(page_title="Session Master", page_icon="🎸", layout="centered")

# --- 데이터베이스 (SQLite) 안정성 강화 연동 로직 ---

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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                song_title TEXT NOT NULL,
                separated_dir TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"데이터베이스 초기화 오류: {e}")

def hash_password(password):
    cleaned_pw = str(password).strip()
    return hashlib.sha256(cleaned_pw.encode('utf-8')).hexdigest()

def register_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    clean_username = str(username).strip()
    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                       (clean_username, hash_password(password)))
        conn.commit()
        return True, "회원가입이 완료되었습니다. 로그인 해주세요."
    except sqlite3.IntegrityError:
        return False, "이미 존재하는 아이디입니다."
    except Exception as e:
        return False, f"오류 발생: {e}"
    finally:
        conn.close()

def login_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    clean_username = str(username).strip()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", 
                   (clean_username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    return user

def save_project(user_id, song_title, separated_dir):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO projects (user_id, song_title, separated_dir, created_at) VALUES (?, ?, ?, ?)",
        (user_id, song_title, separated_dir, now)
    )
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return project_id

def get_user_projects(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY id DESC", (user_id,))
    projects = cursor.fetchall()
    conn.close()
    return projects

def delete_project(project_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT separated_dir FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id))
    row = cursor.fetchone()
    if row and row['separated_dir'] and os.path.exists(row['separated_dir']):
        shutil.rmtree(row['separated_dir'], ignore_errors=True)
        
    cursor.execute("DELETE FROM projects WHERE id = ? AND user_id = ?", (project_id, user_id))
    conn.commit()
    conn.close()

init_db()

# --- 오디오 및 유튜브 처리 로직 ---

def download_youtube_audio(youtube_url, output_dir):
    """유튜브 403 오류 우회를 위한 web_embedded 클라이언트 적용"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'noplaylist': True,
        'socket_timeout': 30,
        # 403 에러 회피율이 가장 높은 embed 클라이언트 지정
        'extractor_args': {
            'youtube': {
                'player_client': ['web_embedded', 'mweb'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info_dict)
            base, _ = os.path.splitext(filename)
            mp3_path = base + ".mp3"
            song_title = info_dict.get('title', 'youtube_song')
            song_title = "".join(c for c in song_title if c.isalnum() or c in (' ', '-', '_', '[', ']')).strip()
        return mp3_path, song_title
    except Exception as e:
        raise RuntimeError(f"다운로드 실패: {e}")
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
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'view' not in st.session_state:
    st.session_state['view'] = 'dashboard'
if 'current_project' not in st.session_state:
    st.session_state['current_project'] = None


# --- UI 레이아웃 ---
if st.session_state['user'] is None:
    st.title("🎸 세션 커스텀 플레이어")
    st.subheader("로그인 후 작업물들을 관리하세요.")
    
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    
    with tab1:
        login_id = st.text_input("아이디", key="login_id")
        login_pw = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", type="primary", use_container_width=True):
            user = login_user(login_id, login_pw)
            if user:
                st.session_state['user'] = dict(user)
                st.session_state['view'] = 'dashboard'
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
                
    with tab2:
        reg_id = st.text_input("사용할 아이디", key="reg_id")
        reg_pw = st.text_input("사용할 비밀번호", type="password", key="reg_pw")
        if st.button("회원가입 완료", use_container_width=True):
            if reg_id and reg_pw:
                success, msg = register_user(reg_id, reg_pw)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("아이디와 비밀번호를 모두 입력해주세요.")

else:
    user_info = st.session_state['user']
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.caption(f"👤 **{user_info['username']}** 님 환영합니다.")
    with top_col2:
        if st.button("로그아웃"):
            st.session_state['user'] = None
            st.session_state['view'] = 'dashboard'
            st.session_state['current_project'] = None
            st.rerun()

    if st.session_state['view'] == 'dashboard':
        st.title("📂 내 작업물 목록")
        projects = get_user_projects(user_info['id'])
        
        if not projects:
            st.info("저장된 작업물이 없습니다. 아래 '+' 버튼을 눌러 새로운 음원을 추가해보세요!")
        else:
            for p in projects:
                with st.container():
                    col_info, col_btn, col_del = st.columns([4, 1.5, 1])
                    with col_info:
                        st.markdown(f"### 🎵 {p['song_title']}")
                        st.caption(f"작성일: {p['created_at']}")
                    with col_btn:
                        if st.button("열기 ▶️", key=f"open_{p['id']}", use_container_width=True):
                            st.session_state['current_project'] = dict(p)
                            st.session_state['view'] = 'project_detail'
                            st.rerun()
                    with col_del:
                        if st.button("삭제 🗑️", key=f"del_{p['id']}", use_container_width=True):
                            delete_project(p['id'], user_info['id'])
                            st.rerun()
                    st.markdown("---")

        if st.button("➕ 새 작업물 추가", type="primary", use_container_width=True):
            st.session_state['view'] = 'new_project'
            st.rerun()

    elif st.session_state['view'] == 'new_project':
        if st.button("⬅️ 목록으로 돌아가기"):
            st.session_state['view'] = 'dashboard'
            st.rerun()

        st.title("➕ 새 음원 작업 추가")
        
        # 파일 업로드 vs 유튜브 링크 입력 탭 분리
        source_tab1, source_tab2 = st.tabs(["🔗 유튜브 링크 입력", "📁 파일 직접 업로드"])
        
        with source_tab1:
            yt_url = st.text_input("유튜브 영상 링크 입력 (예: https://youtu.be/OQWHFmPDVRg?si=aTAsKyJb4x4FBzGv)")
            if st.button("🚀 유튜브 음원 다운로드 및 분리 시작", type="primary", use_container_width=True):
                if yt_url:
                    with st.spinner("유튜브 음원 추출 및 AI 세션 분리 중... (수 분 소요됩니다)"):
                        try:
                            file_path, song_title = download_youtube_audio(yt_url, UPLOAD_DIR)
                            separated_dir = separate_audio(file_path, song_title + ".mp3")
                            project_id = save_project(user_info['id'], song_title, separated_dir)
                            
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
                else:
                    st.warning("유튜브 링크를 입력해주세요.")

        with source_tab2:
            uploaded_file = st.file_uploader("음악 파일 업로드 (MP3, WAV)", type=["mp3", "wav"])
            if uploaded_file is not None:
                file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if st.button("🚀 파일 세션 분리 및 저장 시작", type="primary", use_container_width=True):
                    with st.spinner("AI 모델이 세션을 분리하는 중입니다..."):
                        try:
                            separated_dir = separate_audio(file_path, uploaded_file.name)
                            song_title = os.path.splitext(uploaded_file.name)[0]
                            project_id = save_project(user_info['id'], song_title, separated_dir)
                            
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
        st.subheader("🎛️ 세션 믹서 & 트랙 제어")

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

        st.markdown("#### ⚡ 재생 옵션")
        col_spd, col_s, col_e = st.columns([1, 1, 1])
        with col_spd:
            speed = st.slider("재생 속도", 0.5, 2.0, 1.0, 0.1)
        with col_s:
            start_time = st.number_input("시작 구간 (초)", min_value=0, value=0)
        with col_e:
            end_time = st.number_input("종료 구간 (초, 0은 끝까지)", min_value=0, value=0)

        st.markdown("---")

        if selected_stems:
            with st.spinner("선택한 세션 믹싱 중..."):
                mixed_audio_path = process_mix(separated_dir, selected_stems, speed, start_time, end_time)

            if mixed_audio_path and os.path.exists(mixed_audio_path):
                st.subheader("▶️ 커스텀 트랙 재생")
                st.audio(mixed_audio_path, format="audio/wav")

                with open(mixed_audio_path, "rb") as f:
                    st.download_button(
                        label=f"📥 선택한 세션 합친 음원 다운로드 ({len(selected_stems)}개 세션 조합)",
                        data=f,
                        file_name=f"{project['song_title']}_mix.wav",
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
