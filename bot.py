import asyncio, json, math, os, time
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, KeyboardButton, ReplyKeyboardMarkup,
                            ReplyKeyboardRemove, InlineKeyboardMarkup,
                            InlineKeyboardButton, CallbackQuery)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = os.getenv("BOT_TOKEN", "")
bot = Bot(token=TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ══════════════════════════════════════════
#  MAʼLUMOTLAR
# ══════════════════════════════════════════
with open("azs.json", encoding="utf-8") as f:
    AZS_LIST = json.load(f)

# Foydalanuvchi tillari va limitlar
user_langs   = {}   # uid → "uz"/"ru"
user_add_log = {}   # uid → [timestamp, timestamp, ...]  (AZS qo'shish)
user_upd_log = {}   # uid+azs_id → timestamp  (narx yangilash)

LIMIT_ADD_COUNT = 2          # haftada nechta AZS qo'shish
LIMIT_ADD_SECS  = 7*24*3600  # 1 hafta
LIMIT_UPD_SECS  = 72*3600    # 72 soat

# ══════════════════════════════════════════
#  TUMANLAR STRUKTURASI
# ══════════════════════════════════════════
DISTRICTS = {
    "uz": {
        "Toshkent shahar": {
            "Yunusobod tumani":   ["1"],
            "Olmazor tumani":     ["2", "3"],
            "Bektemir tumani":    ["5"],
            "Yashnobod tumani":   ["6", "7"],
            "Sergeli tumani":     ["8", "10", "11", "11a"],
            "Yangihayot tumani":  ["11b"],
        },
        "Toshkent viloyati": {
            "Zangiota tumani":       ["4", "9", "12", "13/2", "15", "—Jambul"],
            "Qibray tumani":         ["19", "—Kibray"],
            "Bo'stonliq tumani":     ["20"],
            "O'rtachirchiq tumani":  ["14", "—Toytepa"],
            "Chirchiq shahri":       ["—Chirchiq"],
            "Angren shahri":         ["—Angren"],
            "Ohangaron tumani":      ["—Ohangaron"],
            "Olmaliq shahri":        ["—Olmaliq"],
            "Pskent tumani":         ["—Pskent"],
            "Chinoz tumani":         ["—Chinoz"],
        }
    },
    "ru": {
        "г. Ташкент": {
            "Юнусабадский р-н":  ["1"],
            "Олмазарский р-н":   ["2", "3"],
            "Бектемирский р-н":  ["5"],
            "Яшнободский р-н":   ["6", "7"],
            "Сергелийский р-н":  ["8", "10", "11", "11a"],
            "Янгихаётский р-н":  ["11b"],
        },
        "Ташкентская область": {
            "Зангиатинский р-н":     ["4", "9", "12", "13/2", "15", "—Jambul"],
            "Кибрайский р-н":        ["19", "—Kibray"],
            "Бостанлыкский р-н":     ["20"],
            "Уртачирчикский р-н":    ["14", "—Toytepa"],
            "г. Чирчик":             ["—Chirchiq"],
            "г. Ангрен":             ["—Angren"],
            "Ахангаранский р-н":     ["—Ohangaron"],
            "г. Алмалык":            ["—Olmaliq"],
            "Паркентский р-н":       ["—Pskent"],
            "Чиназский р-н":         ["—Chinoz"],
        }
    }
}

# ══════════════════════════════════════════
#  TILLAR
# ══════════════════════════════════════════
TEXTS = {
    "uz": {
        "choose_lang":   "🌐 Tilni tanlang:",
        "welcome":       "⛽ *PropanBorBot* — Propan AZSlari haqida ma'lumot!\n\n📍 Lokatsiyangizni yuboring — eng yaqin AZSni topamiz!",
        "nearest_title": "📍 *Sizga eng yaqin AZSlar:*\n\n",
        "prices_title":  "💰 *Narxlar (arzondan qimmatga):*\n\n",
        "help":          "ℹ️ *Yordam*\n\n📍 Lokatsiya → eng yaqin AZS\n📋 Barcha AZSlar → ro'yxat\n💰 Narxlar → narxlar\n➕ AZS qo'shish → yangi AZS\n✏️ Narx yangilash → narxni o'zgartirish",
        "choose_region": "🗺 Hududni tanlang:",
        "choose_dist":   "📍 Tumanni tanlang:",
        "no_azs":        "❌ Bu tumanda hozircha AZS yo'q.",
        "add_name":      "✏️ AZS nomini kiriting:",
        "add_loc":       "📍 AZS lokatsiyasini yuboring:",
        "add_price":     "💰 Narxni kiriting (so'mda):\nMasalan: 6700",
        "add_hours":     "🕐 Ish vaqti:\nMasalan: 08:00-22:00 yoki 24/7",
        "add_phone":     "📞 Telefon (ixtiyoriy):\nYo'q bo'lsa → /skip",
        "add_region_q":  "🌆 Hudud:",
        "add_done":      "✅ *{name}* qo'shildi!\n💰 {price} so'm | 🕐 {hours}",
        "add_limit":     "⏳ Siz bu hafta {count} ta AZS qo'shdingiz. Keyingi qo'shish: {days} kun {hours} soatdan so'ng.",
        "upd_choose":    "Qaysi AZS narxini yangilaysiz?",
        "upd_price_q":   "💰 *{name}* uchun yangi narx (so'mda):",
        "upd_done":      "✅ Narx yangilandi!\n⛽ *{name}*\n{arrow} {old} → {new} so'm",
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
        "region_city":   "Toshkent shahar",
        "region_vil":    "Toshkent viloyati",
    },
    "ru": {
        "choose_lang":   "🌐 Выберите язык:",
        "welcome":       "⛽ *PropanBorBot* — Информация о пропановых АЗС!\n\n📍 Отправьте локацию — найдём ближайшие АЗС!",
        "nearest_title": "📍 *Ближайшие АЗС:*\n\n",
        "prices_title":  "💰 *Цены (от дешёвых к дорогим):*\n\n",
        "help":          "ℹ️ *Справка*\n\n📍 Локация → ближайшая АЗС\n📋 Все АЗС → список\n💰 Цены → список цен\n➕ Добавить АЗС → новая АЗС\n✏️ Обновить цену → изменить цену",
        "choose_region": "🗺 Выберите регион:",
        "choose_dist":   "📍 Выберите район:",
        "no_azs":        "❌ В этом районе пока нет АЗС.",
        "add_name":      "✏️ Введите название АЗС:",
        "add_loc":       "📍 Отправьте локацию АЗС:",
        "add_price":     "💰 Введите цену (в сумах):\nНапример: 6700",
        "add_hours":     "🕐 Время работы:\nНапример: 08:00-22:00 или 24/7",
        "add_phone":     "📞 Телефон (необязательно):\nЕсли нет → /skip",
        "add_region_q":  "🌆 Регион:",
        "add_done":      "✅ *{name}* добавлена!\n💰 {price} сум | 🕐 {hours}",
        "add_limit":     "⏳ Вы добавили {count} АЗС на этой неделе. Следующее добавление: через {days} д. {hours} ч.",
        "upd_choose":    "Цену какой АЗС обновить?",
        "upd_price_q":   "💰 Новая цена для *{name}* (в сумах):",
        "upd_done":      "✅ Цена обновлена!\n⛽ *{name}*\n{arrow} {old} → {new} сум",
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
        "region_city":   "г. Ташкент",
        "region_vil":    "Ташкентская область",
    }
}

def get_lang(uid): return user_langs.get(uid, "uz")
def t(uid, key, **kw):
    lang = get_lang(uid)
    txt  = TEXTS[lang].get(key, key)
    return txt.format(**kw) if kw else txt

def save_azs():
    with open("azs.json", "w", encoding="utf-8") as f:
        json.dump(AZS_LIST, f, ensure_ascii=False, indent=2)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2-lat1); dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R*2*math.asin(math.sqrt(a))

