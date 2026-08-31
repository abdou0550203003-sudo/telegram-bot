import os
import json
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeDefault, BotCommandScopeChat
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ==================== الإعدادات الأساسية ====================
BOT_TOKEN = "8916563533:AAGIJUuDHdx9cQuWbc4eq0-BJEclMaKiXeA"
CHANNEL_USERNAME = "@kmaaaaaaaaldd"  # معرف قناتك
MASTER_ADMIN_ID = 7360406910         # الآيدي الخاص بك
BOT_USERNAME = "competitions_lucas_bot" # معرف بوتك بدون علامة @
# ==========================================================

DATA_FILE = "contest_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "admins" not in data:
                    data["admins"] = [MASTER_ADMIN_ID]
                elif MASTER_ADMIN_ID not in data["admins"]:
                    data["admins"].append(MASTER_ADMIN_ID)
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

# ==================== لوحة التحكم والأوامر الإدارية ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذه اللوحة مخصصة للإدارة فقط!")
        return

    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات المسابقة", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ إضافة متسابق", callback_data="admin_add_help"), InlineKeyboardButton("🔄 تصفير المسابقة", callback_data="admin_new_contest")],
        [InlineKeyboardButton("🔍 طريقة كشف المصوتين", callback_data="admin_voters_help"), InlineKeyboardButton("✏️ طريقة تعديل الأصوات", callback_data="admin_setvotes_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = "⚙️ **لوحة التحكم الإدارية**\nاختر من الأزرار أدناه للتحكم بالمسابقة والبوت:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="Markdown")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        await query.answer("⛔ غير مصرح لك!", show_alert=True)
        return

    data_action = query.data

    if data_action == "admin_stats":
        data = load_data()
        contestants = data.get("contestants", {})
        total_votes = sum(c.get("votes", 0) for c in contestants.values())
        sorted_c = sorted(contestants.items(), key=lambda x: x[1].get("votes", 0), reverse=True)
        
        report = f"📊 **إحصائيات المسابقة الحالية:**\n\n"
        report += f"👤 عدد المتسابقين: `{len(contestants)}`\n"
        report += f"🗳️ إجمالي الأصوات: `{total_votes}`\n"
        if sorted_c:
            leader = sorted_c[0][1]
            report += f"🏆 المتصدر: **{leader.get('name')}** بـ `{leader.get('votes')}` صوت\n"

        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_back")]]
        await query.edit_message_text(report, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data_action == "admin_add_help":
        msg = "➕ **طريقة إضافة متسابق:**\nأرسل الأمر التالي في الشات:\n`/add <اسم_المتسابق>`\n\nمثال:\n`/add أحمد`"
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_back")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data_action == "admin_new_contest":
        data = load_data()
        data["contestants"] = {}
        save_data(data)
        await query.answer("🔄 تم تصفير المسابقة!", show_alert=True)
        await admin_panel(update, context)

    elif data_action == "admin_voters_help":
        msg = "🔍 **طريقة كشف المصوتين:**\nأرسل الأمر التالي متبوعاً برقم المتسابق:\n`/voters <رقم_المتسابق>`\n\nمثال:\n`/voters 1`"
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_back")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data_action == "admin_setvotes_help":
        msg = "✏️ **تعديل الأصوات:**\nأرسل الأمر متبوعاً برقم المتسابق وعدد الأصوات الجديدة:\n`/setvotes <رقم_المتسابق> <الأصوات>`\n\nمثال:\n`/setvotes 1 50`"
        keyboard = [[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_back")]]
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data_action == "admin_back":
        await admin_panel(update, context)

async def new_contest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر مخصص للإدارة فقط!")
        return

    data = load_data()
    data["contestants"] = {}
    save_data(data)
    await update.message.reply_text("🔄 تم إنهاء المسابقة السابقة وحذف جميع المتسابقين والأصوات بنجاح!")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != MASTER_ADMIN_ID:
        await update.message.reply_text("⛔ هذا الأمر مخصص للمطور الأساسي فقط!")
        return

    if not context.args:
        await update.message.reply_text("❌ اكتب آيدي الأدمن المراد إضافته.\nمثال: `/addadmin 123456789`", parse_mode="Markdown")
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
        
        admin_commands = [
            BotCommand("start", "بدء التشغيل"),
            BotCommand("admin", "فتح لوحة التحكم الإدارية"),
            BotCommand("add", "إضافة متسابق جديد"),
            BotCommand("voters", "عرض المصوتين لمتسابق"),
            BotCommand("setvotes", "تعديل الأصوات"),
            BotCommand("newcontest", "تصفير المسابقة")
        ]
        try:
            await context.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=new_admin_id))
        except Exception:
            pass

        await update.message.reply_text(f"✅ تم إضافة الآيدي `{new_admin_id}` كأدمن جديد وتفعيل لوحة التحكم له!", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ هذا المستخدم مسجل كأدمن مسبقاً.")

async def add_contestant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر مخصص للإدارة فقط!")
        return

    if not context.args:
        await update.message.reply_text("❌ اكتب اسم المتسابق بعد الأمر.\nمثال: `/add يوسف`", parse_mode="Markdown")
        return

    display_name = " ".join(context.args)
    data = load_data()
    contestant_id = str(len(data["contestants"]) + 1)
    
    contestant_text = f"👤 المتسابق ({contestant_id}): {display_name}"
    
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
        
        await update.message.reply_text(f"✅ تم نشر المتسابق ({display_name}) رقم `{contestant_id}` بنجاح!", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء النشر: {e}")

# ==================== نظام التصويت والاستعلام العام ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if context.args and context.args[0].startswith("vote_"):
        contestant_id = context.args[0].replace("vote_", "")
        await process_vote(update, context, contestant_id)
        return

    await update.message.reply_text(
        f"مرحباً بك {user.first_name} في بوت المسابقات! 🏆\n\n"
        "• للتصويت: اضغط على زر التصويت الموجود أسفل منشور المتسابق في القناة.\n"
        "• لمعرفة من صوت لمتسابق معّين: أرسل الأمر `/voters` متبوعاً برقم المتسابق (مثال: `/voters 1`)."
    )

async def process_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, contestant_id: str):
    user = update.effective_user
    user_id = user.id
    
    data = load_data()
    contestant = data["contestants"].get(contestant_id)
    
    if not contestant:
        await update.message.reply_text("❌ المتسابق غير موجود أو انتهت المسابقة!")
        return

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

    username = user.username if user.username else None
    
    voter_entry = {
        "id": user_id,
        "name": user.first_name,
        "username": f"@{username}" if username else None
    }

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

    for c_id, c_data in data["contestants"].items():
        original_voters_count = len(c_data["voters"])
        c_data["voters"] = [v for v in c_data["voters"] if v.get("id") != user_id]
        
        if len(c_data["voters"]) < original_voters_count:
            c_data["votes"] = max(0, c_data["votes"] - 1)
            await update_channel_post(context.bot, c_id, c_data)

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
        await query.answer("❌ لم تشترك في القناة بعد!", show_alert=True)

# ===== إتاحة رؤية المصوتين للجميع بناءً على طلبك =====
async def view_voters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ اكتب رقم المتسابق لمعرفة المصوتين له.\nمثال: `/voters 1`", parse_mode="Markdown")
        return
        
    contestant_id = context.args[0]
    data = load_data()
    contestant = data["contestants"].get(contestant_id)
    
    if not contestant:
        await update.message.reply_text("❌ المتسابق غير موجود!")
        return
        
    voters = contestant.get("voters", [])
    if not voters:
        voters_str = "لا يوجد مصوتين لهذا المتسابق بعد."
    else:
        formatted_voters = []
        for idx, v in enumerate(voters, 1):
            v_name = v.get("name") if v.get("name") else "مستخدم"
            v_username = v.get("username")
            
            if v_username:
                formatted_voters.append(f"• {idx}. {v_name} ({v_username})")
            else:
                formatted_voters.append(f"• {idx}. {v_name} (بدون يوزر)")
                
        voters_str = "\n".join(formatted_voters)
    
    full_msg = (
        f"📊 قائمة المصوتين للمتسابق ({contestant.get('name', '')}):\n"
        f"إجمالي الأصوات: {contestant.get('votes', 0)}\n\n"
        f"{voters_str}"
    )

    try:
        if len(full_msg) > 4000:
            for x in range(0, len(full_msg), 4000):
                await update.message.reply_text(full_msg[x:x+4000])
        else:
            await update.message.reply_text(full_msg)
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء عرض القائمة: {e}")

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

# --- سيرفر Flask ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# إعداد القوائم المخصصة عند الإقلاع
async def setup_bot_commands(app):
    user_commands = [
        BotCommand("start", "بدء تشغيل البوت والتصويت"),
        BotCommand("voters", "عرض المصوتين لمتسابق")
    ]
    await app.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = [
        BotCommand("start", "بدء تشغيل البوت"),
        BotCommand("admin", "فتح لوحة التحكم الإدارية"),
        BotCommand("add", "إضافة متسابق جديد للقناة"),
        BotCommand("voters", "عرض قائمة المصوتين لمتسابق"),
        BotCommand("setvotes", "تعديل عدد أصوات متسابق"),
        BotCommand("newcontest", "إنهاء المسابقة وتصفير الأصوات"),
        BotCommand("addadmin", "إضافة أدمن جديد للبوت")
    ]
    try:
        await app.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=MASTER_ADMIN_ID))
    except Exception as e:
        print(f"تنبيه ضبط قائمة الأدمن: {e}")

def main():
    threading.Thread(target=run_flask, daemon=True).start()

    application = ApplicationBuilder().token(BOT_TOKEN).post_init(setup_bot_commands).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("add", add_contestant))
    application.add_handler(CommandHandler("voters", view_voters))
    application.add_handler(CommandHandler("setvotes", set_votes))
    application.add_handler(CommandHandler("newcontest", new_contest))
    application.add_handler(CommandHandler("addadmin", add_admin))
    
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(check_subscription_button, pattern="^check_vote_"))

    print("البوت يعمل الآن مجهزاً بلواحة التحكم الجديدة...")
    application.run_polling()

if __name__ == "__main__":
    main()
        
