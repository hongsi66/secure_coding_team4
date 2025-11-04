from flask import Flask, render_template, request, redirect, session, url_for, jsonify, send_from_directory
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'instagram-clone-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 제한

DB = 'instagram.db'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 업로드 폴더 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """데이터베이스 초기화"""
    conn = get_db()
    with open('schema.sql', 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.close()

def migrate_db():
    """기존 데이터베이스에 새 테이블 추가 (마이그레이션)"""
    conn = get_db()
    try:
        # 좋아요 테이블이 없으면 생성
        conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (post_id) REFERENCES posts(id),
                UNIQUE(user_id, post_id)
            )
        """)
        # 댓글 테이블이 없으면 생성
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        # 인덱스 생성
        conn.execute("CREATE INDEX IF NOT EXISTS idx_likes_post_id ON likes(post_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_likes_user_id ON likes(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id)")
        conn.commit()
    except Exception as e:
        print(f"마이그레이션 중 오류: {e}")
    finally:
        conn.close()

def allowed_file(filename):
    """허용된 파일 확장자 확인"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    """홈 페이지 - 로그인 상태면 피드로, 아니면 로그인으로"""
    if 'username' in session:
        return redirect(url_for('feed'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인 페이지"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return jsonify({"success": False, "message": "사용자명과 비밀번호를 입력해주세요."})

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['username'] = username
            session['user_id'] = user['id']
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "로그인 실패! 사용자명 또는 비밀번호가 잘못되었습니다."})
    
    return render_template("login.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """회원가입 페이지"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return jsonify({"success": False, "message": "사용자명과 비밀번호를 입력해주세요."})

        if len(password) < 6:
            return jsonify({"success": False, "message": "비밀번호는 최소 6자 이상이어야 합니다."})

        hashed_pw = generate_password_hash(password)
        conn = get_db()
        try:
            cursor = conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                 (username, hashed_pw))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            # 자동 로그인
            session['username'] = username
            session['user_id'] = user_id
            return jsonify({"success": True})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({"success": False, "message": "이미 사용 중인 사용자명입니다!"})
    
    return render_template("signup.html")

@app.route('/logout')
def logout():
    """로그아웃"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/feed')
def feed():
    """공개 피드 - 모든 사용자의 게시물을 볼 수 있음"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db()
    # 최신 게시물부터 정렬하여 가져오기
    posts = conn.execute(
        "SELECT * FROM posts ORDER BY created_at DESC"
    ).fetchall()
    
    # 각 게시물의 좋아요 수와 사용자의 좋아요 여부 확인
    posts_with_likes = []
    user_id = session.get('user_id')
    
    for post in posts:
        post_dict = dict(post)
        # 좋아요 수
        like_count = conn.execute(
            "SELECT COUNT(*) as count FROM likes WHERE post_id=?", (post['id'],)
        ).fetchone()['count']
        post_dict['like_count'] = like_count
        
        # 현재 사용자가 좋아요를 눌렀는지 확인
        user_liked = conn.execute(
            "SELECT COUNT(*) as count FROM likes WHERE post_id=? AND user_id=?", 
            (post['id'], user_id)
        ).fetchone()['count'] > 0
        post_dict['user_liked'] = user_liked
        
        # 댓글 가져오기
        comments = conn.execute(
            "SELECT * FROM comments WHERE post_id=? ORDER BY created_at ASC",
            (post['id'],)
        ).fetchall()
        post_dict['comments'] = [dict(comment) for comment in comments]
        
        posts_with_likes.append(post_dict)
    
    conn.close()
    
    return render_template("feed.html", posts=posts_with_likes, username=session['username'], user_id=user_id)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """게시물 업로드 페이지"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # 파일 확인
        if 'image' not in request.files:
            return jsonify({"success": False, "message": "이미지 파일을 선택해주세요."})
        
        file = request.files['image']
        caption = request.form.get('caption', '')
        
        if file.filename == '':
            return jsonify({"success": False, "message": "파일을 선택해주세요."})
        
        if file and allowed_file(file.filename):
            # 안전한 파일명 생성
            filename = secure_filename(file.filename)
            # 파일명에 타임스탬프 추가하여 중복 방지
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 데이터베이스에 저장
            conn = get_db()
            conn.execute(
                "INSERT INTO posts (user_id, username, image_path, caption) VALUES (?, ?, ?, ?)",
                (session['user_id'], session['username'], filename, caption)
            )
            conn.commit()
            conn.close()
            
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "message": "허용되지 않는 파일 형식입니다. (png, jpg, jpeg, gif만 가능)"})
    
    return render_template("upload.html")

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """업로드된 이미지 파일 서빙"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/like/<int:post_id>', methods=['POST', 'DELETE'])
def toggle_like(post_id):
    """좋아요 추가/삭제"""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401
    
    user_id = session['user_id']
    conn = get_db()
    
    if request.method == 'POST':
        # 좋아요 추가
        try:
            conn.execute(
                "INSERT INTO likes (user_id, post_id) VALUES (?, ?)",
                (user_id, post_id)
            )
            conn.commit()
            # 좋아요 수 조회
            like_count = conn.execute(
                "SELECT COUNT(*) as count FROM likes WHERE post_id=?", (post_id,)
            ).fetchone()['count']
            conn.close()
            return jsonify({"success": True, "liked": True, "like_count": like_count})
        except sqlite3.IntegrityError:
            # 이미 좋아요를 눌렀을 경우
            conn.close()
            return jsonify({"success": False, "message": "이미 좋아요를 눌렀습니다."})
    
    elif request.method == 'DELETE':
        # 좋아요 삭제
        conn.execute(
            "DELETE FROM likes WHERE user_id=? AND post_id=?",
            (user_id, post_id)
        )
        conn.commit()
        # 좋아요 수 조회
        like_count = conn.execute(
            "SELECT COUNT(*) as count FROM likes WHERE post_id=?", (post_id,)
        ).fetchone()['count']
        conn.close()
        return jsonify({"success": True, "liked": False, "like_count": like_count})

