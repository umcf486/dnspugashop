"""
ربات فروشگاهی AyhanX-Freedom - نسخه نهایی با پشتیبانی از پایتون ۳.۱۱
"""

import os
import sys
import json
import logging
import sqlite3
import random
import time
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== تنظیمات اولیه ====================
BOT_TOKEN = '8631736538:AAFkNgUY5QM4Gr8eqQsviUk6NxkLcZvT5yc'
ADMIN_ID = 8907076433
SUPPORT_USERNAME = '@nspubgabot'
CHANNEL_ID = '@dnspubga'
SHOP_NAME = 'AyhanX-Freedom'

# وضعیت‌های سفارش
ORDER_STATUS = {
    'PENDING': 'pending',
    'CONFIRMED': 'confirmed',
    'REJECTED': 'rejected',
    'SENT': 'sent'
}

# محصولات و پلن‌ها
PRODUCTS = {
    'wireguard_gaming': {
        'name': 'وایرگارد گیم و وب گردی',
        'emoji': '🛡️',
        'plans': {
            'plan_wg_1m': {'name': '۱ ماهه ۳۶ گیگ', 'price': 400, 'description': '۳۶ گیگابایت، ۱ ماهه'},
            'plan_wg_2m': {'name': '۲ ماهه ۷۸ گیگ', 'price': 600, 'description': '۷۸ گیگابایت، ۲ ماهه'},
            'plan_wg_3m': {'name': '۳ ماهه ۱۲۷ گیگ', 'price': 800, 'description': '۱۲۷ گیگابایت، ۳ ماهه'},
            'plan_wg_6m': {'name': '۶ ماهه ۳۰۰ گیگ', 'price': 1200, 'description': '۳۰۰ گیگابایت، ۶ ماهه'}
        }
    },
    'config_monthly': {
        'name': 'کانفیگ ماهانه',
        'emoji': '📅',
        'plans': {
            'plan_50': {'name': '۵۰ گیگ', 'price': 35000, 'description': '۵۰ گیگابایت، ۱ ماهه'},
            'plan_100': {'name': '۱۰۰ گیگ', 'price': 55000, 'description': '۱۰۰ گیگابایت، ۱ ماهه'},
            'plan_200': {'name': '۲۰۰ گیگ', 'price': 85000, 'description': '۲۰۰ گیگابایت، ۱ ماهه'}
        }
    },
    'config_quarterly': {
        'name': 'کانفیگ سه‌ماهه',
        'emoji': '📆',
        'plans': {
            'plan_unlimited': {'name': 'نامحدود', 'price': 150000, 'description': 'حجم نامحدود، ۳ ماهه'},
            'plan_500': {'name': '۵۰۰ گیگ', 'price': 120000, 'description': '۵۰۰ گیگابایت، ۳ ماهه'}
        }
    }
}

CONFIG_TYPES = ['WireGuard', 'V2Ray']
PAYMENT_METHODS = ['کارت به کارت', 'رمز دوم (اینترنتی)', 'کیف پول (USDT)']

# ==================== دیتابیس SQLite ====================
DB_PATH = '/data/data.db' if os.path.exists('/data') else 'data.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                userId INTEGER,
                productId TEXT,
                planId TEXT,
                configType TEXT,
                customerName TEXT,
                paymentMethod TEXT,
                trackingCode TEXT,
                receiptPhotoId TEXT,
                status TEXT,
                createdAt INTEGER
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS user_states (
                chatId INTEGER PRIMARY KEY,
                step TEXT,
                tempData TEXT
            )
        ''')
        conn.commit()
    logging.info('✅ دیتابیس آماده شد')

# ==================== توابع کمکی ====================
def generate_order_id():
    return hex(int(time.time() * 1000))[2:] + hex(random.randint(0, 0xFFFF))[2:]

def save_order(order):
    with get_db() as conn:
        conn.execute('''
            INSERT INTO orders (id, userId, productId, planId, configType, customerName, paymentMethod,
                                trackingCode, receiptPhotoId, status, createdAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (order['id'], order['userId'], order['productId'], order['planId'], order['configType'],
              order['customerName'], order['paymentMethod'], order['trackingCode'],
              order['receiptPhotoId'], order['status'], order['createdAt']))
        conn.commit()