def main_menu(uid):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t(uid,"btn_nearest"), request_location=True)],
        [KeyboardButton(text=t(uid,"btn_all")),   KeyboardButton(text=t(uid,"btn_prices"))],
        [KeyboardButton(text=t(uid,"btn_add")),   KeyboardButton(text=t(uid,"btn_update"))],
        [KeyboardButton(text=t(uid,"btn_help")),  KeyboardButton(text=t(uid,"btn_lang"))],
    ], resize_keyboard=True)

def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek tili", callback_data="lang_uz"),
         InlineKeyboardButton(text="🇷🇺 Русский",     callback_data="lang_ru")]
    ])

async def del_msg(msg: Message):
    try: await bot.delete_message(msg.chat.id, msg.message_id)
    except: pass

# ══════════════════════════════════════════
#  FSM
# ══════════════════════════════════════════
class AddAZS(StatesGroup):
    name=State(); location=State(); price=State()
    hours=State(); phone=State(); region=State()

class UpdatePrice(StatesGroup):
    price=State()

# ══════════════════════════════════════════
#  /start — TIL TANLASH
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
    await call.message.answer(t(uid,"welcome"), parse_mode="Markdown", reply_markup=main_menu(uid))
    await call.answer()

@dp.message(F.text.in_(["🌐 Til", "🌐 Язык"]))
async def change_lang(msg: Message):
    await del_msg(msg)
    await msg.answer("🌐 Tilni tanlang / Выберите язык:", reply_markup=lang_kb())

