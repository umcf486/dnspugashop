import os
import json
import sqlite3
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify

# تنظیمات لاگ
logging.basicConfig(level=logging.INFO)

# ==================== تنظیمات ====================
TOKEN = '8631736538:AAFkNgUY5QM4Gr8eqQsviUk6NxkLcZvT5yc'
ADMIN_ID = 8907076433
SUPPORT_USERNAME = '@nspubgabot'
CHANNEL_ID = '@dnspubga'
SHOP_NAME = 'AyhanX-Freedom'

STATUS_PENDING = 'pending'
STATUS_CONFIRMED = 'confirmed'
STATUS_REJECTED = 'rejected'
STATUS_SENT = 'sent'

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

# ==================== دیتابیس ====================
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
import random, time

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

# ==================== توابع Telegram API ====================
def telegram_request(method, params=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    if params is None:
        params = {}
    try:
        resp = requests.post(url, json=params, timeout=10)
        return resp.json()
    except Exception as e:
        logging.error(f"Telegram API error: {e}")
        return None

def send_message(chat_id, text, extra=None):
    params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if extra:
        params.update(extra)
    return telegram_request('sendMessage', params)

def edit_message_text(chat_id, message_id, text, extra=None):
    params = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'HTML'}
    if extra:
        params.update(extra)
    return telegram_request('editMessageText', params)

def answer_callback_query(callback_id, text=None, show_alert=False):
    params = {'callback_query_id': callback_id}
    if text:
        params['text'] = text
        params['show_alert'] = show_alert
    return telegram_request('answerCallbackQuery', params)

# ==================== کیبوردها ====================
def build_keyboard(buttons):
    return json.dumps({'inline_keyboard': buttons})

def main_menu():
    return build_keyboard([
        [
            {'text': '🛒 فروشگاه', 'callback_data': 'menu|shop'},
            {'text': '📋 سفارش‌های من', 'callback_data': 'menu|orders'}
        ],
        [
            {'text': '🆘 پشتیبانی', 'callback_data': 'menu|support'},
            {'text': '📢 کانال', 'callback_data': 'menu|channel'}
        ]
    ])

def products_keyboard():
    keyboard = []
    for pid, prod in PRODUCTS.items():
        keyboard.append([{'text': f"{prod['emoji']} {prod['name']}", 'callback_data': f"product|{pid}"}])
    keyboard.append([{'text': '🔙 بازگشت به منو', 'callback_data': 'menu|main'}])
    return build_keyboard(keyboard)

def plans_keyboard(product_id):
    prod = PRODUCTS.get(product_id)
    if not prod:
        return build_keyboard([])
    keyboard = []
    for pid, plan in prod['plans'].items():
        price_str = f"{plan['price']:,} تومان".replace(',', '،')
        keyboard.append([{'text': f"{plan['name']} - {price_str}", 'callback_data': f"plan|{product_id}|{pid}"}])
    keyboard.append([{'text': '🔙 بازگشت به محصولات', 'callback_data': 'menu|shop'}])
    return build_keyboard(keyboard)

def config_types_keyboard():
    keyboard = []
    for ct in CONFIG_TYPES:
        keyboard.append([{'text': ct, 'callback_data': f"config|{ct}"}])
    keyboard.append([{'text': '🔙 انصراف', 'callback_data': 'menu|main'}])
    return build_keyboard(keyboard)

def payment_methods_keyboard():
    keyboard = []
    for pm in PAYMENT_METHODS:
        keyboard.append([{'text': pm, 'callback_data': f"pay|{pm}"}])
    keyboard.append([{'text': '🔙 انصراف', 'callback_data': 'menu|main'}])
    return build_keyboard(keyboard)

def order_confirm_keyboard(order_id):
    return build_keyboard([
        [
            {'text': '✅ تایید و ثبت', 'callback_data': f"confirm|{order_id}"},
            {'text': '❌ لغو', 'callback_data': f"cancel|{order_id}"}
        ]
    ])

