import os
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from datetime import time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

WARSAW = ZoneInfo("Europe/Warsaw")
STARTING_DEBT = Decimal("497.66")

DB_FILE = "debt.db"


def get_db():
    return sqlite3.connect(DB_FILE)


def init_db():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute(
        "SELECT value FROM settings WHERE key = 'debt'"
    )

    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO settings (key, value) VALUES ('debt', ?)",
            (str(STARTING_DEBT),)
        )

    db.commit()
    db.close()


def get_debt():
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "SELECT value FROM settings WHERE key = 'debt'"
    )

    result = cursor.fetchone()
    db.close()

    return Decimal(result[0])


def set_debt(amount):
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "UPDATE settings SET value = ? WHERE key = 'debt'",
        (str(amount),)
    )

    db.commit()
    db.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    print(f"Adrian Chat ID: {chat_id}")

    await update.message.reply_text(
        "Bot działa. Twój Chat ID został zapisany w logach."
    )


async def debt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = get_debt()

    await update.message.reply_text(
        f"Aktualny dług Adriana wynosi {amount:.2f} PLN."
    )


async def increase_debt(context: ContextTypes.DEFAULT_TYPE):
    old_debt = get_debt()

    new_debt = (
        old_debt * Decimal("1.20")
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    set_debt(new_debt)

    chat_id = os.environ.get("ADRIAN_CHAT_ID")

    if not chat_id:
        print("Brak ADRIAN_CHAT_ID — dług został naliczony, ale wiadomość nie została wysłana.")
        return

    await context.bot.send_message(
        chat_id=int(chat_id),
        text=(
            f"Adrian, minęła kolejna doba.\n\n"
            f"Poprzedni dług: {old_debt:.2f} PLN\n"
            f"Naliczone: 20%\n"
            f"Nowy dług: {new_debt:.2f} PLN"
        )
    )


async def main():
    init_db()

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dlug", debt))

    app.job_queue.run_daily(
        increase_debt,
        time(
            hour=0,
            minute=0,
            second=0,
            tzinfo=WARSAW
        ),
        name="daily_debt_increase"
    )

    print("Bot uruchomiony.")
    print("Naliczanie: codziennie 00:00 Europe/Warsaw.")

    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())