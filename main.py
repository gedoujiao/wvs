from flask import Flask, render_template, session, redirect, url_for
from backend import blueprints
import os



app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

for bp in blueprints:
    app.register_blueprint(bp)


@app.route('/')
def index():
    # 检查用户是否登录
    if 'username' in session:
        return render_template('index.html',
                               username=session['username'],
                               login_count=session.get('login_count', 0),
                               last_login=session.get('last_login', '从未登录'),
                               role=session.get('role', 'user'))
    return redirect(url_for('user.login'))

@app.context_processor
def inject_user_info():
    return {
        'username': session.get('username'),
        'avatar': session.get('avatar'),
        'login_count': session.get('login_count', 0),
        'last_login': session.get('last_login', '从未登录'),
        'role': session.get('role', 'user')
    }


if __name__ == '__main__':
    # 确保数据目录存在
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)

    app.run(host='127.0.0.1', port=5000, debug=True)
