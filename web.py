import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Flask, flash, redirect, render_template_string, request, session, url_for

from app_common import Job, configure, db, get_token, set_value, value

CAIRO = ZoneInfo("Africa/Cairo")
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_urlsafe(32))
configure(app)

POSTS = [
    [
        "🎯 FOOX HUB\nSpinBetter يبدأ من 120، و22Bet يبدأ من 190. لو هتسجل، اكتب MSA1 ثم راجع القواعد قبل الإيداع.",
        "🟣 اختيارك في FOOX واضح: SpinBetter بحد أدنى 120 أو 22Bet بحد أدنى 190. البروموكود MSA1 يُكتب في التسجيل.",
        "مش محتاج تلف كتير: 120 لبداية SpinBetter، و190 لبداية 22Bet. خُد قرارك بعد ما تقرأ شروط المنصة.",
        "📍 تفاصيل FOOX من غير زحمة: MSA1 للتسجيل، SpinBetter من 120، و22Bet من 190. بيانات حسابك تفضل خاصة بك.",
        "⚡ قبل ما تبدأ: اختار المنصة، سجّل بالكود MSA1، واعرف أن SpinBetter من 120 و22Bet من 190. راجع الشروط الرسمية.",
    ],
    [
        "🐯 TIGER BET\nعايز تفتح حساب؟ MSA1 هو كود التسجيل، والحد الأدنى للإيداع 140. امشِ خطوة خطوة وراجع بياناتك.",
        "يا شباب تايجر، البداية مش سباق: حط MSA1 عند التسجيل، واعرف أن الإيداع يبدأ من 140. لا تشارك كلمة السر مع أحد.",
        "🔶 رسالة TIGER BET: البروموكود MSA1، وقيمة البداية 140. لو في تفصيلة مش واضحة اسأل قبل ما تعتمد أي عملية.",
        "الهدوء أهم من الاستعجال 🐅 سجّل معلوماتك صح، أضف MSA1، واقرأ الشروط. الحد الأدنى في TIGER BET هو 140.",
        "🟠 الكلام المختصر لتايجر: MSA1 عند إنشاء الحساب و140 أقل إيداع. تابع الشروط الرسمية بنفسك قبل التأكيد.",
    ],
    [
        "✨ GOLDEN WOL\nخانة التسجيل فيها MSA1، وأقل إيداع 140. خذ وقتك في فهم التفاصيل قبل ما تكمل.",
        "أهل جولدن 👋 المعلومة المهمة: MSA1 وقت فتح الحساب، والإيداع يبدأ من 140. لا تعتمد على رسائل من أشخاص مجهولين.",
        "🌙 GOLDEN WOL بيحب الوضوح: كود MSA1 للتسجيل، و140 كبداية للإيداع. راجع القواعد بعينك.",
        "مش كلام كتير: سجّل بـ MSA1 لو مناسب لك، وخلي في بالك أن الحد الأدنى 140. أمان حسابك مسؤوليتك.",
        "🌟 داخل GOLDEN WOL لأول مرة؟ اكتب MSA1، ثم اقرأ الشروط. مبلغ البداية المحدد هو 140.",
    ],
]


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
            for index in range(3):
                set_value(f"channel_{index}", request.form.get(f"channel_{index}", "").strip())
                set_value(f"contact_{index}", request.form.get(f"contact_{index}", "").strip())
            db.session.commit(); flash("تم حفظ القنوات ويوزر التواصل.", "ok")
        elif action == "manual":
            try:
                due = to_utc(request.form["due_at"])
                if due <= datetime.utcnow(): raise ValueError("اختار موعدًا في المستقبل.")
                channel = request.form["channel"].strip(); text = request.form["text"].strip()
                if not channel or not text: raise ValueError("اكتب القناة ونص المنشور.")
                db.session.add(Job(channel=channel, text=text, due_at=due)); db.session.commit(); flash("تمت الجدولة.", "ok")
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
                Job.query.filter(Job.source == "daily", Job.due_at >= start, Job.due_at < end, Job.status == "pending").delete(synchronize_session=False)
                made = 0
                for ci in range(3):
                    channel = value(f"channel_{ci}")
                    contact = value(f"contact_{ci}")
                    if not channel: continue
                    shift = date.timetuple().tm_yday % len(POSTS[ci])
                    for pi in range(5):
                        text = POSTS[ci][(pi + shift) % len(POSTS[ci])]
                        if contact: text += "\n\n" + contact
                        due = (base + timedelta(minutes=pi * 70 + ci * 20)).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
                        db.session.add(Job(channel=channel, text=text, due_at=due, source="daily")); made += 1
                db.session.commit(); flash(f"تم وضع {made} منشورًا مختلفًا لخطة اليوم.", "ok")
            except Exception as exc: db.session.rollback(); flash(str(exc), "error")
        elif action == "delete":
            job = db.session.get(Job, int(request.form["job_id"]))
            if job and job.status == "pending": db.session.delete(job); db.session.commit(); flash("تم حذف المنشور.", "ok")
        return redirect(url_for("dashboard"))
    jobs = Job.query.order_by(Job.due_at.desc()).limit(80).all()
    channels = [(value(f"channel_{i}"), value(f"contact_{i}")) for i in range(3)]
    return render_template_string(BASE, body=DASHBOARD, jobs=jobs, channels=channels, cairo_text=cairo_text, today=cairo_now().date().isoformat(), token_ready=bool(get_token()))


