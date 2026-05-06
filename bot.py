import os
import sqlite3
import logging
import random
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)

# --- TOKEN ---
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN missing")

# --- DATABASE ---
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

# CREATE TABLES
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    age INTEGER,
    bio TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS likes (
    liker INTEGER,
    liked INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS seen (
    viewer INTEGER,
    seen_user INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    user1 INTEGER,
    user2 INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS photos (
    user_id INTEGER,
    file_id TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS filters (
    user_id INTEGER PRIMARY KEY,
    min_age INTEGER,
    max_age INTEGER
)
""")

conn.commit()

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [["/profile", "/find"], ["/filter"]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        "💘 *LoveMatch Pro*\n\n"
        "Create profile, upload photo, and start matching 🔥",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

# --- PROFILE ---
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send: Name, Age, Bio")

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        name, age, bio = update.message.text.split(",", 2)
        cursor.execute(
            "INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
            (user_id, name.strip(), int(age.strip()), bio.strip())
        )
        conn.commit()
        await update.message.reply_text("✅ Profile saved!")
    except:
        await update.message.reply_text("❌ Format: Name, Age, Bio")

# --- PHOTO ---
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file_id = update.message.photo[-1].file_id
    cursor.execute("DELETE FROM photos WHERE user_id=?", (user_id,))
    cursor.execute("INSERT INTO photos VALUES (?, ?)", (user_id, file_id))
    conn.commit()
    await update.message.reply_text("📸 Photo saved!")

# --- FILTER ---
async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send age range like:\n18-30")

async def save_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        min_age, max_age = map(int, update.message.text.split("-"))
        cursor.execute("DELETE FROM filters WHERE user_id=?", (user_id,))
        cursor.execute("INSERT INTO filters VALUES (?, ?, ?)", (user_id, min_age, max_age))
        conn.commit()
        await update.message.reply_text("✅ Filter saved!")
    except:
        await update.message.reply_text("❌ Format: 18-30")

# --- FIND ---
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # get filter
    cursor.execute("SELECT min_age, max_age FROM filters WHERE user_id=?", (user_id,))
    f = cursor.fetchone()

    if f:
        min_age, max_age = f
        cursor.execute("""
            SELECT * FROM users
            WHERE user_id != ?
            AND age BETWEEN ? AND ?
            AND user_id NOT IN (
                SELECT seen_user FROM seen WHERE viewer = ?
            )
        """, (user_id, min_age, max_age, user_id))
    else:
        cursor.execute("""
            SELECT * FROM users
            WHERE user_id != ?
            AND user_id NOT IN (
                SELECT seen_user FROM seen WHERE viewer = ?
            )
        """, (user_id, user_id))

    users = cursor.fetchall()

    if not users:
        await update.message.reply_text("😢 No more users")
        return

    target = random.choice(users)
    target_id, name, age, bio = target

    # mark seen
    cursor.execute("INSERT INTO seen VALUES (?, ?)", (user_id, target_id))
    conn.commit()

    # get photo
    cursor.execute("SELECT file_id FROM photos WHERE user_id=?", (target_id,))
    photo = cursor.fetchone()

    keyboard = [
        [
            InlineKeyboardButton("❤️ Like", callback_data=f"like_{target_id}"),
            InlineKeyboardButton("❌ Skip", callback_data="skip"),
        ]
    ]

    if photo:
        await update.message.reply_photo(
            photo=photo[0],
            caption=f"{name}, {age}\n\n{bio}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        await update.message.reply_text(
            f"{name}, {age}\n\n{bio}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

# --- BUTTON ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("like_"):
        liked_id = int(data.split("_")[1])

        cursor.execute("INSERT INTO likes VALUES (?, ?)", (user_id, liked_id))
        conn.commit()

        cursor.execute("""
            SELECT * FROM likes WHERE liker=? AND liked=?
        """, (liked_id, user_id))

        match = cursor.fetchone()

        if match:
            await query.edit_message_text("🎉 IT'S A MATCH! ❤️")
            cursor.execute("INSERT INTO matches VALUES (?, ?)", (user_id, liked_id))
            conn.commit()
            await context.bot.send_message(
                chat_id=liked_id,
                text="🎉 You got a match! Start chatting!"
            )
        else:
            await query.edit_message_text("❤️ Liked!")
    else:
        await query.edit_message_text("❌ Skipped")

    # Continue finding next user automatically
    await find(update, context)

# --- CHAT ---
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    cursor.execute("""
        SELECT user1, user2 FROM matches
        WHERE user1=? OR user2=?
    """, (user_id, user_id))

    matches = cursor.fetchall()

    for u1, u2 in matches:
        partner = u2 if u1 == user_id else u1
        try:
            await context.bot.send_message(
                chat_id=partner,
                text=f"💬 {text}"
            )
        except:
            pass

# --- SMART TEXT HANDLER ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "," in text:
        await save_profile(update, context)
    elif "-" in text and text.replace("-", "").isdigit():
        await save_filter(update, context)
    else:
        await chat(update, context)

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("filter", set_filter))

    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button))

    print("🔥 LoveMatch Pro running...")
    app.run_polling()

if __name__ == "__main__":
    main()
