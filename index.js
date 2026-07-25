// ============================================================
// ربات فروشگاهی AyhanX-Freedom - نسخه پایدار با globalThis
// ============================================================

// -------------------- تنظیمات ثابت --------------------
const BOT_TOKEN = '8631736538:AAFkNgUY5QM4Gr8eqQsviUk6NxkLcZvT5yc';
const ADMIN_ID = 6897603496;
const SUPPORT_USERNAME = '@nspubgabot';
const CHANNEL_ID = '@dnspubga';
const SHOP_NAME = 'dnspugashop';

const ORDER_STATUS = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  REJECTED: 'rejected',
  SENT: 'sent'
};

// -------------------- محصولات و پلن‌ها --------------------
const PRODUCTS = {
  'wireguard_gaming': {
    id: 'wireguard_gaming',
    name: 'وایرگارد گیم و وب گردی',
    emoji: '🛡️',
    plans: {
      'plan_wg_1m': { name: '۱ ماهه ۳۶ گیگ', price: 400, description: '۳۶ گیگابایت، ۱ ماهه' },
      'plan_wg_2m': { name: '۲ ماهه ۷۸ گیگ', price: 600, description: '۷۸ گیگابایت، ۲ ماهه' },
      'plan_wg_3m': { name: '۳ ماهه ۱۲۷ گیگ', price: 800, description: '۱۲۷ گیگابایت، ۳ ماهه' },
      'plan_wg_6m': { name: '۶ ماهه ۳۰۰ گیگ', price: 1200, description: '۳۰۰ گیگابایت، ۶ ماهه' }
    }
  },
  'config_monthly': {
    id: 'config_monthly',
    name: 'کانفیگ ماهانه',
    emoji: '📅',
    plans: {
      'plan_50': { name: '۵۰ گیگ', price: 35000, description: '۵۰ گیگابایت، ۱ ماهه' },
      'plan_100': { name: '۱۰۰ گیگ', price: 55000, description: '۱۰۰ گیگابایت، ۱ ماهه' },
      'plan_200': { name: '۲۰۰ گیگ', price: 85000, description: '۲۰۰ گیگابایت، ۱ ماهه' }
    }
  },
  'config_quarterly': {
    id: 'config_quarterly',
    name: 'کانفیگ سه‌ماهه',
    emoji: '📆',
    plans: {
      'plan_unlimited': { name: 'نامحدود', price: 150000, description: 'حجم نامحدود، ۳ ماهه' },
      'plan_500': { name: '۵۰۰ گیگ', price: 120000, description: '۵۰۰ گیگابایت، ۳ ماهه' }
    }
  }
};

const CONFIG_TYPES = ['WireGuard', 'V2Ray'];
const PAYMENT_METHODS = ['کارت به کارت', 'رمز دوم (اینترنتی)', 'کیف پول (USDT)'];

// -------------------- حافظه سراسری (با globalThis) --------------------
// این Map تا حد امکان بین درخواست‌های نزدیک به هم پایدار می‌ماند
if (!globalThis.__orders) {
  globalThis.__orders = new Map();
}
if (!globalThis.__userStates) {
  globalThis.__userStates = new Map();
}
if (!globalThis.__adminSendState) {
  globalThis.__adminSendState = new Map();
}

const orders = globalThis.__orders;
const userStates = globalThis.__userStates;
const adminSendState = globalThis.__adminSendState;

// -------------------- توابع کمکی (بدون تغییر) --------------------
function getUserState(chatId) {
  if (!userStates.has(chatId)) {
    userStates.set(chatId, { step: null, tempData: {} });
  }
  return userStates.get(chatId);
}

function setUserState(chatId, step, tempData = {}) {
  userStates.set(chatId, { step, tempData });
}

function clearUserState(chatId) {
  userStates.delete(chatId);
}

function generateOrderId() {
  return Date.now().toString(36) + Math.random().toString(36).substring(2, 6);
}

