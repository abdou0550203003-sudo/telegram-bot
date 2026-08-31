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
BOT_USERNAME = "competitions_lucas_bot" # معرف بوتك بدون @
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

# ==================== الواجهة الرئيسية والأزرار الشفافة ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    if context.args and context.args[0].startswith("vote_"):
        contestant_id = context.args[0].replace("vote_", "")
        await process_vote(update, context, contestant_id)
        return

    keyboard = [
        [InlineKeyboardButton("💎 الخدمات المميزة 💎", callback_data="btn_services")],
        [InlineKeyboardButton("🏆 قائمة المتسابقين 👥", callback_data="btn_contestants")],
        [InlineKeyboardButton("📢 قناة المسابقة الرسمية 🔗", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("📊 الإحصائيات 📈", callback_data="btn_stats"), InlineKeyboardButton("ℹ️ الشروط والتعليمات ❓", callback_data="btn_help")]
    ]
    
    if is_admin(user_id):
        keyboard.insert(3, [InlineKeyboardButton("🔍 كشف المصوتين (أدمن) 👤", callback_data="btn_voters_select")])
        keyboard.insert(4, [InlineKeyboardButton("⚙️ لوحة تحكم الأدمن 🛠️", callback_data="btn_admin")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    msg_text = (
        f"أهلاً بك يا **{user.first_name}** في بوت المسابقات الرسمي! ⚡\n\n"
        "إليك القائمة الرئيسية للتحكم وإدارة مشاركتك:"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data_key = query.data
    user_id = query.from_user.id
    
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="btn_main_menu")]])

    if data_key == "btn_services":
        text = "⚡ **قائمة الخدمات:**\n\n• تصويت سريع وتلقائي.\n• حماية عالية من الحسابات الوهمية.\n• تحديث إحصائيات القناة مباشرة."
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    elif data_key == "btn_contestants":
        c_data = load_data().get("contestants", {})
        if not c_data:
            text = "⚠️ لا يوجد متسابقين حالياً في المسابقة."
        else:
            text = "📋 **قائمة المتسابقين المشاركين:**\n\n"
            for c_id, info in c_data.items():
                text += f"• 🥇 **المتسابق ({c_id}):** {info['name']} — الأصوات: `{info['votes']}`\n"
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    elif data_key == "btn_stats":
        c_data = load_data().get("contestants", {})
        total_votes = sum(c.get("votes", 0) for c in c_data.values())
        sorted_c = sorted(c_data.items(), key=lambda x: x[1].get("votes", 0), reverse=True)
        
        text = f"📊 **إحصائيات المسابقة:**\n\n👥 عدد المتسابقين: `{len(c_data)}`\n🗳️ إجمالي الأصوات: `{total_votes}`\n"
        if sorted_c:
            leader = sorted_c[0][1]
            text += f"🏆 المتصدر حالياً: **{leader.get('name')}** بـ `{leader.get('votes')}` صوت 🔥"
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    elif data_key == "btn_voters_select":
        if not is_admin(user_id):
            await query.answer("⛔ هذه الميزة خاصة بالأدمن فقط!", show_alert=True)
            return

        c_data = load_data().get("contestants", {})
        if not c_data:
            await query.edit_message_text("⚠️ لا يوجد متسابقين لعرض أصواتهم.", reply_markup=back_btn)
            return

        voters_keyboard = []
        row = []
        for c_id, info in c_data.items():
            btn_text = f"👤 {c_id}. {info['name']} ({info['votes']} صوت)"
            row.append(InlineKeyboardButton(btn_text, callback_data=f"show_voters_{c_id}"))
            if len(row) == 2:
                voters_keyboard.append(row)
                row = []
        if row:
            voters_keyboard.append(row)
            
        voters_keyboard.append([InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="btn_main_menu")])
        
        await query.edit_message_text(
            "🔍 **اختر المتسابق الذي تريد كشف أصواته والمصوتين له:**",
            reply_markup=InlineKeyboardMarkup(voters_keyboard),
            parse_mode="Markdown"
        )

    elif data_key.startswith("show_voters_"):
        if not is_admin(user_id):
            await query.answer("⛔ غير مصرح لك!", show_alert=True)
            return

        c_id = data_key.replace("show_voters_", "")
        data = load_data()
        contestant = data["contestants"].get(c_id)
        
        if not contestant:
            await query.answer("❌ المتسابق غير موجود!", show_alert=True)
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
                    formatted_voters.append(f"{idx}. {v_name} ({v_username})")
                else:
                    formatted_voters.append(f"{idx}. {v_name}")
            voters_str = "\n".join(formatted_voters)

        full_msg = (
            f"📊 **قائمة المصوتين للمتسابق:** {contestant.get('name')}\n"
            f"🗳️ **إجمالي الأصوات:** `{contestant.get('votes', 0)}`\n\n"
            f"👥 **المصوتون:**\n{voters_str}"
        )
        
        back_to_voters_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع لقائمة المتسابقين", callback_data="btn_voters_select")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="btn_main_menu")]
        ])
        
        await query.edit_message_text(full_msg, reply_markup=back_to_voters_btn, parse_mode="Markdown")

    elif data_key == "btn_help":
        text = "ℹ️ **طريقة المشاركة والتصويت:**\n1. للتصويت يجب الاشتراك بالقناة أولاً.\n2. اضغط على زر التصويت أسفل منشور المتسابق في القناة."
        await query.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")

    elif data_key == "btn_admin":
        await admin_panel(update, context)

    elif data_key == "btn_main_menu":
        await start(update, context)

