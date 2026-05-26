import asyncio, json, math, os
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

with open("azs.json", encoding="utf-8") as f:
    AZS_LIST = json.load(f)

# ───────────── Til ─────────────
TEXTS = {
    "uz": {
        "welcome": (
            "⛽ *PropanBorBot ga xush kelibsiz!*\n\n"
            "Bu bot Toshkent va viloyatidagi propan AZSlari haqida ma'lumot beradi.\n\n"
            "📍 Lokatsiyangizni yuboring — eng yaqin AZSni topamiz!\n"
            "Ma'lumotlar foydalanuvchilar tomonidan yangilanib boradi."
        ),
        "nearest_title": "📍 *Sizga eng yaqin AZSlar:*\n\n",
        "all_city": "⛽ *Toshkent shahri ({n} ta):*\n",
        "all_region": "🌆 *Toshkent viloyati ({n} ta):*\n",
        "prices_title": "💰 *Narxlar (arzondan qimmatga):*\n\n",
        "help": (
            "ℹ️ *Yordam*\n\n"
            "📍 Lokatsiya — eng yaqin AZS\n"
            "📋 Barcha AZSlar — to'liq ro'yxat\n"
            "💰 Narxlar — narxlar ro'yxati\n"
            "➕ AZS qo'shish — yangi AZS\n"
            "✏️ Narx yangilash — narxni yangilash\n"
            "🌐 /ru — русский язык"
        ),
        "add_name": "✏️ AZS nomini kiriting:\n(masalan: Sergeli 3)",
        "add_loc": "📍 AZS lokatsiyasini yuboring:",
        "add_price": "💰 Narxni kiriting (so'mda):\n(masalan: 6700)",
        "add_hours": "🕐 Ish vaqtini kiriting:\n(masalan: 08:00-22:00 yoki 24/7)",
        "add_phone": "📞 Telefon (ixtiyoriy):\nYo'q bo'lsa — /skip",
        "add_region_q": "🌆 Hudud:",
        "add_done": "✅ *{name}* qo'shildi!\n💰 {price} so'm | 🕐 {hours}",
        "upd_choose": "Qaysi AZS narxini yangilaysiz?",
        "upd_price_q": "💰 *{name}* uchun yangi narx (so'm):",
        "upd_done": "✅ Narx yangilandi!\n⛽ *{name}*\n{arrow} {old} → {new} so'm",
        "err_price": "❌ Faqat raqam kiriting. Masalan: 6700",
        "unknown": "📋 Menyudan tanlang:",
        "btn_nearest": "📍 Yaqin AZS topish",
        "btn_all": "📋 Barcha AZSlar",
        "btn_prices": "💰 Narxlar",
        "btn_add": "➕ AZS qo'shish",
        "btn_update": "✏️ Narx yangilash",
        "btn_help": "ℹ️ Yordam",
        "btn_lang": "🇷🇺 Русский",
        "region_city": "Toshkent shahar",
        "region_vil": "Toshkent viloyati",
        "unknown_price": "Noma'lum",
        "map_btn": "🗺 Xaritada ko'rish",
    },
    "ru": {
        "welcome": (
            "⛽ *Добро пожаловать в PropanBorBot!*\n\n"
            "Бот предоставляет информацию о пропановых АЗС Ташкента и области.\n\n"
            "📍 Отправьте локацию — найдём ближайшие АЗС!\n"
            "Данные обновляются пользователями."
        ),
        "nearest_title": "📍 *Ближайшие АЗС:*\n\n",
        "all_city": "⛽ *г. Ташкент ({n} шт):*\n",
        "all_region": "🌆 *Ташкентская область ({n} шт):*\n",
        "prices_title": "💰 *Цены (от дешёвых к дорогим):*\n\n",
        "help": (
            "ℹ️ *Справка*\n\n"
            "📍 Локация — ближайшая АЗС\n"
            "📋 Все АЗС — полный список\n"
            "💰 Цены — список цен\n"
            "➕ Добавить АЗС — новая АЗС\n"
            "✏️ Обновить цену — изменить цену\n"
            "🌐 /uz — o'zbek tili"
        ),
        "add_name": "✏️ Введите название АЗС:\n(например: Сергели 3)",
        "add_loc": "📍 Отправьте локацию АЗС:",
        "add_price": "💰 Введите цену (в сумах):\n(например: 6700)",
        "add_hours": "🕐 Введите время работы:\n(например: 08:00-22:00 или 24/7)",
        "add_phone": "📞 Телефон (необязательно):\nЕсли нет — /skip",
        "add_region_q": "🌆 Район:",
        "add_done": "✅ *{name}* добавлена!\n💰 {price} сум | 🕐 {hours}",
        "upd_choose": "Цену какой АЗС обновить?",
        "upd_price_q": "💰 Новая цена для *{name}* (в сумах):",
        "upd_done": "✅ Цена обновлена!\n⛽ *{name}*\n{arrow} {old} → {new} сум",
        "err_price": "❌ Введите только цифры. Например: 6700",
        "unknown": "📋 Выберите из меню:",
        "btn_nearest": "📍 Найти ближайшую АЗС",
        "btn_all": "📋 Все АЗС",
        "btn_prices": "💰 Цены",
        "btn_add": "➕ Добавить АЗС",
        "btn_update": "✏️ Обновить цену",
        "btn_help": "ℹ️ Справка",
        "btn_lang": "🇺🇿 O'zbek tili",
        "region_city": "Toshkent shahar",
        "region_vil": "Toshkent viloyati",
        "unknown_price": "Неизвестно",
        "map_btn": "🗺 Открыть на карте",
    }
}

