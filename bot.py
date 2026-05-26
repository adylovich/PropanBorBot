import asyncio, json, math, os, time
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, KeyboardButton, ReplyKeyboardMarkup,
                            ReplyKeyboardRemove, InlineKeyboardMarkup,
                            InlineKeyboardButton, CallbackQuery)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN    = "8555848969:AAFZHN2eKOv3Mfw6INGSA-gJTTCsRNTtznI"
ADMIN_IDS = [2313720, 7943821541]  # <- O'zingizni Telegram ID ni yozing (t.me/userinfobot dan oling)

bot = Bot(token=TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ══════════════════════════════════════════
#  AZS MA'LUMOTLARI
# ══════════════════════════════════════════
def load_azs():
    try:
        with open("azs.json", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_azs():
    with open("azs.json", "w", encoding="utf-8") as f:
        json.dump(AZS_LIST, f, ensure_ascii=False, indent=2)

AZS_LIST = load_azs()

user_langs   = {}
user_add_log = {}
user_upd_log = {}

LIMIT_ADD_COUNT = 2
LIMIT_ADD_SECS  = 7 * 24 * 3600
LIMIT_UPD_SECS  = 72 * 3600

# ══════════════════════════════════════════
#  TUMANLAR (barcha tumanlar, AZS bo'lmasa ham)
# ══════════════════════════════════════════
ALL_DISTRICTS = {
    "Toshkent shahar": [
        "Bektemir tumani", "Chilonzor tumani", "Hamza tumani",
        "Mirobod tumani", "Mirzo Ulug'bek tumani", "Olmazor tumani",
        "Sergeli tumani", "Shayxontohur tumani", "Uchtepa tumani",
        "Yakkasaroy tumani", "Yangihayot tumani", "Yunusobod tumani",
    ],
    "Toshkent viloyati": [
        "Angren shahri", "Bo'stonliq tumani", "Bo'ka tumani",
        "Chinoz tumani", "Chirchiq shahri", "Qibray tumani",
        "Nurafshon shahri", "Ohangaron tumani", "Olmaliq shahri",
        "Oqqo'rg'on tumani", "O'rtachirchiq tumani", "Parkent tumani",
        "Piskent tumani", "Toshkent tumani", "Uchtepa tumani (viloyat)",
        "Yangiyo'l tumani", "Yuqori Chirchiq tumani", "Zangiota tumani",
    ]
}

ALL_DISTRICTS_RU = {
    "г. Ташкент": [
        "Бектемирский р-н", "Чиланзарский р-н", "Хамзинский р-н",
        "Мирабадский р-н", "Мирзо-Улугбекский р-н", "Олмазарский р-н",
        "Сергелийский р-н", "Шайхантахурский р-н", "Учтепинский р-н",
        "Яккасарайский р-н", "Янгихаётский р-н", "Юнусабадский р-н",
    ],
    "Ташкентская область": [
        "г. Ангрен", "Бостанлыкский р-н", "Букинский р-н",
        "Чиназский р-н", "г. Чирчик", "Кибрайский р-н",
        "г. Нурафшон", "Ахангаранский р-н", "г. Алмалык",
        "Аккурганский р-н", "Уртачирчикский р-н", "Паркентский р-н",
        "Пскентский р-н", "Ташкентский р-н", "Учтепинский р-н (обл.)",
        "Янгиюльский р-н", "Верхнечирчикский р-н", "Зангиатинский р-н",
    ]
}

# Tuman ↔ region map (AZS qo'shishda aniqlash uchun)
DIST_TO_REGION = {}
for reg, dists in ALL_DISTRICTS.items():
    for d in dists:
        DIST_TO_REGION[d] = reg

# ══════════════════════════════════════════
#  REVERSE GEOCODING (lokatsiyadan tuman aniqlash)
# ══════════════════════════════════════════
async def get_district_from_coords(lat, lng):
    url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lng}&format=json&accept-language=uz"
    headers = {"User-Agent": "PropanBorBot/1.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()
                addr = data.get("address", {})
                district = (addr.get("county") or addr.get("suburb") or
                           addr.get("city_district") or addr.get("town") or "")
                city = addr.get("city") or addr.get("state_district") or ""
                state = addr.get("state") or ""
                return district, city, state
    except:
        return "", "", ""

# ══════════════════════════════════════════
#  GOOGLE SHEETS BACKUP
# ══════════════════════════════════════════
SHEETS_WEBHOOK = os.getenv("SHEETS_WEBHOOK", "")

async def backup_to_sheets(azs_data):
    if not SHEETS_WEBHOOK:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(SHEETS_WEBHOOK,
                json={"azs": azs_data},
                timeout=aiohttp.ClientTimeout(total=5))
    except:
        pass

# ══════════════════════════════════════════
#  TILLAR
# ══════════════════════════════════════════
TEXTS = {
    "uz": {
        "choose_lang": "🌐 Tilni tanlang:",
        "welcome": (
            "⛽ *PropanBorBot ga xush kelibsiz!*\n\n"
            "Bu bot Toshkent va viloyatidagi propan AZSlari haqida ma'lumot beradi.\n\n"
            "📍 Lokatsiyangizni yuboring — eng yaqin AZSni topamiz!\n\n"
            "🤝 *Botni rivojlantirishga yordam bering!*\n"
            "Bazamizda bo'lmagan AZSni qo'shing yoki narxni yangilang — "
            "minglab haydovchilarga yordam berasiz!"
        ),
        "nearest_title": "📍 *Sizga eng yaqin AZSlar:*\n\n",
        "prices_title":  "💰 *Narxlar:*\n\n",
        "help": (
            "ℹ️ *Yordam*\n\n"
            "📍 Lokatsiya → eng yaqin AZS\n"
            "📋 Barcha AZSlar → hudud/tuman bo'yicha\n"
            "💰 Narxlar → narxlar ro'yxati\n"
            "➕ AZS qo'shish → yangi AZS qo'shing\n"
            "✏️ Narx yangilash → narxni o'zgartiring\n\n"
            "🤝 Siz ham bazani to'ldirishga yordam bering!"
        ),
        "choose_region":  "🗺 Hududni tanlang:",
        "choose_dist":    "📍 Tumanni tanlang:",
        "no_azs_dist":    (
            "📭 *Bu tumandagi AZSlar hali bazaga kiritilmagan.*\n\n"
            "Agar siz bu hududdagi AZS haqida bilsangiz — "
            "➕ AZS qo'shish orqali bazaga qo'shing!\n"
            "Siz qo'shgan ma'lumot boshqalarga yordam beradi 🙏"
        ),
        "add_name":      "✏️ AZS nomini kiriting:\n(masalan: Sergeli 3, Yunusobod 5)",
        "add_loc":       "📍 AZS lokatsiyasini yuboring:",
        "add_loc_btn":   "📍 Lokatsiya yuborish",
        "add_confirm":   "📍 Bu AZS *{district}* ({region}) da joylashgan.\n\nTo'g'rimi?",
        "add_confirm_yes": "✅ Ha, to'g'ri",
        "add_confirm_no":  "✏️ Yo'q, o'zim belgilayman",
        "add_manual_dist": "📍 Tumanni tanlang:",
        "add_price":     "💰 Narxni kiriting (so'mda):\nMasalan: 6700",
        "add_hours":     "🕐 Ish vaqtini kiriting:\nMasalan: 08:00-22:00 yoki 24/7",
        "add_phone":     "📞 Telefon raqam (ixtiyoriy):\nYo'q bo'lsa — /skip yozing",
        "add_done":      "✅ *{name}* qo'shildi va moderatsiyaga yuborildi!\n💰 {price} so'm | 🕐 {hours}\n\nRahmat! Siz bazani boyitishga hissa qo'shdingiz 🙏",
        "add_limit":     "⏳ Siz bu hafta {count} ta AZS qo'shdingiz.\nKeyingi qo'shish: {days} kun {hours} soatdan so'ng.",
        "upd_choose":    "Qaysi AZS narxini yangilaysiz?",
        "upd_region_q":  "Qaysi hududdagi AZS?",
        "upd_price_q":   "💰 *{name}* uchun yangi narx (so'mda):",
        "upd_done":      "✅ Narx yangilandi!\n⛽ *{name}*\n{arrow} {old} → {new} so'm\n\nRahmat! 🙏",
        "upd_limit":     "⏳ Bu AZS narxini {hours} soat {mins} daqiqadan so'ng yangilay olasiz.",
        "err_price":     "❌ Faqat raqam kiriting. Masalan: 6700",
        "unknown":       "📋 Menyudan tanlang:",
        "unknown_price": "Noma'lum",
        "back":          "⬅️ Orqaga",
        "btn_nearest":   "📍 Yaqin AZS",
        "btn_all":       "📋 Barcha AZSlar",
        "btn_prices":    "💰 Narxlar",
        "btn_add":       "➕ AZS qo'shish",
        "btn_update":    "✏️ Narx yangilash",
        "btn_help":      "ℹ️ Yordam",
        "btn_lang":      "🌐 Til",
        "admin_new_azs": (
            "🆕 *Yangi AZS qo'shildi!*\n\n"
            "📍 *{name}*\n"
            "🗺 {region} / {district}\n"
            "💰 {price} so'm | 🕐 {hours}\n"
            "📞 {phone}\n"
            "👤 @{username}\n\n"
            "Tasdiqlaysizmi?"
        ),
        "admin_approve": "✅ Tasdiqlash",
        "admin_reject":  "❌ Rad etish",
        "approved_notif": "✅ Siz qo'shgan *{name}* AZS tasdiqlandi va bazaga qo'shildi!",
        "rejected_notif": "❌ Siz qo'shgan *{name}* AZS rad etildi.",
    },
    "ru": {
        "choose_lang": "🌐 Выберите язык:",
        "welcome": (
            "⛽ *Добро пожаловать в PropanBorBot!*\n\n"
            "Бот предоставляет информацию о пропановых АЗС Ташкента и области.\n\n"
            "📍 Отправьте локацию — найдём ближайшие АЗС!\n\n"
            "🤝 *Помогите развить бота!*\n"
            "Добавьте АЗС которой нет в базе или обновите цену — "
            "поможете тысячам водителей!"
        ),
        "nearest_title": "📍 *Ближайшие АЗС:*\n\n",
        "prices_title":  "💰 *Цены:*\n\n",
        "help": (
            "ℹ️ *Справка*\n\n"
            "📍 Локация → ближайшая АЗС\n"
            "📋 Все АЗС → по районам\n"
            "💰 Цены → список цен\n"
            "➕ Добавить АЗС → новая АЗС\n"
            "✏️ Обновить цену → изменить цену\n\n"
            "🤝 Помогите пополнить базу!"
        ),
        "choose_region":  "🗺 Выберите регион:",
        "choose_dist":    "📍 Выберите район:",
        "no_azs_dist":    (
            "📭 *АЗС в этом районе ещё не добавлены в базу.*\n\n"
            "Если вы знаете АЗС в этом районе — "
            "добавьте через ➕ Добавить АЗС!\n"
            "Ваша информация поможет другим 🙏"
        ),
        "add_name":      "✏️ Введите название АЗС:\n(например: Сергели 3)",
        "add_loc":       "📍 Отправьте локацию АЗС:",
        "add_loc_btn":   "📍 Отправить локацию",
        "add_confirm":   "📍 Эта АЗС находится в *{district}* ({region}).\n\nВерно?",
        "add_confirm_yes": "✅ Да, верно",
        "add_confirm_no":  "✏️ Нет, укажу сам",
        "add_manual_dist": "📍 Выберите район:",
        "add_price":     "💰 Введите цену (в сумах):\nНапример: 6700",
        "add_hours":     "🕐 Введите время работы:\nНапример: 08:00-22:00 или 24/7",
        "add_phone":     "📞 Телефон (необязательно):\nЕсли нет — /skip",
        "add_done":      "✅ *{name}* добавлена и отправлена на модерацию!\n💰 {price} сум | 🕐 {hours}\n\nСпасибо! Вы помогаете развивать базу 🙏",
        "add_limit":     "⏳ Вы добавили {count} АЗС на этой неделе.\nСледующее добавление: через {days} д. {hours} ч.",
        "upd_choose":    "Цену какой АЗС обновить?",
        "upd_region_q":  "Из какого региона АЗС?",
        "upd_price_q":   "💰 Новая цена для *{name}* (в сумах):",
        "upd_done":      "✅ Цена обновлена!\n⛽ *{name}*\n{arrow} {old} → {new} сум\n\nСпасибо! 🙏",
        "upd_limit":     "⏳ Цену этой АЗС можно обновить через {hours} ч. {mins} мин.",
        "err_price":     "❌ Введите только цифры. Например: 6700",
        "unknown":       "📋 Выберите из меню:",
        "unknown_price": "Неизвестно",
        "back":          "⬅️ Назад",
        "btn_nearest":   "📍 Ближайшая АЗС",
        "btn_all":       "📋 Все АЗС",
        "btn_prices":    "💰 Цены",
        "btn_add":       "➕ Добавить АЗС",
        "btn_update":    "✏️ Обновить цену",
        "btn_help":      "ℹ️ Справка",
        "btn_lang":      "🌐 Язык",
        "admin_new_azs": (
            "🆕 *Новая АЗС добавлена!*\n\n"
            "📍 *{name}*\n"
            "🗺 {region} / {district}\n"
            "💰 {price} сум | 🕐 {hours}\n"
            "📞 {phone}\n"
            "👤 @{username}\n\n"
            "Подтвердить?"
        ),
        "admin_approve": "✅ Подтвердить",
        "admin_reject":  "❌ Отклонить",
        "approved_notif": "✅ Добавленная вами АЗС *{name}* подтверждена!",
        "rejected_notif": "❌ Добавленная вами АЗС *{name}* отклонена.",
    }
}

def get_lang(uid): return user_langs.get(uid, "uz")
def t(uid, key, **kw):
    lang = get_lang(uid)
    txt  = TEXTS[lang].get(key, key)
    return txt.format(**kw) if kw else txt

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2-lat1); dlon = math.radians(lon2-lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))