# ==================== لوحة تحكم الإدارة ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات المسابقة الشاملة", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ إضافة متسابق", callback_data="admin_add_help"), InlineKeyboardButton("🔄 تصفير المسابقة", callback_data="admin_new_contest")],
        [InlineKeyboardButton("🔍 كشف المصوتين مباشرة", callback_data="btn_voters_select"), InlineKeyboardButton("✏️ تعديل الأصوات", callback_data="admin_setvotes_help")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="btn_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "⚙️ **لوحة التحكم الإدارية**\nاختر من الأزرار أدناه لإدارة المسابقة:"
    
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
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للوحة التحكم", callback_data="admin_back")]])

    if data_action == "admin_stats":
        data = load_data()
        contestants = data.get("contestants", {})
        total_votes = sum(c.get("votes", 0) for c in contestants.values())
        report = f"📊 **إحصائيات الإدارة:**\n\n👤 عدد المتسابقين: `{len(contestants)}`\n🗳️ إجمالي الأصوات: `{total_votes}`\n"
        await query.edit_message_text(report, reply_markup=back_btn, parse_mode="Markdown")

    elif data_action == "admin_add_help":
        msg = "➕ **إضافة متسابق:**\nأرسل الأمر المباشر:\n`/add <اسم_المتسابق>`\nمثال: `/add يوسف`"
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")

    elif data_action == "admin_new_contest":
        data = load_data()
        data["contestants"] = {}
        save_data(data)
        await query.answer("🔄 تم تصفير المسابقة بحذف كافة البيانات!", show_alert=True)
        await admin_panel(update, context)

    elif data_action == "admin_setvotes_help":
        msg = "✏️ **تعديل الأصوات:**\nأرسل الأمر المباشر:\n`/setvotes <رقم_المتسابق> <الأصوات>`\nمثال: `/setvotes 1 50`"
        await query.edit_message_text(msg, reply_markup=back_btn, parse_mode="Markdown")

    elif data_action == "admin_back":
        await admin_panel(update, context)

# ==================== الأوامر والتصويت ====================

async def add_contestant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
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

async def view_voters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ هذا الأمر خاص بأدمن البوت فقط!")
        return

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
        formatted_voters = [f"• {idx}. {v.get('name')} ({v.get('username', 'بدون يوزر')})" for idx, v in enumerate(voters, 1)]
        voters_str = "\n".join(formatted_voters)
    
    await update.message.reply_text(
        f"📊 **قائمة المصوتين للمتسابق ({contestant.get('name', '')}):**\n"
        f"إجمالي الأصوات: {contestant.get('votes', 0)}\n\n"
        f"{voters_str}",
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

# --- سيرفر Flask لاستمرار التشغيل وإبقاء البوت حياً على Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

async def setup_bot_commands(app_bot):
    user_commands = [
        BotCommand("start", "فتح القائمة الرئيسية")
    ]
    a
