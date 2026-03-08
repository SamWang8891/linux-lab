from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Student-specific
    provision_status = db.Column(db.String(50), default='pending')  # pending/creating_container/init_script/creating_guac/done/error
    provision_message = db.Column(db.Text, nullable=True)
    container_name = db.Column(db.String(100), nullable=True)
    container_ip = db.Column(db.String(50), nullable=True)
    guac_username = db.Column(db.String(100), nullable=True)
    guac_connection_id_desktop = db.Column(db.String(50), nullable=True)
    guac_connection_id_terminal = db.Column(db.String(50), nullable=True)
    pending_guac_password = db.Column(db.String(255), nullable=True)  # transient, cleared after provisioning

    quiz_answers = db.relationship('QuizAnswer', backref='user', lazy=True)


class Whitelist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class VerifyCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)


class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    hint = db.Column(db.Text, nullable=True)
    check_type = db.Column(db.String(50), nullable=False)  # 'text', 'ssh', 'http', 'script'
    expected_answer = db.Column(db.Text, nullable=True)
    check_script = db.Column(db.Text, nullable=True)  # For automated checks


class NetworkConfig(db.Model):
    """Global network speed limit settings."""
    id = db.Column(db.Integer, primary_key=True)
    download_kbps = db.Column(db.Integer, default=0)  # 0 = unlimited
    upload_kbps = db.Column(db.Integer, default=0)     # 0 = unlimited


class NetworkWhitelist(db.Model):
    """IPs/CIDRs excluded from speed limits."""
    id = db.Column(db.Integer, primary_key=True)
    cidr = db.Column(db.String(50), unique=True, nullable=False)
    note = db.Column(db.String(255), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class QuizAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
    solved_at = db.Column(db.DateTime, nullable=True)

    question = db.relationship('QuizQuestion')