def main_menu(uid):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t(uid,"btn_nearest"), request_location=True)],
        [KeyboardButton(text=t(uid,"btn_all")),    KeyboardButton(text=t(uid,"btn_prices"))],
        [KeyboardButton(text=t(uid,"btn_add")),    KeyboardButton(text=t(uid,"btn_update"))],
        [KeyboardButton(text=t(uid,"btn_help")),   KeyboardButton(text=t(uid,"btn_lang"))],
    ], resize_keyboard=True)

def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="lang_uz"),
        InlineKeyboardButton(text="🇷🇺 Русский",     callback_data="lang_ru")
    ]])

async def del_msg(msg: Message):
    try: await bot.delete_message(msg.chat.id, msg.message_id)
    except: pass

def check_add_limit(uid):
    now  = time.time()
    logs = [ts for ts in user_add_log.get(uid, []) if now - ts < LIMIT_ADD_SECS]
    user_add_log[uid] = logs
    if len(logs) >= LIMIT_ADD_COUNT:
        remain = LIMIT_ADD_SECS - (now - min(logs))
        return False, len(logs), int(remain//86400), int((remain%86400)//3600)
    return True, len(logs), 0, 0

def check_upd_limit(uid, azs_id):
    key = f"{uid}_{azs_id}"
    ts  = user_upd_log.get(key)
    if ts:
        remain = LIMIT_UPD_SECS - (time.time() - ts)
        if remain > 0:
            return False, int(remain//3600), int((remain%3600)//60)
    return True, 0, 0

# ══════════════════════════════════════════
#  FSM
# ══════════════════════════════════════════
class AddAZS(StatesGroup):
    name     = State()
    location = State()
    confirm  = State()
    price    = State()
    hours    = State()
    phone    = State()

class UpdatePrice(StatesGroup):
    choose_region = State()
    choose_azs    = State()
    price         = State()

# ══════════════════════════════════════════
#  /start
# ══════════════════════════════════════════
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    await del_msg(msg)
    await msg.answer("🌐 Tilni tanlang / Выберите язык:", reply_markup=lang_kb())

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    user_langs[uid] = call.data.split("_")[1]
    await call.message.delete()
    await call.message.answer(t(uid,"welcome"), parse_mode="Markdown",
        reply_markup=main_menu(uid))
    await call.answer()

@dp.message(F.text.in_(["🌐 Til","🌐 Язык"]))
async def change_lang(msg: Message):
    await del_msg(msg)
    await msg.answer("🌐 Tilni tanlang / Выберите язык:", reply_markup=lang_kb())

# ══════════════════════════════════════════
#  LOKATSIYA → YAQIN AZS
# ══════════════════════════════════════════
@dp.message(F.location)
async def handle_location(msg: Message, state: FSMContext):
    fsm = await state.get_state()
    if fsm and "location" in fsm:
        await add_location(msg, state)
        return
    uid  = msg.from_user.id
    await del_msg(msg)
    ulat, ulng = msg.location.latitude, msg.location.longitude
    coords = [a for a in AZS_LIST if a.get("lat") and a.get("lng")]
    ranked = sorted(coords, key=lambda a: haversine(ulat, ulng, a["lat"], a["lng"]))[:5]
    if not ranked:
        await msg.answer("❌ Bazada hali AZS yo'q. Birinchi bo'lib qo'shing! ➕")
        return
    text = t(uid, "nearest_title")
    for i, a in enumerate(ranked, 1):
        dist = haversine(ulat, ulng, a["lat"], a["lng"])
        ds   = f"{int(dist*1000)}м" if dist < 1 else f"{dist:.1f}km"
        si   = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
        pr   = f"{a['price']:,} so'm".replace(","," ") if a.get("price") else t(uid,"unknown_price")
        ph   = f"\n   📞 {a['phone']}" if a.get("phone") else ""
        text += f"{i}. {si} *{a['name']}*\n   📏 {ds} | 💰 {pr} | 🕐 {a.get('hours','—')}{ph}\n\n"
    btns = [[InlineKeyboardButton(text=f"🗺 {a['name']}",
             url=a.get("url", f"https://maps.google.com/?q={a['lat']},{a['lng']}"))]
            for a in ranked]
    await msg.answer(text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await msg.answer("📋 Asosiy menyu:", reply_markup=main_menu(uid))

# ══════════════════════════════════════════
#  BARCHA AZSLAR → HUDUD → TUMAN → RO'YXAT
# ══════════════════════════════════════════
@dp.message(F.text.in_(["📋 Barcha AZSlar","📋 Все АЗС"]))
async def all_azs(msg: Message):
    uid  = msg.from_user.id
    await del_msg(msg)
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    regions = list(dct.keys())
    btns = [[InlineKeyboardButton(text=r, callback_data=f"areg_{i}")]
            for i, r in enumerate(regions)]
    await msg.answer(t(uid,"choose_region"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data.startswith("areg_"))
async def azs_region(call: CallbackQuery):
    uid  = call.from_user.id
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    ridx = int(call.data.split("_")[1])
    region = list(dct.keys())[ridx]
    dists  = dct[region]
    btns = [[InlineKeyboardButton(text=d, callback_data=f"adist_{ridx}_{j}")]
            for j, d in enumerate(dists)]
    btns.append([InlineKeyboardButton(text=t(uid,"back"), callback_data="aback_reg")])
    await call.message.edit_text(t(uid,"choose_dist"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@dp.callback_query(F.data == "aback_reg")
async def azs_back_reg(call: CallbackQuery):
    uid  = call.from_user.id
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    btns = [[InlineKeyboardButton(text=r, callback_data=f"areg_{i}")]
            for i, r in enumerate(dct.keys())]
    await call.message.edit_text(t(uid,"choose_region"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@dp.callback_query(F.data.startswith("adist_"))
async def azs_district(call: CallbackQuery):
    uid  = call.from_user.id
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    _, ridx, didx = call.data.split("_")
    region = list(dct.keys())[int(ridx)]
    dist   = dct[region][int(didx)]

    # Tuman nomi bo'yicha AZS qidirish
    azs_here = [a for a in AZS_LIST if
                str(a.get("district","")).lower() == dist.lower() or
                (str(a.get("region","")).lower() == region.lower() and
                not a.get("district"))]

    if not azs_here:
        btns = [[InlineKeyboardButton(text=t(uid,"back"), callback_data=f"areg_{ridx}")]]
        await call.message.edit_text(
            f"📍 *{dist}*\n\n{t(uid,'no_azs_dist')}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
        await call.answer()
        return

    text = f"📍 *{dist}*\n\n"
    btns = []
    for a in azs_here:
        si = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
        pr = f"{a['price']:,}".replace(","," ") if a.get("price") else "—"
        ph = f" | 📞 {a['phone']}" if a.get("phone") else ""
        text += f"{si} *{a['name']}*\n💰 {pr} so'm | 🕐 {a.get('hours','—')}{ph}\n\n"
        if a.get("url") or (a.get("lat") and a.get("lng")):
            url = a.get("url") or f"https://maps.google.com/?q={a['lat']},{a['lng']}"
            btns.append([InlineKeyboardButton(text=f"🗺 {a['name']}", url=url)])

    btns.append([InlineKeyboardButton(text=t(uid,"back"), callback_data=f"areg_{ridx}")])
    await call.message.edit_text(text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

# ══════════════════════════════════════════
#  NARXLAR → HUDUD → TUMAN
# ══════════════════════════════════════════
@dp.message(F.text.in_(["💰 Narxlar","💰 Цены"]))
async def prices(msg: Message):
    uid  = msg.from_user.id
    await del_msg(msg)
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    btns = [[InlineKeyboardButton(text=r, callback_data=f"preg_{i}")]
            for i, r in enumerate(dct.keys())]
    await msg.answer(t(uid,"prices_title") + t(uid,"choose_region"),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data.startswith("preg_"))
async def prices_region(call: CallbackQuery):
    uid  = call.from_user.id
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    ridx = int(call.data.split("_")[1])
    region = list(dct.keys())[ridx]
    azs_in_region = [a for a in AZS_LIST
                     if a.get("price") and
                     str(a.get("region","")).lower() in [region.lower(),
                     list(ALL_DISTRICTS.keys())[ridx].lower()]]
    if not azs_in_region:
        await call.answer("Bu hududda narx ma'lumoti yo'q", show_alert=True)
        return
    srt  = sorted(azs_in_region, key=lambda x: x["price"])
    text = f"💰 *{region}*\n\n"
    for a in srt:
        si    = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
        dist  = f" ({a['district']})" if a.get("district") else ""
        text += f"{si} *{a['price']:,}* so'm — {a['name']}{dist}\n".replace(","," ")
    btns = [[InlineKeyboardButton(text=t(uid,"back"), callback_data="prices_back")]]
    await call.message.edit_text(text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@dp.callback_query(F.data == "prices_back")
async def prices_back(call: CallbackQuery):
    uid  = call.from_user.id
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    btns = [[InlineKeyboardButton(text=r, callback_data=f"preg_{i}")]
            for i, r in enumerate(dct.keys())]
    await call.message.edit_text(t(uid,"prices_title") + t(uid,"choose_region"),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

# ══════════════════════════════════════════
#  YORDAM
# ══════════════════════════════════════════
@dp.message(F.text.in_(["ℹ️ Yordam","ℹ️ Справка"]))
async def help_cmd(msg: Message):
    uid = msg.from_user.id
    await del_msg(msg)
    await msg.answer(t(uid,"help"), parse_mode="Markdown")

# ══════════════════════════════════════════
#  AZS QO'SHISH
# ══════════════════════════════════════════
@dp.message(F.text.in_(["➕ AZS qo'shish","➕ Добавить АЗС"]))
async def add_start(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await del_msg(msg)
    ok, count, days, hours = check_add_limit(uid)
    if not ok:
        await msg.answer(t(uid,"add_limit", count=count, days=days, hours=hours))
        return
    await state.set_state(AddAZS.name)
    await msg.answer(t(uid,"add_name"), reply_markup=ReplyKeyboardRemove())

@dp.message(AddAZS.name)
async def add_name(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await del_msg(msg)
    await state.update_data(name=msg.text)
    await state.set_state(AddAZS.location)
    await msg.answer(t(uid,"add_loc"), reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(uid,"add_loc_btn"), request_location=True)]],
        resize_keyboard=True))

async def add_location(msg: Message, state: FSMContext):
    uid  = msg.from_user.id
    lat  = msg.location.latitude
    lng  = msg.location.longitude
    await state.update_data(lat=lat, lng=lng)

    # Reverse geocoding
    district, city, state_name = await get_district_from_coords(lat, lng)
    await state.update_data(district=district, city=city)

    if district:
        await state.set_state(AddAZS.confirm)
        region = DIST_TO_REGION.get(district, city or state_name)
        btns = [[
            InlineKeyboardButton(text=t(uid,"add_confirm_yes"), callback_data="loc_yes"),
            InlineKeyboardButton(text=t(uid,"add_confirm_no"),  callback_data="loc_no"),
        ]]
        await msg.answer(
            t(uid,"add_confirm", district=district, region=region),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    else:
        await ask_price(msg, state, uid)

@dp.callback_query(F.data == "loc_yes")
async def loc_confirmed(call: CallbackQuery, state: FSMContext):
    uid  = call.from_user.id
    data = await state.get_data()
    district = data.get("district","")
    region   = DIST_TO_REGION.get(district, data.get("city",""))
    await state.update_data(district=district, region=region)
    await call.message.delete()
    await state.set_state(AddAZS.price)
    await call.message.answer(t(uid,"add_price"), reply_markup=ReplyKeyboardRemove())
    await call.answer()

@dp.callback_query(F.data == "loc_no")
async def loc_manual(call: CallbackQuery, state: FSMContext):
    uid  = call.from_user.id
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    btns = []
    for ridx, (reg, dists) in enumerate(dct.items()):
        btns.append([InlineKeyboardButton(text=f"📍 {reg}", callback_data=f"mreg_{ridx}")])
    await call.message.edit_text(t(uid,"add_manual_dist"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@dp.callback_query(F.data.startswith("mreg_"))
async def manual_region(call: CallbackQuery, state: FSMContext):
    uid  = call.from_user.id
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    ridx = int(call.data.split("_")[1])
    region = list(dct.keys())[ridx]
    dists  = dct[region]
    btns = [[InlineKeyboardButton(text=d, callback_data=f"mdist_{ridx}_{j}")]
            for j, d in enumerate(dists)]
    await call.message.edit_text(t(uid,"add_manual_dist"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@dp.callback_query(F.data.startswith("mdist_"))
async def manual_district(call: CallbackQuery, state: FSMContext):
    uid  = call.from_user.id
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    _, ridx, didx = call.data.split("_")
    region   = list(dct.keys())[int(ridx)]
    district = dct[region][int(didx)]
    await state.update_data(region=region, district=district)
    await call.message.delete()
    await state.set_state(AddAZS.price)
    await call.message.answer(t(uid,"add_price"), reply_markup=ReplyKeyboardRemove())
    await call.answer()

async def ask_price(msg, state, uid):
    await state.set_state(AddAZS.price)
    await msg.answer(t(uid,"add_price"), reply_markup=ReplyKeyboardRemove())

@dp.message(AddAZS.price)
async def add_price_h(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await del_msg(msg)
    try:
        price = int(msg.text.replace(" ","").replace(",",""))
        await state.update_data(price=price)
        await state.set_state(AddAZS.hours)
        await msg.answer(t(uid,"add_hours"), reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="24/7")]], resize_keyboard=True))
    except:
        await msg.answer(t(uid,"err_price"))

@dp.message(AddAZS.hours)
async def add_hours_h(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await del_msg(msg)
    await state.update_data(hours=msg.text)
    await state.set_state(AddAZS.phone)
    await msg.answer(t(uid,"add_phone"), reply_markup=ReplyKeyboardRemove())

@dp.message(AddAZS.phone)
async def add_phone_h(msg: Message, state: FSMContext):
    uid  = msg.from_user.id
    await del_msg(msg)
    phone = "" if msg.text == "/skip" else msg.text
    data  = await state.get_data()
    await state.clear()

    # Pending AZS (moderatsiya kutadi)
    pending = {
        "id":       f"p_{uid}_{int(time.time())}",
        "name":     data["name"],
        "price":    data["price"],
        "status":   "Ochiq",
        "hours":    data["hours"],
        "phone":    phone,
        "region":   data.get("region",""),
        "district": data.get("district",""),
        "lat":      data["lat"],
        "lng":      data["lng"],
        "url":      f"https://maps.google.com/?q={data['lat']},{data['lng']}",
        "added_by": uid,
        "username": msg.from_user.username or str(uid),
        "approved": False,
    }

    user_add_log.setdefault(uid, []).append(time.time())

    await msg.answer(
        t(uid,"add_done", name=data["name"],
          price=f"{data['price']:,}".replace(","," "),
          hours=data["hours"]),
        parse_mode="Markdown", reply_markup=main_menu(uid))

    # Admin ga yuborish
    if ADMIN_IDS:
        admin_text = t(uid,"admin_new_azs",
            name=data["name"],
            region=data.get("region","—"),
            district=data.get("district","—"),
            price=f"{data['price']:,}".replace(","," "),
            hours=data["hours"],
            phone=phone or "—",
            username=msg.from_user.username or str(uid))

        pending_json = json.dumps(pending, ensure_ascii=False)
        btns = [[
            InlineKeyboardButton(text=t(uid,"admin_approve"),
                callback_data=f"approve_{uid}"),
            InlineKeyboardButton(text=t(uid,"admin_reject"),
                callback_data=f"reject_{uid}"),
        ]]
        # Pending ni vaqtincha saqlaymiz
        if not hasattr(dp, "pending_azs"):
            dp.pending_azs = {}
        dp.pending_azs[str(uid)] = pending

        for _admin_id in ADMIN_IDS:
            await bot.send_message(_admin_id, admin_text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    else:
        # Admin ID yo'q — darhol qo'shamiz
        AZS_LIST.append(pending)
        save_azs()

# ══════════════════════════════════════════
#  ADMIN: TASDIQLASH / RAD ETISH
# ══════════════════════════════════════════
@dp.callback_query(F.data.startswith("approve_"))
async def admin_approve(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("❌ Ruxsat yo'q"); return
    user_id = call.data.split("_")[1]
    pending = getattr(dp, "pending_azs", {}).get(user_id)
    if not pending:
        await call.answer("❌ Ma'lumot topilmadi"); return
    pending["approved"] = True
    AZS_LIST.append(pending)
    save_azs()
    await call.message.edit_text(f"✅ Tasdiqlandi: *{pending['name']}*", parse_mode="Markdown")
    try:
        await bot.send_message(int(user_id),
            t(int(user_id),"approved_notif", name=pending["name"]),
            parse_mode="Markdown")
    except: pass
    await call.answer("✅ Tasdiqlandi!")

@dp.callback_query(F.data.startswith("reject_"))
async def admin_reject(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("❌ Ruxsat yo'q"); return
    user_id = call.data.split("_")[1]
    pending = getattr(dp, "pending_azs", {}).get(user_id)
    name = pending["name"] if pending else "AZS"
    await call.message.edit_text(f"❌ Rad etildi: *{name}*", parse_mode="Markdown")
    try:
        await bot.send_message(int(user_id),
            t(int(user_id),"rejected_notif", name=name),
            parse_mode="Markdown")
    except: pass
    await call.answer("❌ Rad etildi!")

# ══════════════════════════════════════════
#  NARX YANGILASH
# ══════════════════════════════════════════
@dp.message(F.text.in_(["✏️ Narx yangilash","✏️ Обновить цену"]))
async def update_start(msg: Message, state: FSMContext):
    uid  = msg.from_user.id
    await del_msg(msg)
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    btns = [[InlineKeyboardButton(text=r, callback_data=f"ureg_{i}")]
            for i, r in enumerate(dct.keys())]
    await msg.answer(t(uid,"upd_region_q"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data.startswith("ureg_"))
async def upd_region(call: CallbackQuery, state: FSMContext):
    uid  = call.from_user.id
    ridx = int(call.data.split("_")[1])
    lang = get_lang(uid)
    dct  = ALL_DISTRICTS if lang == "uz" else ALL_DISTRICTS_RU
    region = list(dct.keys())[ridx]
    azs_in_reg = [a for a in AZS_LIST
                  if str(a.get("region","")).lower() in [
                      region.lower(),
                      list(ALL_DISTRICTS.keys())[ridx].lower()]]
    if not azs_in_reg:
        await call.answer("Bu hududda AZS yo'q", show_alert=True); return
    btns = [[InlineKeyboardButton(
        text=f"{'🟢' if a['status']=='Ochiq' else '🔴'} {a['name']} — {a.get('price','?')} so'm",
        callback_data=f"upd_{i}")] for i, a in enumerate(AZS_LIST)
        if str(a.get("region","")).lower() in [region.lower(),
           list(ALL_DISTRICTS.keys())[ridx].lower()]]
    await call.message.edit_text(t(uid,"upd_choose"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@dp.callback_query(F.data.startswith("upd_"))
async def choose_azs_cb(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    idx = int(call.data.split("_")[1])
    azs = AZS_LIST[idx]
    ok, hours, mins = check_upd_limit(uid, azs["id"])
    if not ok:
        await call.answer(t(uid,"upd_limit",hours=hours,mins=mins), show_alert=True)
        return
    await state.update_data(idx=idx)
    await state.set_state(UpdatePrice.price)
    await call.message.edit_text(t(uid,"upd_price_q",name=azs["name"]), parse_mode="Markdown")
    await call.answer()

@dp.message(UpdatePrice.price)
async def update_price_h(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await del_msg(msg)
    try:
        data  = await state.get_data()
        idx   = data["idx"]
        old   = AZS_LIST[idx].get("price", 0)
        new   = int(msg.text.replace(" ","").replace(",",""))
        AZS_LIST[idx]["price"] = new
        save_azs()
        user_upd_log[f"{uid}_{AZS_LIST[idx]['id']}"] = time.time()
        await state.clear()
        arrow = "📈" if new > old else "📉" if new < old else "➡️"
        await msg.answer(
            t(uid,"upd_done", name=AZS_LIST[idx]["name"], arrow=arrow,
              old=f"{old:,}".replace(","," "),
              new=f"{new:,}".replace(","," ")),
            parse_mode="Markdown", reply_markup=main_menu(uid))
    except:
        await msg.answer(t(uid,"err_price"))

# ══════════════════════════════════════════
#  NOMA'LUM
# ══════════════════════════════════════════
@dp.message()
async def unknown(msg: Message):
    uid = msg.from_user.id
    await del_msg(msg)
    await msg.answer(t(uid,"unknown"), reply_markup=main_menu(uid))

# ══════════════════════════════════════════
#  ISHGA TUSHIRISH
# ══════════════════════════════════════════
async def main():
    print("PropanBorBot v3 ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
