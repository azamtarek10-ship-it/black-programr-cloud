import os
import secrets
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

import requests

from flask import Flask, flash, redirect, render_template_string, request, session, url_for

from app_common import Job, Media, configure, db, get_token, set_value, value

CAIRO = ZoneInfo("Africa/Cairo")
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_urlsafe(32))
configure(app)

# إعدادات القنوات الافتراضية تُحفظ في قاعدة البيانات أول مرة فقط.
DEFAULTS = {
    "channel_0": "@FOOX_HUUB", "contact_0": "@EAr_ay",
    "channel_1": "@Cretaiveplus", "contact_1": "",
    "channel_2": "", "contact_2": "",
}
with app.app_context():
    for _key, _default in DEFAULTS.items():
        if not value(_key):
            set_value(_key, _default)
    # FOOX متوقف مؤقتًا بناءً على طلب صاحب المشروع.
    set_value("paused_@FOOX_HUUB", "1")
    db.session.commit()
    db.session.commit()


def _send_due_jobs():
    """Run the scheduler inside the always-on web service as a safety net."""
    while True:
        try:
            with app.app_context():
                token = get_token()
                now = datetime.utcnow()
                if token:
                    jobs = (Job.query.filter(Job.status == "pending", Job.due_at <= now,
                                             Job.due_at >= now - timedelta(hours=2))
                            .order_by(Job.due_at).limit(20).all())
                    for job in jobs:
                        if value(f"paused_{job.channel}", "0") == "1":
                            continue
                        try:
                            method = "sendVideo" if job.media and job.media.mime.startswith("video/") else ("sendPhoto" if job.media else "sendMessage")
                            endpoint = f"https://api.telegram.org/bot{token}/{method}"
                            if job.media:
                                field = "video" if method == "sendVideo" else "photo"
                                response = requests.post(endpoint, data={"chat_id": job.channel, "caption": job.text}, files={field: (job.media.filename, job.media.data, job.media.mime)}, timeout=120)
                            else:
                                response = requests.post(endpoint, json={"chat_id": job.channel, "text": job.text}, timeout=30)
                            data = response.json()
                            if not response.ok or not data.get("ok"):
                                raise RuntimeError(data.get("description", "Telegram send failed"))
                            job.status, job.sent_at, job.error = "sent", datetime.utcnow(), None
                        except Exception as exc:
                            job.status, job.error = "failed", str(exc)[:900]
                    if jobs:
                        db.session.commit()
        except Exception:
            # The dashboard must remain available even during a temporary DB/network issue.
            db.session.rollback()
        time.sleep(20)


threading.Thread(target=_send_due_jobs, name="telegram-scheduler", daemon=True).start()

