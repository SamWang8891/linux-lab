"""Linux Lab — Flask application."""
import os
import string
import random
import threading
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message as MailMessage
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models import db, User, Whitelist, VerifyCode, QuizQuestion, QuizAnswer
from guac_api import GuacamoleAPI
import lxd_manager as lxd
from quiz_checker import QUIZ_QUESTIONS, check_answer

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = '請先登入'

guac = GuacamoleAPI(
    app.config['GUAC_URL'],
    app.config['GUAC_ADMIN_USER'],
    app.config['GUAC_ADMIN_PASS'],
)

# Transient in-memory store for plaintext passwords during provisioning.
# Key: user_id, Value: plaintext password. Cleared after provisioning completes.
_pending_passwords = {}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash('權限不足', 'error')
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated


def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.SystemRandom().choice(chars) for _ in range(length))


# ─── Auth ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard' if current_user.is_admin else 'student_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('admin_dashboard' if user.is_admin else 'student_dashboard'))
        flash('帳號或密碼錯誤', 'error')
    return render_template('login.html')


def generate_verify_code():
    return ''.join(random.SystemRandom().choice('0123456789') for _ in range(6))


def _set_provision_status(user, status, message=None):
    user.provision_status = status
    user.provision_message = message
    db.session.commit()