# ══════════════════════════════════════════
#  LOKATSIYA → YAQIN AZS
# ══════════════════════════════════════════
@dp.message(F.location)
async def nearest_azs(msg: Message, state: FSMContext):
    fsm = await state.get_state()
    if fsm == AddAZS.location:
        await add_location(msg, state); return
    uid = msg.from_user.id
    await del_msg(msg)
    ulat, ulng = msg.location.latitude, msg.location.longitude
    coords = [a for a in AZS_LIST if a.get("lat") and a.get("lng")]
    ranked = sorted(coords, key=lambda a: haversine(ulat, ulng, a["lat"], a["lng"]))[:5]
    text = t(uid,"nearest_title")
    for i,a in enumerate(ranked,1):
        dist = haversine(ulat, ulng, a["lat"], a["lng"])
        ds   = f"{dist*1000:.0f}м" if dist<1 else f"{dist:.1f}km"
        si   = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
        pr   = f"{a['price']:,} so'm".replace(","," ") if a.get("price") else t(uid,"unknown_price")
        ph   = f"\n📞 {a['phone']}" if a.get("phone") else ""
        text += f"{i}. {si} *{a['name']}*\n   📏 {ds} | 💰 {pr} | 🕐 {a.get('hours','—')}{ph}\n\n"
    btns = [[InlineKeyboardButton(text=f"🗺 {a['name']}",
             url=a.get("url",f"https://maps.google.com/?q={a['lat']},{a['lng']}"))] for a in ranked]
    await msg.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

