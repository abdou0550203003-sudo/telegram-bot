import os
import json
import random
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== الإعدادات (عدّلها بما يناسبك) ====================
BOT_TOKEN = "ضع_توكن_البوت_هنا"   # توكن البوت من BotFather
CHANNEL_USERNAME = "@momomimoo"    # معرف قناتك (يجب أن يكون البوت مشرفاً فيها)
ADMIN_ID = 123456789              # الآيدي الخاص بك في تليجرام (ليمكنك استخدام أمر القرعة)
# =======================================================================

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
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    
    # التحقق من الاشتراك في القناة
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        # حفظ المشارك
        participants = load_participants()
        participants[str(user_id)] = {
            "name": user.full_name,
            "username": user.username or "بدون يوزر"
        }
        save_participants(participants)
        
        await update.message.reply_text(
            f"مرحباً بك {user.first_name}! 👋\n\n"
            "✅ أنت مشترك في القناة وتم تسجيلك بنجاح في السحب! 🎯\n"
            "حظاً موفقاً للجميع!"
        )
    else:
        # إرسال رابط القناة وزر التحقق
        clean_channel = CHANNEL_USERNAME.replace("@", "")
        keyboard = [
            [InlineKeyboardButton("📢 رابط القناة", url=f"https://t.me/{clean_channel}")],
            [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"مرحباً بك {user.first_name}! 👋\n\n"
            f"عذراً، يجب عليك الاشتراك في قناتنا أولاً للمشاركة في السحب:\n"
            f"👉 {CHANNEL_USERNAME}\n\n"
            "اشترك في القناة ثم اضغط على زر **'تحقق من الاشتراك'** بالأسفل 👇",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

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
        await query.edit_message_text(
            f"شكراً لاشتراكك يا {user.first_name}! ❤️\n\n"
            "🎉 تم تسجيلك بنجاح في السحب! 🎯\n"
            "انتظر إعلان الفائز."
        )
    else:
        await query.answer("❌ لم تشترك في القناة بعد! اشترك أولاً ثم اضغط مجدداً.", show_alert=True)

async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التحقق من أن منفذ الأمر هو الأدمن
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر مخصص لمدير البوت فقط!")
        return

    participants = load_participants()
    
    if not participants:
        await update.message.reply_text("❌ لا يوجد أي مشاركين مسجلين في السحب حتى الآن!")
        return

    # اختيار فائز عشوائي
    winner_id, winner_info = random.choice(list(participants.items()))
    
    winner_name = winner_info.get("name", "غير معروف")
    winner_username = winner_info.get("username", "بدون يوزر")
    username_text = f"(@{winner_username})" if winner_username != "بدون يوزر" else ""

    await update.message.reply_text(
        "🎉 **الفائز في السحب العشوائي:** 🎉\n\n"
        f"👤 **الاسم:** {winner_name}\n"
        f"🆔 **اليوزر:** {username_text}\n"
        f"🔢 **الآيدي:** `{winner_id}`\n\n"
        "ألف مبروك للفائز! 🥳",
        parse_mode="Markdown"
    )

# --- سيرفر Flask لضمان استمرار عمل Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def main():
    # تشغيل سيرفر Flask في الخلفية
    threading.Thread(target=run_flask, daemon=True).start()

    # تشغيل بوت تليجرام
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("winner", pick_winner))
    application.add_handler(CallbackQueryHandler(check_subscription_button, pattern="^check_sub$"))

    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
