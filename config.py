import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///linux_lab.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'timeout': 30}}

    # Guacamole
    GUAC_URL = os.environ.get('GUAC_URL', 'http://localhost:8080/guacamole')
    GUAC_ADMIN_USER = os.environ.get('GUAC_ADMIN_USER', 'guacadmin')
    GUAC_ADMIN_PASS = os.environ.get('GUAC_ADMIN_PASS', 'guacadmin')

    # Email (SMTP)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_SSL = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_SENDER', 'lab@example.com')

    # LXD
    LXD_NETWORK = os.environ.get('LXD_NETWORK', 'lab-net')
    LXD_PROFILE = os.environ.get('LXD_PROFILE', 'lab-student')
    LXD_IMAGE = os.environ.get('LXD_IMAGE', 'images:debian/12')

    # Public URLs
    SITE_URL = os.environ.get('SITE_URL', 'http://localhost')
    GUAC_PUBLIC_URL = os.environ.get('GUAC_PUBLIC_URL', '/guacamole')

    # Admin credentials (first run)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')
