import os
import json
import random
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== البيانات الخاصة بك ====================
BOT_TOKEN = "8556834336:AAG8dBUKD4R8O_U4GCNeZYqJRaLKsu40nys"
CHANNEL_USERNAME = "@momomimoo"
ADMIN_ID = 7360406910
# ==========================================================

DATA_FILE = "participants.json"

def load_participants():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_participants(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطأ في حفظ البيانات: {e}")

async def is_user_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception as e:
        print(f"خطأ في التحقق من الاشتراك: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        participants = load_participants()
        participants[str(user_id)] = {
            "name": user.full_name,
            "username": user.username or "بدون يوزر"
        }
        save_participants(participants)
        
        msg = f"مرحباً بك {user.first_name}! 👋\n\n✅ أنت مشترك في القناة وتم تسجيلك بنجاح في السحب! 🎯\nحظاً موفقاً للجميع!"
        await update.message.reply_text(msg)
    else:
        clean_channel = CHANNEL_USERNAME.replace("@", "")
        keyboard = [
            [InlineKeyboardButton("📢 رابط القناة", url=f"https://t.me/{clean_channel}")],
            [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        msg = (
            f"مرحباً بك {user.first_name}! 👋\n\n"
            f"عذراً، يجب عليك الاشتراك في قناتنا أولاً للمشاركة في السحب:\n"
            f"👉 {CHANNEL_USERNAME}\n\n"
            f"اشترك في القناة ثم اضغط على زر 'تحقق من الاشتراك' بالأسفل 👇"
        )
        await update.message.reply_text(msg, reply_markup=reply_markup)

async def check_subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        participants = load_participants()
        participants[str(user_id)] = {
            "name": user.full_name,
            "username": user.username or "بدون يوزر"
        }
        save_participants(participants)
        
        await query.answer("✅ تم التحقق بنجاح!")
        msg = f"شكراً لاشتراكك يا {user.first_name}! ❤️\n\n🎉 تم تسجيلك بنجاح في السحب! 🎯\nانتظر إعلان الفائز."
        await query.edit_message_text(msg)
    else:
        await query.answer("❌ لم تشترك في القناة بعد! اشترك أولاً ثم اضغط مجدداً.", show_alert=True)

async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر مخصص لمدير البوت فقط!")
        return

    participants = load_participants()
    
    if not participants:
        await update.message.reply_text("❌ لا يوجد أي مشاركين مسجلين في السحب حتى الآن!")
        return

    winner_id, winner_info = random.choice(list(participants.items()))
    
    winner_name = winner_info.get("name", "غير معروف")
    winner_username = winner_info.get("username", "بدون يوزر")
    username_text = f"(@{winner_username})" if winner_username != "بدون يوزر" else ""

    msg = (
        f"🎉 الفائز في السحب العشوائي: 🎉\n\n"
        f"👤 الاسم: {winner_name}\n"
        f"🆔 اليوزر: {username_text}\n"
        f"🔢 الآيدي: {winner_id}\n\n"
        f"ألف مبروك للفائز! 🥳"
    )
    await update.message.reply_text(msg)

# --- سيرفر Flask لضمان استمرار عمل Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("winner", pick_winner))
    application.add_handler(CallbackQueryHandler(check_subscription_button, pattern="^check_sub$"))

    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
