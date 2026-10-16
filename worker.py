import time
from datetime import datetime, timedelta

import requests
from flask import Flask

from app_common import Job, configure, db, get_token, value

app = Flask(__name__)
configure(app)


def telegram_send(token, job):
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": job.channel, "text": job.text}, timeout=30,
    )
    data = response.json()
    if not response.ok or not data.get("ok"):
        raise RuntimeError(data.get("description", f"Telegram HTTP {response.status_code}"))
    message_id = (data.get("result") or {}).get("message_id")
    if message_id and str(job.channel).startswith("@"):
        job.telegram_link = f"https://t.me/{job.channel.lstrip('@')}/{message_id}"


def run_once():
    token = get_token()
    if not token:
        return
    now = datetime.utcnow()
    # يرسل المواعيد التي فاتت خلال ساعتين فقط، ولا يعيد نشر القديم جدًا.
    jobs = (Job.query.filter(Job.status == "pending", Job.due_at <= now,
                             Job.due_at >= now - timedelta(hours=2))
            .order_by(Job.due_at).limit(20).all())
    for job in jobs:
        if value(f"paused_{job.channel}", "0") == "1":
            continue
        try:
            telegram_send(token, job)
            job.status, job.sent_at, job.error = "sent", datetime.utcnow(), None
        except Exception as exc:
            job.status, job.error = "failed", str(exc)[:900]
        db.session.commit()


if __name__ == "__main__":
    while True:
        with app.app_context():
            run_once()
        time.sleep(20)
