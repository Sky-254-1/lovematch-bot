import os
import sqlite3
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
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
        "💘 LoveMatch Pro\n\nCreate profile, upload photo, and start matching 🔥",
        reply_markup=keyboard
    )

# --- PROFILE ---
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send: Name, Age, Bio")

async def save_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        name, age, bio = update.message.text.split(",", 2)

        cursor.execute("""
        INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)
        """, (user_id, name.strip(), int(age.strip()), bio.strip()))

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
    await update.message.reply_text("Send age range like: 18-30")

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

# --- MAIN ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("filter", set_filter))

    print("🔥 Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