def admin_order_keyboard(order_id):
    return build_keyboard([
        [
            {'text': '✅ تایید', 'callback_data': f"admin|confirm|{order_id}"},
            {'text': '❌ رد', 'callback_data': f"admin|reject|{order_id}"}
        ],
        [
            {'text': '📤 ارسال اکانت', 'callback_data': f"admin|send|{order_id}"}
        ]
    ])

# ==================== توابع فرمت پیام ====================
def format_order_summary(order):
    product = PRODUCTS.get(order['productId'], {})
    plan = product.get('plans', {}).get(order['planId'], {})
    price_str = f"{plan.get('price', 0):,} تومان".replace(',', '،') if plan else 'نامشخص'
    date = datetime.fromtimestamp(order['createdAt'] / 1000).strftime('%Y-%m-%d %H:%M')
    status_text = {
        STATUS_PENDING: '⏳ در انتظار تایید',
        STATUS_CONFIRMED: '✅ تایید شده',
        STATUS_REJECTED: '❌ رد شده',
        STATUS_SENT: '📤 ارسال شده'
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
👤 کاربر: <a href=\"tg://user?id={order['userId']}\">{order.get('customerName', 'کاربر')}</a>
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
        STATUS_PENDING: '⏳ در انتظار تایید',
        STATUS_CONFIRMED: '✅ تایید شده',
        STATUS_REJECTED: '❌ رد شده',
        STATUS_SENT: '📤 ارسال شده'
    }.get(order['status'], order['status'])

# ==================== هندلرها ====================
def handle_start(chat_id):
    clear_user_state(chat_id)
    send_message(chat_id, f"👋 به <b>{SHOP_NAME}</b> خوش آمدید!\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", {'reply_markup': main_menu()})