function saveOrder(order) {
  orders.set(order.id, order);
  console.log(`✅ سفارش ذخیره شد. شناسه: ${order.id}، تعداد کل سفارش‌ها: ${orders.size}`);
}

function getOrder(orderId) {
  return orders.get(orderId);
}

function updateOrderStatus(orderId, status, extra = {}) {
  const order = getOrder(orderId);
  if (order) {
    order.status = status;
    Object.assign(order, extra);
    orders.set(orderId, order);
  }
  return order;
}

// -------------------- توابع Telegram API (بدون تغییر) --------------------
const TELEGRAM_API = `https://api.telegram.org/bot${BOT_TOKEN}`;

async function callTelegram(method, params = {}) {
  const url = `${TELEGRAM_API}/${method}`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });
  return resp.json();
}

function sendMessage(chatId, text, extra = {}) {
  return callTelegram('sendMessage', {
    chat_id: chatId,
    text,
    parse_mode: 'HTML',
    ...extra
  });
}

function editMessageText(chatId, messageId, text, extra = {}) {
  return callTelegram('editMessageText', {
    chat_id: chatId,
    message_id: messageId,
    text,
    parse_mode: 'HTML',
    ...extra
  });
}

function answerCallbackQuery(callbackQueryId, text = '', showAlert = false) {
  return callTelegram('answerCallbackQuery', {
    callback_query_id: callbackQueryId,
    text,
    show_alert: showAlert
  });
}

function getMe() {
  return callTelegram('getMe');
}

function getWebhookInfo() {
  return callTelegram('getWebhookInfo');
}

function setWebhook(url) {
  return callTelegram('setWebhook', { url });
}

// -------------------- کیبوردها (با جداکننده |) --------------------
function mainMenu() {
  return {
    inline_keyboard: [
      [
        { text: '🛒 فروشگاه', callback_data: 'menu|shop' },
        { text: '📋 سفارش‌های من', callback_data: 'menu|orders' }
      ],
      [
        { text: '🆘 پشتیبانی', callback_data: 'menu|support' },
        { text: '📢 کانال', callback_data: 'menu|channel' }
      ]
    ]
  };
}

function productsKeyboard() {
  const keys = [];
  for (const [id, prod] of Object.entries(PRODUCTS)) {
    keys.push([{ text: `${prod.emoji} ${prod.name}`, callback_data: `product|${id}` }]);
  }
  keys.push([{ text: '🔙 بازگشت به منو', callback_data: 'menu|main' }]);
  return { inline_keyboard: keys };
}

function plansKeyboard(productId) {
  const prod = PRODUCTS[productId];
  if (!prod) return { inline_keyboard: [] };
  const keys = [];
  for (const [planId, plan] of Object.entries(prod.plans)) {
    const priceStr = plan.price.toLocaleString() + ' تومان';
    keys.push([{ text: `${plan.name} - ${priceStr}`, callback_data: `plan|${productId}|${planId}` }]);
  }
  keys.push([{ text: '🔙 بازگشت به محصولات', callback_data: 'menu|shop' }]);
  return { inline_keyboard: keys };
}

function configTypesKeyboard() {
  const keys = CONFIG_TYPES.map(type => ([{ text: type, callback_data: `config|${type}` }]));
  keys.push([{ text: '🔙 انصراف', callback_data: 'menu|main' }]);
  return { inline_keyboard: keys };
}

function paymentMethodsKeyboard() {
  const keys = PAYMENT_METHODS.map(m => ([{ text: m, callback_data: `pay|${m}` }]));
  keys.push([{ text: '🔙 انصراف', callback_data: 'menu|main' }]);
  return { inline_keyboard: keys };
}

function orderConfirmKeyboard(orderId) {
  return {
    inline_keyboard: [
      [
        { text: '✅ تایید و ثبت', callback_data: `confirm|${orderId}` },
        { text: '❌ لغو', callback_data: `cancel|${orderId}` }
      ]
    ]
  };
}

