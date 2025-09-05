import os
import json
import zipfile
from io import BytesIO
from datetime import datetime, timedelta
import httpx
import logging
from keep_alive import keep_alive

keep_alive()

# your Telegram bot code starts here
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes, ConversationHandler
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8313361063:AAGgNKxT-u3JlloPt1xy9ezmplCJvVMSx3E")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6170894121"))

DB_FILE = "database.json"
LOGO_DIR = "logo_uploads"
if not os.path.exists(LOGO_DIR):
    os.makedirs(LOGO_DIR)
if not os.path.exists(DB_FILE):
    with open(DB_FILE, "w") as f:
        json.dump({"premium": {}, "website_data": {}, "unban_status": {}}, f)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FREE_URL, ADV_ONBOARD, LOGO, WHATSAPP_UNBAN, WEBSITE_HISTORY, PROFILE_MENU = range(6)
# ------------------ WELCOME NEW USERS ------------------
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        welcome_text = (
            f"👋 Welcome [{member.first_name}](tg://user?id={member.id})!\n\n"
            "You’ve joined one of the best communities 💎\n"
            "Here you can learn, share, and grow with us 🚀\n\n"
            "⚡ Be respectful, contribute positively, and enjoy your stay!\n\n"
            "💡 *Made with ❤️ by MR DEV*\n"
            "📞 Contact: [Click Here](https://t.me/Mrddev)"
        )
        await update.message.reply_text(
            welcome_text,
            parse_mode="Markdown"
        )
# ------------------ GOODBYE USERS ------------------
async def goodbye_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.left_chat_member and not update.message.left_chat_member.is_bot:
        member = update.message.left_chat_member
        bye_text = (
            f"😢 [{member.first_name}](tg://user?id={member.id}) has left the group.\n\n"
            "We hope you enjoyed your time here and learned something useful ✨\n"
            "Remember, you’re always welcome back! 🔄\n\n"
            "💡 *Made with ❤️ by MR DEV*\n"
            "📞 Contact: [Click Here](https://t.me/Mrddev)"
        )
        await update.message.reply_text(
            bye_text,
            parse_mode="Markdown"
        )

# ------------------ TAG ALL (Normal Ping) ------------------
async def tag_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ This command only works in groups.")
        return

    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        await update.message.reply_text("❌ Only admins can use this command.")
        return

    extra_text = " ".join(context.args) if context.args else "📢 Attention everyone!"
    try:
        count = await context.bot.get_chat_member_count(chat.id)
        text_batch, batch_size = [], 30
        sent = 0

        for user_id in range(count):
            try:
                member = await context.bot.get_chat_member(chat.id, user_id)
                u = member.user
                if u.is_bot:
                    continue
                mention = f"@{u.username}" if u.username else f"[{u.first_name}](tg://user?id={u.id})"
                text_batch.append(mention)

                if len(text_batch) >= batch_size:
                    text = f"{extra_text}\n\n" + " ".join(text_batch) + "\n\n💡 Made with ❤️ by MR DEV"
                    await update.message.reply_text(text, parse_mode="Markdown")
                    text_batch = []
                    sent += 1
            except Exception:
                continue

        if text_batch:
            text = f"{extra_text}\n\n" + " ".join(text_batch) + "\n\n💡 Made with ❤️ by MR DEV"
            await update.message.reply_text(text, parse_mode="Markdown")
            sent += 1

        await update.message.reply_text(f"✅ Tagged all in {sent} batch(es).")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to tag all: {e}")
        
# ------------------ TAG REPLY (Silent) ------------------
async def tag_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    # only works in groups
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("❌ This command only works in groups.")
        return

    # check if user is admin
    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
        await update.message.reply_text("❌ Only admins can use this command.")
        return

    # must be a reply
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ You must reply to a message with /tag.")
        return

    try:
        count = await context.bot.get_chat_member_count(chat.id)
        text_batch = []

        for user_id in range(count):
            try:
                member = await context.bot.get_chat_member(chat.id, user_id)
                u = member.user
                if u.is_bot:
                    continue
                mention = f"@{u.username}" if u.username else f"[{u.first_name}](tg://user?id={u.id})"
                text_batch.append(mention)
            except Exception:
                continue

        if text_batch:
            text = "🔔 " + " ".join(text_batch) + "\n\n💡 Made with ❤️ by MR DEV\n📞 Contact: [Click Here](https://t.me/Mrddev)"
            await update.message.reply_to_message.reply_text(
                text, parse_mode="Markdown", disable_notification=True
            )

    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed to tag reply: {e}")

