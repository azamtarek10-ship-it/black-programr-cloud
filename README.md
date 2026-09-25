# BLACK PROGRAMR Cloud

لوحة خاصة لجدولة منشورات تليجرام لثلاث قنوات، مع عامل نشر يعمل باستمرار.

## متغيرات Railway المطلوبة

- `DATABASE_URL`: رابط PostgreSQL من Railway.
- `ADMIN_PASSWORD`: كلمة دخول لوحة التحكم.
- `FLASK_SECRET`: نص عشوائي طويل للجلسات.
- `TELEGRAM_BOT_TOKEN`: توكن البوت من BotFather. لا يُرفع إلى GitHub.

أنشئ خدمتين من نفس المستودع في Railway: خدمة **Web** بالأمر `gunicorn --workers 1 --threads 4 --bind 0.0.0.0:$PORT web:app`، وخدمة **Worker** بالأمر `python worker.py`. أضف خدمة PostgreSQL واربط `DATABASE_URL` بالخدمتين.