user_langs = {}

def get_lang(user_id):
    return user_langs.get(user_id, "uz")

def t(user_id, key, **kwargs):
    lang = get_lang(user_id)
    text = TEXTS[lang].get(key, key)
    return text.format(**kwargs) if kwargs else text

def save_azs():
    with open("azs.json", "w", encoding="utf-8") as f:
        json.dump(AZS_LIST, f, ensure_ascii=False, indent=2)

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def main_menu(uid):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=t(uid,"btn_nearest"), request_location=True)],
        [KeyboardButton(text=t(uid,"btn_all")),    KeyboardButton(text=t(uid,"btn_prices"))],
        [KeyboardButton(text=t(uid,"btn_add")),    KeyboardButton(text=t(uid,"btn_update"))],
        [KeyboardButton(text=t(uid,"btn_help")),   KeyboardButton(text=t(uid,"btn_lang"))],
    ], resize_keyboard=True)

# ───────────── FSM ─────────────
class AddAZS(StatesGroup):
    name = State(); location = State(); price = State()
    hours = State(); phone = State(); region = State()

class UpdatePrice(StatesGroup):
    choose = State(); price = State()

# ───────────── /start ─────────────
@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    await msg.answer(t(uid,"welcome"), parse_mode="Markdown", reply_markup=main_menu(uid))

# ───────────── Til almashtirish ─────────────
@dp.message(F.text == "/ru")
async def set_ru(msg: Message):
    user_langs[msg.from_user.id] = "ru"
    uid = msg.from_user.id
    await msg.answer(t(uid,"welcome"), parse_mode="Markdown", reply_markup=main_menu(uid))

@dp.message(F.text == "/uz")
async def set_uz(msg: Message):
    user_langs[msg.from_user.id] = "uz"
    uid = msg.from_user.id
    await msg.answer(t(uid,"welcome"), parse_mode="Markdown", reply_markup=main_menu(uid))

@dp.message(F.text.in_(["🇷🇺 Русский", "🇺🇿 O'zbek tili"]))
async def toggle_lang(msg: Message):
    uid = msg.from_user.id
    user_langs[uid] = "ru" if msg.text == "🇷🇺 Русский" else "uz"
    await msg.answer(t(uid,"welcome"), parse_mode="Markdown", reply_markup=main_menu(uid))

# ───────────── Lokatsiya ─────────────
@dp.message(F.location)
async def nearest_azs(msg: Message, state: FSMContext):
    fsm = await state.get_state()
    if fsm == AddAZS.location:
        await add_location(msg, state)
        return
    uid = msg.from_user.id
    ulat, ulng = msg.location.latitude, msg.location.longitude
    coords = [a for a in AZS_LIST if a.get("lat") and a.get("lng")]
    ranked = sorted(coords, key=lambda a: haversine(ulat, ulng, a["lat"], a["lng"]))[:5]
    text = t(uid, "nearest_title")
    for i, a in enumerate(ranked, 1):
        dist = haversine(ulat, ulng, a["lat"], a["lng"])
        ds = f"{dist*1000:.0f}м" if dist < 1 else f"{dist:.1f}km"
        si = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
        pr = f"{a['price']:,} so'm".replace(",", " ") if a.get("price") else t(uid,"unknown_price")
        ph = f"\n📞 {a['phone']}" if a.get("phone") else ""
        text += f"{i}. {si} *{a['name']}*\n   📏 {ds} | 💰 {pr} | 🕐 {a.get('hours','—')}{ph}\n\n"
    buttons = [[InlineKeyboardButton(text=f"🗺 {a['name']}",
        url=a.get("url", f"https://maps.google.com/?q={a['lat']},{a['lng']}"))] for a in ranked]
    await msg.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# ───────────── Barcha AZS ─────────────
@dp.message(F.text.in_(["📋 Barcha AZSlar", "📋 Все АЗС"]))
async def all_azs(msg: Message):
    uid = msg.from_user.id
    shahar  = [a for a in AZS_LIST if a.get("region")=="Toshkent shahar"]
    viloyat = [a for a in AZS_LIST if a.get("region")=="Toshkent viloyati"]
    def fmt(lst):
        lines = []
        for a in lst:
            s = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
            p = f"{a['price']:,}".replace(",", " ") if a.get("price") else "—"
            lines.append(f"{s} {a['name']} — {p} so'm")
        return "\n".join(lines)
    text = t(uid,"all_city",n=len(shahar)) + fmt(shahar) + "\n\n" + t(uid,"all_region",n=len(viloyat)) + fmt(viloyat)
    await msg.answer(text, parse_mode="Markdown")