function adminOrderKeyboard(orderId) {
  return {
    inline_keyboard: [
      [
        { text: '✅ تایید', callback_data: `admin|confirm|${orderId}` },
        { text: '❌ رد', callback_data: `admin|reject|${orderId}` }
      ],
      [
        { text: '📤 ارسال اکانت', callback_data: `admin|send|${orderId}` }
      ]
    ]
  };
}

// -------------------- توابع فرمت پیام (بدون تغییر) --------------------
function formatOrderSummary(order) { /* ... */ }
function formatAdminOrderMessage(order) { /* ... */ }
function formatOrderStatus(order) { /* ... */ }
// (برای اختصار حذف شد، ولی در کد نهایی کامل وجود دارد)

// -------------------- هندلرهای اصلی (با جداکننده |) --------------------
// (همانند نسخه قبلی، فقط توابع showUserOrders و saveOrder تغییر کرده‌اند)

async function showUserOrders(chatId) {
  console.log(`🔍 بررسی سفارش‌های کاربر ${chatId}، تعداد کل سفارش‌ها: ${orders.size}`);
  
  const userOrders = [];
  for (const [id, order] of orders) {
    console.log(`   سفارش ${id} متعلق به کاربر ${order.userId}`);
    if (order.userId === chatId) {
      userOrders.push(order);
    }
  }
  if (userOrders.length === 0) {
    await sendMessage(chatId, '📭 شما هیچ سفارشی ندارید.');
    return;
  }
  let msg = '📋 <b>سفارش‌های شما:</b>\n\n';
  for (const order of userOrders) {
    const statusText = formatOrderStatus(order);
    msg += `🆔 <code>${order.id}</code> - ${statusText}\n`;
  }
  await sendMessage(chatId, msg);
}

// بقیه هندلرها (handleStart, handleMainMenu, ...) دقیقاً مانند نسخه قبلی با جداکننده |
// (برای جلوگیری از تکرار، در اینجا حذف شده‌اند، ولی در کد نهایی کامل وجود دارند)

// -------------------- ورودی اصلی Worker --------------------
export default {
  async fetch(request, env, ctx) {
    try {
      const url = new URL(request.url);
      const path = url.pathname;

      if (path === '/webhook' && request.method === 'POST') {
        const update = await request.json();
        ctx.waitUntil(processUpdate(update));
        return new Response('OK', { status: 200 });
      }

      if (path === '/') {
        const tokenTest = await testBotToken();
        const webhookInfo = await getWebhookInfo();
        const webhookStatus = webhookInfo.ok ? webhookInfo.result : null;
        const ordersCount = orders.size;
        const html = renderHomePage(tokenTest, webhookStatus, ordersCount);
        return new Response(html, {
          headers: { 'Content-Type': 'text/html; charset=utf-8' }
        });
      }

      if (path === '/test') {
        const result = await testBotToken();
        return new Response(result.ok ? `✅ ربات فعال است. نام کاربری: @${result.username}` : `❌ خطا: ${result.error}`, { status: result.ok ? 200 : 500 });
      }

      if (path === '/webhook-info') {
        const info = await getWebhookInfo();
        return new Response(JSON.stringify(info, null, 2), {
          headers: { 'Content-Type': 'application/json' }
        });
      }

      if (path === '/force-webhook') {
        const baseUrl = request.url.replace(/\/force-webhook$/, '');
        const result = await setupWebhookAutomatically(baseUrl);
        return new Response(result.ok ? `✅ Webhook روی ${result.url} تنظیم شد.` : `❌ خطا: ${result.error}`, { status: result.ok ? 200 : 500 });
      }

      return new Response('404 Not Found', { status: 404 });
    } catch (err) {
      console.error('❌ خطای کلی:', err);
      return new Response('Internal Server Error: ' + err.message, { status: 500 });
    }
  }
};