def handle_callback(chat_id, data, callback_id, message_id=None):
    answer_callback_query(callback_id)
    parts = data.split('|')
    action = parts[0]

    if action == 'menu':
        sub = parts[1] if len(parts) > 1 else 'main'
        clear_user_state(chat_id)
        if sub == 'shop':
            send_message(chat_id, '🛒 <b>محصولات موجود:</b>', {'reply_markup': products_keyboard()})
        elif sub == 'orders':
            show_user_orders(chat_id)
        elif sub == 'support':
            send_message(chat_id, f"🆘 برای پشتیبانی با {SUPPORT_USERNAME} تماس بگیرید.", {'reply_markup': main_menu()})
        elif sub == 'channel':
            send_message(chat_id, f"📢 کانال ما: {CHANNEL_ID}", {'reply_markup': main_menu()})
        elif sub == 'main':
            send_message(chat_id, '🏠 منوی اصلی:', {'reply_markup': main_menu()})
        return

    if action == 'product':
        product_id = parts[1]
        if product_id not in PRODUCTS:
            send_message(chat_id, '❌ محصول نامعتبر.')
            return
        set_user_state(chat_id, 'selecting_plan', {'productId': product_id})
        send_message(chat_id, f"📦 <b>{PRODUCTS[product_id]['name']}</b>\nلطفاً پلن مورد نظر را انتخاب کنید:", {'reply_markup': plans_keyboard(product_id)})
        return

    if action == 'plan':
        if len(parts) != 3:
            send_message(chat_id, 'خطا در انتخاب پلن.')
            return
        product_id, plan_id = parts[1], parts[2]
        if product_id not in PRODUCTS or plan_id not in PRODUCTS[product_id]['plans']:
            send_message(chat_id, '❌ پلن نامعتبر.')
            return
        set_user_state(chat_id, 'selecting_config_type', {'productId': product_id, 'planId': plan_id})
        plan = PRODUCTS[product_id]['plans'][plan_id]
        price_str = f"{plan['price']:,} تومان".replace(',', '،')
        send_message(chat_id, f"✅ پلن <b>{plan['name']}</b> با قیمت {price_str} انتخاب شد.\n\n🔧 حالا <b>نوع کانفیگ</b> مورد نظر را انتخاب کنید:", {'reply_markup': config_types_keyboard()})
        return

    if action == 'config':
        config_type = parts[1]
        if config_type not in CONFIG_TYPES:
            send_message(chat_id, 'نوع کانفیگ نامعتبر.')
            return
        state = get_user_state(chat_id)
        state['tempData']['configType'] = config_type
        set_user_state(chat_id, 'entering_name', state['tempData'])
        send_message(chat_id, f"🔧 نوع کانفیگ: <b>{config_type}</b>\n\n👤 لطفاً <b>نام کامل</b> خود را وارد کنید:")
        return

    if action == 'pay':
        method = parts[1]
        if method not in PAYMENT_METHODS:
            send_message(chat_id, 'روش پرداخت نامعتبر.')
            return
        state = get_user_state(chat_id)
        state['tempData']['paymentMethod'] = method
        set_user_state(chat_id, 'entering_tracking', state['tempData'])
        send_message(chat_id, f"💳 روش پرداخت: {method}\n\n🔢 لطفاً <b>کد پیگیری</b> پرداخت را وارد کنید:")
        return

    if action in ['confirm', 'cancel']:
        order_id = parts[1]
        state = get_user_state(chat_id)
        if not state or not state['tempData'].get('order') or state['tempData']['order']['id'] != order_id:
            send_message(chat_id, '❌ سفارش یافت نشد. دوباره تلاش کنید.')
            clear_user_state(chat_id)
            return
        if action == 'cancel':
            clear_user_state(chat_id)
            send_message(chat_id, '❌ سفارش لغو شد.', {'reply_markup': main_menu()})
            return
        if action == 'confirm':
            order = state['tempData']['order']
            order['status'] = STATUS_PENDING
            save_order(order)
            clear_user_state(chat_id)
            admin_msg = format_admin_order_message(order)
            send_message(ADMIN_ID, f"🔔 <b>سفارش جدید نیاز به تایید دارد</b>\n{admin_msg}", {'reply_markup': admin_order_keyboard(order['id'])})
            send_message(chat_id, f"✅ سفارش شما با شناسه <code>{order['id']}</code> ثبت شد و در انتظار تایید ادمین می‌باشد.", {'reply_markup': main_menu()})
        return

    if action == 'admin':
        if len(parts) < 3:
            send_message(chat_id, 'دستور نامعتبر.')
            return
        sub_action = parts[1]
        order_id = parts[2]
        order = get_order(order_id)
        if not order:
            send_message(chat_id, f"❌ سفارش با شناسه {order_id} یافت نشد.")
            return
        if sub_action == 'confirm':
            update_order_status(order_id, STATUS_CONFIRMED)
            send_message(ADMIN_ID, f"✅ سفارش <code>{order_id}</code> تایید شد. لطفاً کانفیگ را به کاربر ارسال کنید.")
            send_message(order['userId'], f"✅ سفارش شما با شناسه <code>{order_id}</code> تایید شد. به زودی اکانت برای شما ارسال خواهد شد.")
            if message_id:
                edit_message_text(ADMIN_ID, message_id, f"🔔 <b>سفارش {order_id}</b>\n{format_admin_order_message(order)}\n\nوضعیت: {STATUS_CONFIRMED} (منتظر ارسال اکانت)", {'reply_markup': build_keyboard([])})
        elif sub_action == 'reject':
            update_order_status(order_id, STATUS_REJECTED)
            send_message(ADMIN_ID, f"❌ سفارش <code>{order_id}</code> رد شد.")
            send_message(order['userId'], f"❌ سفارش شما با شناسه <code>{order_id}</code> رد شد.")
            if message_id:
                edit_message_text(ADMIN_ID, message_id, f"🔔 <b>سفارش {order_id}</b>\n{format_admin_order_message(order)}\n\nوضعیت: {STATUS_REJECTED}", {'reply_markup': build_keyboard([])})
        elif sub_action == 'send':
            set_user_state(chat_id, 'admin_sending', {'orderId': order_id})
            send_message(chat_id, f"📤 لطفاً <b>متن اکانت</b> را برای سفارش <code>{order_id}</code> ارسال کنید.")
            send_message(order['userId'], f"🔄 ادمین در حال ارسال اکانت برای سفارش <code>{order_id}</code> می‌باشد.")
        return

    send_message(chat_id, 'دستور نامعتبر.')

