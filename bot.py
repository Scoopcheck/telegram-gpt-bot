import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ââ Logging ââââ
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",h
    level=logging.INFO,
)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
histories: dict[int, list[dict]] = {}

SYSTEM_PROMPT = (
    "You are a smart, concise personal AI assistant. "
    "Help the user with any task they ask â research, writing, planning, coding, or anything else. "
    "Keep answers clear and to the point."
)

def get_history(user_id: int) -> list[dict]:
    if user_id not in histories:
        histories[user_id] = []
    return histories[user_id]

def trim_history(user_id: int, max_pairs: int = 15):
    h = histories.get(user_id, [])
    if len(h) > max_pairs * 2:
        histories[user_id] = h[-(max_pairs * 2):]

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ð *Hey! I'm your personal GPT-4o assistant.*\n\nJust send me any message â I'll help you with anything.\n\nCommands:\nâ¢ /clear â reset conversation\nâ¢ /help  - show this message",
        parse_mode="Markdown",
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ð¡ *How to use me:*\n\nâ¢ Type any message â I'll respond intelligently\nâ¢ I remember the conversation context\nâ¢ /clear to start a fresh conversation",
        parse_mode="Markdown",
    )

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    histories[update.effective_user.id] = []
    await update.message.reply_text("â Conversation cleared. Starting fresh!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    history = get_history(user_id)
    history.append({"role": "user", "content": text})
    trim_history(user_id)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            max_tokens=1500, temperature=0.7,
        )
        reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": reply})
        await update.message.reply_text(reply)
    except Exception as exc:
        logging.error("OpenAI error: %s", exc)
        await update.message.reply_text("â ï¸ Something went wrong. Please try again.")

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set!")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set!")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logging.info("ð¤ Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