BASE = """<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>BLACK PROGRAMR</title><style>
*{box-sizing:border-box}body{margin:0;background:#0d0d14;color:#eee;font-family:Tahoma,Arial,sans-serif}.wrap{max-width:1180px;margin:auto;padding:28px}h1{margin:0;color:#a970ff}h2{font-size:18px;margin:0 0 16px;color:#ddd}.top{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}.tag{color:#a970ff}.card{background:#191924;border:1px solid #2b2b3d;border-radius:14px;padding:20px;margin-bottom:18px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.fields{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}label{display:block;color:#bdb9ce;font-size:13px;margin-bottom:6px}input,textarea,select{width:100%;background:#10101a;border:1px solid #424254;border-radius:8px;color:white;padding:11px;font:inherit}textarea{min-height:110px;resize:vertical}button{background:#8f5af7;color:white;border:0;border-radius:8px;padding:11px 16px;font-weight:bold;cursor:pointer}.danger{background:#e34a6f}.muted{color:#a5a1b4;font-size:13px}.flash{padding:10px;border-radius:8px;margin-bottom:14px}.ok{background:#163a2a}.error{background:#4a1e2c}table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:10px;text-align:right;border-bottom:1px solid #303041;vertical-align:top}.pending{color:#e6c15a}.sent{color:#65d99a}.failed{color:#ff6a86}.login{max-width:420px;margin:15vh auto;text-align:center}.login input{margin:18px 0}@media(max-width:760px){.grid,.fields{grid-template-columns:1fr}.wrap{padding:16px}table{font-size:11px}}
</style></head><body><main class='wrap'>{{ body|safe }}</main></body></html>"""

DASHBOARD = """<div class='top'><div><h1>BLACK PROGRAMR</h1><div class='muted'>جدولة تليجرام السحابية — توقيت القاهرة</div></div><div><span class='tag'>{{ 'البوت جاهز' if token_ready else 'أضف توكن البوت في Railway' }}</span> · <a href='/logout' style='color:#ddd'>خروج</a></div></div>
{% with messages=get_flashed_messages(with_categories=true) %}{% for category,msg in messages %}<div class='flash {{category}}'>{{msg}}</div>{% endfor %}{% endwith %}
<section class='card'><h2>القنوات ويوزر التواصل</h2><form method='post'><input type='hidden' name='action' value='settings'><div class='fields'>{% for i in range(3) %}<div><label>القناة {{i+1}}</label><input name='channel_{{i}}' value='{{channels[i][0]}}' placeholder='@channel'><label style='margin-top:10px'>يوزر التواصل</label><input name='contact_{{i}}' value='{{channels[i][1]}}' placeholder='@username'></div>{% endfor %}</div><p><button>حفظ الإعدادات</button></p></form></section>
<div class='grid'><section class='card'><h2>إضافة منشور يدوي</h2><form method='post'><input type='hidden' name='action' value='manual'><label>القناة</label><select name='channel'>{% for channel,contact in channels %}<option value='{{channel}}'>{{channel}}</option>{% endfor %}</select><label>الموعد</label><input name='due_at' type='datetime-local' required><label>النص</label><textarea name='text' required></textarea><button>إضافة للجدول</button></form></section>
<section class='card'><h2>خطة اليوم</h2><p class='muted'>5 بوستات مستقلة لكل قناة، من وقتك الحالي اليوم أو 12:00 ظهرًا في اليوم القادم.</p><form method='post'><input type='hidden' name='action' value='daily'><label>التاريخ</label><input type='date' name='day' value='{{today}}' required><p><button>إنشاء خطة اليوم</button></p></form></section>
<section class='card'><h2>تشغيل دائم</h2><p class='muted'>خدمة Worker هي التي ترسل، فلا يلزم فتح اللابتوب. لا تضع التوكن في GitHub؛ أضفه كمتغير سري في Railway فقط.</p></section></div>
<section class='card'><h2>الجدول والسجل</h2><table><tr><th>موعد القاهرة</th><th>القناة</th><th>المنشور</th><th>الحالة</th><th></th></tr>{% for job in jobs %}<tr><td>{{cairo_text(job.due_at)}}</td><td>{{job.channel}}</td><td style='white-space:pre-line'>{{job.text}}</td><td class='{{job.status}}'>{{job.status}}{% if job.error %}<br>{{job.error}}{% endif %}</td><td>{% if job.status=='pending' %}<form method='post'><input type='hidden' name='action' value='delete'><input type='hidden' name='job_id' value='{{job.id}}'><button class='danger'>حذف</button></form>{% endif %}</td></tr>{% endfor %}</table></section>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
