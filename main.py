import os
import json
import asyncio
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeDefault
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8916563533:AAHFIYibwWWg3yM0_9aLxCA_EJ3cwL2HX4g")
CHANNEL_USERNAME = "@kmaaaaaaaaldd"
MASTER_ADMIN_ID = 7360406910
BOT_USERNAME = "competitions_lucas_bot"
DATA_FILE = "contest_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if "admins" not in d: d["admins"] = [MASTER_ADMIN_ID]
                elif MASTER_ADMIN_ID not in d["admins"]: d["admins"].append(MASTER_ADMIN_ID)
                if "contestants" not in d: d["contestants"] = {}
                return d
        except Exception: pass
    return {"admins": [MASTER_ADMIN_ID], "contestants": {}}

def save_data(d):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception as e: print(f"Save error: {e}")

def is_admin(u_id):
    return u_id in load_data().get("admins", [MASTER_ADMIN_ID])

async def is_user_subscribed(bot, u_id):
    try:
        m = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=u_id)
        return m.status in ['creator', 'administrator', 'member']
    except Exception: return False

async def update_channel_post(bot, c_id, c_data):
    msg_id = c_data.get("message_id")
    if not msg_id: return
    votes = c_data.get("votes", 0)
    clean_bot = BOT_USERNAME.replace("@", "")
    vote_url = f"https://t.me/{clean_bot}?start=vote_{c_id}"
    kb = [[InlineKeyboardButton(f"❤️ {votes}", url=vote_url)]]
    try:
        await bot.edit_message_reply_markup(chat_id=CHANNEL_USERNAME, message_id=msg_id, reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e: print(f"Post err: {e}")
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usr = update.effective_user
    if context.args and context.args[0].startswith("vote_"):
        await process_vote(update, context, context.args[0].replace("vote_", ""))
        return

    kb = [
        [InlineKeyboardButton("🏆 المتسابقين 👥", callback_data="btn_contestants")],
        [InlineKeyboardButton("📢 قناة المسابقة 🔗", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("📊 الإحصائيات 📈", callback_data="btn_stats"), InlineKeyboardButton("ℹ️ التعليمات ❓", callback_data="btn_help")]
    ]
    if is_admin(usr.id):
        kb.insert(2, [InlineKeyboardButton("⚙️ لوحة التحكم 🛠️", callback_data="btn_admin")])

    msg = f"أهلاً بك **{usr.first_name}** في البوت! 👋"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def button_click_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    k = q.data
    back = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="btn_main_menu")]])

    if k == "btn_contestants":
        c_data = load_data().get("contestants", {})
        txt = "📋 **المتسابقين:**\n\n" + "\n".join([f"• ({i}): {v['name']} — الأصوات: `{v['votes']}`" for i, v in c_data.items()]) if c_data else "⚠️ لا يوجد متسابقين."
        await q.edit_message_text(txt, reply_markup=back, parse_mode="Markdown")
    elif k == "btn_stats":
        c_data = load_data().get("contestants", {})
        tot = sum(c.get("votes", 0) for c in c_data.values())
        txt = f"📊 **الإحصائيات:**\n\n👥 المتسابقين: `{len(c_data)}`\n🗳️ الأصوات: `{tot}`"
        await q.edit_message_text(txt, reply_markup=back, parse_mode="Markdown")
    elif k == "btn_help":
        await q.edit_message_text("ℹ️ اشترك بالقناة ثم اضغط زر التصويت.", reply_markup=back, parse_mode="Markdown")
    elif k == "btn_admin":
        await admin_panel(update, context)
    elif k == "btn_main_menu":
        await start(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    kb = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("➕ إضافة متسابق", callback_data="admin_add_help"), InlineKeyboardButton("👑 إضافة أدمن", callback_data="admin_addadmin_help")],
        [InlineKeyboardButton("🔄 تصفير المسابقة", callback_data="admin_new_contest"), InlineKeyboardButton("✏️ تعديل الأصوات", callback_data="admin_setvotes_help")],
        [InlineKeyboardButton("🔍 كشف المصوتين", callback_data="admin_voters_help")],
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="btn_main_menu")]
    ]
    msg = "⚙️ **لوحة التحكم:**"
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id): return await q.answer("⛔ غير مصرح!", show_alert=True)
    act = q.data
    back = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة للوحة", callback_data="admin_back")]])

    if act == "admin_stats":
        d = load_data()
        await q.edit_message_text(f"👤 المتسابقين: `{len(d.get('contestants', {}))}`\n👑 الأدمنية: `{len(d.get('admins', []))}`", reply_markup=back, parse_mode="Markdown")
    elif act == "admin_add_help":
        await q.edit_message_text("➕ أرسل: `/add <الاسم>`", reply_markup=back, parse_mode="Markdown")
    elif act == "admin_addadmin_help":
        await q.edit_message_text("👑 أرسل: `/addadmin <الآيدي>`", reply_markup=back, parse_mode="Markdown")
    elif act == "admin_new_contest":
        d = load_data(); d["contestants"] = {}; save_data(d)
        await q.answer("🔄 تم التصفير!", show_alert=True)
        await admin_panel(update, context)
    elif act == "admin_voters_help":
        await q.edit_message_text("🔍 أرسل: `/voters <الرقم>`", reply_markup=back, parse_mode="Markdown")
    elif act == "admin_setvotes_help":
        await q.edit_message_text("✏️ أرسل: `/setvotes <الرقم> <الأصوات>`", reply_markup=back, parse_mode="Markdown")
    elif act == "admin_back":
        await admin_panel(update, context)
       async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("❌ اكتب: `/addadmin 123456789`", parse_mode="Markdown")
    try: n_id = int(context.args[0])
    except: return await update.message.reply_text("❌ يجب أن يكون رقم!")
    d = load_data()
    if n_id not in d["admins"]: d["admins"].append(n_id); save_data(d)
    await update.message.reply_text(f"✅ تم إضافة `{n_id}` كـ أدمن!", parse_mode="Markdown")

