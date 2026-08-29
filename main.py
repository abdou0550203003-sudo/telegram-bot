import os
import json
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== الإعدادات الخاصة بك ====================
BOT_TOKEN = "8556834336:AAG8dBUKD4R8O_U4GCNeZYqJRaLKsu40nys"
CHANNEL_USERNAME = "@momomimoo"   # معرف قناتك (تأكد من رفع البوت مديراً فيها)
ADMIN_ID = 7360406910             # الآيدي الخاص بك
BOT_USERNAME = "Dhhdhdhffdhd_bot" # معرف بوتك بدون علامة @ (تأكد منه في تليجرام)
# ==========================================================

DATA_FILE = "contest_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"contestants": {}}
    return {"contestants": {}}

def save_data(data):
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

# تحديث زر القناة مباشرة بعد زيادة الأصوات
async def update_channel_post(bot, contestant_id, contestant_data):
    msg_id = contestant_data.get("message_id")
    if not msg_id:
        return
    
    votes = contestant_data.get("votes", 0)
    clean_bot = BOT_USERNAME.replace("@", "")
    vote_url = f"https://t.me/{clean_bot}?start=vote_{contestant_id}"
    
    keyboard = [[InlineKeyboardButton(f"❤️ {votes}", url=vote_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await bot.edit_message_reply_markup(
            chat_id=CHANNEL_USERNAME,
            message_id=msg_id,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"خطأ في تحديث منشور القناة: {e}")

# أمر إضافة متسابق ونشره في القناة (الأدمن فقط)
async def add_contestant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر مخصص لمدير البوت فقط!")
        return

    name = " ".join(context.args)
    if not name:
        await update.message.reply_text("❌ يرجى كتابة اسم المتسابق بعد الأمر.\nمثال: `/add يوسف`", parse_mode="Markdown")
        return

    data = load_data()
    contestant_id = str(len(data["contestants"]) + 1)
    
    clean_bot = BOT_USERNAME.replace("@", "")
    vote_url = f"https://t.me/{clean_bot}?start=vote_{contestant_id}"
    keyboard = [[InlineKeyboardButton("❤️ 0", url=vote_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        msg = await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=f"👤 المتسابق: {name}",
            reply_markup=reply_markup
        )
        
        data["contestants"][contestant_id] = {
            "name": name,
            "votes": 0,
            "voters": [],
            "message_id": msg.message_id
        }
        save_data(data)
        
        await update.message.reply_text(f"✅ تم نشر المتسابق ({name}) في القناة بنجاح!\nرقم المتسابق: `{contestant_id}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء النشر في القناة: {e}\nتأكد أن البوت مشرف في القناة ولديه صلاحية نشر الرسائل!")

# التعامل مع رابط التصويت العميق عند الضغط من القناة
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if context.args and context.args[0].startswith("vote_"):
        contestant_id = context.args[0].replace("vote_", "")
        await process_vote(update, context, contestant_id)
        return

    await update.message.reply_text(
        f"مرحباً بك {user.first_name} في بوت المسابقات! 🏆\n"
        "اضغط على زر التصويت الموجود أسفل متسابقك المفضل في القناة للمشاركة."
    )

# فحص التصويت
async def process_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, contestant_id: str):
    user = update.effective_user
    user_id = user.id
    
    data = load_data()
    contestant = data["contestants"].get(contestant_id)
    
    if not contestant:
        await update.message.reply_text("❌ المتسابق غير موجود أو انتهت المسابقة!")
        return

    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if not subscribed:
        clean_channel = CHANNEL_USERNAME.replace("@", "")
        keyboard = [
            [InlineKeyboardButton("📢 رابط القناة", url=f"https://t.me/{clean_channel}")],
            [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data=f"check_vote_{contestant_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        msg = (
            f"مرحباً بك {user.first_name}! 👋\n\n"
            f"يجب عليك الاشتراك في قناتنا أولاً ليتم احتساب صوتك للمتسابق {contestant['name']}:\n"
            f"👉 {CHANNEL_USERNAME}\n\n"
            f"اشترك في القناة ثم اضغط على زر 'تحقق من الاشتراك' بالأسفل 👇"
        )
        await update.message.reply_text(msg, reply_markup=reply_markup)
        return

    await apply_vote(update, context, contestant_id, user)

# تنفيذ التصويت وتعديل القلوب
async def apply_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, contestant_id: str, user, is_callback=False):
    user_id = user.id
    data = load_data()
    contestant = data["contestants"].get(contestant_id)
    
    if not contestant:
        return

    # للأدمن: إضافة صوت في كل مرة بدون حدود
    if user_id == ADMIN_ID:
        contestant["votes"] += 1
        if str(user_id) not in contestant["voters"]:
            contestant["voters"].append(str(user_id))
        save_data(data)
        await update_channel_post(context.bot, contestant_id, contestant)
        
        msg = f"👑 (وضع الأدمن) تم زيادة صوت للمتسابق {contestant['name']}!\nعدد القلوب الحالي: {contestant['votes']}"
        if is_callback:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    # للمشاركين العاديين: صوت واحد فقط لكل متسابق
    if str(user_id) in contestant["voters"]:
        msg = f"⚠️ يا {user.first_name}، لقد قمت بالتصويت للمتسابق {contestant['name']} من قبل!"
        if is_callback:
            await update.callback_query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    contestant["voters"].append(str(user_id))
    contestant["votes"] += 1
    save_data(data)
    
    await update_channel_post(context.bot, contestant_id, contestant)
    
    msg = f"تم التحقق من اشتراككم وتم احتساب التصويت بنجاح للمتسابق {contestant['name']}! ❤️"
    if is_callback:
        await update.callback_query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)

async def check_subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    
    contestant_id = query.data.replace("check_vote_", "")
    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        await query.answer("✅ تم التحقق بنجاح!")
        await apply_vote(update, context, contestant_id, user, is_callback=True)
    else:
        await query.answer("❌ لم تشترك في القناة بعد! اشترك أولاً ثم اضغط مجدداً.", show_alert=True)

# أمر معرفة المصوتين لمتسابق (الأدمن فقط)
async def view_voters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
        
    if not context.args:
        await update.message.reply_text("❌ اكتب رقم المتسابق لمعرفة المصوتين.\nمثال: `/voters 1`", parse_mode="Markdown")
        return
        
    contestant_id = context.args[0]
    data = load_data()
    contestant = data["contestants"].get(contestant_id)
    
    if not contestant:
        await update.message.reply_text("❌ المتسابق غير موجود!")
        return
        
    voters = contestant.get("voters", [])
    voters_str = "\n".join([f"• `{v}`" for v in voters]) if voters else "لا يوجد مصوتين بعد."
    
    await update.message.reply_text(
        f"📊 **المصوتين للمتسابق ({contestant['name']}):**\n"
        f"إجمالي الأصوات: {contestant['votes']}\n\n"
        f"قائمة الآيديهات:\n{voters_str}",
        parse_mode="Markdown"
    )

# أمر تحديد الأصوات يدويًا لأي متسابق (الأدمن فقط)
async def set_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ الاستخدام: `/setvotes <رقم_المتسابق> <عدد_الأصوات>`\nمثال: `/setvotes 1 50`", parse_mode="Markdown")
        return

    contestant_id = context.args[0]
    try:
        new_votes = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ يجب أن يكون عدد الأصوات رقماً!")
        return

    data = load_data()
    contestant = data["contestants"].get(contestant_id)
    if not contestant:
        await update.message.reply_text("❌ المتسابق غير موجود!")
        return

    contestant["votes"] = new_votes
    save_data(data)
    await update_channel_post(context.bot, contestant_id, contestant)
    
    await update.message.reply_text(f"✅ تم تعديل أصوات {contestant['name']} إلى {new_votes} وتحديث القناة!")

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
    application.add_handler(CommandHandler("add", add_contestant))
    application.add_handler(CommandHandler("voters", view_voters))
    application.add_handler(CommandHandler("setvotes", set_votes))
    application.add_handler(CallbackQueryHandler(check_subscription_button, pattern="^check_vote_"))

    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
