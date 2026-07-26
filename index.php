<?php
// ============================================================
// ربات فروشگاهی AyhanX-Freedom - نسخه PHP برای Railway
// ============================================================

// -------------------- تنظیمات ثابت --------------------
define('BOT_TOKEN', '8631736538:AAFkNgUY5QM4Gr8eqQsviUk6NxkLcZvT5yc');
define('ADMIN_ID', 8907076433);
define('SUPPORT_USERNAME', '@nspubgabot');
define('CHANNEL_ID', '@dnspubga');
define('SHOP_NAME', 'AyhanX-Freedom');
define('DATA_FILE', __DIR__ . '/data.json');

// وضعیت‌های سفارش
define('STATUS_PENDING', 'pending');
define('STATUS_CONFIRMED', 'confirmed');
define('STATUS_REJECTED', 'rejected');
define('STATUS_SENT', 'sent');

// -------------------- محصولات و پلن‌ها --------------------
$PRODUCTS = [
    'wireguard_gaming' => [
        'name' => 'وایرگارد گیم و وب گردی',
        'emoji' => '🛡️',
        'plans' => [
            'plan_wg_1m' => ['name' => '۱ ماهه ۳۶ گیگ', 'price' => 400, 'description' => '۳۶ گیگابایت، ۱ ماهه'],
            'plan_wg_2m' => ['name' => '۲ ماهه ۷۸ گیگ', 'price' => 600, 'description' => '۷۸ گیگابایت، ۲ ماهه'],
            'plan_wg_3m' => ['name' => '۳ ماهه ۱۲۷ گیگ', 'price' => 800, 'description' => '۱۲۷ گیگابایت، ۳ ماهه'],
            'plan_wg_6m' => ['name' => '۶ ماهه ۳۰۰ گیگ', 'price' => 1200, 'description' => '۳۰۰ گیگابایت، ۶ ماهه']
        ]
    ],
    'config_monthly' => [
        'name' => 'کانفیگ ماهانه',
        'emoji' => '📅',
        'plans' => [
            'plan_50' => ['name' => '۵۰ گیگ', 'price' => 35000, 'description' => '۵۰ گیگابایت، ۱ ماهه'],
            'plan_100' => ['name' => '۱۰۰ گیگ', 'price' => 55000, 'description' => '۱۰۰ گیگابایت، ۱ ماهه'],
            'plan_200' => ['name' => '۲۰۰ گیگ', 'price' => 85000, 'description' => '۲۰۰ گیگابایت، ۱ ماهه']
        ]
    ],
    'config_quarterly' => [
        'name' => 'کانفیگ سه‌ماهه',
        'emoji' => '📆',
        'plans' => [
            'plan_unlimited' => ['name' => 'نامحدود', 'price' => 150000, 'description' => 'حجم نامحدود، ۳ ماهه'],
            'plan_500' => ['name' => '۵۰۰ گیگ', 'price' => 120000, 'description' => '۵۰۰ گیگابایت، ۳ ماهه']
        ]
    ]
];

$CONFIG_TYPES = ['WireGuard', 'V2Ray'];
$PAYMENT_METHODS = ['کارت به کارت', 'رمز دوم (اینترنتی)', 'کیف پول (USDT)'];

// -------------------- توابع ذخیره‌سازی (JSON) --------------------
function loadData() {
    if (!file_exists(DATA_FILE)) {
        return ['orders' => [], 'states' => []];
    }
    $content = file_get_contents(DATA_FILE);
    return json_decode($content, true) ?: ['orders' => [], 'states' => []];
}