POSTS = [
    [
        "لو هتسجل على 22 بت، اكتب البروموكود MSA1 وقت التسجيل.\nبعد التسجيل ابعت صورة تسجيل ظاهر فيها البروموكود، وبعد الإيداع ابعت صورة الإيداع عشان نبدأ طلب تفعيل السكربت.",
        "عايز تبدأ على 22 بت؟ الخطوات بسيطة:\nسجّل بالبروموكود MSA1، اعمل الإيداع المناسب لك، وبعدها ابعت صورتين: تسجيل واضح + إيداع واضح.",
        "أول ما تخلص تسجيل 22 بت بالبروموكود MSA1، جهّز صورة التسجيل وصورة الإيداع وابعتهم في رسالة واحدة لطلب تفعيل السكربت.",
        "خدها خطوة خطوة 👌\n22 بت فقط — البروموكود MSA1 — ثم صورة من صفحة التسجيل وصورة من تأكيد الإيداع لإرسال طلب السكربت.",
        "لو التسجيل تم على 22 بت، متنساش الصورة المطلوبة: لقطة يظهر فيها البروموكود MSA1، ولقطة ثانية لتأكيد الإيداع. بعدها نبدأ طلب السكربت.",
        "رسالة للي داخل جديد 🔥\nاستخدم MSA1 في 22 بت، وبعد الإيداع ابعت صورة التسجيل وصورة العملية، عشان نعرف نتابع طلب تفعيل السكربت.",
        "الطريقة واضحة: تسجيل 22 بت بالبروموكود MSA1، ثم إيداع تختاره أنت، ثم إرسال صورتين للتأكد من الطلب: التسجيل والإيداع.",
        "قبل ما تبعت الطلب، تأكد إن عندك صورتين منفصلتين: صورة تسجيل يظهر فيها MSA1 وصورة إيداع. ابعتهم لطلب تفعيل السكربت على 22 بت.",
    ],
    [
        "يا كبير، جاهز تبدأ؟ 🐯\nخدها بهدوء: سجّل، اكتب SMA1، وبعدها راجع الشروط قبل أي تأكيد.\nالحد الأدنى للإيداع 140.",
        "مفيش حاجة اسمها سؤال بايخ.\nلو وقفت في خانة أو خطوة، اكتب لنا إيه اللي ظهر قدامك ونوضح لك الطريق.\nالبروموكود SMA1 والبداية 140.",
        "خلي أول خطوة محسوبة ✅\nاملأ بياناتك، تأكد إن كل حاجة مكتوبة صح، وحط SMA1 في مكان البروموكود.\nبعدها شوف تفاصيل الإيداع من 140.",
        "رسالة من صاحبك اللي عايز يسهّلها عليك: متجريش ورا السرعة.\nاقرأ القواعد، استخدم SMA1، وخد قرارك بالمبلغ اللي يناسبك — الحد الأدنى 140.",
        "لو لسه فاتح التسجيل، سيب دقيقة للمراجعة.\nSMA1 وقت إنشاء الحساب، والإيداع يبدأ من 140، وكل التفاصيل مكتوبة قدامك.",
        "النهارده نبدأها صح؟ 👌\nافتح الحساب، أضف SMA1، راجع الخطوات واحدة واحدة، وبعدها كمل باللي يناسبك.\nالبداية من 140.",
        "عايز تعرف المختصر؟\nالبروموكود SMA1، الحد الأدنى 140، والشروط لازم تتقري قبل ما تعتمد أي خطوة.\nلو محتاج شرح اسألنا.",
        "قبل ما تخلص التسجيل، بص على البيانات مرة أخيرة.\nالغلط الصغير بيعمل لخبطة، فخليك هادي واستخدم SMA1 وخلي البداية من 140 أو أكثر حسب اختيارك.",
    ],
    [
        "مساء الخير يا صديقي ✨\nلو هتسجل لأول مرة، اكتب SMA1 في خانة البروموكود وراجع الصفحة براحتك.\nأقل إيداع 140.",
        "خلينا نتكلم ببساطة: التسجيل خطوة، والمراجعة خطوة أهم.\nاستخدم SMA1، اقرأ شروط الإيداع والسحب، وبعدها شوف البداية المناسبة لك من 140.",
        "لو دي أول مرة، اسأل عادي 👋\nابدأ بفتح الحساب، اكتب SMA1، ولو ظهر لك شيء مش واضح اكتب لنا ونشرح لك الخطوة.",
        "متاخدش قرارك وأنت مستعجل.\nراجع الاسم والمبلغ والقواعد، وخلي في بالك إن الحد الأدنى للإيداع 140 والبروموكود SMA1.",
        "رسالة بسيطة قبل البداية: مفيش داعي للكلام الكبير.\nالتفاصيل واضحة، SMA1 للتسجيل، و140 هو الحد الأدنى، والباقي تختاره بعد ما تفهم.",
        "صباحكم هادي 🌟\nلو فاتح صفحة التسجيل، جهّز SMA1 وخد وقتك في قراءة الشروط.\nابدأ من 140 أو المبلغ اللي يناسبك.",
        "أول خطوة مش محتاجة توتر.\nاكتب SMA1، راجع كل خانة، وبعدها قرر بهدوء.\nالحد الأدنى للإيداع 140.",
        "قبل نهاية التسجيل، اعمل مراجعة صغيرة ✅\nالبروموكود SMA1 موجود، والشروط قدامك، والبداية من 140. كمل فقط وأنت فاهم الخطوة.",
    ],
    [
        "لو هتجرب WowBet، اكتب البروموكود MSA1 أثناء التسجيل.\nبعدها راجع البيانات والشروط، ولو تم الإيداع ابعت صورة تسجيل وصورة إيداع بدون أي معلومات حساسة.",
        "خطوات WowBet بسيطة وواضحة:\nسجّل بالبروموكود MSA1، والحد الأدنى للإيداع 145 جنيه، ثم احتفظ بإثبات التسجيل والإيداع بعد إخفاء البيانات الخاصة.",
        "قبل ما تكمل على WowBet، تأكد إن MSA1 ظاهر في صفحة التسجيل.\nبعد الإيداع، أرسل لقطتين منفصلتين: التسجيل والإيداع، مع تغطية الأرقام والبيانات الحساسة.",
        "رسالة سريعة للي داخل جديد 👋\nWowBet + البروموكود MSA1، والبداية من 145 جنيه. اقرأ الشروط بهدوء وخد قرارك بالمبلغ المناسب لك.",
        "اختار وقتك وخدها خطوة خطوة:\nافتح حساب WowBet، أضف MSA1، راجع التفاصيل، ثم أكمل بإيداع يبدأ من 145 جنيه إذا كان مناسبًا لك.",
        "لو التسجيل خلص، راجع إن البروموكود هو MSA1 قبل أي إيداع.\nوعند إرسال الإثبات، خلي صورة التسجيل وصورة الإيداع واضحتين ومن غير بيانات شخصية.",
        "المختصر المفيد لـ WowBet:\nMSA1 في خانة البروموكود، والحد الأدنى 145 جنيه، والشروط قدامك قبل أي خطوة. اسأل لو في خانة مش واضحة.",
        "نظّم خطواتك من البداية ✅\nسجّل على WowBet باستخدام MSA1، اقرأ شروط الإيداع والسحب، وبعدها ابعت إثبات التسجيل والإيداع بعد إخفاء أي معلومات حساسة.",
    ],
]

