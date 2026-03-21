"""Linux Lab — Local VM Flask application (no auth, no LXD, no Guacamole)."""
import os
import re
import subprocess
import json

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'local-lab-key'

@app.template_filter('inline_code')
def inline_code_filter(text):
    from markupsafe import Markup, escape
    return Markup(re.sub(r'`([^`]+)`', r'<code>\1</code>', str(escape(text))))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///linux_lab_local.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

# ── Models ───────────────────────────────────────────────────────────────

class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    hint = db.Column(db.Text, nullable=True)
    check_type = db.Column(db.String(50), nullable=False)
    expected_answer = db.Column(db.Text, nullable=True)
    check_script = db.Column(db.Text, nullable=True)


class QuizAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    question = db.relationship('QuizQuestion')


# ── Load questions from JSON ─────────────────────────────────────────────

_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'challenges.json')
try:
    with open(_json_path, 'r') as f:
        QUIZ_QUESTIONS = json.load(f)
except Exception as e:
    QUIZ_QUESTIONS = []
    print(f"Error loading challenges.json: {e}")


# ── Quiz checker (local — uses subprocess instead of LXD) ───────────────

def _run_local(cmd):
    """Run a command locally and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.returncode, r.stdout, r.stderr
    except Exception:
        return 1, '', ''


def check_answer(question, answer):
    """Check answer — runs checks locally on this machine."""
    check_type = question.get('check_type', '')
    expected = question.get('expected_answer', '')

    if check_type == 'text':
        if not expected:
            return False
        return answer.strip().lower() == expected.strip().lower()

    elif check_type == 'http':
        try:
            import urllib.request
            r = urllib.request.urlopen('http://localhost:80', timeout=5)
            return r.status == 200
        except Exception:
            return False

    elif check_type == 'ssh':
        # For local VM, just check if the password was actually changed
        # by trying su with the new password
        try:
            r = subprocess.run(
                ['su', '-c', 'echo ok', 'user'],
                input='linux-lab-2026\n',
                capture_output=True, text=True, timeout=5,
            )
            return r.returncode == 0 and 'ok' in r.stdout
        except Exception:
            return False

    elif check_type == 'script':
        script_name = question.get('check_script', '')
        return _run_check_script(script_name, answer)

    return False


def _run_check_script(script_name, answer):
    """Run check scripts locally."""

    if script_name == 'check_id':
        return 'uid=1000(user)' in answer.strip() and 'gid=1000(user)' in answer.strip()

    elif script_name == 'check_edit_file':
        rc, out, _ = _run_local(['cat', '/home/user/challenges/edit_me.txt'])
        return rc == 0 and out.strip() == 'Linux is awesome'

    elif script_name == 'check_mkdir':
        rc, _, _ = _run_local(['test', '-d', '/home/user/challenges/gdg_is_great'])
        return rc == 0

    elif script_name == 'check_delete':
        for path in ['/home/user/challenges/delete_me.txt',
                     '/home/user/challenges/remove_this_dir',
                     '/home/user/challenges/protected_dir']:
            rc, _, _ = _run_local(['test', '-e', path])
            if rc == 0:
                return False
        return True

    elif script_name == 'check_cp':
        rc1, _, _ = _run_local(['test', '-f', '/home/user/challenges/copy_of_original.txt'])
        rc2, _, _ = _run_local(['test', '-d', '/home/user/challenges/sample_dir_backup'])
        return rc1 == 0 and rc2 == 0

    elif script_name == 'check_mv':
        rc1, _, _ = _run_local(['test', '-f', '/home/user/challenges/moved/move_me.txt'])
        rc2, _, _ = _run_local(['test', '-f', '/home/user/challenges/renamed.txt'])
        rc3, _, _ = _run_local(['test', '-f', '/home/user/challenges/move_me.txt'])
        rc4, _, _ = _run_local(['test', '-f', '/home/user/challenges/rename_me.txt'])
        return rc1 == 0 and rc2 == 0 and rc3 != 0 and rc4 != 0

    elif script_name == 'check_softlink':
        rc, out, _ = _run_local(['readlink', '/home/user/challenges/link_to_original'])
        return rc == 0 and 'original.txt' in out.strip()

    elif script_name == 'check_tar':
        rc1, _, _ = _run_local(['test', '-f', '/home/user/challenges/compress_me.tar.gz'])
        rc2, _, _ = _run_local(['test', '-d', '/home/user/challenges/extracted'])
        return rc1 == 0 and rc2 == 0

    elif script_name == 'check_chmod':
        rc, out, _ = _run_local(['stat', '-c', '%a', '/home/user/challenges/22.sh'])
        if rc != 0:
            return False
        try:
            mode = int(out.strip(), 8)
        except ValueError:
            return False
        return bool(mode & 0o111)

    elif script_name == 'check_chown':
        rc, out, _ = _run_local(['stat', '-c', '%U', '/home/user/challenges/22.sh'])
        return rc == 0 and out.strip() == 'user'

    elif script_name == 'check_fastfetch':
        rc, _, _ = _run_local(['which', 'fastfetch'])
        return rc == 0 and len(answer.strip()) > 0

    elif script_name == 'check_bashrc':
        rc, out, _ = _run_local(
            ['bash', '-c', 'source /home/user/.bashrc && echo $LAB_COMPLETE'])
        return rc == 0 and out.strip() == '1'

    return False


# ── Routes ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    questions = QuizQuestion.query.order_by(QuizQuestion.order).all()
    answered = {a.question_id: a for a in QuizAnswer.query.all()}

    solved = sum(1 for a in answered.values() if a.is_correct)
    total = len(questions)

    return render_template('dashboard.html',
                           questions=questions, answered=answered,
                           solved=solved, total=total)


@app.route('/quiz/<int:question_id>', methods=['GET', 'POST'])
def quiz(question_id):
    question = db.session.get(QuizQuestion, question_id)
    if not question:
        return redirect(url_for('index'))

    existing = QuizAnswer.query.filter_by(question_id=question_id).first()

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
        correct = check_answer(q_dict, answer)

        if not existing:
            existing = QuizAnswer(question_id=question_id)
            db.session.add(existing)

        existing.answer = answer
        existing.is_correct = correct
        if correct:
            flash('✅ 答對了！', 'success')
        else:
            flash('❌ 答錯了，再試試看。', 'error')
        db.session.commit()

    questions = QuizQuestion.query.order_by(QuizQuestion.order).all()
    answered = {a.question_id: a for a in QuizAnswer.query.all()}
    return render_template('quiz.html', question=question, existing=existing,
                           questions=questions, answered=answered)


@app.route('/reset', methods=['POST'])
def reset_progress():
    """Reset quiz progress and challenge files."""
    QuizAnswer.query.delete()
    db.session.commit()

    # Re-run challenge setup script
    script = '/usr/local/bin/reset-lab'
    if os.path.exists(script):
        subprocess.run(['bash', script], timeout=30)

    flash('🔄 已重置所有進度和挑戰檔案！', 'success')
    return redirect(url_for('index'))


# ── Init ─────────────────────────────────────────────────────────────────

def init_db():
    db.create_all()
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
