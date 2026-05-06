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