def show_user_orders(chat_id):
    orders = get_user_orders(chat_id)
    if not orders:
        send_message(chat_id, '📭 شما هیچ سفارشی ندارید.', {'reply_markup': main_menu()})
        return
    msg = '📋 <b>سفارش‌های شما:</b>\n\n'
    for o in orders:
        msg += f"🆔 <code>{o['id']}</code> - {format_order_status(o)}\n"
    send_message(chat_id, msg, {'reply_markup': main_menu()})

def handle_message(chat_id, text, photo=None):
    state = get_user_state(chat_id)
    step = state.get('step')

    if step == 'admin_sending' and text:
        order_id = state['tempData'].get('orderId')
        if not order_id:
            send_message(chat_id, '❌ شما در حال ارسال اکانت نیستید.')
            clear_user_state(chat_id)
            return
        order = get_order(order_id)
        if not order:
            send_message(chat_id, f"❌ سفارش {order_id} یافت نشد.")
            clear_user_state(chat_id)
            return
        send_message(order['userId'], f"📤 <b>اکانت شما برای سفارش <code>{order_id}</code></b>\n\n{text}")
        update_order_status(order_id, STATUS_SENT)
        clear_user_state(chat_id)
        send_message(ADMIN_ID, f"📤 اکانت سفارش <code>{order_id}</code> به کاربر ارسال شد.")
        send_message(chat_id, f"✅ اکانت سفارش <code>{order_id}</code> با موفقیت ارسال شد.")
        return

    if photo and step == 'sending_receipt':
        photo_id = photo[-1]['file_id']
        state['tempData']['receiptPhotoId'] = photo_id
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
            'status': STATUS_PENDING,
            'createdAt': int(datetime.now().timestamp() * 1000)
        }
        state['tempData']['order'] = order
        set_user_state(chat_id, 'confirming_order', state['tempData'])
        summary = format_order_summary(order)
        send_message(chat_id, f"📋 <b>خلاصه سفارش</b>\n{summary}\n\nآیا اطلاعات صحیح است؟", {'reply_markup': order_confirm_keyboard(order_id)})
        return

    if text:
        if step == 'entering_name':
            if len(text.strip()) < 2:
                send_message(chat_id, '❌ لطفاً نام معتبر (حداقل ۲ کاراکتر) وارد کنید.')
                return
            state['tempData']['customerName'] = text.strip()
            set_user_state(chat_id, 'selecting_payment', state['tempData'])
            send_message(chat_id, '👤 نام شما ثبت شد.\n\n💳 روش پرداخت را انتخاب کنید:', {'reply_markup': payment_methods_keyboard()})
            return
        if step == 'entering_tracking':
            if len(text.strip()) < 3:
                send_message(chat_id, '❌ لطفاً کد پیگیری معتبر (حداقل ۳ کاراکتر) وارد کنید.')
                return
            state['tempData']['trackingCode'] = text.strip()
            set_user_state(chat_id, 'sending_receipt', state['tempData'])
            send_message(chat_id, '🔢 کد پیگیری ثبت شد.\n\n🖼️ لطفاً <b>عکس رسید</b> پرداخت را ارسال کنید (به صورت عکس).')
            return

    send_message(chat_id, 'لطفاً از منوی اصلی استفاده کنید:', {'reply_markup': main_menu()})