function saveData($data) {
    file_put_contents(DATA_FILE, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

function getOrders() {
    $data = loadData();
    return $data['orders'] ?? [];
}

function saveOrder($order) {
    $data = loadData();
    $data['orders'][$order['id']] = $order;
    saveData($data);
}

function getOrder($orderId) {
    $orders = getOrders();
    return $orders[$orderId] ?? null;
}

function updateOrderStatus($orderId, $status, $extra = []) {
    $order = getOrder($orderId);
    if (!$order) return null;
    $order['status'] = $status;
    foreach ($extra as $key => $value) {
        $order[$key] = $value;
    }
    $data = loadData();
    $data['orders'][$orderId] = $order;
    saveData($data);
    return $order;
}

function getUserState($chatId) {
    $data = loadData();
    return $data['states'][$chatId] ?? ['step' => null, 'tempData' => []];
}

function setUserState($chatId, $step, $tempData = []) {
    $data = loadData();
    $data['states'][$chatId] = ['step' => $step, 'tempData' => $tempData];
    saveData($data);
}

function clearUserState($chatId) {
    $data = loadData();
    unset($data['states'][$chatId]);
    saveData($data);
}

function generateOrderId() {
    return uniqid() . bin2hex(random_bytes(4));
}

function getUserOrders($userId) {
    $orders = getOrders();
    $result = [];
    foreach ($orders as $order) {
        if ($order['userId'] == $userId) {
            $result[] = $order;
        }
    }
    usort($result, function($a, $b) {
        return $b['createdAt'] - $a['createdAt'];
    });
    return $result;
}

// -------------------- توابع Telegram API --------------------
function callTelegram($method, $params = []) {
    $url = "https://api.telegram.org/bot" . BOT_TOKEN . "/" . $method;
    $options = [
        'http' => [
            'header' => "Content-Type: application/json\r\n",
            'method' => 'POST',
            'content' => json_encode($params),
            'ignore_errors' => true
        ]
    ];
    $context = stream_context_create($options);
    $response = file_get_contents($url, false, $context);
    return json_decode($response, true);
}

function sendMessage($chatId, $text, $extra = []) {
    $params = array_merge([
        'chat_id' => $chatId,
        'text' => $text,
        'parse_mode' => 'HTML'
    ], $extra);
    return callTelegram('sendMessage', $params);
}

function editMessageText($chatId, $messageId, $text, $extra = []) {
    $params = array_merge([
        'chat_id' => $chatId,
        'message_id' => $messageId,
        'text' => $text,
        'parse_mode' => 'HTML'
    ], $extra);
    return callTelegram('editMessageText', $params);
}

function answerCallbackQuery($callbackId, $text = '', $showAlert = false) {
    return callTelegram('answerCallbackQuery', [
        'callback_query_id' => $callbackId,
        'text' => $text,
        'show_alert' => $showAlert
    ]);
}

// -------------------- کیبوردها --------------------
function mainMenu() {
    return json_encode([
        'inline_keyboard' => [
            [
                ['text' => '🛒 فروشگاه', 'callback_data' => 'menu|shop'],
                ['text' => '📋 سفارش‌های من', 'callback_data' => 'menu|orders']
            ],
            [
                ['text' => '🆘 پشتیبانی', 'callback_data' => 'menu|support'],
                ['text' => '📢 کانال', 'callback_data' => 'menu|channel']
            ]
        ]
    ]);
}

function productsKeyboard() {
    global $PRODUCTS;
    $keyboard = [];
    foreach ($PRODUCTS as $id => $product) {
        $keyboard[] = [['text' => $product['emoji'] . ' ' . $product['name'], 'callback_data' => "product|$id"]];
    }
    $keyboard[] = [['text' => '🔙 بازگشت به منو', 'callback_data' => 'menu|main']];
    return json_encode(['inline_keyboard' => $keyboard]);
}

function plansKeyboard($productId) {
    global $PRODUCTS;
    $product = $PRODUCTS[$productId] ?? null;
    if (!$product) return json_encode(['inline_keyboard' => []]);
    $keyboard = [];
    foreach ($product['plans'] as $planId => $plan) {
        $priceStr = number_format($plan['price']) . ' تومان';
        $keyboard[] = [['text' => $plan['name'] . ' - ' . $priceStr, 'callback_data' => "plan|$productId|$planId"]];
    }
    $keyboard[] = [['text' => '🔙 بازگشت به محصولات', 'callback_data' => 'menu|shop']];
    return json_encode(['inline_keyboard' => $keyboard]);
}

function configTypesKeyboard() {
    global $CONFIG_TYPES;
    $keyboard = [];
    foreach ($CONFIG_TYPES as $type) {
        $keyboard[] = [['text' => $type, 'callback_data' => "config|$type"]];
    }
    $keyboard[] = [['text' => '🔙 انصراف', 'callback_data' => 'menu|main']];
    return json_encode(['inline_keyboard' => $keyboard]);
}

function paymentMethodsKeyboard() {
    global $PAYMENT_METHODS;
    $keyboard = [];
    foreach ($PAYMENT_METHODS as $method) {
        $keyboard[] = [['text' => $method, 'callback_data' => "pay|$method"]];
    }
    $keyboard[] = [['text' => '🔙 انصراف', 'callback_data' => 'menu|main']];
    return json_encode(['inline_keyboard' => $keyboard]);
}

function orderConfirmKeyboard($orderId) {
    return json_encode([
        'inline_keyboard' => [
            [
                ['text' => '✅ تایید و ثبت', 'callback_data' => "confirm|$orderId"],
                ['text' => '❌ لغو', 'callback_data' => "cancel|$orderId"]
            ]
        ]
    ]);
}

function adminOrderKeyboard($orderId) {
    return json_encode([
        'inline_keyboard' => [
            [
                ['text' => '✅ تایید', 'callback_data' => "admin|confirm|$orderId"],
                ['text' => '❌ رد', 'callback_data' => "admin|reject|$orderId"]
            ],
            [
                ['text' => '📤 ارسال اکانت', 'callback_data' => "admin|send|$orderId"]
            ]
        ]
    ]);
}

// -------------------- توابع فرمت پیام --------------------
function formatOrderSummary($order) {
    global $PRODUCTS;
    $product = $PRODUCTS[$order['productId']] ?? null;
    $plan = $product['plans'][$order['planId']] ?? null;
    $priceStr = $plan ? number_format($plan['price']) . ' تومان' : 'نامشخص';
    $date = date('Y-m-d H:i', $order['createdAt'] / 1000);
    $statusText = [
        STATUS_PENDING => '⏳ در انتظار تایید',
        STATUS_CONFIRMED => '✅ تایید شده',
        STATUS_REJECTED => '❌ رد شده',
        STATUS_SENT => '📤 ارسال شده'
    ][$order['status']] ?? $order['status'];
    
    return "
📋 <b>خلاصه سفارش</b>
🆔 شناسه: <code>{$order['id']}</code>
📦 محصول: " . ($product['name'] ?? $order['productId']) . "
📊 پلن: " . ($plan['name'] ?? $order['planId']) . "
🔧 نوع کانفیگ: " . ($order['configType'] ?? 'تعیین نشده') . "
💰 قیمت: $priceStr
👤 نام: " . ($order['customerName'] ?? 'ندارد') . "
💳 روش پرداخت: " . ($order['paymentMethod'] ?? 'ندارد') . "
🔢 کد پیگیری: " . ($order['trackingCode'] ?? 'ندارد') . "
📎 رسید: " . ($order['receiptPhotoId'] ? '✅ ارسال شده' : '❌ ارسال نشده') . "
📅 تاریخ: $date
📌 وضعیت: $statusText
    ";
}

function formatAdminOrderMessage($order) {
    global $PRODUCTS;
    $product = $PRODUCTS[$order['productId']] ?? null;
    $plan = $product['plans'][$order['planId']] ?? null;
    $priceStr = $plan ? number_format($plan['price']) . ' تومان' : 'نامشخص';
    $date = date('Y-m-d H:i', $order['createdAt'] / 1000);
    
    return "
🆕 <b>سفارش جدید</b>
🆔 شناسه: <code>{$order['id']}</code>
👤 کاربر: <a href=\"tg://user?id={$order['userId']}\">" . ($order['customerName'] ?? 'کاربر') . "</a>
📦 محصول: " . ($product['name'] ?? $order['productId']) . "
📊 پلن: " . ($plan['name'] ?? $order['planId']) . "
🔧 نوع کانفیگ: " . ($order['configType'] ?? 'تعیین نشده') . "
💰 قیمت: $priceStr
💳 روش پرداخت: " . ($order['paymentMethod'] ?? 'ندارد') . "
🔢 کد پیگیری: " . ($order['trackingCode'] ?? 'ندارد') . "
📎 رسید: " . ($order['receiptPhotoId'] ? '✅ ارسال شده' : '❌ ارسال نشده') . "
📅 تاریخ: $date
    ";
}

function formatOrderStatus($order) {
    return [
        STATUS_PENDING => '⏳ در انتظار تایید',
        STATUS_CONFIRMED => '✅ تایید شده',
        STATUS_REJECTED => '❌ رد شده',
        STATUS_SENT => '📤 ارسال شده'
    ][$order['status']] ?? $order['status'];
}

// ==================== پردازش Webhook ====================

function processUpdate($update) {
    // پیام
    if (isset($update['message'])) {
        $message = $update['message'];
        $chatId = $message['chat']['id'];
        $text = $message['text'] ?? null;
        $photo = $message['photo'] ?? null;
        
        // /start
        if ($text && str_starts_with($text, '/start')) {
            handleStart($chatId);
            return;
        }
        
        // ادمین در حال ارسال اکانت
        $state = getUserState($chatId);
        if ($state['step'] === 'admin_sending' && $text) {
            handleAdminSendMessage($chatId, $text);
            return;
        }
        
        // عکس رسید
        if ($photo && $state['step'] === 'sending_receipt') {
            $photoId = $photo[count($photo)-1]['file_id'];
            handleReceiptPhoto($chatId, $photoId);
            return;
        }
        
        // مراحل ثبت سفارش
        if ($text) {
            handleOrderStep($chatId, $text);
            return;
        }
        
        sendMessage($chatId, 'برای شروع از /start استفاده کنید.', ['reply_markup' => mainMenu()]);
    }
    
    // Callback Query
    if (isset($update['callback_query'])) {
        $callback = $update['callback_query'];
        $chatId = $callback['from']['id'];
        $data = $callback['data'];
        $callbackId = $callback['id'];
        $messageId = $callback['message']['message_id'] ?? null;
        
        handleCallback($chatId, $data, $callbackId, $messageId);
    }
}

// ==================== هندلرها ====================

function handleStart($chatId) {
    clearUserState($chatId);
    sendMessage($chatId, "👋 به <b>" . SHOP_NAME . "</b> خوش آمدید!\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:", [
        'reply_markup' => mainMenu()
    ]);
}

function handleCallback($chatId, $data, $callbackId, $messageId) {
    answerCallbackQuery($callbackId);
    $parts = explode('|', $data);
    $action = $parts[0];
    
    // منو
    if ($action === 'menu') {
        $subAction = $parts[1] ?? 'main';
        clearUserState($chatId);
        if ($subAction === 'shop') {
            sendMessage($chatId, '🛒 <b>محصولات موجود:</b>', ['reply_markup' => productsKeyboard()]);
        } elseif ($subAction === 'orders') {
            showUserOrders($chatId);
        } elseif ($subAction === 'support') {
            sendMessage($chatId, "🆘 برای پشتیبانی با " . SUPPORT_USERNAME . " تماس بگیرید.", ['reply_markup' => mainMenu()]);
        } elseif ($subAction === 'channel') {
            sendMessage($chatId, "📢 کانال ما: " . CHANNEL_ID, ['reply_markup' => mainMenu()]);
        } elseif ($subAction === 'main') {
            sendMessage($chatId, '🏠 منوی اصلی:', ['reply_markup' => mainMenu()]);
        }
        return;
    }
    
    // انتخاب محصول
    if ($action === 'product') {
        $productId = $parts[1];
        global $PRODUCTS;
        if (!isset($PRODUCTS[$productId])) {
            sendMessage($chatId, '❌ محصول نامعتبر.');
            return;
        }
        setUserState($chatId, 'selecting_plan', ['productId' => $productId]);
        sendMessage($chatId, "📦 <b>{$PRODUCTS[$productId]['name']}</b>\nلطفاً پلن مورد نظر را انتخاب کنید:", [
            'reply_markup' => plansKeyboard($productId)
        ]);
        return;
    }
    
    // انتخاب پلن
    if ($action === 'plan') {
        $productId = $parts[1];
        $planId = $parts[2];
        global $PRODUCTS;
        if (!isset($PRODUCTS[$productId]['plans'][$planId])) {
            sendMessage($chatId, '❌ پلن نامعتبر.');
            return;
        }
        setUserState($chatId, 'selecting_config_type', [
            'productId' => $productId,
            'planId' => $planId
        ]);
        $plan = $PRODUCTS[$productId]['plans'][$planId];
        $priceStr = number_format($plan['price']) . ' تومان';
        sendMessage($chatId, "✅ پلن <b>{$plan['name']}</b> با قیمت $priceStr انتخاب شد.\n\n🔧 حالا <b>نوع کانفیگ</b> مورد نظر را انتخاب کنید:", [
            'reply_markup' => configTypesKeyboard()
        ]);
        return;
    }
    
    // انتخاب نوع کانفیگ
    if ($action === 'config') {
        $configType = $parts[1];
        global $CONFIG_TYPES;
        if (!in_array($configType, $CONFIG_TYPES)) {
            sendMessage($chatId, 'نوع کانفیگ نامعتبر.');
            return;
        }
        $state = getUserState($chatId);
        $state['tempData']['configType'] = $configType;
        setUserState($chatId, 'entering_name', $state['tempData']);
        sendMessage($chatId, "🔧 نوع کانفیگ: <b>$configType</b>\n\n👤 لطفاً <b>نام کامل</b> خود را وارد کنید:");
        return;
    }
    
    // انتخاب روش پرداخت
    if ($action === 'pay') {
        $method = $parts[1];
        global $PAYMENT_METHODS;
        if (!in_array($method, $PAYMENT_METHODS)) {
            sendMessage($chatId, 'روش پرداخت نامعتبر.');
            return;
        }
        $state = getUserState($chatId);
        $state['tempData']['paymentMethod'] = $method;
        setUserState($chatId, 'entering_tracking', $state['tempData']);
        sendMessage($chatId, "💳 روش پرداخت: $method\n\n🔢 لطفاً <b>کد پیگیری</b> پرداخت را وارد کنید:");
        return;
    }
    
    // تایید یا لغو سفارش
    if ($action === 'confirm' || $action === 'cancel') {
        $orderId = $parts[1];
        $state = getUserState($chatId);
        if (!isset($state['tempData']['order']) || $state['tempData']['order']['id'] !== $orderId) {
            sendMessage($chatId, '❌ سفارش یافت نشد. دوباره تلاش کنید.');
            clearUserState($chatId);
            return;
        }
        if ($action === 'cancel') {
            clearUserState($chatId);
            sendMessage($chatId, '❌ سفارش لغو شد.', ['reply_markup' => mainMenu()]);
            return;
        }
        if ($action === 'confirm') {
            $order = $state['tempData']['order'];
            $order['status'] = STATUS_PENDING;
            saveOrder($order);
            clearUserState($chatId);
            
            // ارسال به ادمین
            $adminMsg = formatAdminOrderMessage($order);
            sendMessage(ADMIN_ID, "🔔 <b>سفارش جدید نیاز به تایید دارد</b>\n$adminMsg", [
                'reply_markup' => adminOrderKeyboard($order['id'])
            ]);
            
            sendMessage($chatId, "✅ سفارش شما با شناسه <code>{$order['id']}</code> ثبت شد و در انتظار تایید ادمین می‌باشد.", [
                'reply_markup' => mainMenu()
            ]);
        }
        return;
    }
    
    // اقدامات ادمین
    if ($action === 'admin') {
        $subAction = $parts[1] ?? '';
        $orderId = $parts[2] ?? '';
        $order = getOrder($orderId);
        if (!$order) {
            sendMessage($chatId, "❌ سفارش با شناسه $orderId یافت نشد.");
            return;
        }
        
        if ($subAction === 'confirm') {
            updateOrderStatus($orderId, STATUS_CONFIRMED);
            sendMessage(ADMIN_ID, "✅ سفارش <code>$orderId</code> تایید شد. لطفاً کانفیگ را به کاربر ارسال کنید.");
            sendMessage($order['userId'], "✅ سفارش شما با شناسه <code>$orderId</code> تایید شد. به زودی اکانت برای شما ارسال خواهد شد.");
            // ویرایش پیام ادمین
            if ($messageId) {
                editMessageText(ADMIN_ID, $messageId, 
                    "🔔 <b>سفارش $orderId</b>\n" . formatAdminOrderMessage($order) . "\n\nوضعیت: " . STATUS_CONFIRMED . " (منتظر ارسال اکانت)",
                    ['reply_markup' => json_encode(['inline_keyboard' => []])]
                );
            }
        } elseif ($subAction === 'reject') {
            updateOrderStatus($orderId, STATUS_REJECTED);
            sendMessage(ADMIN_ID, "❌ سفارش <code>$orderId</code> رد شد.");
            sendMessage($order['userId'], "❌ سفارش شما با شناسه <code>$orderId</code> رد شد.");
            if ($messageId) {
                editMessageText(ADMIN_ID, $messageId,
                    "🔔 <b>سفارش $orderId</b>\n" . formatAdminOrderMessage($order) . "\n\nوضعیت: " . STATUS_REJECTED,
                    ['reply_markup' => json_encode(['inline_keyboard' => []])]
                );
            }
        } elseif ($subAction === 'send') {
            setUserState($chatId, 'admin_sending', ['orderId' => $orderId]);
            sendMessage($chatId, "📤 لطفاً <b>متن اکانت</b> را برای سفارش <code>$orderId</code> ارسال کنید.");
            sendMessage($order['userId'], "🔄 ادمین در حال ارسال اکانت برای سفارش <code>$orderId</code> می‌باشد.");
        }
        return;
    }
    
    sendMessage($chatId, 'دستور نامعتبر.');
}

function showUserOrders($chatId) {
    $orders = getUserOrders($chatId);
    if (empty($orders)) {
        sendMessage($chatId, '📭 شما هیچ سفارشی ندارید.', ['reply_markup' => mainMenu()]);
        return;
    }
    $msg = '📋 <b>سفارش‌های شما:</b>\n\n';
    foreach ($orders as $order) {
        $msg .= "🆔 <code>{$order['id']}</code> - " . formatOrderStatus($order) . "\n";
    }
    sendMessage($chatId, $msg, ['reply_markup' => mainMenu()]);
}

function handleOrderStep($chatId, $text) {
    $state = getUserState($chatId);
    $step = $state['step'];
    
    if ($step === 'entering_name') {
        if (strlen(trim($text)) < 2) {
            sendMessage($chatId, '❌ لطفاً نام معتبر (حداقل ۲ کاراکتر) وارد کنید.');
            return;
        }
        $state['tempData']['customerName'] = trim($text);
        setUserState($chatId, 'selecting_payment', $state['tempData']);
        sendMessage($chatId, '👤 نام شما ثبت شد.\n\n💳 روش پرداخت را انتخاب کنید:', [
            'reply_markup' => paymentMethodsKeyboard()
        ]);
        return;
    }
    
    if ($step === 'entering_tracking') {
        if (strlen(trim($text)) < 3) {
            sendMessage($chatId, '❌ لطفاً کد پیگیری معتبر (حداقل ۳ کاراکتر) وارد کنید.');
            return;
        }
        $state['tempData']['trackingCode'] = trim($text);
        setUserState($chatId, 'sending_receipt', $state['tempData']);
        sendMessage($chatId, '🔢 کد پیگیری ثبت شد.\n\n🖼️ لطفاً <b>عکس رسید</b> پرداخت را ارسال کنید (به صورت عکس).');
        return;
    }
    
    sendMessage($chatId, 'لطفاً از منوی اصلی استفاده کنید:', ['reply_markup' => mainMenu()]);
}

function handleReceiptPhoto($chatId, $photoId) {
    $state = getUserState($chatId);
    if ($state['step'] !== 'sending_receipt') {
        sendMessage($chatId, '❌ در حال حاضر منتظر عکس رسید نیستید. از منوی اصلی شروع کنید.');
        return;
    }
    
    $state['tempData']['receiptPhotoId'] = $photoId;
    $orderId = generateOrderId();
    $temp = $state['tempData'];
    
    $order = [
        'id' => $orderId,
        'userId' => $chatId,
        'productId' => $temp['productId'],
        'planId' => $temp['planId'],
        'configType' => $temp['configType'] ?? 'V2Ray',
        'customerName' => $temp['customerName'],
        'paymentMethod' => $temp['paymentMethod'],
        'trackingCode' => $temp['trackingCode'],
        'receiptPhotoId' => $photoId,
        'status' => STATUS_PENDING,
        'createdAt' => round(microtime(true) * 1000)
    ];
    
    $state['tempData']['order'] = $order;
    setUserState($chatId, 'confirming_order', $state['tempData']);
    
    $summary = formatOrderSummary($order);
    sendMessage($chatId, "📋 <b>خلاصه سفارش</b>\n$summary\n\nآیا اطلاعات صحیح است؟", [
        'reply_markup' => orderConfirmKeyboard($orderId)
    ]);
}

function handleAdminSendMessage($chatId, $text) {
    $state = getUserState($chatId);
    $orderId = $state['tempData']['orderId'] ?? null;
    if (!$orderId) {
        sendMessage($chatId, '❌ شما در حال ارسال اکانت نیستید.');
        clearUserState($chatId);
        return;
    }
    $order = getOrder($orderId);
    if (!$order) {
        sendMessage($chatId, "❌ سفارش $orderId یافت نشد.");
        clearUserState($chatId);
        return;
    }
    
    sendMessage($order['userId'], "📤 <b>اکانت شما برای سفارش <code>$orderId</code></b>\n\n$text");
    updateOrderStatus($orderId, STATUS_SENT);
    clearUserState($chatId);
    
    sendMessage(ADMIN_ID, "📤 اکانت سفارش <code>$orderId</code> به کاربر ارسال شد.");
    sendMessage($chatId, "✅ اکانت سفارش <code>$orderId</code> با موفقیت ارسال شد.");
}

// ==================== صفحه اصلی ====================

function renderHomePage() {
    $orders = getOrders();
    $ordersCount = count($orders);
    $productCount = count($GLOBALS['PRODUCTS']);
    
    $html = '
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>' . SHOP_NAME . ' - ربات فروشگاهی</title>
    <style>
        body {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #fff;
            font-family: "Segoe UI", Tahoma, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255,255,255,0.1);
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
        .status-item .value { font-size: 1.3rem; font-weight: 600; margin-top: 6px; color: #60a5fa; }
        .btn {
            display: inline-block;
            background: #4f46e5;
            color: #fff;
            padding: 12px 24px;
            border-radius: 40px;
            text-decoration: none;
            font-weight: 600;
            margin: 8px 4px;
            transition: 0.2s;
            font-size: 0.9rem;
        }
        .btn:hover { background: #4338ca; transform: scale(1.02); }
        .btn-outline { background: transparent; border: 1px solid #4f46e5; color: #4f46e5; }
        .btn-outline:hover { background: #4f46e5; color: #fff; }
        .footer { margin-top: 25px; color: #666; font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 18px; }
        .badge {
            display: inline-block;
            background: rgba(74,222,128,0.2);
            color: #4ade80;
            padding: 4px 14px;
            border-radius: 30px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge.fail { background: rgba(248,113,113,0.2); color: #f87171; }
    </style>
</head>
<body>
<div class="card">
    <h1>🛒 ' . SHOP_NAME . '</h1>
    <div class="subtitle">ربات فروشگاهی کانفیگ</div>
    <div class="status-grid">
        <div class="status-item">
            <div class="label">وضعیت</div>
            <div class="value" style="color:#4ade80;">✅ فعال</div>
        </div>
        <div class="status-item">
            <div class="label">تعداد محصولات</div>
            <div class="value">' . $productCount . '</div>
        </div>
        <div class="status-item">
            <div class="label">تعداد سفارش‌ها</div>
            <div class="value">' . $ordersCount . '</div>
        </div>
        <div class="status-item">
            <div class="label">ذخیره‌سازی</div>
            <div class="value" style="color:#f59e0b;">📁 JSON</div>
        </div>
    </div>
    <div>
        <a href="/setwebhook" class="btn">⚙️ تنظیم Webhook</a>
        <a href="/webhook-info" class="btn btn-outline">📡 اطلاعات Webhook</a>
    </div>
    <div class="footer">
        <span class="badge">ربات فعال</span>
        <span class="badge">PHP 8.x</span>
        <br><br>
        <span style="color:#555;">نسخه ۱.۰ | AyhanX-Freedom</span>
    </div>
</div>
</body>
</html>
';
    return $html;
}

// ==================== تنظیم Webhook ====================

function setWebhook() {
    $baseUrl = (isset($_SERVER['HTTPS']) ? 'https://' : 'http://') . $_SERVER['HTTP_HOST'];
    $webhookUrl = $baseUrl . '/webhook';
    $url = "https://api.telegram.org/bot" . BOT_TOKEN . "/setWebhook?url=" . urlencode($webhookUrl);
    $response = file_get_contents($url);
    $data = json_decode($response, true);
    
    $html = '
<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تنظیم Webhook</title>
    <style>
        body { background: #0f0c29; color: #fff; font-family: "Segoe UI", Tahoma, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .card { background: rgba(255,255,255,0.05); border-radius: 20px; padding: 30px; max-width: 600px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }
        h1 { color: ' . ($data['ok'] ? '#4ade80' : '#f87171') . '; }
        code { background: #1a1a2e; padding: 5px 10px; border-radius: 5px; color: #60a5fa; display: block; margin: 10px 0; word-break: break-all; }
        .btn { display: inline-block; background: #4f46e5; color: #fff; padding: 12px 24px; border-radius: 40px; text-decoration: none; margin-top: 15px; }
        .btn:hover { background: #4338ca; }
        .result { color: #aaa; text-align: right; margin-top: 15px; background: #1a1a2e; padding: 15px; border-radius: 10px; }
    </style>
</head>
<body>
<div class="card">
    <h1>' . ($data['ok'] ? '✅ Webhook تنظیم شد' : '❌ خطا در تنظیم Webhook') . '</h1>
    <p>آدرس Webhook:</p>
    <code>' . $webhookUrl . '</code>
    <div class="result">
        ' . json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) . '
    </div>
    <a href="/" class="btn">بازگشت به صفحه اصلی</a>
</div>
</body>
</html>
';
    return $html;
}

// ==================== اطلاعات Webhook ====================

function webhookInfo() {
    $url = "https://api.telegram.org/bot" . BOT_TOKEN . "/getWebhookInfo";
    $response = file_get_contents($url);
    $data = json_decode($response, true);
    
    header('Content-Type: application/json');
    echo json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

// ==================== ورودی اصلی ====================

$path = $_SERVER['REQUEST_URI'] ?? '/';
$path = parse_url($path, PHP_URL_PATH);

// مسیر Webhook (دریافت آپدیت‌ها)
if ($path === '/webhook' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = file_get_contents('php://input');
    $update = json_decode($input, true);
    if ($update) {
        processUpdate($update);
    }
    http_response_code(200);
    echo 'OK';
    exit;
}

// مسیر تنظیم Webhook
if ($path === '/setwebhook') {
    echo setWebhook();
    exit;
}

// مسیر اطلاعات Webhook
if ($path === '/webhook-info') {
    webhookInfo();
    exit;
}

// صفحه اصلی
echo renderHomePage();
