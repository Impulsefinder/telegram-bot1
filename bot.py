import asyncio
import json
from datetime import datetime
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==================== تنظیمات ====================
import os

BOT_TOKEN = os.environ.get('BOT_TOKEN', '8966196250:AAHcuEZY4DJ0kymLKotGNlzv0y8x5cCW1Jw')
CHANNEL_ID = os.environ.get('CHANNEL_ID', '@khaneyeroyaeeantalya')
ADMIN_ID = int(os.environ.get('ADMIN_ID', '132101989'))آیدی عددی ادمین

# ==================== دیتابیس موقت ====================
user_states = {}
admin_states = {}

REGISTRATION_STEPS = [
    'first_name',
    'telegram_username',
    'email',
    'account_number',
    'broker_name',
    'account_type',
    'account_balance'
]

QUESTIONS = [
    '📝 لطفاً نام و نام خانوادگی خود را وارد کنید:',
    '📱 لطفاً یوزر تلگرام خود را وارد کنید (بدون @):',
    '📧 لطفاً ایمیل خود را وارد کنید:',
    '🔢 لطفاً شماره اکانت/حساب خود را وارد کنید:',
    '🏢 لطفاً نام بروکر خود را وارد کنید:',
    '💳 نوع حساب خود را انتخاب کنید:\n1️⃣ دلاری\n2️⃣ سنتی',
    '💰 لطفاً موجودی اکانت خود را وارد کنید (به دلار):'
]

# ==================== توابع Google Sheets ====================
def setup_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("YOUR_SHEET_ID").sheet1
    return sheet

# ==================== مدیریت شروع ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    first_name = user.first_name
    username = user.username or ""
    
    user_states[user_id] = {
        'step': 0,
        'data': {
            'user_id': user_id,
            'username': username,
            'first_name': first_name
        },
        'type': 'registration'
    }
    
    welcome_message = (
        f"👋 سلام {first_name} عزیز!\n\n"
        "به ربات ثبت نام خوش آمدید.\n\n"
        "لطفاً اطلاعات خود را به صورت گام به گام وارد کنید.\n\n"
        "📝 نام و نام خانوادگی خود را وارد کنید:"
    )
    
    await update.message.reply_text(welcome_message)

# ==================== مدیریت پیام‌ها ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text
    
    # دستورات ادمین
    if user_id == ADMIN_ID:
        if text == '/admin':
            await show_admin_panel(update)
            return
        elif text == '/report':
            await generate_report(update)
            return
        elif text.startswith('/user_'):
            username = text.replace('/user_', '')
            await show_user_details(update, username)
            return
        elif text.startswith('/link_'):
            username = text.replace('/link_', '')
            admin_states[user_id] = {'action': 'send_link', 'username': username}
            await update.message.reply_text(f"لینک دعوت برای کاربر @{username} را وارد کنید:")
            return
    
    # پردازش وضعیت کاربر
    if user_id in user_states:
        state = user_states[user_id]
        
        if state['type'] == 'registration':
            await handle_registration(update, context)
        elif state['type'] == 'documents':
            await handle_documents(update, context)
    elif text != '/start':
        await update.message.reply_text("لطفاً /start را بزنید.")

# ==================== مدیریت ثبت نام ====================
async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    state = user_states[user_id]
    step = state['step']
    step_name = REGISTRATION_STEPS[step]
    
    # اعتبارسنجی
    if step_name == 'telegram_username':
        text = text.replace('@', '')
    elif step_name == 'email':
        if '@' not in text or '.' not in text:
            await update.message.reply_text('❌ ایمیل نامعتبر است. لطفاً یک ایمیل صحیح وارد کنید:')
            return
    elif step_name == 'account_balance':
        try:
            float(text)
        except:
            await update.message.reply_text('❌ لطفاً یک عدد صحیح وارد کنید (به دلار):')
            return
    
    # ذخیره اطلاعات
    state['data'][step_name] = text
    state['step'] += 1
    
    if state['step'] < len(REGISTRATION_STEPS):
        await update.message.reply_text(QUESTIONS[state['step']])
    else:
        await show_summary(update, state['data'])