def process_update(update):
    try:
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            text = msg.get('text')
            photo = msg.get('photo')
            if text and text.startswith('/start'):
                handle_start(chat_id)
            else:
                handle_message(chat_id, text, photo)
        elif 'callback_query' in update:
            cb = update['callback_query']
            chat_id = cb['from']['id']
            data = cb['data']
            callback_id = cb['id']
            message_id = cb.get('message', {}).get('message_id')
            handle_callback(chat_id, data, callback_id, message_id)
    except Exception as e:
        logging.error(f"Error processing update: {e}", exc_info=True)

# ==================== Flask App ====================
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if update:
            process_update(update)
        return 'OK', 200
    except Exception as e:
        logging.error(f"Webhook error: {e}", exc_info=True)
        return 'Error', 500

@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    base_url = request.host_url.rstrip('/')
    webhook_url = f"{base_url}/webhook"
    resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}")
    return f"""
    <html dir="rtl">
    <body style="background:#0f0c29;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;">
        <div style="background:rgba(255,255,255,0.05);border-radius:20px;padding:30px;max-width:500px;text-align:center;">
            <h1 style="color:#4ade80;">✅ Webhook تنظیم شد</h1>
            <p>آدرس: <code style="background:#1a1a2e;padding:5px 10px;border-radius:5px;color:#60a5fa;">{webhook_url}</code></p>
            <p>پاسخ: <code style="background:#1a1a2e;padding:5px 10px;border-radius:5px;color:#ffd200;">{resp.json()}</code></p>
            <a href="/" style="color:#6C63FF;text-decoration:none;">بازگشت</a>
        </div>
    </body>
    </html>
    """

@app.route('/webhook-info', methods=['GET'])
def webhook_info():
    resp = requests.get(f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo")
    return resp.json()

@app.route('/')
def home():
    product_count = len(PRODUCTS)
    return f"""
    <html dir="rtl">
    <head><title>{SHOP_NAME}</title></head>
    <body style="background:#0f0c29;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;">
        <div style="background:rgba(255,255,255,0.05);border-radius:28px;padding:40px;max-width:500px;text-align:center;border:1px solid rgba(255,255,255,0.1);">
            <h1 style="font-size:2.5rem;background:linear-gradient(to left,#f7971e,#ffd200);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">🛒 {SHOP_NAME}</h1>
            <p style="color:#aaa;">ربات فروشگاهی کانفیگ</p>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;margin:25px 0;">
                <div style="background:rgba(255,255,255,0.06);border-radius:16px;padding:15px;">
                    <div style="color:#aaa;font-size:0.8rem;">تعداد محصولات</div>
                    <div style="font-size:1.5rem;font-weight:600;color:#60a5fa;">{product_count}</div>
                </div>
                <div style="background:rgba(255,255,255,0.06);border-radius:16px;padding:15px;">
                    <div style="color:#aaa;font-size:0.8rem;">وضعیت</div>
                    <div style="font-size:1.5rem;font-weight:600;color:#4ade80;">✅ فعال</div>
                </div>
            </div>
            <a href="/setwebhook" style="background:#4f46e5;color:#fff;padding:12px 24px;border-radius:40px;text-decoration:none;display:inline-block;margin:5px;">⚙️ تنظیم Webhook</a>
            <a href="/webhook-info" style="background:transparent;border:1px solid #4f46e5;color:#4f46e5;padding:12px 24px;border-radius:40px;text-decoration:none;display:inline-block;margin:5px;">📡 اطلاعات Webhook</a>
            <div style="color:#666;font-size:0.8rem;margin-top:20px;border-top:1px solid rgba(255,255,255,0.05);padding-top:20px;">
                <span style="color:#4ade80;">● ربات فعال است</span>
                <br><br>
                <span style="color:#555;">نسخه ۱.۰ | AyhanX-Freedom</span>
            </div>
        </div>
    </body>
    </html>
    """

# ==================== اجرا ====================
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