@app.route('/api/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    """댓글 추가"""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401
    
    content = request.json.get('content', '').strip()
    if not content:
        return jsonify({"success": False, "message": "댓글 내용을 입력해주세요."})
    
    user_id = session['user_id']
    username = session['username']
    
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO comments (post_id, user_id, username, content) VALUES (?, ?, ?, ?)",
        (post_id, user_id, username, content)
    )
    comment_id = cursor.lastrowid
    conn.commit()
    
    # 추가된 댓글 조회
    comment = conn.execute(
        "SELECT * FROM comments WHERE id=?", (comment_id,)
    ).fetchone()
    conn.close()
    
    return jsonify({
        "success": True,
        "comment": {
            "id": comment['id'],
            "username": comment['username'],
            "content": comment['content'],
            "created_at": comment['created_at']
        }
    })

@app.route('/api/post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    """게시물 삭제"""
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "로그인이 필요합니다."}), 401
    
    user_id = session['user_id']
    conn = get_db()
    
    # 게시물이 존재하는지 및 현재 사용자의 게시물인지 확인
    post = conn.execute(
        "SELECT * FROM posts WHERE id=? AND user_id=?", (post_id, user_id)
    ).fetchone()
    
    if not post:
        conn.close()
        return jsonify({"success": False, "message": "게시물을 찾을 수 없거나 삭제 권한이 없습니다."}), 403
    
    try:
        # 관련 좋아요 삭제
        conn.execute("DELETE FROM likes WHERE post_id=?", (post_id,))
        
        # 관련 댓글 삭제
        conn.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        
        # 게시물 삭제
        conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.commit()
        
        # 업로드된 이미지 파일 삭제
        image_path = post['image_path']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], image_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"파일 삭제 중 오류: {e}")
        
        conn.close()
        return jsonify({"success": True, "message": "게시물이 삭제되었습니다."})
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"success": False, "message": f"게시물 삭제 중 오류가 발생했습니다: {str(e)}"}), 500

if __name__ == "__main__":
    # 데이터베이스 초기화 (처음 실행 시)
    if not os.path.exists(DB):
        init_db()
    else:
        # 기존 DB에 새 테이블 추가 (마이그레이션)
        migrate_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