# ══════════════════════════════════════════
#  BARCHA AZSLAR → HUDUD → TUMAN → RO'YXAT
# ══════════════════════════════════════════
@dp.message(F.text.in_(["📋 Barcha AZSlar","📋 Все АЗС"]))
async def all_azs(msg: Message):
    uid = msg.from_user.id
    await del_msg(msg)
    lang = get_lang(uid)
    regions = list(DISTRICTS[lang].keys())
    btns = [[InlineKeyboardButton(text=r, callback_data=f"reg_{i}")] for i,r in enumerate(regions)]
    await msg.answer(t(uid,"choose_region"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data.startswith("reg_"))
async def choose_region(call: CallbackQuery):
    uid  = call.from_user.id
    lang = get_lang(uid)
    idx  = int(call.data.split("_")[1])
    region = list(DISTRICTS[lang].keys())[idx]
    dists  = list(DISTRICTS[lang][region].keys())
    btns = [[InlineKeyboardButton(text=d, callback_data=f"dist_{idx}_{j}")] for j,d in enumerate(dists)]
    btns.append([InlineKeyboardButton(text=t(uid,"back"), callback_data="back_regions")])
    await call.message.edit_text(t(uid,"choose_dist"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@dp.callback_query(F.data == "back_regions")
async def back_regions(call: CallbackQuery):
    uid  = call.from_user.id
    lang = get_lang(uid)
    regions = list(DISTRICTS[lang].keys())
    btns = [[InlineKeyboardButton(text=r, callback_data=f"reg_{i}")] for i,r in enumerate(regions)]
    await call.message.edit_text(t(uid,"choose_region"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

@dp.callback_query(F.data.startswith("dist_"))
async def show_district(call: CallbackQuery):
    uid  = call.from_user.id
    lang = get_lang(uid)
    _, reg_idx, dist_idx = call.data.split("_")
    region = list(DISTRICTS[lang].keys())[int(reg_idx)]
    dist   = list(DISTRICTS[lang][region].keys())[int(dist_idx)]
    ids    = DISTRICTS[lang][region][dist]
    azs_in_dist = [a for a in AZS_LIST if str(a.get("id","")) in ids]

    if not azs_in_dist:
        await call.answer(t(uid,"no_azs"), show_alert=True); return

    text = f"📍 *{dist}*\n\n"
    btns = []
    for a in azs_in_dist:
        si = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
        pr = f"{a['price']:,}".replace(","," ") if a.get("price") else "—"
        ph = f" | 📞{a['phone']}" if a.get("phone") else ""
        text += f"{si} *{a['name']}*\n💰 {pr} so'm | 🕐 {a.get('hours','—')}{ph}\n\n"
        if a.get("url"):
            btns.append([InlineKeyboardButton(text=f"🗺 {a['name']}",
                url=a["url"])])

    btns.append([InlineKeyboardButton(text=t(uid,"back"), callback_data=f"reg_{reg_idx}")])
    await call.message.edit_text(text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await call.answer()

# ══════════════════════════════════════════
#  NARXLAR
# ══════════════════════════════════════════
@dp.message(F.text.in_(["💰 Narxlar","💰 Цены"]))
async def prices(msg: Message):
    uid = msg.from_user.id
    await del_msg(msg)
    srt  = sorted([a for a in AZS_LIST if a.get("price")], key=lambda x: x["price"])
    text = t(uid,"prices_title")
    for a in srt:
        si = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
        text += f"{si} {a['price']:,} so'm — {a['name']}\n".replace(","," ")
    await msg.answer(text, parse_mode="Markdown")

# ══════════════════════════════════════════
#  YORDAM
# ══════════════════════════════════════════
@dp.message(F.text.in_(["ℹ️ Yordam","ℹ️ Справка"]))
async def help_cmd(msg: Message):
    uid = msg.from_user.id
    await del_msg(msg)
    await msg.answer(t(uid,"help"), parse_mode="Markdown")

# ══════════════════════════════════════════
#  AZS QO'SHISH + LIMIT
# ══════════════════════════════════════════
def check_add_limit(uid):
    now  = time.time()
    logs = user_add_log.get(uid, [])
    logs = [ts for ts in logs if now - ts < LIMIT_ADD_SECS]
    user_add_log[uid] = logs
    if len(logs) >= LIMIT_ADD_COUNT:
        oldest   = min(logs)
        remain   = LIMIT_ADD_SECS - (now - oldest)
        days     = int(remain // 86400)
        hours    = int((remain % 86400) // 3600)
        return False, len(logs), days, hours
    return True, len(logs), 0, 0

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
        keyboard=[[KeyboardButton(text="📍 Lokatsiya", request_location=True)]],
        resize_keyboard=True))

async def add_location(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await state.update_data(lat=msg.location.latitude, lng=msg.location.longitude)
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
    uid = msg.from_user.id
    await del_msg(msg)
    await state.update_data(phone="" if msg.text=="/skip" else msg.text)
    await state.set_state(AddAZS.region)
    await msg.answer(t(uid,"add_region_q"), reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Toshkent shahar")],
                  [KeyboardButton(text="Toshkent viloyati")]], resize_keyboard=True))

@dp.message(AddAZS.region)
async def add_region_h(msg: Message, state: FSMContext):
    uid  = msg.from_user.id
    await del_msg(msg)
    data = await state.get_data()
    new_azs = {
        "id":     f"u{len(AZS_LIST)+1}",
        "name":   data["name"],
        "price":  data["price"],
        "status": "Ochiq",
        "hours":  data["hours"],
        "phone":  data.get("phone",""),
        "region": msg.text,
        "lat":    data["lat"],
        "lng":    data["lng"],
        "url":    f"https://maps.google.com/?q={data['lat']},{data['lng']}",
        "note":   f"@{msg.from_user.username or uid}"
    }
    AZS_LIST.append(new_azs)
    save_azs()
    user_add_log.setdefault(uid,[]).append(time.time())
    await state.clear()
    await msg.answer(t(uid,"add_done",
        name=data["name"],
        price=f"{data['price']:,}".replace(","," "),
        hours=data["hours"]),
        parse_mode="Markdown", reply_markup=main_menu(uid))

# ══════════════════════════════════════════
#  NARX YANGILASH + LIMIT
# ══════════════════════════════════════════
def check_upd_limit(uid, azs_id):
    key = f"{uid}_{azs_id}"
    ts  = user_upd_log.get(key)
    if ts:
        remain = LIMIT_UPD_SECS - (time.time() - ts)
        if remain > 0:
            hours = int(remain // 3600)
            mins  = int((remain % 3600) // 60)
            return False, hours, mins
    return True, 0, 0

@dp.message(F.text.in_(["✏️ Narx yangilash","✏️ Обновить цену"]))
async def update_start(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await del_msg(msg)
    btns = [[InlineKeyboardButton(
        text=f"{'🟢' if a['status']=='Ochiq' else '🔴' if a['status']=='Yopiq' else '⚪'} {a['name']} — {a.get('price','?')} so'm",
        callback_data=f"upd_{i}")] for i,a in enumerate(AZS_LIST)]
    await msg.answer(t(uid,"upd_choose"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@dp.callback_query(F.data.startswith("upd_"))
async def choose_azs_cb(call: CallbackQuery, state: FSMContext)