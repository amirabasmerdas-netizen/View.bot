import json
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
TOKEN = "8275637960:AAGVhL33pMp0vXRdgXzfaZqF5rYuHwDfrPw"
WEBHOOK_URL = "https://https://view-bot-0qxp.onrender.com"

OWNER_ID = 8588773170
OWNER_USERNAME = "@amele55"
DB_FILE = "db.json"

# ---------------- DB ----------------
def load_db():
    if not os.path.exists(DB_FILE):
        return {
            "users": {},
            "pending": {},
            "source_channels": [],
            "target_groups": [],
            "forwarding": False
        }
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

# ---------------- Keyboards ----------------
def owner_panel():
    return ReplyKeyboardMarkup([
        ["➕ افزودن گروه مقصد", "➖ حذف گروه مقصد"],
        ["➕ افزودن کانال مبدأ", "➖ حذف کانال مبدأ"],
        ["📋 لیست کامل"],
        ["▶️ شروع فروارد", "⏹ توقف فروارد"],
        ["❌ حذف کاربر"]
    ], resize_keyboard=True)

def user_panel():
    return ReplyKeyboardMarkup([
        ["➕ افزودن کانال", "➖ حذف کانال"],
        ["▶️ شروع فروارد", "⏹ توقف فروارد"],
        ["📖 راهنما", "✉️ ارتباط با ادمین"]
    ], resize_keyboard=True)

# ---------------- Utils ----------------
async def bot_is_admin(bot, chat_username):
    try:
        chat = await bot.get_chat(chat_username)
        member = await bot.get_chat_member(chat.id, bot.id)
        return member.status in ["administrator", "creator"]
    except:
        return False

# ---------------- Start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    user = update.effective_user

    if user.id == OWNER_ID:
        await update.message.reply_text("👑 پنل مالک فعال شد", reply_markup=owner_panel())
        return

    if str(user.id) in db["users"]:
        await update.message.reply_text("✅ شما قبلاً تأیید شده‌اید", reply_markup=user_panel())
        return

    db["pending"][str(user.id)] = {
        "name": user.full_name,
        "username": user.username
    }
    save_db(db)

    buttons = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ پذیرش", callback_data=f"accept_{user.id}"),
        InlineKeyboardButton("❌ رد", callback_data=f"reject_{user.id}")
    ]])

    await context.bot.send_message(
        OWNER_ID,
        f"🔔 درخواست جدید\n\n"
        f"👤 نام: {user.full_name}\n"
        f"🔗 یوزرنیم: @{user.username}\n"
        f"🆔 آیدی عددی: {user.id}",
        reply_markup=buttons
    )

    await update.message.reply_text("⏳ درخواست شما برای مالک ارسال شد")

# ---------------- Accept / Reject ----------------
async def approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    db = load_db()

    action, uid = query.data.split("_")

    if action == "accept":
        db["users"][uid] = {"channel": None}
        await context.bot.send_message(int(uid), "✅ شما تأیید شدید", reply_markup=user_panel())
    else:
        await context.bot.send_message(int(uid), "❌ درخواست شما رد شد")

    db["pending"].pop(uid, None)
    save_db(db)
    await query.answer("انجام شد")

# ---------------- User actions ----------------
async def user_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = str(update.effective_user.id)
    text = update.message.text

    if uid not in db["users"]:
        return

    if text == "➕ افزودن کانال":
        await update.message.reply_text("🔗 یوزرنیم کانال را ارسال کنید (@channel)")
        context.user_data["add_channel"] = True

    elif context.user_data.get("add_channel"):
        if db["users"][uid]["channel"]:
            await update.message.reply_text("❌ فقط یک کانال مجاز است")
            return

        if not text.startswith("@"):
            await update.message.reply_text("❌ فقط یوزرنیم معتبر")
            return

        if not await bot_is_admin(context.bot, text):
            await update.message.reply_text("❌ ربات ادمین کانال نیست")
            return

        db["users"][uid]["channel"] = text
        save_db(db)
        context.user_data.clear()
        await update.message.reply_text("✅ کانال ثبت شد")

    elif text == "➖ حذف کانال":
        db["users"][uid]["channel"] = None
        save_db(db)
        await update.message.reply_text("🗑 کانال حذف شد")

    elif text == "📖 راهنما":
        await update.message.reply_text(
            "1️⃣ ربات را ادمین کانال کنید\n"
            "2️⃣ یوزرنیم کانال را اضافه کنید\n"
            "3️⃣ فروارد را شروع کنید"
        )

    elif text == "✉️ ارتباط با ادمین":
        await update.message.reply_text(f"👤 ادمین: {OWNER_USERNAME}")

# ---------------- Forwarding ----------------
async def forward_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not db["forwarding"]:
        return

    for group in db["target_groups"]:
        try:
            await context.bot.forward_message(
                chat_id=group,
                from_chat_id=update.effective_chat.id,
                message_id=update.message.message_id
            )
        except:
            pass

# ---------------- Main ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(approve_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_actions))
    app.add_handler(MessageHandler(filters.ALL, forward_all))

    app.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    main()