def provision_container_bg(app_obj, user_id):
    """Background thread to provision LXD + Guacamole for a user."""
    with app_obj.app_context():
        u = db.session.get(User, user_id)
        container_name = u.container_name
        try:
            _set_provision_status(u, 'creating_container', '正在建立容器...')
            ip = lxd.create_container(
                container_name,
                image=app_obj.config['LXD_IMAGE'],
                profile=app_obj.config['LXD_PROFILE'],
                network=app_obj.config['LXD_NETWORK'],
            )
            u.container_ip = ip
            db.session.commit()

            _set_provision_status(u, 'init_script', '正在初始化系統與題目檔案...')
            script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'init_container.sh')
            lxd.exec_in_container(container_name,
                ['bash', '-c', open(script_path).read()])

            _set_provision_status(u, 'creating_guac', '正在設定遠端連線...')

            guac_password = _pending_passwords.pop(user_id, None) or generate_password(8)
            u.guac_username = u.email

            guac.create_user(u.email, guac_password)
            app_obj.logger.info(f'Guac user created: {u.email}')

            desktop_id = guac.create_connection(
                f'{u.email} - 桌面', 'rdp', ip, 3389,
                username='user', password='user',
            )
            u.guac_connection_id_desktop = desktop_id

            terminal_id = guac.create_connection(
                f'{u.email} - 終端機', 'ssh', ip, 22,
                username='user', password='user',
            )
            u.guac_connection_id_terminal = terminal_id

            if desktop_id:
                guac.grant_connection(u.email, desktop_id)
            if terminal_id:
                guac.grant_connection(u.email, terminal_id)

            _set_provision_status(u, 'done', '佈建完成！')
            app_obj.logger.info(f'Provisioned {container_name} at {ip} — all done!')

        except Exception as e:
            import traceback
            app_obj.logger.error(f'Provisioning failed for {container_name}: {e}\n{traceback.format_exc()}')
            _set_provision_status(u, 'error', str(e))
            lxd.delete_container(container_name)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Step 1: Enter email → send verification code."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        # Check exact match or domain match (e.g. @mail.ntust.edu.tw)
        domain = '@' + email.split('@', 1)[1] if '@' in email else ''
        if not (Whitelist.query.filter_by(email=email).first() or
                Whitelist.query.filter_by(email=domain).first()):
            flash('此 Email 不在白名單中，請聯絡管理員。', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('此 Email 已註冊過，請直接登入。', 'error')
            return redirect(url_for('login'))

        # Invalidate old codes
        VerifyCode.query.filter_by(email=email, used=False).update({'used': True})

        # Generate and save code
        code = generate_verify_code()
        vc = VerifyCode(
            email=email,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db.session.add(vc)
        db.session.commit()

        # Send verification email
        try:
            msg = MailMessage(
                subject='Linux Lab 驗證碼',
                recipients=[email],
            )
            msg.body = f'你的驗證碼是：{code}\n\n此驗證碼將在 10 分鐘後失效。'
            mail.send(msg)
            flash('驗證碼已寄出，請檢查你的 Email。', 'success')
        except Exception as e:
            app.logger.warning(f'Failed to send verify email to {email}: {e}')
            flash(f'無法寄送 Email，請聯絡管理員。（除錯用驗證碼：{code}）', 'warning')

        return redirect(url_for('verify', email=email))

    return render_template('register.html')


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    """Step 2: Enter verification code."""
    email = request.args.get('email', '') or request.form.get('email', '')
    email = email.strip().lower()

    if not email:
        return redirect(url_for('register'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()

        vc = VerifyCode.query.filter_by(
            email=email, code=code, used=False
        ).first()

        if not vc or vc.expires_at < datetime.utcnow():
            flash('驗證碼錯誤或已過期，請重新註冊。', 'error')
            return render_template('verify.html', email=email)

        # Code is valid → go to set password
        vc.used = True
        db.session.commit()
        return redirect(url_for('set_password', email=email, token=vc.id))

    return render_template('verify.html', email=email)


@app.route('/set-password', methods=['GET', 'POST'])
def set_password():
    """Step 3: Set password and create account."""
    email = request.args.get('email', '') or request.form.get('email', '')
    token = request.args.get('token', '') or request.form.get('token', '')
    email = email.strip().lower()

    if not email or not token:
        return redirect(url_for('register'))

    # Verify the token is a used (verified) code for this email
    vc = VerifyCode.query.filter_by(id=token, email=email, used=True).first()
    if not vc:
        flash('無效的連結，請重新註冊。', 'error')
        return redirect(url_for('register'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if len(password) < 6:
            flash('密碼至少需要 6 個字元。', 'error')
            return render_template('set_password.html', email=email, token=token)

        if password != password_confirm:
            flash('兩次輸入的密碼不一致。', 'error')
            return render_template('set_password.html', email=email, token=token)

        if User.query.filter_by(email=email).first():
            flash('此帳號已存在，請直接登入。', 'error')
            return redirect(url_for('login'))

        # Create user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            container_name='pending',
        )
        db.session.add(user)
        db.session.commit()

        user.container_name = f'lab-student-{user.id}'
        db.session.commit()

        # Stash plaintext password for provisioning thread (cleared after use)
        _pending_passwords[user.id] = password

        # Provision in background
        threading.Thread(
            target=provision_container_bg,
            args=(app, user.id),
            daemon=True,
        ).start()

        flash('帳號建立成功！機器正在建立中，請稍候幾分鐘後再連線。', 'success')
        return redirect(url_for('login'))

    return render_template('set_password.html', email=email, token=token)


# ─── Forgot Password ────────────────────────────────────────────────────

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    """Step 1: Enter email → send verification code."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('此 Email 尚未註冊。', 'error')
            return render_template('forgot.html')

        # Invalidate old codes
        VerifyCode.query.filter_by(email=email, used=False).update({'used': True})

        code = generate_verify_code()
        vc = VerifyCode(
            email=email,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db.session.add(vc)
        db.session.commit()

        try:
            msg = MailMessage(
                subject='Linux Lab 密碼重設驗證碼',
                recipients=[email],
            )
            msg.body = f'你的驗證碼是：{code}\n\n此驗證碼將在 10 分鐘後失效。'
            mail.send(msg)
            flash('驗證碼已寄出，請檢查你的 Email。', 'success')
        except Exception as e:
            app.logger.warning(f'Failed to send reset email to {email}: {e}')
            flash(f'無法寄送 Email，請聯絡管理員。（除錯用驗證碼：{code}）', 'warning')

        return redirect(url_for('forgot_verify', email=email))

    return render_template('forgot.html')


@app.route('/forgot/verify', methods=['GET', 'POST'])
def forgot_verify():
    """Step 2: Enter verification code."""
    email = request.args.get('email', '') or request.form.get('email', '')
    email = email.strip().lower()

    if not email:
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        vc = VerifyCode.query.filter_by(
            email=email, code=code, used=False
        ).first()

        if not vc or vc.expires_at < datetime.utcnow():
            flash('驗證碼錯誤或已過期。', 'error')
            return render_template('verify.html', email=email, action='forgot_verify')

        vc.used = True
        db.session.commit()
        return redirect(url_for('reset_password', email=email, token=vc.id))

    return render_template('verify.html', email=email, action='forgot_verify')


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Step 3: Set new password."""
    email = request.args.get('email', '') or request.form.get('email', '')
    token = request.args.get('token', '') or request.form.get('token', '')
    email = email.strip().lower()

    if not email or not token:
        return redirect(url_for('forgot_password'))

    vc = VerifyCode.query.filter_by(id=token, email=email, used=True).first()
    if not vc:
        flash('無效的連結，請重新操作。', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')

        if len(password) < 6:
            flash('密碼至少需要 6 個字元。', 'error')
            return render_template('set_password.html', email=email, token=token, is_reset=True)

        if password != password_confirm:
            flash('兩次輸入的密碼不一致。', 'error')
            return render_template('set_password.html', email=email, token=token, is_reset=True)

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('帳號不存在。', 'error')
            return redirect(url_for('forgot_password'))

        user.password_hash = generate_password_hash(password)

        # Update Guacamole password if user exists there
        if user.guac_username:
            try:
                _reset_guac_for_user(user, plaintext_password=password)
            except Exception as e:
                app.logger.warning(f'Failed to update Guac password for {email}: {e}')

        db.session.commit()
        flash('密碼已更新，請重新登入。', 'success')
        return redirect(url_for('login'))

    return render_template('set_password.html', email=email, token=token, is_reset=True)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ─── Student Dashboard ──────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def student_dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    status = lxd.get_container_status(current_user.container_name) if current_user.container_name else 'unknown'
    guac_url = app.config['GUAC_PUBLIC_URL']

    # Quiz progress
    answered = {a.question_id: a for a in current_user.quiz_answers}
    questions = QuizQuestion.query.order_by(QuizQuestion.order).all()

    return render_template('student_dashboard.html',
                           status=status, guac_url=guac_url,
                           questions=questions, answered=answered)


@app.route('/machine/reset', methods=['POST'])
@login_required
def reset_machine():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    try:
        name = current_user.container_name
        # Clean up old container (ignore if doesn't exist)
        try: lxd.delete_container(name)
        except Exception: pass

        # Clean up old Guac resources
        if current_user.guac_connection_id_desktop:
            try: guac.delete_connection(current_user.guac_connection_id_desktop)
            except Exception: pass
        if current_user.guac_connection_id_terminal:
            try: guac.delete_connection(current_user.guac_connection_id_terminal)
            except Exception: pass

        # Reset state and re-provision in background
        current_user.container_ip = None
        current_user.guac_connection_id_desktop = None
        current_user.guac_connection_id_terminal = None
        current_user.provision_status = 'pending'
        current_user.provision_message = None
        QuizAnswer.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        threading.Thread(
            target=provision_container_bg,
            args=(app, current_user.id),
            daemon=True,
        ).start()

        flash('機器重置中，請稍候幾分鐘...', 'success')
    except Exception as e:
        flash(f'重置失敗：{e}', 'error')

    return redirect(url_for('student_dashboard'))


@app.route('/machine/start', methods=['POST'])
@login_required
def start_machine():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    try:
        lxd.start_container(current_user.container_name)
        flash('機器已啟動！', 'success')
    except Exception as e:
        flash(f'啟動失敗：{e}', 'error')
    return redirect(url_for('student_dashboard'))


@app.route('/machine/stop', methods=['POST'])
@login_required
def stop_machine():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    try:
        lxd.stop_container(current_user.container_name)
        flash('機器已關閉！', 'success')
    except Exception as e:
        flash(f'關閉失敗：{e}', 'error')
    return redirect(url_for('student_dashboard'))


@app.route('/machine/restart', methods=['POST'])
@login_required
def restart_machine():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    try:
        lxd.restart_container(current_user.container_name)
        flash('機器已重新啟動！', 'success')
    except Exception as e:
        flash(f'重啟失敗：{e}', 'error')
    return redirect(url_for('student_dashboard'))


@app.route('/guac/reset', methods=['POST'])
@login_required
def reset_guac():
    """Reset Guacamole account for current user."""
    u = current_user
    if u.is_admin:
        return redirect(url_for('admin_dashboard'))
    try:
        _reset_guac_for_user(u)
        flash('Guacamole 帳號已重置！', 'success')
    except Exception as e:
        flash(f'重置失敗：{e}', 'error')
    return redirect(url_for('student_dashboard'))


def _reset_guac_for_user(u, plaintext_password=None):
    """Delete and recreate Guac user + connections for a user.

    If plaintext_password is provided, use it as the new Guac password.
    Otherwise generate a random one (user will need to use 'forgot password' to sync).
    """
    # Clean up old
    if u.guac_connection_id_desktop:
        try: guac.delete_connection(u.guac_connection_id_desktop)
        except Exception: pass
    if u.guac_connection_id_terminal:
        try: guac.delete_connection(u.guac_connection_id_terminal)
        except Exception: pass
    if u.guac_username:
        try: guac.delete_user(u.guac_username)
        except Exception: pass

    if not u.container_ip:
        raise RuntimeError('機器尚未建立，無法設定 Guacamole')

    # Recreate
    guac_password = plaintext_password or generate_password(8)
    u.guac_username = u.email
    guac.create_user(u.email, guac_password)

    desktop_id = guac.create_connection(
        f'{u.email} - 桌面', 'rdp', u.container_ip, 3389,
        username='user', password='user',
    )
    u.guac_connection_id_desktop = desktop_id

    terminal_id = guac.create_connection(
        f'{u.email} - 終端機', 'ssh', u.container_ip, 22,
        username='user', password='user',
    )
    u.guac_connection_id_terminal = terminal_id

    if desktop_id:
        guac.grant_connection(u.email, desktop_id)
    if terminal_id:
        guac.grant_connection(u.email, terminal_id)

    db.session.commit()
    return guac_password


@app.route('/machine/status')
@login_required
def machine_status():
    u = current_user
    if u.provision_status != 'done':
        status_labels = {
            'pending': '⏳ 等待佈建',
            'creating_container': '📦 正在建立容器...',
            'init_script': '⚙️ 正在初始化系統...',
            'creating_guac': '🔗 正在設定遠端連線...',
            'error': '❌ 佈建失敗',
        }
        return jsonify({
            'status': u.provision_status,
            'label': status_labels.get(u.provision_status, u.provision_status),
            'message': u.provision_message,
            'ready': False,
        })

    container_status = lxd.get_container_status(u.container_name) if u.container_name else 'unknown'
    status_map = {'running': '🟢 執行中', 'stopped': '🔴 已停止', 'error': '⚠️ 錯誤'}
    return jsonify({
        'status': container_status,
        'label': status_map.get(container_status, '❓ 未知'),
        'ready': True,
    })


@app.route('/admin/provision-status')
@admin_required
def admin_provision_status():
    """Return all students' provision status as JSON."""
    students = User.query.filter_by(is_admin=False).all()
    result = []
    for s in students:
        result.append({
            'id': s.id,
            'email': s.email,
            'provision_status': s.provision_status,
            'provision_message': s.provision_message,
            'container_name': s.container_name,
            'container_ip': s.container_ip,
        })
    return jsonify(result)


# ─── Quiz ────────────────────────────────────────────────────────────────

@app.route('/quiz/<int:question_id>', methods=['GET', 'POST'])
@login_required
def quiz(question_id):
    question = QuizQuestion.query.get_or_404(question_id)
    existing = QuizAnswer.query.filter_by(user_id=current_user.id, question_id=question_id).first()

    if request.method == 'POST':
        if existing and existing.is_correct:
            flash('你已經答對這題了！', 'info')
            return redirect(url_for('quiz', question_id=question_id))

        answer = request.form.get('answer', '').strip()

        q_dict = {
            'check_type': question.check_type,
            'expected_answer': question.expected_answer,
            'check_script': question.check_script,
        }
        correct = check_answer(q_dict, answer, current_user.container_name, current_user.container_ip)

        if not existing:
            existing = QuizAnswer(user_id=current_user.id, question_id=question_id)
            db.session.add(existing)

        existing.answer = answer
        existing.is_correct = correct
        if correct:
            from datetime import datetime
            existing.solved_at = datetime.utcnow()
            flash('✅ 答對了！', 'success')
        else:
            flash('❌ 答錯了，再試試看。', 'error')
        db.session.commit()

    questions = QuizQuestion.query.order_by(QuizQuestion.order).all()
    answered = {a.question_id: a for a in current_user.quiz_answers}
    return render_template('quiz.html', question=question, existing=existing,
                           questions=questions, answered=answered)


# ─── Admin Dashboard ─────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    students = User.query.filter_by(is_admin=False).all()
    whitelist = Whitelist.query.all()

    # Gather stats
    student_data = []
    for s in students:
        stats = lxd.get_container_stats(s.container_name) if s.container_name else None
        solved = QuizAnswer.query.filter_by(user_id=s.id, is_correct=True).count()
        total = QuizQuestion.query.count()
        student_data.append({
            'user': s,
            'stats': stats,
            'quiz_progress': f'{solved}/{total}',
        })

    return render_template('admin_dashboard.html',
                           students=student_data, whitelist=whitelist)


@app.route('/admin/whitelist', methods=['POST'])
@admin_required
def add_whitelist():
    emails = request.form.get('emails', '')
    count = 0
    for line in emails.split('\n'):
        email = line.strip().lower()
        if email and not Whitelist.query.filter_by(email=email).first():
            db.session.add(Whitelist(email=email))
            count += 1
    db.session.commit()
    flash(f'已新增 {count} 個 Email 到白名單', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/whitelist/delete/<int:wid>', methods=['POST'])
@admin_required
def delete_whitelist(wid):
    w = Whitelist.query.get_or_404(wid)
    db.session.delete(w)
    db.session.commit()
    flash(f'已移除 {w.email}', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/student/<int:uid>/reset', methods=['POST'])
@admin_required
def admin_reset_student(uid):
    user = User.query.get_or_404(uid)
    try:
        name = user.container_name
        lxd.delete_container(name)
        ip = lxd.create_container(
            name,
            image=app.config['LXD_IMAGE'],
            profile=app.config['LXD_PROFILE'],
            network=app.config['LXD_NETWORK'],
        )
        script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'init_container.sh')
        lxd.exec_in_container(name, ['bash', '-c', open(script_path).read()])
        user.container_ip = ip
        QuizAnswer.query.filter_by(user_id=uid).delete()
        db.session.commit()
        flash(f'已重置 {user.email} 的機器', 'success')
    except Exception as e:
        flash(f'重置失敗：{e}', 'error')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/student/<int:uid>/delete', methods=['POST'])
@admin_required
def admin_delete_student(uid):
    user = User.query.get_or_404(uid)
    email = user.email
    try:
        # Delete LXD container
        if user.container_name and user.container_name != 'pending':
            lxd.delete_container(user.container_name)

        # Delete Guacamole connections and user
        if user.guac_connection_id_desktop:
            try:
                guac.delete_connection(user.guac_connection_id_desktop)
            except Exception:
                pass
        if user.guac_connection_id_terminal:
            try:
                guac.delete_connection(user.guac_connection_id_terminal)
            except Exception:
                pass
        if user.guac_username:
            try:
                guac.delete_user(user.guac_username)
            except Exception:
                pass

        # Delete quiz answers
        QuizAnswer.query.filter_by(user_id=uid).delete()

        # Delete verify codes
        VerifyCode.query.filter_by(email=email).delete()

        # Delete user
        db.session.delete(user)
        db.session.commit()

        flash(f'已刪除使用者 {email} 及其所有資源', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'刪除失敗：{e}', 'error')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/student/<int:uid>/reset-guac', methods=['POST'])
@admin_required
def admin_reset_guac(uid):
    user = User.query.get_or_404(uid)
    try:
        _reset_guac_for_user(user)
        flash(f'已重置 {user.email} 的 Guacamole，請通知使用者透過「忘記密碼」重設密碼以同步 Guacamole 密碼。', 'success')
    except Exception as e:
        flash(f'重置失敗：{e}', 'error')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/student/<int:uid>/restart', methods=['POST'])
@admin_required
def admin_restart_student(uid):
    user = User.query.get_or_404(uid)
    try:
        lxd.restart_container(user.container_name)
        flash(f'已重啟 {user.email} 的機器', 'success')
    except Exception as e:
        flash(f'重啟失敗：{e}', 'error')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/student/<int:uid>/provision', methods=['POST'])
@admin_required
def admin_provision_student(uid):
    """Manually trigger provisioning for a student whose container failed."""
    user = User.query.get_or_404(uid)
    if user.provision_status == 'done' and user.container_ip and user.guac_username:
        flash(f'{user.email} 已經完成佈建', 'info')
    else:
        # Clean up any partial state
        if user.container_name and user.container_name != 'pending':
            try: lxd.delete_container(user.container_name)
            except Exception: pass
        user.container_ip = None
        user.guac_username = None
        user.guac_connection_id_desktop = None
        user.guac_connection_id_terminal = None
        user.provision_status = 'pending'
        user.provision_message = None
        db.session.commit()
        threading.Thread(
            target=provision_container_bg,
            args=(app, user.id),
            daemon=True,
        ).start()
        flash(f'正在重新佈建 {user.email} 的機器...', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/stats')
@admin_required
def admin_system_stats():
    """Return host system stats as JSON."""
    import psutil
    return jsonify({
        'cpu_percent': psutil.cpu_percent(interval=1),
        'memory': {
            'total': psutil.virtual_memory().total,
            'used': psutil.virtual_memory().used,
            'percent': psutil.virtual_memory().percent,
        },
        'disk': {
            'total': psutil.disk_usage('/').total,
            'used': psutil.disk_usage('/').used,
            'percent': psutil.disk_usage('/').percent,
        },
    })


# ─── Init ────────────────────────────────────────────────────────────────

def init_db():
    """Create tables, seed admin and quiz questions."""
    db.create_all()

    # Create admin
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            email=app.config['ADMIN_EMAIL'],
            password_hash=generate_password_hash(app.config['ADMIN_PASSWORD']),
            is_admin=True,
        )
        db.session.add(admin)

    # Seed quiz questions
    if QuizQuestion.query.count() == 0:
        for q in QUIZ_QUESTIONS:
            db.session.add(QuizQuestion(
                order=q['order'],
                title=q['title'],
                description=q['description'],
                hint=q.get('hint'),
                check_type=q['check_type'],
                expected_answer=q.get('expected_answer'),
                check_script=q.get('check_script'),
            ))

    db.session.commit()


with app.app_context():
    init_db()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