async def add_contestant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("❌ اكتب: `/add الاسم`", parse_mode="Markdown")
    name = " ".join(context.args)
    d = load_data()
    c_id = str(len(d["contestants"]) + 1)
    clean_bot = BOT_USERNAME.replace("@", "")
    kb = [[InlineKeyboardButton("❤️ 0", url=f"https://t.me/{clean_bot}?start=vote_{c_id}")]]
    try:
        msg = await context.bot.send_message(chat_id=CHANNEL_USERNAME, text=f"👤 المتسابق ({c_id}): {name}", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        d["contestants"][c_id] = {"name": name, "votes": 0, "voters": [], "message_id": msg.message_id}
        save_data(d)
        await update.message.reply_text(f"✅ تم نشر ({name}) رقم `{c_id}`!", parse_mode="Markdown")
    except Exception as e: await update.message.reply_text(f"❌ خطأ: {e}")

async def process_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, c_id: str):
    usr = update.effective_user
    d = load_data()
    c = d["contestants"].get(c_id)
    if not c: return await update.message.reply_text("❌ غير موجود!")
    if is_admin(usr.id): return await apply_vote(update, context, c_id, usr, False, True)
    if not await is_user_subscribed(context.bot, usr.id):
        kb = [[InlineKeyboardButton("📢 القناة", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")], [InlineKeyboardButton("✅ تحقق", callback_data=f"check_vote_{c_id}")]]
        return await update.message.reply_text(f"اشترك للقناة أولاً: {CHANNEL_USERNAME}", reply_markup=InlineKeyboardMarkup(kb))
    await apply_vote(update, context, c_id, usr, False, False)

async def apply_vote(update: Update, context: ContextTypes.DEFAULT_TYPE, c_id: str, usr, is_cb=False, skip=False):
    d = load_data()
    t = d["contestants"].get(c_id)
    if not t: return
    entry = {"id": usr.id, "name": usr.first_name, "username": f"@{usr.username}" if usr.username else None}
    if not skip:
        for cid, cd in d["contestants"].items():
            l1 = len(cd["voters"])
            cd["voters"] = [v for v in cd["voters"] if v.get("id") != usr.id]
            if len(cd["voters"]) < l1:
                cd["votes"] = max(0, cd["votes"] - 1)
                await update_channel_post(context.bot, cid, cd)
    t["voters"].append(entry); t["votes"] += 1; save_data(d)
    await update_channel_post(context.bot, c_id, t)
    msg = f"✅ تم التصويت لـ {t['name']}"
    if is_cb: await update.callback_query.edit_message_text(msg, parse_mode="Markdown")
    else: await update.message.reply_text(msg, parse_mode="Markdown")

async def check_subscription_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    usr = q.from_user
    cid = q.data.replace("check_vote_", "")
    if is_admin(usr.id):
        await q.answer("✅")
        return await apply_vote(update, context, cid, usr, True, True)
    if await is_user_subscribed(context.bot, usr.id):
        await q.answer("✅")
        await apply_vote(update, context, cid, usr, True, False)
    else: await q.answer("❌ لم تشترك!", show_alert=True)

async def view_voters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("❌ أرسل: `/voters 1`", parse_mode="Markdown")
    d = load_data(); c = d["contestants"].get(context.args[0])
    if not c: return await update.message.reply_text("❌ غير موجود!")
    v_list = c.get("voters", [])
    txt = f"📊 المصوتين لـ {c['name']}:\n" + "\n".join([f"• {i+1}. {v['name']} ({v.get('username','بدون')})" for i, v in enumerate(v_list)]) if v_list else "لا يوجد."
    await update.message.reply_text(txt[:4000])

async def set_votes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or len(context.args) < 2: return
    cid, nv = context.args[0], int(context.args[1])
    d = load_data(); c = d["contestants"].get(cid)
    if c:
        c["votes"] = nv; save_data(d)
        await update_channel_post(context.bot, cid, c)
        await update.message.reply_text(f"✅ تم التعديل إلى {nv}")

app = Flask(__name__)
@app.route('/')
def home(): return "OK", 200

async def main():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin_panel))
    app_bot.add_handler(CommandHandler("add", add_contestant))
    app_bot.add_handler(CommandHandler("addadmin", add_admin))
    app_bot.add_handler(CommandHandler("voters", view_voters))
    app_bot.add_handler(CommandHandler("setvotes", set_votes))
    app_bot.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    app_bot.add_handler(CallbackQueryHandler(button_click_handler, pattern="^btn_"))
    app_bot.add_handler(CallbackQueryHandler(check_subscription_button, pattern="^check_vote_"))

    await app_bot.bot.set_my_commands([BotCommand("start", "القائمة")], scope=BotCommandScopeDefault())

    from werkzeug.serving import run_simple
    port = int(os.environ.get("PORT", 8080))
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, lambda: run_simple('0.0.0.0', port, app))

    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
    