def get_order(order_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
        return dict(row) if row else None

def update_order_status(order_id, status, extra=None):
    order = get_order(order_id)
    if not order:
        return None
    if extra:
        order.update(extra)
    order['status'] = status
    with get_db() as conn:
        conn.execute('UPDATE orders SET status = ?, configType = ?, receiptPhotoId = ? WHERE id = ?',
                     (status, order.get('configType'), order.get('receiptPhotoId'), order_id))
        conn.commit()
    return order

def get_user_orders(user_id):
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM orders WHERE userId = ? ORDER BY createdAt DESC', (user_id,)).fetchall()
        return [dict(row) for row in rows]

def get_all_orders():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM orders ORDER BY createdAt DESC').fetchall()
        return [dict(row) for row in rows]

def get_user_state(chat_id):
    with get_db() as conn:
        row = conn.execute('SELECT step, tempData FROM user_states WHERE chatId = ?', (chat_id,)).fetchone()
        if row:
            return {'step': row['step'], 'tempData': json.loads(row['tempData'] or '{}')}
        return {'step': None, 'tempData': {}}

def set_user_state(chat_id, step, temp_data=None):
    if temp_data is None:
        temp_data = {}
    with get_db() as conn:
        conn.execute('INSERT OR REPLACE INTO user_states (chatId, step, tempData) VALUES (?, ?, ?)',
                     (chat_id, step, json.dumps(temp_data)))
        conn.commit()

def clear_user_state(chat_id):
    with get_db() as conn:
        conn.execute('DELETE FROM user_states WHERE chatId = ?', (chat_id,))
        conn.commit()

# ==================== کیبوردها ====================
def main_menu():
    keyboard = [
        [InlineKeyboardButton('🛒 فروشگاه', callback_data='menu|shop'),
         InlineKeyboardButton('📋 سفارش‌های من', callback_data='menu|orders')],
        [InlineKeyboardButton('🆘 پشتیبانی', callback_data='menu|support'),
         InlineKeyboardButton('📢 کانال', callback_data='menu|channel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def products_keyboard():
    keyboard = []
    for pid, prod in PRODUCTS.items():
        keyboard.append([InlineKeyboardButton(f"{prod['emoji']} {prod['name']}", callback_data=f"product|{pid}")])
    keyboard.append([InlineKeyboardButton('🔙 بازگشت به منو', callback_data='menu|main')])
    return InlineKeyboardMarkup(keyboard)

def plans_keyboard(product_id):
    prod = PRODUCTS.get(product_id)
    if not prod:
        return InlineKeyboardMarkup([])
    keyboard = []
    for pid, plan in prod['plans'].items():
        price_str = f"{plan['price']:,} تومان".replace(',', '،')
        keyboard.append([InlineKeyboardButton(f"{plan['name']} - {price_str}", callback_data=f"plan|{product_id}|{pid}")])
    keyboard.append([InlineKeyboardButton('🔙 بازگشت به محصولات', callback_data='menu|shop')])
    return InlineKeyboardMarkup(keyboard)

def config_types_keyboard():
    keyboard = []
    for ct in CONFIG_TYPES:
        keyboard.append([InlineKeyboardButton(ct, callback_data=f"config|{ct}")])
    keyboard.append([InlineKeyboardButton('🔙 انصراف', callback_data='menu|main')])
    return InlineKeyboardMarkup(keyboard)

def payment_methods_keyboard():
    keyboard = []
    for pm in PAYMENT_METHODS:
        keyboard.append([InlineKeyboardButton(pm, callback_data=f"pay|{pm}")])
    keyboard.append([InlineKeyboardButton('🔙 انصراف', callback_data='menu|main')])
    return InlineKeyboardMarkup(keyboard)

def order_confirm_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton('✅ تایید و ثبت', callback_data=f"confirm|{order_id}"),
         InlineKeyboardButton('❌ لغو', callback_data=f"cancel|{order_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_order_keyboard(order_id):
    keyboard = [
        [InlineKeyboardButton('✅ تایید', callback_data=f"admin|confirm|{order_id}"),
         InlineKeyboardButton('❌ رد', callback_data=f"admin|reject|{order_id}")],
        [InlineKeyboardButton('📤 ارسال اکانت', callback_data=f"admin|send|{order_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== توابع فرمت پیام ====================
def format_order_summary(order):
    product = PRODUCTS.get(order['productId'], {})
    plan = product.get('plans', {}).get(order['planId'], {})
    price_str = f"{plan.get('price', 0):,} تومان".replace(',', '،') if plan else 'نامشخص'
    date = datetime.fromtimestamp(order['createdAt'] / 1000).strftime('%Y-%m-%d %H:%M')
    status_text = {
        'pending': '⏳ در انتظار تایید',
        'confirmed': '✅ تایید شده',
        'rejected': '❌ رد شده',
        'sent': '📤 ارسال شده'
    }.get(order['status'], order['status'])
    return f"""
📋 <b>خلاصه سفارش</b>
🆔 شناسه: <code>{order['id']}</code>
📦 محصول: {product.get('name', order['productId'])}
📊 پلن: {plan.get('name', order['planId'])}
🔧 نوع کانفیگ: {order.get('configType', 'تعیین نشده')}
💰 قیمت: {price_str}
👤 نام: {order.get('customerName', 'ندارد')}
💳 روش پرداخت: {order.get('paymentMethod', 'ندارد')}
🔢 کد پیگیری: {order.get('trackingCode', 'ندارد')}
📎 رسید: {'✅ ارسال شده' if order.get('receiptPhotoId') else '❌ ارسال نشده'}
📅 تاریخ: {date}
📌 وضعیت: {status_text}
    """.strip()

def format_admin_order_message(order):
    product = PRODUCTS.get(order['productId'], {})
    plan = product.get('plans', {}).get(order['planId'], {})
    price_str = f"{plan.get('price', 0):,} تومان".replace(',', '،') if plan else 'نامشخص'
    date = datetime.fromtimestamp(order['createdAt'] / 1000).strftime('%Y-%m-%d %H:%M')
    return f"""
🆕 <b>سفارش جدید</b>
🆔 شناسه: <code>{order['id']}</code>
👤 کاربر: <a href="tg://user?id={order['userId']}">{order.get('customerName', 'کاربر')}</a>
📦 محصول: {product.get('name', order['productId'])}
📊 پلن: {plan.get('name', order['planId'])}
🔧 نوع کانفیگ: {order.get('configType', 'تعیین نشده')}
💰 قیمت: {price_str}
💳 روش پرداخت: {order.get('paymentMethod', 'ندارد')}
🔢 کد پیگیری: {order.get('trackingCode', 'ندارد')}
📎 رسید: {'✅ ارسال شده' if order.get('receiptPhotoId') else '❌ ارسال نشده'}
📅 تاریخ: {date}
    """.strip()

def format_order_status(order):
    return {
        'pending': '⏳ در انتظار تایید',
        'confirmed': '✅ تایید شده',
        'rejected': '❌ رد شده',
        'sent': '📤 ارسال شده'
    }.get(order['status'], order['status'])

# ==================== هندلرهای ربات ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await clear_user_state(chat_id)
    await update.message.reply_text(
        f"👋 به <b>{SHOP_NAME}</b> خوش آمدید!\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=main_menu(),
        parse_mode='HTML'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.from_user.id
    data = query.data

    # منو
    if data.startswith('menu|'):
        parts = data.split('|')
        action = parts[1]
        await clear_user_state(chat_id)
        if action == 'shop':
            await query.edit_message_text('🛒 <b>محصولات موجود:</b>', reply_markup=products_keyboard(), parse_mode='HTML')
        elif action == 'orders':
            await show_user_orders(chat_id, query)
        elif action == 'support':
            await query.edit_message_text(f'🆘 برای پشتیبانی با {SUPPORT_USERNAME} تماس بگیرید.', reply_markup=main_menu())
        elif action == 'channel':
            await query.edit_message_text(f'📢 کانال ما: {CHANNEL_ID}', reply_markup=main_menu())
        elif action == 'main':
            await query.edit_message_text('🏠 منوی اصلی:', reply_markup=main_menu())
        return

    # انتخاب محصول
    if data.startswith('product|'):
        parts = data.split('|')
        product_id = parts[1]
        if product_id not in PRODUCTS:
            await query.edit_message_text('❌ محصول نامعتبر. لطفاً دوباره تلاش کنید.')
            return
        state = await get_user_state(chat_id)
        state['tempData']['productId'] = product_id
        state['step'] = 'selecting_plan'
        await set_user_state(chat_id, state['step'], state['tempData'])
        await query.edit_message_text(
            f"📦 <b>{PRODUCTS[product_id]['name']}</b>\nلطفاً پلن مورد نظر را انتخاب کنید:",
            reply_markup=plans_keyboard(product_id),
            parse_mode='HTML'
        )
        return

    # انتخاب پلن
    if data.startswith('plan|'):
        parts = data.split('|')
        if len(parts) != 3:
            await query.edit_message_text('خطا در انتخاب پلن. لطفاً دوباره تلاش کنید.')
            return
        product_id, plan_id = parts[1], parts[2]
        product = PRODUCTS.get(product_id)
        if not product or plan_id not in product['plans']:
            await query.edit_message_text('❌ محصول یا پلن نامعتبر.')
            return
        state = await get_user_state(chat_id)
        state['tempData']['productId'] = product_id
        state['tempData']['planId'] = plan_id
        state['step'] = 'selecting_config_type'
        await set_user_state(chat_id, state['step'], state['tempData'])
        plan = product['plans'][plan_id]
        price_str = f"{plan['price']:,} تومان".replace(',', '،')
        await query.edit_message_text(
            f"✅ پلن <b>{plan['name']}</b> با قیمت {price_str} انتخاب شد.\n\n🔧 حالا <b>نوع کانفیگ</b> مورد نظر را انتخاب کنید:",
            reply_markup=config_types_keyboard(),
            parse_mode='HTML'
        )
        return

    # انتخاب نوع کانفیگ
    if data.startswith('config|'):
        parts = data.split('|')
        config_type = parts[1]
        if config_type not in CONFIG_TYPES:
            await query.edit_message_text('نوع کانفیگ نامعتبر.')
            return
        state = await get_user_state(chat_id)
        state['tempData']['configType'] = config_type
        state['step'] = 'entering_name'
        await set_user_state(chat_id, state['step'], state['tempData'])
        await query.edit_message_text(
            f"🔧 نوع کانفیگ: <b>{config_type}</b>\n\n👤 لطفاً <b>نام کامل</b> خود را وارد کنید:",
            parse_mode='HTML'
        )
        return

    # انتخاب روش پرداخت
    if data.startswith('pay|'):
        parts = data.split('|')
        method = parts[1]
        if method not in PAYMENT_METHODS:
            await query.edit_message_text('روش پرداخت نامعتبر.')
            return
        state = await get_user_state(chat_id)
        state['tempData']['paymentMethod'] = method
        state['step'] = 'entering_tracking'
        await set_user_state(chat_id, state['step'], state['tempData'])
        await query.edit_message_text(
            f"💳 روش پرداخت: {method}\n\n🔢 لطفاً <b>کد پیگیری</b> پرداخت را وارد کنید:",
            parse_mode='HTML'
        )
        return

    # تایید یا لغو سفارش
    if data.startswith('confirm|') or data.startswith('cancel|'):
        parts = data.split('|')
        action = parts[0]
        order_id = parts[1]
        state = await get_user_state(chat_id)
        if not state or not state['tempData'].get('order') or state['tempData']['order']['id'] != order_id:
            await query.edit_message_text('❌ سفارش یافت نشد. دوباره تلاش کنید.')
            await clear_user_state(chat_id)
            return
        if action == 'cancel':
            await clear_user_state(chat_id)
            await query.edit_message_text('❌ سفارش لغو شد.', reply_markup=main_menu())
            return
        if action == 'confirm':
            order = state['tempData']['order']
            order['status'] = ORDER_STATUS['PENDING']
            await save_order(order)
            await clear_user_state(chat_id)
            # ارسال به ادمین
            admin_msg = format_admin_order_message(order)
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 <b>سفارش جدید نیاز به تایید دارد</b>\n{admin_msg}",
                reply_markup=admin_order_keyboard(order['id']),
                parse_mode='HTML'
            )
            await query.edit_message_text(
                f"✅ سفارش شما با شناسه <code>{order['id']}</code> ثبت شد و در انتظار تایید ادمین می‌باشد.",
                reply_markup=main_menu(),
                parse_mode='HTML'
            )
        return

    # اقدامات ادمین
    if data.startswith('admin|'):
        parts = data.split('|')
        if len(parts) < 3:
            await query.edit_message_text('دستور نامعتبر.')
            return
        action = parts[1]
        order_id = parts[2]
        order = await get_order(order_id)
        if not order:
            await query.edit_message_text(f'❌ سفارش با شناسه {order_id} یافت نشد.')
            return
        if action == 'confirm':
            await update_order_status(order_id, ORDER_STATUS['CONFIRMED'])
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ سفارش <code>{order_id}</code> تایید شد. لطفاً کانفیگ را به کاربر ارسال کنید.", parse_mode='HTML')
            await context.bot.send_message(chat_id=order['userId'], text=f"✅ سفارش شما با شناسه <code>{order_id}</code> تایید شد. به زودی اکانت برای شما ارسال خواهد شد.", parse_mode='HTML')
            await query.edit_message_text(
                f"🔔 <b>سفارش {order_id}</b>\n{format_admin_order_message(order)}\n\nوضعیت: {ORDER_STATUS['CONFIRMED']} (منتظر ارسال اکانت)",
                reply_markup=None
            )
        elif action == 'reject':
            await update_order_status(order_id, ORDER_STATUS['REJECTED'])
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ سفارش <code>{order_id}</code> رد شد.", parse_mode='HTML')
            await context.bot.send_message(chat_id=order['userId'], text=f"❌ سفارش شما با شناسه <code>{order_id}</code> رد شد.", parse_mode='HTML')
            await query.edit_message_text(
                f"🔔 <b>سفارش {order_id}</b>\n{format_admin_order_message(order)}\n\nوضعیت: {ORDER_STATUS['REJECTED']}",
                reply_markup=None
            )
        elif action == 'send':
            context.user_data['admin_send_order'] = order_id
            await query.edit_message_text(f"📤 لطفاً <b>متن اکانت</b> را برای سفارش <code>{order_id}</code> ارسال کنید.", parse_mode='HTML')
            await context.bot.send_message(chat_id=order['userId'], text=f"🔄 ادمین در حال ارسال اکانت برای سفارش <code>{order_id}</code> می‌باشد.", parse_mode='HTML')
        return

    await query.edit_message_text('دستور نامعتبر.')

async def show_user_orders(chat_id, query=None):
    orders = await get_user_orders(chat_id)
    if not orders:
        text = '📭 شما هیچ سفارشی ندارید.'
        if query:
            await query.edit_message_text(text, reply_markup=main_menu())
        return
    msg = '📋 <b>سفارش‌های شما:</b>\n\n'
    for o in orders:
        msg += f"🆔 <code>{o['id']}</code> - {format_order_status(o)}\n"
    if query:
        await query.edit_message_text(msg, reply_markup=main_menu(), parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=main_menu(), parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    photo = update.message.photo

    # اگر ادمین در حال ارسال اکانت است
    if context.user_data.get('admin_send_order') and text:
        order_id = context.user_data.pop('admin_send_order')
        order = await get_order(order_id)
        if not order:
            await update.message.reply_text(f'❌ سفارش {order_id} یافت نشد.')
            return
        await context.bot.send_message(
            chat_id=order['userId'],
            text=f"📤 <b>اکانت شما برای سفارش <code>{order_id}</code></b>\n\n{text}",
            parse_mode='HTML'
        )
        await update_order_status(order_id, ORDER_STATUS['SENT'])
        await context.bot.send_message(chat_id=ADMIN_ID, text=f"📤 اکانت سفارش <code>{order_id}</code> به کاربر ارسال شد.", parse_mode='HTML')
        await update.message.reply_text(f"✅ اکانت سفارش <code>{order_id}</code> با موفقیت ارسال شد.", parse_mode='HTML')
        return

    # بررسی مرحله فعلی کاربر
    state = await get_user_state(chat_id)
    step = state.get('step')

    if photo and step == 'sending_receipt':
        photo_id = photo[-1].file_id
        state['tempData']['receiptPhotoId'] = photo_id
        state['step'] = 'confirming_order'
        # تولید سفارش موقت
        order_id = generate_order_id()
        temp = state['tempData']
        order = {
            'id': order_id,
            'userId': chat_id,
            'productId': temp.get('productId'),
            'planId': temp.get('planId'),
            'configType': temp.get('configType', 'V2Ray'),
            'customerName': temp.get('customerName'),
            'paymentMethod': temp.get('paymentMethod'),
            'trackingCode': temp.get('trackingCode'),
            'receiptPhotoId': photo_id,
            'status': ORDER_STATUS['PENDING'],
            'createdAt': int(datetime.now().timestamp() * 1000)
        }
        state['tempData']['order'] = order
        await set_user_state(chat_id, state['step'], state['tempData'])
        summary = format_order_summary(order)
        await update.message.reply_text(
            f"📋 <b>خلاصه سفارش</b>\n{summary}\n\nآیا اطلاعات صحیح است؟",
            reply_markup=order_confirm_keyboard(order_id),
            parse_mode='HTML'
        )
        return

    # پردازش ورودی نام یا کد پیگیری
    if text:
        if step == 'entering_name':
            if len(text.strip()) < 2:
                await update.message.reply_text('❌ لطفاً نام معتبر (حداقل ۲ کاراکتر) وارد کنید.')
                return
            state['tempData']['customerName'] = text.strip()
            state['step'] = 'selecting_payment'
            await set_user_state(chat_id, state['step'], state['tempData'])
            await update.message.reply_text(
                '👤 نام شما ثبت شد.\n\n💳 روش پرداخت را انتخاب کنید:',
                reply_markup=payment_methods_keyboard()
            )
            return
        elif step == 'entering_tracking':
            if len(text.strip()) < 3:
                await update.message.reply_text('❌ لطفاً کد پیگیری معتبر (حداقل ۳ کاراکتر) وارد کنید.')
                return
            state['tempData']['trackingCode'] = text.strip()
            state['step'] = 'sending_receipt'
            await set_user_state(chat_id, state['step'], state['tempData'])
            await update.message.reply_text(
                '🔢 کد پیگیری ثبت شد.\n\n🖼️ لطفاً <b>عکس رسید</b> پرداخت را ارسال کنید (به صورت عکس).',
                parse_mode='HTML'
            )
            return

    # اگر هیچکدام نبود
    await update.message.reply_text(
        'لطفاً از منوی اصلی استفاده کنید:',
        reply_markup=main_menu()
    )

# ==================== اجرا با Polling (ساده‌تر و بدون نیاز به Webhook) ====================
async def main():
    # مقداردهی اولیه دیتابیس
    init_db()
    
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # ثبت هندلرها
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_message))
    
    # شروع Polling
    logging.info("🚀 ربات با روش Polling شروع به کار کرد...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # نگه داشتن برنامه
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logging.info("⏹️ توقف ربات...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    asyncio.run(main())
