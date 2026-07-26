// ============================================================
// ربات فروشگاهی AyhanX-Freedom - نسخه نهایی با جداکننده |
// ============================================================

// -------------------- تنظیمات ثابت --------------------
const BOT_TOKEN = '8631736538:AAF_JKC7hI3aRPfKEdk1TQwtNnOwbhfeF1M';
const ADMIN_ID = 8907076433;
const SUPPORT_USERNAME = '@nspubgabot';
const CHANNEL_ID = '@dnspubga';
const SHOP_NAME = 'AyhanX-Freedom';

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

// -------------------- حافظه --------------------
const userStates = new Map();
const orders = new Map();
const adminSendState = new Map();

// -------------------- توابع کمکی --------------------
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

// -------------------- توابع Telegram API --------------------
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

// -------------------- توابع فرمت پیام --------------------
function formatOrderSummary(order) {
  const product = PRODUCTS[order.productId];
  const plan = product?.plans?.[order.planId];
  const priceStr = plan?.price?.toLocaleString() + ' تومان' || 'نامشخص';
  const date = new Date(order.createdAt).toLocaleString('fa-IR');
  let statusText = '';
  switch (order.status) {
    case ORDER_STATUS.PENDING: statusText = '⏳ در انتظار تایید'; break;
    case ORDER_STATUS.CONFIRMED: statusText = '✅ تایید شده'; break;
    case ORDER_STATUS.REJECTED: statusText = '❌ رد شده'; break;
    case ORDER_STATUS.SENT: statusText = '📤 ارسال شده'; break;
    default: statusText = order.status;
  }
  return `
📋 <b>خلاصه سفارش</b>
🆔 شناسه: <code>${order.id}</code>
📦 محصول: ${product?.name || order.productId}
📊 پلن: ${plan?.name || order.planId}
🔧 نوع کانفیگ: ${order.configType || 'تعیین نشده'}
💰 قیمت: ${priceStr}
👤 نام: ${order.customerName || 'ندارد'}
💳 روش پرداخت: ${order.paymentMethod || 'ندارد'}
🔢 کد پیگیری: ${order.trackingCode || 'ندارد'}
📎 رسید: ${order.receiptPhotoId ? '✅ ارسال شده' : '❌ ارسال نشده'}
📅 تاریخ: ${date}
📌 وضعیت: ${statusText}
  `.trim();
}

function formatAdminOrderMessage(order) {
  const product = PRODUCTS[order.productId];
  const plan = product?.plans?.[order.planId];
  const priceStr = plan?.price?.toLocaleString() + ' تومان' || 'نامشخص';
  const date = new Date(order.createdAt).toLocaleString('fa-IR');
  return `
🆕 <b>سفارش جدید</b>
🆔 شناسه: <code>${order.id}</code>
👤 کاربر: <a href="tg://user?id=${order.userId}">${order.customerName || 'کاربر'}</a>
📦 محصول: ${product?.name || order.productId}
📊 پلن: ${plan?.name || order.planId}
🔧 نوع کانفیگ: ${order.configType || 'تعیین نشده'}
💰 قیمت: ${priceStr}
💳 روش پرداخت: ${order.paymentMethod || 'ندارد'}
🔢 کد پیگیری: ${order.trackingCode || 'ندارد'}
📎 رسید: ${order.receiptPhotoId ? '✅ ارسال شده' : '❌ ارسال نشده'}
📅 تاریخ: ${date}
  `.trim();
}

function formatOrderStatus(order) {
  let status = '';
  switch (order.status) {
    case ORDER_STATUS.PENDING: status = '⏳ در انتظار تایید'; break;
    case ORDER_STATUS.CONFIRMED: status = '✅ تایید شده'; break;
    case ORDER_STATUS.REJECTED: status = '❌ رد شده'; break;
    case ORDER_STATUS.SENT: status = '📤 ارسال شده'; break;
    default: status = order.status;
  }
  return status;
}

// -------------------- هندلرهای اصلی (با جداکننده |) --------------------
async function handleStart(chatId) {
  clearUserState(chatId);
  await sendMessage(chatId, `👋 به <b>${SHOP_NAME}</b> خوش آمدید!\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:`, {
    reply_markup: mainMenu()
  });
}

