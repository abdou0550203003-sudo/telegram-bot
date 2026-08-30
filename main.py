
    
import os
import json
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== الإعدادات الأساسية ====================
BOT_TOKEN = "8556834336:AAG8dBUKD4R8O_U4GCNeZYqJRaLKsu40nys"
CHANNEL_USERNAME = "@momomimoo"   # معرف قناتك
MASTER_ADMIN_ID = 7360406910      # الآيدي الأساسي الخاص بك (المطور الرئيسي)
BOT_USERNAME = "Dhhdhdhffdhd_bot" # معرف بوتك بدون علامة @
# ==========================================================

DATA_FILE = "contest_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "admins" not in data:
                    data["admins"] = [MASTER_ADMIN_ID]
                if "contestants" not in data:
                    data["contestants"] = {}
                return data
        except Exception:
            return {"admins": [MASTER_ADMIN_ID], "contestants": {}}
    return {"admins": [MASTER_ADMIN_ID], "contestants": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطأ في حفظ البيانات: {e}")

def is_admin(user_id):
    data = load_data()
    return user_id in data.get("admins", [MASTER_ADMIN_ID])

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

# ==================== الأوامر الإدارية ====================

async def new_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر مخصص للإدارة فقط!")
        return

    data = load_data()
    data["contestants"] = {}
    save_data(data)
    await update.message.reply_text("🔄 تم إنهاء المسابقة السابقة وحذف جميع المتسابقين والأصوات بنجاح! البوت جاهز لمسابقة جديدة.")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != MASTER_ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر مخصص للمطور الأساسي للبوت فقط!")
        return

    if not context.args:
        await update.message.reply_text("❌ يرجى كتابة آيدي الأدمن المراد إضافته.\nمثال: `/addadmin 123456789`", parse_mode="Markdown")
        return

    try:
        new_admin_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ آيدي الأدمن يجب أن يكون رقماً صحيحاً!")
        return

    data = load_data()
    if new_admin_id not in data["admins"]:
        data["admins"].append(new_admin_id)
        save_data(data)
        await update.message.reply_text(f"✅ تم إضافة الآيدي `{new_admin_id}` كأدمن جديد للبوت بنجاح!", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ هذا المستخدم مسجل كأدمن مسبقاً.")

async def add_contestant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر مخصص للإدارة فقط!")
        return

    if not context.args:
        await update.message.reply_text("❌ يرجى كتابة اسم المتسابق أو يوزره بعد الأمر.\nمثال:\n`/add يوسف`\n`/add @lrdlocas`", parse_mode="Markdown")
        return

    raw_input = " ".join(context.args)
    
    if raw_input.startswith("@"):
        username = raw_input
        display_name = username
        contestant_text = f"👤 المتسابق: {username}"
    else:
        display_name = raw_input
        contestant_text = f"👤 المتسابق: {display_name}"

    data = load_data()
    contestant_id = str(len(data["contestants"]) + 1)
    
    clean_bot = BOT_USERNAME.replace("@", "")
    vote_url = f"https://t.me/{clean_bot}?start=vote_{contestant_id}"
    keyboard = [[InlineKeyboardButton("❤️ 0", url=vote_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        msg = await context.bot.send_message(
            chat_id=CHANNEL_USERNAME,
            text=contestant_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        data["contestants"][contestant_id] = {
            "name": display_name,
            "votes": 0,
            "voters": [],
            "message_id": msg.message_id
        }
        save_data(data)
        
        await update.message.reply_text(f"✅ تم نشر المتسابق ({display_name}) في القناة بنجاح!\nرقم المتسابق: `{contestant_id}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء النشر في القناة: {e}")

# ==================== نظام التصويت والمستخدمين ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if context.args and context.args[0].startswith("vote_"):
        contestant_id = context.args[0].replace("vote_", "")
        await process_vote(update, context, contestant_id)
        return

    await update.message.reply_text(
        f"مرحباً بك {user.first_name} في بوت المسابقات والأسئلة! 🏆\n"
        "اضغط على زر التصويت الموجود أسفل متسابقك المفضل في القناة للمشاركة."
    )

async def process_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, contestant_id: str):
    user = update.effective_user
    user_id = user.id
    
    data = load_data()
    contestant = data["contestants"].get(contestant_id)
    
    if not contestant:
        await update.message.reply_text("❌ المتسابق غير موجود أو انتهت المسابقة!")
        return

    # استثناء للأدمن: يسمح له بالتصويت بلا حدود دون اشتراك إجباري
    if is_admin(user_id):
        await apply_vote(update, context, contestant_id, user, is_callback=False, skip_limits=True)
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

    await apply_vote(update, context, contestant_id, user, is_callback=False, skip_limits=False)

async def apply_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, contestant_id: str, user, is_callback=False, skip_limits=False):
    user_id = user.id
    data = load_data()
    target_contestant = data["contestants"].get(contestant_id)
    
    if not target_contestant:
        return

    voter_display_name = f"[{user.first_name}](tg://user?id={user_id})"
    voter_entry = {
        "id": user_id,
        "name": user.first_name,
        "markdown_name": voter_display_name
    }

    # إذا كان المستخدم أدمن، نزيد صوته مباشرة دون مسح أصوات سابقة أو قيود
    if skip_limits:
        target_contestant["voters"].append(voter_entry)
        target_contestant["votes"] += 1
        save_data(data)
        await update_channel_post(context.bot, contestant_id, target_contestant)
        msg = f'⚡ [أدمن] تم احتساب صوتك بنجاح للمتسابق "{target_contestant["name"]}"!'
        if is_callback:
            await update.callback_query.edit_message_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, parse_mode="Markdown")
        return

    # للمستخدمين العاديين: البحث عن أي تصويت سابق لهذا المستخدم في أي متسابق وسحبه
    old_contestant_key = None
    for c_id, c_data in data["contestants"].items():
        for v in c_data.get("voters", []):
            if isinstance(v, dict) and v.get("id") == user_id:
                old_contestant_key = c_id
                break
            elif str(v) == str(user_id):
                old_contestant_key = c_id
                break
        if old_contestant_key:
            break

    # إذا كان قد صوت لنفس المتسابق الحالي مسبقاً، نسمح له بسحب صوته أو إخباره (حسب رغبتك: هنا نسمح له بالإعادة ونسحب ثم نضيفه مجدداً ليتم تحديثه)
    if old_contestant_key and old_contestant_key == contestant_id:
        # إزالة من نفس المتسابق وإعادة إضافته (أو رسالة تم التصويت مسبقاً)
        # بناءً على طلبك: "ايذا حاولت ان اعيد تصويتي للمتسابق الاول البوت لا يسمح لي واريده ان يسمح بذالك وكالعادة يسحب التصويت من المتسابق الثاني"
        pass

    # إذا كان صوت لمتسابق آخر سابقاً (أو نفس المتسابق)، نسحب صوته من ذلك المتسابق القديم أياً كان
    if old_contestant_key:
        old_contestant = data["contestants"][old_contestant_key]
        old_contestant["voters"] = [v for v in old_contestant["voters"] if (v.get("id") if isinstance(v, dict) else str(v)) != str(user_id)]
        old_contestant["votes"] = max(0, old_contestant["votes"] - 1)
        await update_channel_post(context.bot, old_contestant_key, old_contestant)

    # إضافة الصوت للمتسابق الجديد
    target_contestant["voters"].append(voter_entry)
    target_contestant["votes"] += 1
    save_data(data)
    
    await update_channel_post(context.bot, contestant_id, target_contestant)

    msg = f'تم التحقق من الاشتراك وتم احتساب التصويت بنجاح للمتسابق "{target_contestant["name"]}"'
    
    if is_callback:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, parse_mode="Markdown")

async def check_subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    
    contestant_id = query.data.replace("check_vote_", "")
    
    if is_admin(user_id):
        await query.answer("✅ تم التحقق!")
        await apply_vote(update, context, contestant_id, user, is_callback=True, skip_limits=True)
        return

    subscribed = await is_user_subscribed(context.bot, user_id)
    
    if subscribed:
        await query.answer("✅ تم التحقق بنجاح!")
        await apply_vote(update, context, contestant_id, user, is_callback=True, skip_limits=False)
    else:
        await query.answer("❌ لم تشترك في القناة بعد! اشترك أولاً ثم اضغط مجدداً.", show_alert=True)

# عرض المصوتين مع تصحيح الرابط ليفتح الحساب بضغطة زر
async def view_voters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
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
    if not voters:
        voters_str = "لا يوجد مصوتين بعد."
    else:
        formatted_voters = []
        for v in voters:
            if isinstance(v, dict):
                v_id = v.get("id")
                v_name = v.get("name")
                # تصحيح صيغة الـ Markdown لضمان عمل الاسم الأزرق القابل للنقر بشكل صحيح
                name_md = f"[{v_name}](tg://user?id={v_id})"
                formatted_voters.append(f"• {name_md}")
            else:
                formatted_voters.append(f"• [مستخدم](tg://user?id={v})")
        voters_str = "\n".join(formatted_voters)
    
    await update.message.reply_text(
        f"📊 **المصوتين للمتسابق ({contestant['name']}):**\n"
        f"إجمالي الأصوات: {contestant['votes']}\n\n"
        f"اضغط على الاسم للانتقال لحسابه مباشرة:\n{voters_str}",
        parse_mode="Markdown"
    )

async def set_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
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
    application.add_handler(CommandHandler("newcontest", new_contest))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CallbackQueryHandler(check_subscription_button, pattern="^check_vote_"))

    print("البوت يعمل الآن بكل التحديثات والإصلاحات...")
    application.run_polling()

if __name__ == "__main__":
    main()
