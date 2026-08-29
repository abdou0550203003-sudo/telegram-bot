import os
import random
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- خادم ويب خفيف لإبقاء Render شغالاً 24/7 ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is active and running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

# --- البيانات الخاصة بك مدمجة ---
BOT_TOKEN = "8556834336:AAG8dBUKD4R8O_U4GCNeZYqJRaLKsu40nys"
CHANNEL_USERNAME = "@momomimoo"
ADMIN_ID = 7360406910

participants = set()

async def start_competition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [[InlineKeyboardButton("🎯 المشاركة في المسابقة", callback_data="join")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎉 **مسابقة جديدة!**\n\nاضغط على الزر أدناه للمشاركة (بشرط الاشتراك في القناة أولاً).",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['left', 'kicked']:
            await query.answer("❌ يجب عليك الاشتراك في القناة أولاً للمشاركة!", show_alert=True)
            return
    except Exception:
        await query.answer("⚠️ حدث خطأ! تأكد أن البوت مضاف كـ (مشرف / Admin) في القناة.", show_alert=True)
        return

    if user_id in participants:
        await query.answer("⚠️ أنت مسجل بالفعل في هذه المسابقة!", show_alert=True)
    else:
        participants.add(user_id)
        await query.answer(f"✅ تم قبول مشاركتك بنجاح! عدد المشاركين الحالي: {len(participants)}", show_alert=True)

async def pick_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not participants:
        await update.message.reply_text("❌ لا يوجد أي مشاركين في المسابقة بعد.")
        return
    
    winner_id = random.choice(list(participants))
    try:
        winner = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=winner_id)
        winner_name = winner.user.first_name
        await update.message.reply_text(
            f"🏆 **مبارك للفائز!**\n\n"
            f"الفائز في المسابقة هو: [{winner_name}](tg://user?id={winner_id})\n"
            f"إجمالي عدد المشاركين: {len(participants)}",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text(f"🏆 الفائز هو صاحب الآيدي: {winner_id}")

def main():
    # تشغيل سيرفر الويب في الخلفية
    Thread(target=run_web, daemon=True).start()
    
    # تشغيل البوت
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("create", start_competition))
    app.add_handler(CommandHandler("winner", pick_winner))
    app.add_handler(CallbackQueryHandler(join_callback, pattern="^join$"))
    
    print("✅ البوت يعمل الآن بنجاح...")
    app.run_polling()

if __name__ == "__main__":
    main()
  