DAILY_ENDINGS = [
    "لو محتاج تفصيل في خطوة، اسألنا ونوضحها لك.",
    "خد وقتك، واقرأ الشروط قبل ما تكمل.",
    "المهم تبدأ وأنت فاهم كل خطوة.",
    "اكتب سؤالك بوضوح ونساعدك في الخطوة التالية.",
    "اختار اللي يناسبك من غير استعجال.",
    "تابع التحديثات الجديدة أولًا بأول.",
    "كل خطوة واضحة لما تمشي فيها واحدة واحدة.",
    "لو ظهر لك شيء غير مفهوم، ابعته ونشرحه لك.",
]


def unique_daily_text(channel_index, post_index, day, used):
    """Choose a never-before-used exact text, rotating both body and ending."""
    bodies = POSTS[channel_index]
    body_shift = (day.toordinal() + channel_index * 11) % len(bodies)
    ending_shift = (day.toordinal() // 7 + channel_index * 3) % len(DAILY_ENDINGS)
    for attempt in range(len(bodies) * len(DAILY_ENDINGS)):
        body = bodies[(post_index + body_shift + attempt) % len(bodies)]
        ending = DAILY_ENDINGS[(post_index + ending_shift + attempt) % len(DAILY_ENDINGS)]
        candidate = f"{body}\n\n{ending}"
        if candidate not in used:
            used.add(candidate)
            return candidate
    # This branch is only reached after all combinations were consumed;
    # the date marker still guarantees an exact-text difference.
    candidate = f"{bodies[(post_index + body_shift) % len(bodies)]}\n\n{DAILY_ENDINGS[ending_shift]}\n\nتحديث {day.isoformat()} — منشور {post_index + 1}"
    used.add(candidate)
    return candidate


def require_login(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def cairo_now():
    return datetime.now(CAIRO)


def to_utc(text):
    local = datetime.strptime(text, "%Y-%m-%dT%H:%M").replace(tzinfo=CAIRO)
    return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def cairo_text(moment):
    return moment.replace(tzinfo=ZoneInfo("UTC")).astimezone(CAIRO).strftime("%Y-%m-%d %H:%M")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        expected = os.environ.get("ADMIN_PASSWORD", "")
        if expected and secrets.compare_digest(request.form.get("password", ""), expected):
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("كلمة الدخول غير صحيحة أو لم تُضف بعد في Railway.", "error")
    return render_template_string(BASE, body="""
      <section class='login'><h1>BLACK PROGRAMR</h1><p>لوحة الجدولة السحابية</p>
      <form method='post'><input type='password' name='password' placeholder='كلمة دخول الإدارة' required><button>دخول</button></form></section>""")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
@require_login
def dashboard():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "settings":
            for index in range(2):
                set_value(f"channel_{index}", request.form.get(f"channel_{index}", "").strip())
                set_value(f"contact_{index}", request.form.get(f"contact_{index}", "").strip())
                set_value(f"paused_{request.form.get(f'channel_{index}', '').strip()}", "1" if request.form.get(f"paused_{index}") else "0")
            db.session.commit(); flash("تم حفظ القنوات ويوزر التواصل.", "ok")
        elif action == "manual":
            try:
                due = to_utc(request.form["due_at"])
                if due <= datetime.utcnow(): raise ValueError("اختار موعدًا في المستقبل.")
                channel = request.form["channel"].strip(); text = request.form["text"].strip()
                if not channel or not text: raise ValueError("اكتب القناة ونص المنشور.")
                job = Job(channel=channel, text=text, due_at=due)
                upload = request.files.get("media")
                if upload and upload.filename:
                    raw = upload.read()
                    if len(raw) > 45 * 1024 * 1024: raise ValueError("حجم الملف كبير؛ استخدم ملفًا أقل من 45 ميجابايت.")
                    mime = upload.mimetype or "application/octet-stream"
                    if not (mime.startswith("image/") or mime.startswith("video/")): raise ValueError("ارفع صورة أو فيديو فقط.")
                    job.media = Media(filename=upload.filename, mime=mime, data=raw)
                db.session.add(job); db.session.commit(); flash("تمت الجدولة.", "ok")
            except Exception as exc: flash(str(exc), "error")
        elif action == "daily":
            try:
                date = datetime.strptime(request.form["day"], "%Y-%m-%d").date()
                today = cairo_now().date()
                if date < today: raise ValueError("اختر اليوم أو يومًا قادمًا.")
                base = cairo_now().replace(second=0, microsecond=0) if date == today else datetime.combine(date, datetime.min.time()).replace(tzinfo=CAIRO) + timedelta(hours=12)
                if date == today: base += timedelta(minutes=(10 - base.minute % 10) % 10)
                # استبدال خطة اليوم السحابية فقط، من دون لمس المنشورات اليدوية.
                start = datetime.combine(date, datetime.min.time()).replace(tzinfo=CAIRO).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
                end = start + timedelta(days=1)
                # عند إعادة إنشاء الخطة، احذف كل المنشورات المعلّقة لذلك اليوم
                # حتى لا تختلط القوالب القديمة بالجديدة.
                Job.query.filter(Job.due_at >= start, Job.due_at < end, Job.status == "pending").delete(synchronize_session=False)
                made = 0
                for ci in range(2):
                    channel = value(f"channel_{ci}")
                    contact = value(f"contact_{ci}")
                    if not channel: continue
                    # امنع التكرار النصي مع أي منشور سابق لنفس القناة.
                    used = {row.text for row in Job.query.filter(Job.channel == channel).all()}
                    for pi in range(8):
                        text = unique_daily_text(ci, pi, date, used)
                        if contact: text += "\n\n" + contact
                        # بوست جديد كل ساعة؛ فرق 5 دقائق فقط بين القنوات.
                        due = (base + timedelta(minutes=pi * 70 + ci * 5)).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
                        db.session.add(Job(channel=channel, text=text, due_at=due, source="daily")); made += 1
                db.session.commit(); flash(f"تم وضع {made} منشورًا مختلفًا لخطة اليوم.", "ok")
            except Exception as exc: db.session.rollback(); flash(str(exc), "error")
        elif action == "bulk_122":
            try:
                channel = value("channel_1") or "@Cretaiveplus"
                if not channel: raise ValueError("أضف قناة Cretaiveplus أولًا.")
                now = cairo_now().replace(second=0, microsecond=0)
                finish = now.replace(hour=22, minute=0)
                if now >= finish: raise ValueError("الوقت الحالي بعد 10 مساءً؛ أنشئ الخطة غدًا.")
                # إيقاف FOOX وإلغاء أي منشورات معلّقة له حتى لا يرسل أثناء التجربة.
                set_value("paused_@FOOX_HUUB", "1")
                Job.query.filter(Job.channel == value("channel_0"), Job.status == "pending").update({"status": "cancelled"}, synchronize_session=False)
                # استبدال خطة Cretaiveplus المعلّقة لليوم فقط.
                start_utc = datetime.combine(now.date(), datetime.min.time()).replace(tzinfo=CAIRO).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
                end_utc = start_utc + timedelta(days=1)
                Job.query.filter(Job.channel == channel, Job.due_at >= start_utc, Job.due_at < end_utc, Job.status == "pending").delete(synchronize_session=False)
                used = {row.text for row in Job.query.filter(Job.channel == channel).all()}
                span_seconds = max(60, int((finish - now).total_seconds()))
                for index in range(122):
                    text = unique_daily_text(1, index, now.date(), used)
                    due = now + timedelta(seconds=(span_seconds * index / 121 if index else 0))
                    db.session.add(Job(channel=channel, text=text, due_at=due.astimezone(ZoneInfo("UTC")).replace(tzinfo=None), source="bulk-122"))
                db.session.commit()
                interval = span_seconds / 121 / 60
                flash(f"تم إيقاف FOOX وجدولة 122 منشورًا لـ {channel} حتى 10 مساءً (فاصل تقريبي {interval:.1f} دقيقة).", "ok")
            except Exception as exc: db.session.rollback(); flash(str(exc), "error")
        elif action == "delete":
            job = db.session.get(Job, int(request.form["job_id"]))
            if job and job.status == "pending": db.session.delete(job); db.session.commit(); flash("تم حذف المنشور.", "ok")
        elif action == "edit":
            try:
                job = db.session.get(Job, int(request.form["job_id"]))
                if not job or job.status != "pending": raise ValueError("لا يمكن تعديل هذا المنشور الآن.")
                new_text = request.form.get("text", "").strip()
                new_time = to_utc(request.form["due_at"])
                if not new_text or new_time <= datetime.utcnow(): raise ValueError("اكتب نصًا وموعدًا مستقبليًا.")
                duplicate = Job.query.filter(Job.channel == job.channel, Job.text == new_text, Job.id != job.id).first()
                if duplicate: raise ValueError("هذا النص مستخدم بالفعل لنفس القناة.")
                job.text, job.due_at = new_text, new_time
                db.session.commit(); flash("تم تعديل المنشور.", "ok")
            except Exception as exc: db.session.rollback(); flash(str(exc), "error")
        return redirect(url_for("dashboard"))
    jobs = Job.query.order_by(Job.due_at.desc()).limit(80).all()
    stats = {status: Job.query.filter(Job.status == status).count() for status in ("pending", "sent", "failed")}
    channels = [(value(f"channel_{index}"), value(f"contact_{index}")) for index in range(2) if value(f"channel_{index}")]
    channel_paused = [value(f"paused_{channel}", "0") == "1" for channel, _ in channels]
    inner = render_template_string(
        DASHBOARD,
        jobs=jobs,
        channels=channels,
        cairo_text=cairo_text,
        today=cairo_now().date().isoformat(),
        token_ready=bool(get_token()),
        stats=stats,
        channel_paused=channel_paused,
    )
    return render_template_string(BASE, body=inner)


BASE = """<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>BLACK PROGRAMR</title><style>
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% 0,#21133d 0,#0d0d14 40%);color:#eee;font-family:Tahoma,Arial,sans-serif}.wrap{max-width:1180px;margin:auto;padding:32px}h1{margin:0;color:#b57bff;letter-spacing:.5px}h2{font-size:18px;margin:0 0 16px;color:#eee}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:26px}.tag{color:#bd8bff}.card{background:rgba(25,25,36,.94);border:1px solid #37324f;border-radius:16px;padding:22px;margin-bottom:18px;box-shadow:0 10px 30px rgba(0,0,0,.16)}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.fields{display:grid;grid-template-columns:1fr;gap:10px;max-width:520px}label{display:block;color:#c5bfd8;font-size:13px;margin-bottom:6px}input,textarea,select{width:100%;background:#11111b;border:1px solid #514866;border-radius:10px;color:white;padding:12px;font:inherit}input:focus,textarea:focus,select:focus{outline:2px solid #8f5af7;border-color:#9e6bff}textarea{min-height:120px;resize:vertical}button{background:linear-gradient(135deg,#9b63ff,#7140d3);color:white;border:0;border-radius:10px;padding:12px 18px;font-weight:bold;cursor:pointer;box-shadow:0 5px 14px rgba(126,74,231,.25)}button:hover{filter:brightness(1.12);transform:translateY(-1px)}.danger{background:#df4d74}.muted{color:#aaa4ba;font-size:13px;line-height:1.8}.flash{padding:12px;border-radius:10px;margin-bottom:14px}.ok{background:#163a2a}.error{background:#4a1e2c}.stats{display:flex;gap:12px;flex-wrap:wrap}.stats span{background:#11111b;border:1px solid #514866;border-radius:10px;padding:12px 18px;color:#dfd2ff}.pause{margin-top:10px;display:flex;align-items:center;gap:6px}.pause input{width:auto}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:12px;text-align:right;border-bottom:1px solid #353248;vertical-align:top}.pending{color:#e6c15a}.sent{color:#65d99a}.failed{color:#ff6a86}.login{max-width:420px;margin:15vh auto;text-align:center}.login input{margin:18px 0}@media(max-width:760px){.grid{grid-template-columns:1fr}.wrap{padding:16px}table{font-size:11px}}
</style></head><body><main class='wrap'>{{ body|safe }}</main></body></html>"""

DASHBOARD = """<div class='top'><div><h1>BLACK PROGRAMR</h1><div class='muted'>جدولة تليجرام السحابية — توقيت القاهرة</div></div><div><span class='tag'>{{ 'البوت جاهز' if token_ready else 'أضف توكن البوت في Railway' }}</span> · <a href='/logout' style='color:#ddd'>خروج</a></div></div>
{% with messages=get_flashed_messages(with_categories=true) %}{% for category,msg in messages %}<div class='flash {{category}}'>{{msg}}</div>{% endfor %}{% endwith %}
<section class='card'><h2>ملخص سريع</h2><div class='stats'><span>معلّق: {{stats['pending']}}</span><span>تم إرساله: {{stats['sent']}}</span><span>فشل: {{stats['failed']}}</span></div></section>
<section class='card'><h2>إعدادات القنوات</h2><p class='muted'>FOOX وCretaiveplus يعملان بشكل مستقل. اترك يوزر التواصل فارغًا إذا لم ترد إضافته أسفل المنشور.</p><form method='post'><input type='hidden' name='action' value='settings'><div class='fields'><label>FOOX HUB</label><input name='channel_0' value='{{channels[0][0] if channels|length > 0 else "@FOOX_HUUB"}}' placeholder='@FOOX_HUUB'><label>يوزر التواصل في FOOX</label><input name='contact_0' value='{{channels[0][1] if channels|length > 0 else ""}}' placeholder='@username'><label class='pause'><input type='checkbox' name='paused_0' {% if channel_paused[0] %}checked{% endif %}> إيقاف FOOX مؤقتًا</label><label>القناة الجديدة</label><input name='channel_1' value='{{channels[1][0] if channels|length > 1 else "@Cretaiveplus"}}' placeholder='@Cretaiveplus'><label>يوزر التواصل في Cretaiveplus</label><input name='contact_1' value='{{channels[1][1] if channels|length > 1 else ""}}' placeholder='@username'><label class='pause'><input type='checkbox' name='paused_1' {% if channel_paused|length > 1 and channel_paused[1] %}checked{% endif %}> إيقاف Cretaiveplus مؤقتًا</label></div><p><button>حفظ إعدادات القنوات</button></p></form></section>
<div class='grid'><section class='card'><h2>إضافة منشور يدوي</h2><form method='post' enctype='multipart/form-data'><input type='hidden' name='action' value='manual'><label>القناة</label><select name='channel'>{% for channel,contact in channels %}<option value='{{channel}}'>{{channel}}</option>{% endfor %}</select><label>الموعد</label><input name='due_at' type='datetime-local' required><label>النص</label><textarea name='text' required></textarea><label>صورة أو فيديو اختياري</label><input name='media' type='file' accept='image/*,video/*'><button>إضافة للجدول</button></form></section>
<section class='card'><h2>خطة اليوم</h2><p class='muted'>8 بوستات مختلفة لكل قناة، بفاصل ساعة و10 دقائق، من وقتك الحالي اليوم أو 12:00 ظهرًا في اليوم القادم.</p><form method='post'><input type='hidden' name='action' value='daily'><label>التاريخ</label><input type='date' name='day' value='{{today}}' required><p><button>إنشاء خطة اليوم للقناتين</button></p></form></section>
<section class='card'><h2>خطة Cretaiveplus المكثفة</h2><p class='muted'>توقف FOOX مؤقتًا وتضع 122 منشورًا مختلفًا في Cretaiveplus من الآن حتى 10 مساءً. الفاصل يُحسب تلقائيًا حسب الوقت المتبقي، وقد يكون قصيرًا؛ تأكد من قواعد Telegram قبل التشغيل.</p><form method='post'><input type='hidden' name='action' value='bulk_122'><button>إيقاف FOOX وجدولة 122 لـ Cretaiveplus</button></form></section>
<section class='card'><h2>تشغيل دائم</h2><p class='muted'>خدمة Worker هي التي ترسل، فلا يلزم فتح اللابتوب. لا تضع التوكن في GitHub؛ أضفه كمتغير سري في Railway فقط.</p></section></div>
<section class='card'><h2>الجدول والسجل</h2><table><tr><th>موعد القاهرة</th><th>القناة</th><th>المنشور</th><th>الحالة</th><th>إجراء</th></tr>{% for job in jobs %}<tr><td>{{cairo_text(job.due_at)}}</td><td>{{job.channel}}</td><td style='white-space:pre-line'>{{job.text}}</td><td class='{{job.status}}'>{{job.status}}{% if job.error %}<br>{{job.error}}{% endif %}</td><td>{% if job.status=='pending' %}<details><summary>تعديل</summary><form method='post'><input type='hidden' name='action' value='edit'><input type='hidden' name='job_id' value='{{job.id}}'><textarea name='text' required>{{job.text}}</textarea><input name='due_at' type='datetime-local' required><button>حفظ التعديل</button></form></details><form method='post'><input type='hidden' name='action' value='delete'><input type='hidden' name='job_id' value='{{job.id}}'><button class='danger'>حذف</button></form>{% endif %}</td></tr>{% endfor %}</table></section>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