async function handleMainMenu(chatId, data, callbackId) {
  await answerCallbackQuery(callbackId);
  clearUserState(chatId);

  const parts = data.split('|'); // menu|shop
  const action = parts[1];

  if (action === 'shop') {
    await sendMessage(chatId, '🛒 <b>محصولات موجود:</b>', {
      reply_markup: productsKeyboard()
    });
  } else if (action === 'orders') {
    await showUserOrders(chatId);
  } else if (action === 'support') {
    await sendMessage(chatId, `🆘 برای پشتیبانی با ${SUPPORT_USERNAME} تماس بگیرید.`);
  } else if (action === 'channel') {
    await sendMessage(chatId, `📢 کانال ما: ${CHANNEL_ID}`);
  } else if (action === 'main') {
    await sendMessage(chatId, '🏠 منوی اصلی:', { reply_markup: mainMenu() });
  }
}

async function showUserOrders(chatId) {
  const userOrders = [];
  for (const [id, order] of orders) {
    if (order.userId === chatId) userOrders.push(order);
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

async function handleProductSelect(chatId, data, callbackId) {
  await answerCallbackQuery(callbackId);
  const parts = data.split('|'); // product|productId
  const productId = parts[1];

  if (!PRODUCTS[productId]) {
    await sendMessage(chatId, '❌ محصول نامعتبر. لطفاً دوباره تلاش کنید.');
    return;
  }

  const state = getUserState(chatId);
  state.tempData.productId = productId;
  state.step = 'selecting_plan';
  userStates.set(chatId, state);

  await sendMessage(chatId, `📦 <b>${PRODUCTS[productId].name}</b>\nلطفاً پلن مورد نظر را انتخاب کنید:`, {
    reply_markup: plansKeyboard(productId)
  });
}

async function handlePlanSelect(chatId, data, callbackId) {
  await answerCallbackQuery(callbackId);
  const parts = data.split('|'); // plan|productId|planId
  if (parts.length !== 3) {
    await sendMessage(chatId, 'خطا در انتخاب پلن. لطفاً دوباره تلاش کنید.');
    return;
  }
  const productId = parts[1];
  const planId = parts[2];

  const product = PRODUCTS[productId];
  if (!product) {
    await sendMessage(chatId, '❌ محصول نامعتبر. لطفاً دوباره تلاش کنید.');
    return;
  }
  if (!product.plans[planId]) {
    await sendMessage(chatId, '❌ پلن نامعتبر. لطفاً دوباره تلاش کنید.');
    return;
  }

  const state = getUserState(chatId);
  state.tempData.productId = productId;
  state.tempData.planId = planId;
  state.step = 'selecting_config_type';
  userStates.set(chatId, state);

  const plan = product.plans[planId];
  const priceStr = plan.price.toLocaleString() + ' تومان';
  await sendMessage(chatId, `✅ پلن <b>${plan.name}</b> با قیمت ${priceStr} انتخاب شد.\n\n🔧 حالا <b>نوع کانفیگ</b> مورد نظر را انتخاب کنید:`, {
    reply_markup: configTypesKeyboard()
  });
}

async function handleConfigTypeSelect(chatId, data, callbackId) {
  await answerCallbackQuery(callbackId);
  const parts = data.split('|');
  const configType = parts[1];
  if (!CONFIG_TYPES.includes(configType)) {
    await sendMessage(chatId, 'نوع کانفیگ نامعتبر.');
    return;
  }
  const state = getUserState(chatId);
  state.tempData.configType = configType;
  state.step = 'entering_name';
  userStates.set(chatId, state);

  await sendMessage(chatId, `🔧 نوع کانفیگ: <b>${configType}</b>\n\n👤 لطفاً <b>نام کامل</b> خود را وارد کنید:`);
}

async function handleEnteringName(chatId, text) {
  if (!text || text.trim().length < 2) {
    await sendMessage(chatId, '❌ لطفاً نام معتبر (حداقل ۲ کاراکتر) وارد کنید.');
    return;
  }
  const state = getUserState(chatId);
  state.tempData.customerName = text.trim();
  state.step = 'selecting_payment';
  userStates.set(chatId, state);

  await sendMessage(chatId, '👤 نام شما ثبت شد.\n\n💳 روش پرداخت را انتخاب کنید:', {
    reply_markup: paymentMethodsKeyboard()
  });
}

async function handlePaymentSelect(chatId, data, callbackId) {
  await answerCallbackQuery(callbackId);
  const parts = data.split('|');
  const method = parts[1];
  if (!PAYMENT_METHODS.includes(method)) {
    await sendMessage(chatId, 'روش پرداخت نامعتبر.');
    return;
  }
  const state = getUserState(chatId);
  state.tempData.paymentMethod = method;
  state.step = 'entering_tracking';
  userStates.set(chatId, state);

  await sendMessage(chatId, `💳 روش پرداخت: ${method}\n\n🔢 لطفاً <b>کد پیگیری</b> پرداخت را وارد کنید:`);
}

async function handleEnteringTracking(chatId, text) {
  if (!text || text.trim().length < 3) {
    await sendMessage(chatId, '❌ لطفاً کد پیگیری معتبر (حداقل ۳ کاراکتر) وارد کنید.');
    return;
  }
  const state = getUserState(chatId);
  state.tempData.trackingCode = text.trim();
  state.step = 'sending_receipt';
  userStates.set(chatId, state);

  await sendMessage(chatId, '🔢 کد پیگیری ثبت شد.\n\n🖼️ لطفاً <b>عکس رسید</b> پرداخت را ارسال کنید (به صورت عکس).');
}

async function handleReceiptPhoto(chatId, photoId) {
  const state = getUserState(chatId);
  if (!state || state.step !== 'sending_receipt') {
    await sendMessage(chatId, '❌ در حال حاضر منتظر عکس رسید نیستید. از منوی اصلی شروع کنید.');
    return;
  }
  state.tempData.receiptPhotoId = photoId;
  state.step = 'confirming_order';
  userStates.set(chatId, state);

  const orderId = generateOrderId();
  const { productId, planId, configType, customerName, paymentMethod, trackingCode } = state.tempData;
  const product = PRODUCTS[productId];
  const plan = product?.plans?.[planId];
  const order = {
    id: orderId,
    userId: chatId,
    productId,
    planId,
    configType: configType || 'V2Ray',
    customerName,
    paymentMethod,
    trackingCode,
    receiptPhotoId: photoId,
    status: ORDER_STATUS.PENDING,
    createdAt: Date.now()
  };
  state.tempData.orderId = orderId;
  state.tempData.order = order;
  userStates.set(chatId, state);

  const summary = formatOrderSummary(order);
  await sendMessage(chatId, `📋 <b>خلاصه سفارش</b>\n${summary}\n\nآیا اطلاعات صحیح است؟`, {
    reply_markup: orderConfirmKeyboard(orderId)
  });
}

async function handleOrderConfirm(chatId, data, callbackId) {
  await answerCallbackQuery(callbackId);
  const parts = data.split('|');
  const action = parts[0];
  const orderId = parts[1];
  const state = getUserState(chatId);
  if (!state || state.tempData.orderId !== orderId) {
    await sendMessage(chatId, '❌ سفارش یافت نشد. دوباره تلاش کنید.');
    clearUserState(chatId);
    return;
  }

  if (action === 'cancel') {
    clearUserState(chatId);
    await sendMessage(chatId, '❌ سفارش لغو شد.', { reply_markup: mainMenu() });
    return;
  }

  if (action === 'confirm') {
    const order = state.tempData.order;
    if (!order) {
      await sendMessage(chatId, 'خطا در ثبت سفارش.');
      clearUserState(chatId);
      return;
    }
    order.status = ORDER_STATUS.PENDING;
    saveOrder(order);
    clearUserState(chatId);

    const adminMsg = formatAdminOrderMessage(order);
    await sendMessage(ADMIN_ID, `🔔 <b>سفارش جدید نیاز به تایید دارد</b>\n${adminMsg}`, {
      reply_markup: adminOrderKeyboard(order.id)
    });

    await sendMessage(chatId, `✅ سفارش شما با شناسه <code>${order.id}</code> ثبت شد و در انتظار تایید ادمین می‌باشد.`, {
      reply_markup: mainMenu()
    });
  }
}

// -------------------- مدیریت اقدامات ادمین --------------------
async function handleAdminAction(chatId, data, callbackId, callbackMessage) {
  await answerCallbackQuery(callbackId);
  const parts = data.split('|');
  if (parts.length < 3) {
    await sendMessage(chatId, 'دستور نامعتبر.');
    return;
  }
  const action = parts[1];
  const orderId = parts[2];
  const order = getOrder(orderId);
  if (!order) {
    await sendMessage(chatId, `❌ سفارش با شناسه ${orderId} یافت نشد.`);
    return;
  }

  if (action === 'confirm') {
    updateOrderStatus(orderId, ORDER_STATUS.CONFIRMED);
    await sendMessage(ADMIN_ID, `✅ سفارش <code>${orderId}</code> تایید شد. لطفاً کانفیگ را به کاربر ارسال کنید.`);
    await sendMessage(order.userId, `✅ سفارش شما با شناسه <code>${orderId}</code> تایید شد. به زودی اکانت برای شما ارسال خواهد شد.`);
    if (callbackMessage) {
      try {
        await editMessageText(ADMIN_ID, callbackMessage.message_id,
          `🔔 <b>سفارش ${orderId}</b>\n${formatAdminOrderMessage(order)}\n\nوضعیت: ${ORDER_STATUS.CONFIRMED} (منتظر ارسال اکانت)`,
          { reply_markup: { inline_keyboard: [] } }
        );
      } catch (e) { console.error(e); }
    }
  } else if (action === 'reject') {
    updateOrderStatus(orderId, ORDER_STATUS.REJECTED);
    await sendMessage(ADMIN_ID, `❌ سفارش <code>${orderId}</code> رد شد.`);
    await sendMessage(order.userId, `❌ سفارش شما با شناسه <code>${orderId}</code> رد شد.`);
    if (callbackMessage) {
      try {
        await editMessageText(ADMIN_ID, callbackMessage.message_id,
          `🔔 <b>سفارش ${orderId}</b>\n${formatAdminOrderMessage(order)}\n\nوضعیت: ${ORDER_STATUS.REJECTED}`,
          { reply_markup: { inline_keyboard: [] } }
        );
      } catch (e) { console.error(e); }
    }
  } else if (action === 'send') {
    adminSendState.set(chatId, orderId);
    await sendMessage(chatId, `📤 لطفاً <b>متن اکانت</b> را برای سفارش <code>${orderId}</code> ارسال کنید.`);
    await sendMessage(order.userId, `🔄 ادمین در حال ارسال اکانت برای سفارش <code>${orderId}</code> می‌باشد.`);
    return;
  }
}

async function handleAdminSendMessage(chatId, text) {
  const orderId = adminSendState.get(chatId);
  if (!orderId) {
    await sendMessage(chatId, '❌ شما در حال ارسال اکانت نیستید.');
    return;
  }
  const order = getOrder(orderId);
  if (!order) {
    await sendMessage(chatId, `❌ سفارش ${orderId} یافت نشد.`);
    adminSendState.delete(chatId);
    return;
  }
  await sendMessage(order.userId, `📤 <b>اکانت شما برای سفارش <code>${orderId}</code></b>\n\n${text}`);
  updateOrderStatus(orderId, ORDER_STATUS.SENT);
  adminSendState.delete(chatId);

  await sendMessage(ADMIN_ID, `📤 اکانت سفارش <code>${orderId}</code> به کاربر ارسال شد.`);
  await sendMessage(chatId, `✅ اکانت سفارش <code>${orderId}</code> با موفقیت ارسال شد.`);
}

// -------------------- پردازش پیام‌های مرحله‌ای --------------------
async function handleOrderStepMessage(chatId, text) {
  const state = getUserState(chatId);
  if (!state || !state.step) {
    await sendMessage(chatId, 'لطفاً از منوی اصلی استفاده کنید:', { reply_markup: mainMenu() });
    return;
  }

  switch (state.step) {
    case 'entering_name':
      await handleEnteringName(chatId, text);
      break;
    case 'entering_tracking':
      await handleEnteringTracking(chatId, text);
      break;
    default:
      await sendMessage(chatId, '⏳ در مرحله غیرمنتظره‌ای هستید. از منو شروع کنید.', { reply_markup: mainMenu() });
      clearUserState(chatId);
  }
}

async function handlePhoto(chatId, photo) {
  const state = getUserState(chatId);
  if (state && state.step === 'sending_receipt') {
    const photoId = photo[photo.length - 1].file_id;
    await handleReceiptPhoto(chatId, photoId);
  } else {
    await sendMessage(chatId, '📸 لطفاً فقط زمانی که سیستم درخواست عکس رسید کرد، عکس ارسال کنید.');
  }
}

// -------------------- پردازش Callback Query --------------------
async function handleCallbackQuery(callbackQuery) {
  const chatId = callbackQuery.from.id;
  const data = callbackQuery.data;

  try {
    if (data.startsWith('product|')) {
      await handleProductSelect(chatId, data, callbackQuery.id);
    } else if (data.startsWith('plan|')) {
      await handlePlanSelect(chatId, data, callbackQuery.id);
    } else if (data.startsWith('config|')) {
      await handleConfigTypeSelect(chatId, data, callbackQuery.id);
    } else if (data.startsWith('pay|')) {
      await handlePaymentSelect(chatId, data, callbackQuery.id);
    } else if (data.startsWith('confirm|') || data.startsWith('cancel|')) {
      await handleOrderConfirm(chatId, data, callbackQuery.id);
    } else if (data.startsWith('admin|')) {
      await handleAdminAction(chatId, data, callbackQuery.id, callbackQuery.message);
    } else if (data.startsWith('menu|')) {
      await handleMainMenu(chatId, data, callbackQuery.id);
    } else {
      await answerCallbackQuery(callbackQuery.id, 'دستور نامعتبر', true);
    }
  } catch (err) {
    console.error('❌ خطا در پردازش Callback:', err);
    await answerCallbackQuery(callbackQuery.id, 'خطا در پردازش درخواست', true);
  }
}

// -------------------- پردازش Webhook --------------------
async function processUpdate(update) {
  try {
    if (update.message) {
      const chatId = update.message.chat.id;
      const text = update.message.text;
      const photo = update.message.photo;

      if (text && text.startsWith('/start')) {
        await handleStart(chatId);
        return;
      }

      if (adminSendState.has(chatId) && text) {
        await handleAdminSendMessage(chatId, text);
        return;
      }

      if (photo) {
        await handlePhoto(chatId, photo);
        return;
      }

      if (text) {
        await handleOrderStepMessage(chatId, text);
        return;
      }

      await sendMessage(chatId, 'برای شروع از /start استفاده کنید.', { reply_markup: mainMenu() });
    }

    if (update.callback_query) {
      await handleCallbackQuery(update.callback_query);
    }
  } catch (err) {
    console.error('❌ خطا در پردازش آپدیت:', err);
  }
}

// -------------------- توابع تست و تنظیم Webhook --------------------
async function testBotToken() {
  try {
    const me = await getMe();
    if (me.ok) {
      return { ok: true, username: me.result.username };
    } else {
      return { ok: false, error: me.description };
    }
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

async function setupWebhookAutomatically(workerUrl) {
  try {
    const webhookUrl = workerUrl + '/webhook';
    const result = await setWebhook(webhookUrl);
    if (result.ok) {
      return { ok: true, url: webhookUrl, description: result.description };
    } else {
      return { ok: false, error: result.description };
    }
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

// -------------------- صفحه اصلی HTML --------------------
function renderHomePage(tokenTest, webhookStatus, ordersCount) {
  const productCount = Object.keys(PRODUCTS).length;
  return `
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${SHOP_NAME} - ربات فروشگاهی</title>
  <style>
    body {
      background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
      color: #fff;
      font-family: 'Segoe UI', Tahoma, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
      padding: 20px;
    }
    .card {
      background: rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 28px;
      padding: 30px 35px;
      max-width: 550px;
      width: 100%;
      box-shadow: 0 25px 50px -12px rgba(0,0,0,0.8);
      text-align: center;
    }
    h1 {
      font-size: 2.2rem;
      background: linear-gradient(to left, #f7971e, #ffd200);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin: 0 0 5px;
    }
    .subtitle { color: #aaa; margin-bottom: 25px; font-size: 0.95rem; }
    .status-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 15px;
      margin: 25px 0;
    }
    .status-item {
      background: rgba(255,255,255,0.06);
      border-radius: 16px;
      padding: 14px 10px;
      border: 1px solid rgba(255,255,255,0.08);
    }
    .status-item .label { color: #aaa; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .status-item .value { font-size: 1.1rem; font-weight: 600; margin-top: 6px; }
    .value.ok { color: #4ade80; }
    .value.fail { color: #f87171; }
    .value.info { color: #60a5fa; }
    .btn {
      display: inline-block;
      background: #4f46e5;
      color: #fff;
      padding: 12px 24px;
      border-radius: 40px;
      text-decoration: none;
      font-weight: 600;
      margin: 8px 4px;
      border: none;
      cursor: pointer;
      transition: 0.2s;
      font-size: 0.9rem;
    }
    .btn:hover { background: #4338ca; transform: scale(1.02); }
    .btn-outline { background: transparent; border: 1px solid #4f46e5; color: #4f46e5; }
    .btn-outline:hover { background: #4f46e5; color: #fff; }
    .footer { margin-top: 25px; color: #666; font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 18px; }
    .badge {
      display: inline-block;
      background: rgba(74, 222, 128, 0.2);
      color: #4ade80;
      padding: 4px 14px;
      border-radius: 30px;
      font-size: 0.75rem;
      font-weight: 600;
    }
    .badge.fail { background: rgba(248, 113, 113, 0.2); color: #f87171; }
  </style>
</head>
<body>
<div class="card">
  <h1>🛒 ${SHOP_NAME}</h1>
  <div class="subtitle">ربات فروشگاهی کانفیگ</div>

  <div class="status-grid">
    <div class="status-item">
      <div class="label">وضعیت توکن</div>
      <div class="value ${tokenTest.ok ? 'ok' : 'fail'}">
        ${tokenTest.ok ? '✅ ' + tokenTest.username : '❌ ' + (tokenTest.error || 'نامعتبر')}
      </div>
    </div>
    <div class="status-item">
      <div class="label">وضعیت Webhook</div>
      <div class="value ${webhookStatus && webhookStatus.url ? 'ok' : 'fail'}">
        ${webhookStatus && webhookStatus.url ? '✅ تنظیم شده' : '❌ تنظیم نشده'}
      </div>
    </div>
    <div class="status-item">
      <div class="label">تعداد محصولات</div>
      <div class="value info">${productCount}</div>
    </div>
    <div class="status-item">
      <div class="label">تعداد سفارش‌ها</div>
      <div class="value info">${ordersCount}</div>
    </div>
  </div>

  <div>
    <a href="/test" class="btn">🔍 تست ربات</a>
    <a href="/force-webhook" class="btn btn-outline">⚙️ تنظیم Webhook</a>
    <a href="/webhook-info" class="btn btn-outline">📡 اطلاعات Webhook</a>
  </div>

  <div class="footer">
    <span class="badge ${tokenTest.ok ? '' : 'fail'}">${tokenTest.ok ? 'ربات فعال' : 'ربات غیرفعال'}</span>
    <span class="badge ${webhookStatus && webhookStatus.url ? '' : 'fail'}">${webhookStatus && webhookStatus.url ? 'Webhook OK' : 'Webhook مشکل دارد'}</span>
    <br><br>
    <span style="color:#555;">نسخه ۱.۰ | ${SHOP_NAME}</span>
  </div>
</div>
</body>
</html>
  `;
}

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
