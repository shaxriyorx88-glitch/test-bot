

import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Xatoliklarni kuzatib borish uchun sozlama (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ⚠️ BOT TOKENINGIZNI SHU YERGA YOZING:
TOKEN = "9078968898:AAHsT8Kt4iQAyYbxEM0v6AMWXj3XI4MCSdU"

# O'qituvchining (Admin) Telegram ID raqami
ADMIN_ID = 5552792356  # <-- O'z Telegram ID raqamingizga o'zgartiring!


# --- BAZA BILAN ISHLASH (Ma'lumotlarni saqlash) ---
def init_db():
    conn = sqlite3.connect('test_bot.db')
    cursor = conn.cursor()
    
    # O'quvchilar natijalari jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            score INTEGER
        )
    ''')
    
    # Test kalitlari va vaqtini saqlash jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY,
            key_data TEXT,
            expires_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Bazani ishga tushiramiz
init_db()


# --- BOT BUYRUQLARI VA FUNKSIYALARI ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    O'quvchi botga birinchi kirganda (/start) ishlaydigan funksiya.
    """
    user_name = update.effective_user.first_name
    msg = (
        f"Assalomu alaykum, {user_name}!\n\n"
        "🤖 Bu test tekshiruvchi bot.\n\n"
        "📝 **Test topshirish tartibi:**\n"
        "Javoblaringizni bitta xabarda, orasini bo'sh joy (probel) bilan ajratib yuboring (jami 35 ta javob).\n"
        "• 1-32 gacha: `a`, `b` yoki `c`\n"
        "• 33, 34, 35-savollar: 5 ta harfli birikma (masalan: `abcde`)\n\n"
        "🏆 Umumiy reytingni ko'rish uchun /rating buyrug'ini bosing."
    )
    await update.message.reply_text(msg, parse_mode='Markdown')


async def set_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    O'qituvchi uchun: Test kalitlari va vaqtini belgilash buyrug'i.
    Ishlatilish tartibi: /setanswers [minut] [35 ta kalit]
    Masalan: /setanswers 20 a b c ... abcde
    """
    text = update.message.text.replace('/setanswers', '').strip()
    parts = text.split()

    if len(parts) < 36:
        await update.message.reply_text(
            "❌ Xatolik! Format noto'g'ri.\n"
            "To'g'ri yozish: `/setanswers [minut] [35 ta javob]`\n"
            "Masalan: `/setanswers 15 a b c ... abcde`",
            parse_mode='Markdown'
        )
        return

    try:
        duration_minutes = int(parts[0])  # Test davomiyligi (daqiqa)
        answers = parts[1:36]             # 35 ta to'g'ri javob
    except ValueError:
        await update.message.reply_text("❌ Xatolik! Vaqtni raqam bilan yozing (masalan: 20).")
        return

    # Test tugash vaqtini hisoblaymiz
    expires_time = datetime.now() + timedelta(minutes=duration_minutes)
    expires_str = expires_time.strftime('%Y-%m-%d %H:%M:%S')

    # Bazaga saqlaymiz
    conn = sqlite3.connect('test_bot.db')
    cursor = conn.cursor()
    answers_str = " ".join(answers)
    cursor.execute('DELETE FROM answers')
    cursor.execute('INSERT INTO answers (id, key_data, expires_at) VALUES (1, ?, ?)', (answers_str, expires_str))
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Test muvaffaqiyatli yuklandi!\n"
        f"⏳ Belgilangan vaqt: **{duration_minutes} daqiqa**.\n"
        f"⏰ Tugash vaqti: {expires_time.strftime('%H:%M:%S')}"
    )


async def check_answers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    O'quvchi javob yuborganda ishlaydigan funksiya.
    Vaqt tugagan bo'lsa ham javobni qabul qiladi, tekshiradi va 
    to'g'ri/xatolar sonini chiqarib beradi.
    """
    text = update.message.text.strip().lower()
    answers = text.split()
    user_id = update.effective_user.id
    user_name = update.effective_user.full_name

    # Bazadan kalitlar va vaqtni o'qib olamiz
    conn = sqlite3.connect('test_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT key_data, expires_at FROM answers WHERE id = 1')
    row = cursor.fetchone()
    conn.close()

    if not row:
        await update.message.reply_text("⚠️ Hozircha o'qituvchi tomonidan test kalitlari kiritilmagan.")
        return

    correct_answers = row[0].split()
    expires_at_str = row[1]
    expires_at = datetime.strptime(expires_at_str, '%Y-%m-%d %H:%M:%S')

    # Vaqt tugaganligini aniqlash
    is_time_up = datetime.now() > expires_at

    # Javoblar soni 35 taligini tekshirish
    if len(answers) != 35:
        await update.message.reply_text(
            f"❌ Xatolik! Javoblar soni 35 ta bo'lishi kerak. Siz {len(answers)} ta yubordingiz.\n"
            "Iltimos, qaytadan barcha 35 ta javobni probel bilan yuboring."
        )
        return

    # Ballni va xatolarni hisoblash jarayoni
    score = 0
    errors = 0
    details = []

    for i in range(35):
        user_ans = answers[i]
        correct_ans = correct_answers[i]

        if user_ans == correct_ans:
            score += 1
        else:
            errors += 1
            details.append(f"{i+1}-savol: Sizda ({user_ans}) | To'g'risi: ({correct_ans})")

    # O'quvchi natijasini bazaga saqlash
    conn = sqlite3.connect('test_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO results (user_id, name, score)
        VALUES (?, ?, ?)
    ''', (user_id, user_name, score))
    conn.commit()
    conn.close()

    # Natija xabarini tayyorlash (vaqt tugagan bo'lsa eslatma qo'shiladi)
    time_status = "⚠️ (Vaqt tugagandan keyin topshirildi)" if is_time_up else "✅ (O'z vaqtida topshirildi)"

    result_text = (
        f"📊 **Test Natijangiz** {time_status}\n"
        f"👤 O'quvchi: {user_name}\n\n"
        f"✅ To'g'ri javoblar soni: **{score} ta**\n"
        f"❌ Xato javoblar soni: **{errors} ta**\n"
        f"🎯 Umumiy ball: **{score} / 35**\n\n"
        f"🏆 Reytingni ko'rish uchun /rating buyrug'ini bosing."
    )
    
    await update.message.reply_text(result_text, parse_mode='Markdown')


async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    O'quvchilar reytingini chiqarish buyrug'i (/rating).
    """
    conn = sqlite3.connect('test_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, score FROM results ORDER BY score DESC')
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Hali hech kim test topshirmadi.")
        return

    text = "🏆 **O'quvchilar Reytingi** 🏆\n\n"
    for idx, (name, score) in enumerate(rows, 1):
        text += f"{idx}. {name} — **{score} ball**\n"

    await update.message.reply_text(text, parse_mode='Markdown')


# --- BOTNI ISHGA TUSHIRISH ---
import os
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

def main():
    # Render'dagi Environment Variable'dan tokenni xavfsiz olish
    token = os.environ.get("TOKEN")
    
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setanswers", set_answers))
    app.add_handler(CommandHandler("rating", rating))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answers))

    print("Bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()

if __name__ == '__main__':
    main()