from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime
import uuid

user_bp = Blueprint('user', __name__)

# 数据库文件路径
DATABASE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.db')
AVATAR_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'avatars')

# 确保头像目录存在
os.makedirs(AVATAR_DIR, exist_ok=True)


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            avatar TEXT,
            login_count INTEGER DEFAULT 0,
            last_login TEXT
        )
    ''')

    # 检查是否已存在 avatar 列，如果不存在则添加
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'avatar' not in columns:
        conn.execute('ALTER TABLE users ADD COLUMN avatar TEXT')
        conn.commit()

    # 创建默认管理员账户
    admin_exists = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin_exists:
        conn.execute(
            'INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
            ('admin', generate_password_hash('admin123'), 'admin')
        )

    conn.commit()
    conn.close()


# 初始化数据库
init_db()


@user_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = True if request.form.get('remember') else False

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if not user or not check_password_hash(user['password'], password):
            flash('用户名或密码错误', 'danger')
            return redirect(url_for('user.login'))

        # 使用当前时间更新登录信息
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        conn.execute('''
            UPDATE users 
            SET login_count = login_count + 1, last_login = ? 
            WHERE id = ?
        ''', (current_time, user['id']))
        conn.commit()
        conn.close()

        # 设置会话
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['avatar'] = user['avatar'] if 'avatar' in user.keys() else None
        session['login_count'] = user['login_count'] + 1
        session['last_login'] = current_time

        flash('登录成功！', 'success')
        return redirect(url_for('index'))

    return render_template('login.html')


@user_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return redirect(url_for('user.register'))

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
            )
            conn.commit()
            flash('注册成功！请登录', 'success')
            return redirect(url_for('user.login'))
        except sqlite3.IntegrityError:
            flash('用户名已存在', 'danger')
        finally:
            conn.close()

    return render_template('register.html')


@user_bp.route('/logout')
def logout():
    session.clear()
    flash('您已退出登录', 'info')
    return redirect(url_for('user.login'))


@user_bp.route('/manage')
def manage_users():
    if 'user_id' not in session:
        flash('请先登录', 'danger')
        return redirect(url_for('user.login'))

    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = 10  # 每页显示10条记录
    search_term = request.args.get('search', '')

    conn = get_db_connection()

    # 根据角色构建查询
    if session['role'] == 'admin':
        # 管理员可以查看所有用户
        base_query = 'SELECT * FROM users'
        count_query = 'SELECT COUNT(*) FROM users'
        if search_term:
            base_query += f" WHERE username LIKE '%{search_term}%'"
            count_query += f" WHERE username LIKE '%{search_term}%'"
    else:
        # 普通用户只能查看自己
        base_query = f'SELECT * FROM users WHERE id = {session["user_id"]}'
        count_query = f'SELECT COUNT(*) FROM users WHERE id = {session["user_id"]}'
        search_term = ''  # 普通用户忽略搜索

    # 获取总记录数
    total_users = conn.execute(count_query).fetchone()[0]
    total_pages = max(1, (total_users + per_page - 1) // per_page)  # 计算总页数

    # 确保页码在有效范围内
    page = max(1, min(page, total_pages))

    # 添加分页和排序
    offset = (page - 1) * per_page
    users_query = f"{base_query} ORDER BY id LIMIT {per_page} OFFSET {offset}"
    users = conn.execute(users_query).fetchall()

    conn.close()

    return render_template('user_management.html',
                           users=users,
                           username=session['username'],
                           avatar=session.get('avatar'),  # 从 session 获取头像
                           login_count=session.get('login_count', 0),
                           last_login=session.get('last_login', '从未登录'),
                           role=session['role'],
                           current_page=page,
                           total_pages=total_pages,
                           total_users=total_users,
                           search_term=search_term,
                           current_user_id=session['user_id'])


@user_bp.route('/update_role/<int:user_id>', methods=['POST'])
def update_role(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return {'status': 'error', 'message': '无权限操作'}, 403

    new_role = request.form.get('role')
    if new_role not in ['admin', 'user']:
        return {'status': 'error', 'message': '无效的角色'}, 400

    conn = get_db_connection()
    conn.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
    conn.commit()
    conn.close()

    return {'status': 'success', 'message': '角色更新成功'}


@user_bp.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'role' not in session or session['role'] != 'admin':
        return {'status': 'error', 'message': '无权限操作'}, 403

    if user_id == session.get('user_id'):
        return {'status': 'error', 'message': '不能删除当前登录账户'}, 400

    conn = get_db_connection()
    try:
        # 获取用户信息
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return {'status': 'error', 'message': '用户不存在'}, 404

        # 强制删除头像文件（即使失败也不影响用户删除）
        avatar = user.get('avatar')
        if avatar and avatar != 'avatar.png':
            avatar_path = os.path.join(AVATAR_DIR, avatar)
            if os.path.exists(avatar_path):
                try:
                    os.remove(avatar_path)
                except OSError as e:
                    print(f"删除头像失败（继续删除用户）: {e}")

        # 强制删除用户（不允许失败）
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return {'status': 'success', 'message': '用户删除成功'}

    except Exception as e:
        # 即使出现异常也强制删除
        print(f"强制删除过程中出现异常: {e}")
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return {'status': 'success', 'message': '用户已强制删除'}
    finally:
        conn.close()


@user_bp.route('/upload_avatar/<int:user_id>', methods=['POST'])
def upload_avatar(user_id):
    if 'user_id' not in session:
        return {'status': 'error', 'message': '未登录'}, 401

    if session['role'] != 'admin' and session['user_id'] != user_id:
        return {'status': 'error', 'message': '无权限操作'}, 403

    if 'avatar' not in request.files:
        return {'status': 'error', 'message': '未选择文件'}, 400

    file = request.files['avatar']
    if file.filename == '':
        return {'status': 'error', 'message': '未选择文件'}, 400

    # 简化文件类型检查 - 只检查扩展名
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if '.' not in file.filename:
        return {'status': 'error', 'message': '文件名缺少扩展名'}, 400

    ext = file.filename.rsplit('.', 1)[1].lower()

    if ext not in allowed_extensions:
        return {'status': 'error', 'message': '不支持的图片格式'}, 400

    # 获取用户信息
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()

    if not user:
        return {'status': 'error', 'message': '用户不存在'}, 404

    # 直接访问 Row 对象的字段
    old_avatar = user['avatar'] if 'avatar' in user.keys() else None

    # 生成简单安全的文件名
    import uuid
    new_filename = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
    save_path = os.path.join(AVATAR_DIR, new_filename)

    try:
        # 1. 先保存新文件
        file.save(save_path)

        # 2. 更新数据库
        conn = get_db_connection()
        conn.execute('UPDATE users SET avatar = ? WHERE id = ?', (new_filename, user_id))
        conn.commit()
        conn.close()

        # 3. 删除旧头像（如果是自定义头像）
        if old_avatar and old_avatar != 'avatar.png':
            old_path = os.path.join(AVATAR_DIR, old_avatar)
            if os.path.exists(old_path) and os.path.isfile(old_path):
                try:
                    os.remove(old_path)
                except Exception as e:
                    print(f"删除旧头像失败（可忽略）: {e}")

        # 更新session
        if session['user_id'] == user_id:
            session['avatar'] = new_filename

        return {
            'status': 'success',
            'message': '头像上传成功',
            'avatar_url': url_for('static', filename=f'avatars/{new_filename}')
        }

    except Exception as e:
        # 错误处理：删除可能已保存的部分文件
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except:
                pass

        return {'status': 'error', 'message': f'上传失败: {str(e)}'}, 500