# ───────────── Narxlar ─────────────
@dp.message(F.text.in_(["💰 Narxlar", "💰 Цены"]))
async def prices(msg: Message):
    uid = msg.from_user.id
    srt = sorted([a for a in AZS_LIST if a.get("price")], key=lambda x: x["price"])
    text = t(uid,"prices_title")
    for a in srt:
        s = "🟢" if a["status"]=="Ochiq" else "🔴" if a["status"]=="Yopiq" else "⚪"
        text += f"{s} {a['price']:,} so'm — {a['name']}\n".replace(",", " ")
    await msg.answer(text, parse_mode="Markdown")

# ───────────── Yordam ─────────────
@dp.message(F.text.in_(["ℹ️ Yordam", "ℹ️ Справка"]))
async def help_cmd(msg: Message):
    await msg.answer(t(msg.from_user.id,"help"), parse_mode="Markdown")

# ───────────── AZS qo'shish ─────────────
@dp.message(F.text.in_(["➕ AZS qo'shish", "➕ Добавить АЗС"]))
async def add_start(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await state.set_state(AddAZS.name)
    await msg.answer(t(uid,"add_name"), reply_markup=ReplyKeyboardRemove())

@dp.message(AddAZS.name)
async def add_name(msg: Message, state: FSMContext):
    uid = msg.from_user.id
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
async def add_price_handler(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    try:
        price = int(msg.text.replace(" ","").replace(",",""))
        await state.update_data(price=price)
        await state.set_state(AddAZS.hours)
        await msg.answer(t(uid,"add_hours"), reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="24/7")]], resize_keyboard=True))
    except:
        await msg.answer(t(uid,"err_price"))

@dp.message(AddAZS.hours)
async def add_hours_handler(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await state.update_data(hours=msg.text)
    await state.set_state(AddAZS.phone)
    await msg.answer(t(uid,"add_phone"), reply_markup=ReplyKeyboardRemove())

@dp.message(AddAZS.phone)
async def add_phone_handler(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await state.update_data(phone="" if msg.text=="/skip" else msg.text)
    await state.set_state(AddAZS.region)
    await msg.answer(t(uid,"add_region_q"), reply_markup=ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Toshkent shahar")],
                  [KeyboardButton(text="Toshkent viloyati")]], resize_keyboard=True))

@dp.message(AddAZS.region)
async def add_region_handler(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    data = await state.get_data()
    new_azs = {
        "id": f"u{len(AZS_LIST)+1}",
        "name": data["name"], "price": data["price"],
        "status": "Ochiq", "hours": data["hours"],
        "phone": data.get("phone",""), "region": msg.text,
        "lat": data["lat"], "lng": data["lng"],
        "url": f"https://maps.google.com/?q={data['lat']},{data['lng']}",
        "note": f"@{msg.from_user.username or uid}"
    }
    AZS_LIST.append(new_azs)
    save_azs()
    await state.clear()
    await msg.answer(t(uid,"add_done",name=data["name"],
        price=f"{data['price']:,}".replace(",", " "), hours=data["hours"]),
        parse_mode="Markdown", reply_markup=main_menu(uid))

# ───────────── Narx yangilash ─────────────
@dp.message(F.text.in_(["✏️ Narx yangilash", "✏️ Обновить цену"]))
async def update_start(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    await state.set_state(UpdatePrice.choose)
    buttons = [[InlineKeyboardButton(text=f"⛽ {a['name']}", callback_data=f"upd_{i}")]
               for i, a in enumerate(AZS_LIST)]
    await msg.answer(t(uid,"upd_choose"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("upd_"))
async def choose_azs_cb(call: CallbackQuery, state: FSMContext):
    uid = call.from_user.id
    idx = int(call.data.split("_")[1])
    await state.update_data(idx=idx)
    await state.set_state(UpdatePrice.price)
    await call.message.answer(t(uid,"upd_price_q", name=AZS_LIST[idx]["name"]),
        parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    await call.answer()

@dp.message(UpdatePrice.price)
async def update_price_handler(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    try:
        data = await state.get_data()
        idx  = data["idx"]
        old  = AZS_LIST[idx].get("price", 0)
        new  = int(msg.text.replace(" ","").replace(",",""))
        AZS_LIST[idx]["price"] = new
        save_azs()
        await state.clear()
        arrow = "📈" if new > old else "📉" if new < old else "➡️"
        await msg.answer(t(uid,"upd_done", name=AZS_LIST[idx]["name"],
            arrow=arrow,
            old=f"{old:,}".replace(",", " "),
            new=f"{new:,}".replace(",", " ")),
            parse_mode="Markdown", reply_markup=main_menu(uid))
    except:
        await msg.answer(t(uid,"err_price"))

# ───────────── Noma'lum xabar ─────────────
@dp.message()
async def unknown(msg: Message):
    await msg.answer(t(msg.from_user.id,"unknown"), reply_markup=main_menu(msg.from_user.id))

async def main():
    print("PropanBorBot ishga tushdi ✅")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