# ==================== نمایش خلاصه ====================
async def show_summary(update: Update, data):
    user_id = update.effective_user.id
    account_type = 'دلاری' if data['account_type'] == '1' else 'سنتی'
    
    summary = (
        f"📋 **خلاصه اطلاعات**\n\n"
        f"👤 نام: {data['first_name']}\n"
        f"📱 تلگرام: @{data['telegram_username']}\n"
        f"📧 ایمیل: {data['email']}\n"
        f"🔢 شماره حساب: {data['account_number']}\n"
        f"🏢 بروکر: {data['broker_name']}\n"
        f"💳 نوع حساب: {account_type}\n"
        f"💰 موجودی: ${data['account_balance']}\n\n"
        f"✅ آیا اطلاعات صحیح است؟"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"confirm_{user_id}"),
            InlineKeyboardButton("❌ ویرایش", callback_data=f"edit_{user_id}")
        ]
    ]
    
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== مدیریت دکمه‌ها ====================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    await query.answer()
    
    if data.startswith('confirm_'):
        target_id = int(data.split('_')[1])
        await confirm_registration(target_id, query)
    elif data.startswith('edit_'):
        target_id = int(data.split('_')[1])
        user_states[target_id] = {
            'step': 0,
            'data': user_states[target_id]['data'],
            'type': 'registration'
        }
        await query.message.reply_text('🔄 لطفاً اطلاعات را مجدداً وارد کنید.\n\n📝 نام و نام خانوادگی:')
    elif data == 'send_documents':
        user_states[user_id] = {'step': 0, 'data': {}, 'type': 'documents'}
        await query.message.reply_text('📄 لطفاً تصویر مدارک ID خود را ارسال کنید:')
    elif data == 'check_status':
        await query.message.reply_text('📋 وضعیت شما: ثبت نام شده')

# ==================== تایید ثبت نام ====================
async def confirm_registration(user_id, query):
    user_data = user_states[user_id]['data']
    user_data['account_type'] = 'دلاری' if user_data['account_type'] == '1' else 'سنتی'
    
    # ارسال به کانال
    channel_message = (
        f"🔔 **کاربر جدید**\n\n"
        f"👤 نام: {user_data['first_name']}\n"
        f"📱 تلگرام: @{user_data['telegram_username']}\n"
        f"📧 ایمیل: {user_data['email']}\n"
        f"💰 موجودی: ${user_data['account_balance']}"
    )
    
    try:
        await query.message.bot.send_message(CHANNEL_ID, channel_message)
    except:
        pass
    
    # ارسال به ادمین
    admin_message = f"🔔 ثبت نام جدید\n👤 {user_data['first_name']}\n📱 @{user_data['telegram_username']}"
    try:
        await query.message.bot.send_message(ADMIN_ID, admin_message)
    except:
        pass
    
    success_message = (
        "✅ اطلاعات شما ثبت شد!\n\n"
        "📌 پس از بررسی، کد IB برای شما ارسال خواهد شد.\n"
        "لطفاً شکیبا باشید. 🙏"
    )
    
    await query.message.reply_text(success_message)
    del user_states[user_id]

# ==================== توابع ادمین ====================
async def show_admin_panel(update: Update):
    message = (
        "🔧 **پنل مدیریت**\n\n"
        "/report - گزارش کامل\n"
        "/user_username - اطلاعات کاربر\n"
        "/link_username - ارسال لینک"
    )
    await update.message.reply_text(message)

async def generate_report(update: Update):
    await update.message.reply_text("📊 گزارش کاربران:\n\nهنوز کاربری ثبت نشده.")

async def show_user_details(update: Update, username):
    await update.message.reply_text(f"🔍 اطلاعات کاربر @{username}")

# ==================== مدیریت مدارک ====================
async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_states[user_id]
    step = state['step']
    
    file_id = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document:
        file_id = update.message.document.file_id
    
    if not file_id:
        await update.message.reply_text('❌ لطفاً تصویر یا فایل ارسال کنید.')
        return
    
    if step == 0:
        state['data']['id_document'] = file_id
        state['step'] = 1
        await update.message.reply_text('📄 حالا مدارک تاییدیه را ارسال کنید:')
    elif step == 1:
        state['data']['verification_document'] = file_id
        
        # ارسال به ادمین
        await update.message.bot.send_document(ADMIN_ID, state['data']['id_document'])
        await update.message.bot.send_document(ADMIN_ID, state['data']['verification_document'])
        
        await update.message.reply_text('✅ مدارک دریافت شد.')
        del user_states[user_id]

# ==================== main ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", lambda u, c: u.message.reply_text("❌ لغو شد")))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, handle_documents))
    
    print("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
