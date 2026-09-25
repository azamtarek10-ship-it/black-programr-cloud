import os
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import LargeBinary

db = SQLAlchemy()


class Setting(db.Model):
    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=False, default="")


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(160), nullable=False)
    text = db.Column(db.Text, nullable=False)
    due_at = db.Column(db.DateTime, nullable=False, index=True)
    status = db.Column(db.String(32), nullable=False, default="pending")
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    source = db.Column(db.String(32), nullable=False, default="manual")
    media = db.relationship("Media", backref="job", uselist=False, cascade="all, delete-orphan")


class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False, unique=True)
    filename = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(120), nullable=False)
    data = db.Column(LargeBinary, nullable=False)


def configure(app):
    database_url = os.environ.get("DATABASE_URL", "sqlite:///black_programr.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()


def value(key, fallback=""):
    item = db.session.get(Setting, key)
    return item.value if item else fallback


def set_value(key, new_value):
    item = db.session.get(Setting, key)
    if item is None:
        item = Setting(key=key, value=new_value)
        db.session.add(item)
    else:
        item.value = new_value


def get_token():
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or value("telegram_token").strip()