def main_menu(is_premium=False):
    keyboard = [
        [InlineKeyboardButton("📝 Copy Website Code", callback_data="copy_web")],
        [InlineKeyboardButton("🚀 Create Advanced Website", callback_data="create_adv")],
        [InlineKeyboardButton("📂 My Websites", callback_data="my_websites")],
        [InlineKeyboardButton("⚙️ Profile & Settings", callback_data="profile")],
        [InlineKeyboardButton("🔓 WhatsApp Unban (Premium)", callback_data="whatsapp_unban")],
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="upgrade")],
        [InlineKeyboardButton("📞 Contact Dev: MR DEV | Telegram", url="https://t.me/Mrddev")],
        [InlineKeyboardButton("📚 Teacher Help & Guide", callback_data="teacher")],
    ]
    return InlineKeyboardMarkup(keyboard)

CHANNEL_USERNAME = "@dannytech07"  # your Telegram channel username

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CHANNEL_LINK = "@dannytech07"  # optional, used for get_chat_member

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
import logging

CHANNEL_USERNAME = "@dannytech07"  # Use your channel username
CHANNEL_LINK = "https://t.me/+Cpc0PV1vtMFlNDY8"

async def start(update, context):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ("member", "administrator", "creator"):
            # User is in channel – continue normally
            db = load_db()
            uid = str(user_id)
            is_premium = db["premium"].get(uid, False)
            await update.message.reply_text(
                "👋 Welcome to *MR DEV Bot PRIME*\n\n"
                "1️⃣ Free: Download zipped website from a URL\n"
                "2️⃣ Premium: Build a full website with logo/pages/sections\n"
                "3️⃣ WhatsApp Unban: Premium users only\n"
                "4️⃣ Website history/download\n"
                "5️⃣ Profile/settings\n"
                "⚡ Choose an option below:",
                parse_mode="Markdown",
                reply_markup=main_menu(is_premium)
            )
        else:
            # Not joined
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]
            ])
            await update.message.reply_text(
                "⚠️ You must join our channel to use this bot.\n\n"
                "Tap the button below to join, then press /start again.",
                reply_markup=keyboard
            )

    except BadRequest as e:
        # Specific check for "user not participant"
        if "user not a participant" in str(e).lower():
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)]
            ])
            await update.message.reply_text(
                "⚠️ You must join our channel to use this bot.\n\n"
                "Tap the button below to join, then press /start again.",
                reply_markup=keyboard
            )
        else:
            # Other BadRequest errors
            logging.error(f"BadRequest error for user {user_id}: {e}")
            await update.message.reply_text(
                "⚠️ Something went wrong. Please try /start again later."
            )
    except Exception as e:
        # Any unexpected errors
        logging.error(f"Unexpected error for user {user_id}: {e}")
        await update.message.reply_text(
            "⚠️ Something went wrong. Please try /start again later."
        )
        
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    db = load_db()
    uid = str(query.from_user.id)
    is_premium = db["premium"].get(uid, False)
    await query.answer()
    if query.data == "copy_web":
        await query.message.reply_text("🙃 Send a URL (Pastebin, CodePen, etc) containing your HTML. I'll send you a zipped website!")
        return FREE_URL
    elif query.data == "create_adv":
        if not is_premium:
            await query.message.reply_text("🔒 This feature is only for premium users. Please upgrade to use Advanced Website Builder!")
            return ConversationHandler.END
        context.user_data["adv_step"] = 0
        context.user_data["adv_data"] = {}
        await query.message.reply_text("Let's create your advanced website! What is your website name?")
        return ADV_ONBOARD
    elif query.data == "upgrade":
        await query.message.reply_text(
            "💎 To upgrade to premium, contact MR DEV at WhatsApp: 2349164624021 or click the contact button below."
        )
        return ConversationHandler.END
    elif query.data == "my_websites":
        await send_website_history(query, uid)
        return WEBSITE_HISTORY
    elif query.data == "whatsapp_unban":
        if not is_premium:
            await query.message.reply_text("🔒 This feature is only for premium users. Please upgrade to use WhatsApp unban!")
            return ConversationHandler.END
        await query.message.reply_text("Enter your WhatsApp number (with country code):")
        return WHATSAPP_UNBAN
    elif query.data == "profile":
        await send_profile(query, uid)
        return ConversationHandler.END
    elif query.data == "teacher":
        await query.message.reply_text(
            "📚 *Bot Teacher Guide*\n\n"
            "• For free ZIP, paste a URL to get zipped HTML.\n"
            "• Premium users can build advanced websites with logo/sections.\n"
            "• WhatsApp Unban is for premium users only. Contact admin for upgrade.\n"
            "• /admin commands: set premium and WhatsApp unban times (admin only).\n"
            "• Use /help for more commands.\n",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

async def handle_free_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        await update.message.reply_text("❌ Invalid URL. Please send a correct link (http/https).")
        return FREE_URL
    await update.message.reply_text("🔗 Fetching HTML from your URL...")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html_code = resp.text
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch the HTML: {e}")
        return ConversationHandler.END

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        zipf.writestr("index.html", html_code)
    zip_buffer.seek(0)

    # Save history
    db = load_db()
    uid = str(update.effective_user.id)
    db.setdefault("website_data", {}).setdefault(uid, [])
    db["website_data"][uid].append({
        "type": "free",
        "timestamp": datetime.utcnow().isoformat(),
        "filename": "website_code.zip",
        "content": html_code
    })
    save_db(db)

    await update.message.reply_document(
        document=InputFile(zip_buffer, filename="website_code.zip"),
        caption="🙃 Here is your zipped website code (index.html inside)!"
    )
    await update.message.reply_text("You can /start again to use other features.")
    return ConversationHandler.END

ADV_QUESTIONS = [
    "What is your website name?",
    "Describe your website (About section):",
    "What color or color code should be the main theme?",
    "What sections do you want? (e.g., Home, Services, Contact, About)",
    "Write your contact info (email, phone, WhatsApp, etc):",
    "Please upload your logo image (send as file, not photo), or type 'skip'."
]

def load_db():
    with open(DB_FILE, "r") as f:
        return json.load(f)
def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

async def adv_onboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("adv_step", 0)
    data = context.user_data.setdefault("adv_data", {})
    text = update.message.text

    if step == 0:
        data["name"] = text
    elif step == 1:
        data["about"] = text
    elif step == 2:
        data["color"] = text
    elif step == 3:
        data["sections"] = [s.strip() for s in text.split(",") if s.strip()]
    elif step == 4:
        data["contact"] = text

    if step < 5:
        context.user_data["adv_step"] = step + 1
        await update.message.reply_text(ADV_QUESTIONS[step])
        return ADV_ONBOARD
    else:
        await update.message.reply_text("Send your logo as a file or type 'skip'.")
        return LOGO

async def adv_logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data["adv_data"]
    logo_path = None
    if update.message.text and update.message.text.strip().lower() == "skip":
        logo_path = None
    elif update.message.document:
        file = await update.message.document.get_file()
        ext = os.path.splitext(update.message.document.file_name)[1]
        logo_path = os.path.join(LOGO_DIR, f"{update.effective_user.id}_logo{ext}")
        await file.download_to_drive(logo_path)
    else:
        await update.message.reply_text("Send a logo as file or type 'skip'.")
        return LOGO

    data["logo"] = logo_path
    db = load_db()
    uid = str(update.effective_user.id)
    db.setdefault("website_data", {}).setdefault(uid, [])
    db["website_data"][uid].append({
        "type": "adv",
        "timestamp": datetime.utcnow().isoformat(),
        "filename": "advanced_website.zip",
        "content": data
    })
    save_db(db)

    zip_buf = generate_website_zip(data, logo_path)
    await update.message.reply_document(
        document=InputFile(zip_buf, filename="advanced_website.zip"),
        caption="Here is your advanced website ZIP. Unzip and host anywhere!"
    )
    await update.message.reply_text("If you want to update info, just start again with /start.")
    return ConversationHandler.END

def generate_website_zip(data, logo_path=None):
    pages = {}
    sections = data.get("sections", ["Home", "About", "Contact"])
    nav_links = "".join([f"<a href='{s.lower()}.html'>{s}</a> | " for s in sections])[:-3]

    home_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{data['name']}</title>
    <style>
        body {{ background: {data['color']}; font-family: Arial, sans-serif; color: #222; max-width: 700px; margin: 40px auto; border-radius: 16px; padding: 32px; box-shadow: 0 0 24px #0002; }}
        nav {{ margin-bottom: 32px; }}
        .logo {{ width: 180px; display: block; margin-bottom: 24px; }}
        .dev-contact {{font-size: 12px; margin-top: 32px; color: #888}}
        .hero {{ font-size:2em; margin-top: 0; }}
    </style>
</head>
<body>
    <nav>{nav_links}</nav>
    {"<img src='logo.png' class='logo'>" if logo_path else ""}
    <h1 class="hero">{data['name']}</h1>
    <p>{data['about']}</p>
    <div class="dev-contact">
        Developed by MR DEV<br>
        Contact: 2349164624021
    </div>
</body>
</html>"""
    pages["index.html"] = home_html

    if "About" in sections:
        about_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>About - {data['name']}</title>
    <style>body {{ background: {data['color']}; font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; border-radius: 16px; padding: 32px; box-shadow: 0 0 24px #0002; }} nav {{ margin-bottom: 32px; }} .dev-contact {{font-size: 12px; margin-top: 32px; color: #888}}</style>
</head>
<body>
    <nav>{nav_links}</nav>
    <h1>About {data['name']}</h1>
    <p>{data['about']}</p>
    <div class="dev-contact">
        Developed by MR DEV<br>
        Contact: 2349164624021
    </div>
</body>
</html>"""
        pages["about.html"] = about_html

    if "Contact" in sections:
        contact_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Contact - {data['name']}</title>
    <style>body {{ background: {data['color']}; font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; border-radius: 16px; padding: 32px; box-shadow: 0 0 24px #0002; }} nav {{ margin-bottom: 32px; }} .dev-contact {{font-size: 12px; margin-top: 32px; color: #888}}</style>
</head>
<body>
    <nav>{nav_links}</nav>
    <h1>Contact</h1>
    <div>
        <p>{data['contact']}</p>
    </div>
    <div class="dev-contact">
        Developed by MR DEV<br>
        Contact: 2349164624021
    </div>
</body>
</html>"""
        pages["contact.html"] = contact_html

    for s in sections:
        if s not in ("Home", "About", "Contact"):
            html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{s} - {data['name']}</title>
    <style>body {{ background: {data['color']}; font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; border-radius: 16px; padding: 32px; box-shadow: 0 0 24px #0002; }} nav {{ margin-bottom: 32px; }} .dev-contact {{font-size: 12px; margin-top: 32px; color: #888}}</style>
</head>
<body>
    <nav>{nav_links}</nav>
    <h1>{s}</h1>
    <p>This page is coming soon.</p>
    <div class="dev-contact">
        Developed by MR DEV<br>
        Contact: 2349164624021
    </div>
</body>
</html>"""
            pages[f"{s.lower()}.html"] = html

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for fname, content in pages.items():
            zipf.writestr(fname, content)
        if logo_path and os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                zipf.writestr("logo.png", f.read())
    zip_buffer.seek(0)
    return zip_buffer

async def handle_whatsapp_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = str(update.effective_user.id)
    is_premium = db["premium"].get(uid, False)
    if not is_premium:
        await update.message.reply_text("🔒 This feature is only for premium users. Please upgrade to use WhatsApp unban!")
        return ConversationHandler.END

    # Instead of asking number, send the tool link directly
    unban_tool_link = "https://mrdevunbantoolprem.vercel.app"

    await update.message.reply_text(
        "⚠️ This is an UNBAN TOOL. Use wisely.\n\n"
        f"Click the link below to access the tool:\n{unban_tool_link}\n\n"
        "Make sure you follow instructions carefully."
    )
    return ConversationHandler.END

async def send_website_history(query, uid):
    db = load_db()
    sites = db.get("website_data", {}).get(uid, [])
    if not sites:
        await query.message.reply_text("No websites found in your history.")
        return
    msg = "📂 *Your Websites:*\n\n"
    for i, site in enumerate(sites, 1):
        typ = "Free" if site["type"] == "free" else "Advanced"
        time = site["timestamp"].replace("T", " ")[:19]
        msg += f"{i}. {typ} ({time}) — {site['filename']}\n"
    msg += "\nReply with the number to download, or /start to go back."
    query.message.chat_data["websites"] = sites
    await query.message.reply_text(msg, parse_mode="Markdown")

async def handle_website_download(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    sites = update.message.chat_data.get("websites", [])
    txt = update.message.text.strip()
    if not txt.isdigit():
        return
    idx = int(txt) - 1
    if idx < 0 or idx >= len(sites):
        await update.message.reply_text("Invalid number. Please try again.")
        return
    site = sites[idx]
    if site["type"] == "free":
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            zipf.writestr("index.html", site["content"])
        zip_buffer.seek(0)
        await update.message.reply_document(
            document=InputFile(zip_buffer, filename="website_code.zip"),
            caption="🙃 Here is your zipped website code (index.html inside)!"
        )
    else:
        zip_buf = generate_website_zip(site["content"], site["content"].get("logo"))
        await update.message.reply_document(
            document=InputFile(zip_buf, filename="advanced_website.zip"),
            caption="Here is your advanced website ZIP. Unzip and host anywhere!"
        )
    await update.message.reply_text("You can /start again to use other features.")

async def send_profile(query, uid):
    db = load_db()
    is_premium = db["premium"].get(uid, False)
    msg = f"⚙️ *Your Profile:*\n\n"
    msg += f"👤 User ID: `{uid}`\n"
    msg += f"💎 Premium: {'Yes' if is_premium else 'No'}\n"
    msg += f"🌐 Websites Created: {len(db.get('website_data', {}).get(uid, []))}\n"
    msg += "\nNeed to upgrade or edit your info? Contact support!"
    await query.message.reply_text(msg, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Use /start to open the main menu. Free: Paste a URL for instant ZIP. Premium: Build a full site. WhatsApp unban status is for premium users only."
    )

# --- Admin Commands ---
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use admin commands.")
        return
    args = update.message.text.strip().split()
    if len(args) < 2:
        await update.message.reply_text("Usage: /admin premium user_id [on|off]\n/admin unban number YYYY-MM-DD HH:MM")
        return
    cmd = args[1]
    db = load_db()
    if cmd == "premium" and len(args) == 4:
        user_id, val = args[2], args[3].lower()
        db["premium"][user_id] = (val == "on")
        save_db(db)
        await update.message.reply_text(f"User {user_id} premium set to {val}")
    elif cmd == "unban" and len(args) >= 5:
        number = args[2]
        dt_str = " ".join(args[3:5])
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        except Exception:
            await update.message.reply_text("Invalid date/time format. Use YYYY-MM-DD HH:MM")
            return
        db.setdefault("unban_status", {})[number] = {
            "unban_time": dt.isoformat()
        }
        save_db(db)
        await update.message.reply_text(f"Unban time for {number} set to {dt_str}")
    else:
        await update.message.reply_text("Unknown admin command or wrong parameters.")

async def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")
    if update and getattr(update, "message", None):
        await update.message.reply_text("⚠️ Oops! Something went wrong. Please try again or /start.")

conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler('start', start),
        CallbackQueryHandler(menu_callback)
    ],
    states={
        FREE_URL: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_free_url)],
        ADV_ONBOARD: [MessageHandler(filters.TEXT & (~filters.COMMAND), adv_onboard)],
        LOGO: [MessageHandler(filters.Document.ALL | filters.TEXT, adv_logo)],
        WHATSAPP_UNBAN: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_whatsapp_unban)],
        WEBSITE_HISTORY: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_website_download)],
    },
    fallbacks=[CommandHandler('start', start)],
    allow_reentry=True
)

def main():
    from keep_alive import keep_alive
    keep_alive()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_member))
    app.add_handler(CommandHandler("tagall", tag_all))
    app.add_handler(CommandHandler("tag", tag_reply))
    app.add_error_handler(error_handler)
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    import time
    while True:
        try:
            main()
        except Exception as e:
            print(f"⚠️ Bot crashed with error: {e}")
            print("🔄 Restarting in 5 seconds...")
            time.sleep(5)
