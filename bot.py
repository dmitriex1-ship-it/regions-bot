import asyncio
import json
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile,
    InputMediaPhoto,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# -------------------- КОНФИГ --------------------
TOKEN = "8937134974:AAG6W4nCKzr6dCRFdW9hs9G0vcLfDHDxiy0"
IMAGES_DIR = Path("images")
BLUR_DIR = Path("images_blur")
DATA_FILE = Path("regions_data.json")
USERS_FILE = Path("users.json")

DOP_TO_MAIN = {
    "95": "20", "116": "16", "123": "23", "138": "38",
    "150": "50", "152": "52", "154": "54", "161": "61",
    "174": "74", "178": "78", "186": "86", "777": "77",
}

DISTRICTS = {
    "Центральный": ["31","32","33","36","37","40","44","46","48","50","57","62","67","68","69","71","76","77","150"],
    "Северо-Западный": ["10","11","29","35","39","47","51","53","60","78","83","178"],
    "Южный": ["01","08","23","30","34","61","82","92","123","161"],
    "Северо-Кавказский": ["05","06","07","09","15","20","26","95"],
    "Приволжский": ["02","12","13","16","18","21","43","52","56","58","59","63","64","73","116","152"],
    "Уральский": ["45","66","72","74","86","89","174","186"],
    "Сибирский": ["03","04","17","19","22","24","38","42","54","55","70","138","154"],
    "Дальневосточный": ["14","25","27","28","41","49","65","75","79","87"],
}

# -------------------- ЗАГРУЗКА ДАННЫХ --------------------
with open(DATA_FILE, "r", encoding="utf-8") as f:
    regions = json.load(f)

ALL_CODES = list(regions.keys())
ORDERED_CODES = sorted(ALL_CODES, key=lambda x: int(x))

# -------------------- ХРАНЕНИЕ ПОЛЬЗОВАТЕЛЕЙ --------------------
def load_users():
    if not USERS_FILE.exists():
        return {}
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(user_id: str):
    users = load_users()
    if user_id not in users:
        users[user_id] = {
            "total": 0, "correct": 0, "wrong": 0, "hints_used": 0,
            "quiz_total": 0, "quiz_correct": 0,
            "match_total": 0, "match_correct": 0,
            "tf_total": 0, "tf_correct": 0,
            "exam_total": 0, "exam_correct": 0,
            "quiz_state": None, "match_state": None, "exam_state": None,
            "district_state": None, "ordered_state": None, "neighbors_state": None,
            "region_stats": {},
        }
        save_users(users)
    return users, users[user_id]

def update_stats(user_id: str, correct: bool, mode: str = "quiz", code: str = None, hint_used: bool = False):
    users, user = get_user(str(user_id))
    user["total"] += 1
    if correct:
        user["correct"] += 1
    else:
        user["wrong"] += 1
    if hint_used:
        user["hints_used"] += 1

    if mode == "quiz":
        user["quiz_total"] += 1
        if correct: user["quiz_correct"] += 1
    elif mode == "match":
        user["match_total"] += 1
        if correct: user["match_correct"] += 1
    elif mode == "tf":
        user["tf_total"] += 1
        if correct: user["tf_correct"] += 1
    elif mode == "exam":
        user["exam_total"] += 1
        if correct: user["exam_correct"] += 1

    if code:
        eff = DOP_TO_MAIN.get(code, code)
        if eff not in user["region_stats"]:
            user["region_stats"][eff] = {"correct": 0, "total": 0}
        user["region_stats"][eff]["total"] += 1
        if correct:
            user["region_stats"][eff]["correct"] += 1

    save_users(users)

# -------------------- ПОМОЩНИКИ --------------------
def get_effective_code(code: str) -> str:
    return DOP_TO_MAIN.get(code, code)

def image_exists(code: str) -> bool:
    eff = get_effective_code(code)
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if (IMAGES_DIR / f"{eff}{ext}").exists():
            return True
    return False

def get_image_path(code: str) -> Path | None:
    eff = get_effective_code(code)
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = IMAGES_DIR / f"{eff}{ext}"
        if p.exists():
            return p
    return None

def blur_exists(code: str) -> bool:
    eff = get_effective_code(code)
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if (BLUR_DIR / f"{eff}{ext}").exists():
            return True
    return False

def get_blur_path(code: str) -> Path | None:
    eff = get_effective_code(code)
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = BLUR_DIR / f"{eff}{ext}"
        if p.exists():
            return p
    return None

def progress_percent(user: dict) -> float:
    if user["total"] == 0:
        return 0.0
    return (user["correct"] / user["total"]) * 100

def mode_percent(user: dict, mode: str) -> float:
    total = user.get(f"{mode}_total", 0)
    if total == 0:
        return 0.0
    return (user.get(f"{mode}_correct", 0) / total) * 100

# -------------------- КЛАВИАТУРЫ --------------------
def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Изучение", callback_data="go_study_menu")],
        [InlineKeyboardButton(text="🎮 Тренировка", callback_data="go_game_menu")],
        [InlineKeyboardButton(text="📝 Экзамен", callback_data="mode_exam")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="🏆 Рейтинг", callback_data="rating")],
    ])

def study_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Регионы с ассоциациями", callback_data="mode_cards_all")],
        [InlineKeyboardButton(text="📜 Регионы по порядку", callback_data="mode_ordered")],
        [InlineKeyboardButton(text="🗺 По округам", callback_data="mode_district")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu")],
    ])

def game_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Угадай по ассоциации", callback_data="mode_quiz")],
        [InlineKeyboardButton(text="🧩 Найди пару", callback_data="mode_match")],
        [InlineKeyboardButton(text="⚡ Верно / Неверно", callback_data="mode_truefalse")],
        [InlineKeyboardButton(text="🧩 Игра «Соседи»", callback_data="mode_neighbors")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu")],
    ])

def district_menu_kb():
    builder = InlineKeyboardBuilder()
    for d in DISTRICTS:
        builder.button(text=d, callback_data=f"district_{d}")
    builder.row(
        InlineKeyboardButton(text="📚 К изучению", callback_data="go_study_menu"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"),
    )
    builder.adjust(1)
    return builder.as_markup()

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu")]
    ])

# -------------------- БОТ --------------------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== КОМАНДЫ И МЕНЮ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🚗 Привет! Я тренажёр кодов регионов России.\n\n"
        "📚 <b>Изучение</b> — карточки, округа, порядок\n"
        "🎮 <b>Тренировка</b> — игры и тесты\n"
        "📊 <b>Статистика</b> — твой прогресс",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    users = load_users()
    users[str(message.chat.id)] = {
        "total": 0, "correct": 0, "wrong": 0, "hints_used": 0,
        "quiz_total": 0, "quiz_correct": 0,
        "match_total": 0, "match_correct": 0,
        "tf_total": 0, "tf_correct": 0,
        "exam_total": 0, "exam_correct": 0,
        "quiz_state": None, "match_state": None, "exam_state": None,
        "district_state": None, "ordered_state": None, "neighbors_state": None,
        "region_stats": {},
    }
    save_users(users)
    await message.answer("✅ Статистика сброшена.")

@dp.callback_query(F.data == "to_menu")
async def to_menu(callback: types.CallbackQuery):
    await bot.send_message(chat_id=callback.from_user.id, text="🚗 Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()

@dp.callback_query(F.data == "go_study_menu")
async def go_study_menu(callback: types.CallbackQuery):
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="📚 <b>Изучение</b> — выбери режим:",
        parse_mode="HTML",
        reply_markup=study_menu_kb(),
    )
    await callback.answer()

@dp.callback_query(F.data == "go_game_menu")
async def go_game_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("🎮 <b>Тренировка</b> — выбери игру:", parse_mode="HTML", reply_markup=game_menu_kb())
    await callback.answer()

# ========== СТАТИСТИКА ==========
@dp.callback_query(F.data == "stats")
async def cb_stats(callback: types.CallbackQuery):
    _, user = get_user(str(callback.from_user.id))
    total = user["total"]
    correct = user["correct"]
    wrong = user["wrong"]
    hints = user["hints_used"]
    pct = progress_percent(user)
    exam_unlocked = pct >= 70

    text = (
        f"📊 <b>Общая статистика</b>\n\n"
        f"Всего ответов: <b>{total}</b>\n"
        f"✅ Правильных: <b>{correct}</b>\n"
        f"❌ Ошибок: <b>{wrong}</b>\n"
        f"💡 Подсказок: <b>{hints}</b>\n"
        f"🎯 Точность: <b>{pct:.1f}%</b>\n\n"
    )
    if exam_unlocked:
        text += "🔓 <b>Экзамен открыт!</b> (70%+)\n\n"
    else:
        text += f"🔒 <b>Экзамен закрыт</b> (нужно 70%, сейчас {pct:.1f}%)\n\n"

    text += "<b>По режимам:</b>\n"
    text += f"🎯 Ассоциации: {user['quiz_correct']}/{user['quiz_total']} ({mode_percent(user, 'quiz'):.0f}%)\n"
    text += f"🧩 Найди пару: {user['match_correct']}/{user['match_total']} ({mode_percent(user, 'match'):.0f}%)\n"
    text += f"⚡ Верно/Неверно: {user['tf_correct']}/{user['tf_total']} ({mode_percent(user, 'tf'):.0f}%)\n"
    text += f"📝 Экзамен: {user['exam_correct']}/{user['exam_total']} ({mode_percent(user, 'exam'):.0f}%)\n"

    stats = user.get("region_stats", {})
    if stats:
        worst = [item for item in stats.items() if item[1]["total"] > 0]
        worst.sort(key=lambda x: x[1]["correct"] / x[1]["total"])
        worst = worst[:5]
        if worst:
            text += "\n<b>🔴 Сложные регионы (ошибок %):</b>\n"
            for code, s in worst:
                name = regions.get(code, {}).get("name", code)
                error_pct = 100 - (s["correct"] / max(s["total"], 1)) * 100
                text += f"{code} — {name}: {error_pct:.0f}%\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="stats")
    builder.button(text="🗑 Сбросить", callback_data="reset_stats_confirm")
    builder.button(text="🏠 В главное меню", callback_data="to_menu")
    builder.adjust(1)

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "reset_stats_confirm")
async def reset_stats_confirm(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, сбросить", callback_data="reset_stats_yes")
    builder.button(text="❌ Отмена", callback_data="stats")
    builder.adjust(2)
    await callback.message.edit_text("🗑 <b>Точно сбросить всю статистику?</b>", parse_mode="HTML", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "reset_stats_yes")
async def reset_stats_yes(callback: types.CallbackQuery):
    users = load_users()
    users[str(callback.from_user.id)] = {
        "total": 0, "correct": 0, "wrong": 0, "hints_used": 0,
        "quiz_total": 0, "quiz_correct": 0,
        "match_total": 0, "match_correct": 0,
        "tf_total": 0, "tf_correct": 0,
        "exam_total": 0, "exam_correct": 0,
        "quiz_state": None, "match_state": None, "exam_state": None,
        "district_state": None, "ordered_state": None, "neighbors_state": None,
        "region_stats": {},
    }
    save_users(users)
    await callback.message.edit_text("✅ Статистика сброшена!", reply_markup=back_kb())
    await callback.answer()

# ========== РЕЖИМ: КАРТОЧКИ (ВСЕ) ==========
@dp.callback_query(F.data == "mode_cards_all")
async def start_cards_all(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    user["ordered_state"] = {"index": 0, "codes": ORDERED_CODES.copy()}
    save_users(users)
    await show_card(callback)

async def show_card(update):
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
        msg = update.message
        is_cb = True
    else:
        user_id = str(update.chat.id)
        msg = update
        is_cb = False

    _, user = get_user(user_id)
    state = user.get("ordered_state")
    if not state or state["index"] >= len(state["codes"]):
        text = "✅ Все регионы пройдены!"
        builder = InlineKeyboardBuilder()
        builder.button(text="📚 К изучению", callback_data="go_study_menu")
        builder.button(text="🏠 В главное меню", callback_data="to_menu")
        if is_cb:
            await msg.edit_text(text, reply_markup=builder.as_markup())
        else:
            await msg.answer(text, reply_markup=builder.as_markup())
        return

    code = state["codes"][state["index"]]
    region = regions[code]
    progress_text = f"{state['index'] + 1} / {len(state['codes'])}"

    text = (
        f"📖 <b>Карточка {progress_text}</b>\n\n"
        f"Код: <b>{code}</b>\n"
        f"Регион: <b>{region['name']}</b>\n"
        f"Округ: {region.get('district', '—')}\n\n"
        f"💡 <i>{region['hint']}</i>\n"
        f"💡 <i>{region['hint2']}</i>\n\n"
        f"📌 {region['facts']}"
    )

    builder = InlineKeyboardBuilder()
    nav_buttons = []
    if state["index"] > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_card"))
    nav_buttons.append(InlineKeyboardButton(text="▶️ Дальше", callback_data="next_card"))
    builder.row(*nav_buttons)
    builder.row(
        InlineKeyboardButton(text="📚 К изучению", callback_data="go_study_menu"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"),
    )

    img_path = get_image_path(code)
    if img_path and is_cb:
        photo = FSInputFile(img_path)
        await msg.edit_media(InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"), reply_markup=builder.as_markup())
    elif img_path:
        photo = FSInputFile(img_path)
        await msg.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=builder.as_markup())
    elif is_cb:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data == "next_card")
async def next_card(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    state = user.get("ordered_state")
    if state:
        state["index"] += 1
        save_users(users)
    await show_card(callback)

# ========== РЕЖИМ: ПО ПОРЯДКУ ==========
@dp.callback_query(F.data == "mode_ordered")
async def start_ordered(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    user["ordered_state"] = {"index": 0, "codes": ORDERED_CODES.copy()}
    save_users(users)
    await show_ordered(callback)

async def show_ordered(update):
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
        msg = update.message
        is_cb = True
    else:
        user_id = str(update.chat.id)
        msg = update
        is_cb = False

    _, user = get_user(user_id)
    state = user.get("ordered_state")
    if not state or state["index"] >= len(state["codes"]):
        text = "✅ Все коды пройдены по порядку!"
        builder = InlineKeyboardBuilder()
        builder.button(text="📚 К изучению", callback_data="go_study_menu")
        builder.button(text="🏠 В главное меню", callback_data="to_menu")
        if is_cb:
            await msg.edit_text(text, reply_markup=builder.as_markup())
        else:
            await msg.answer(text, reply_markup=builder.as_markup())
        return

    code = state["codes"][state["index"]]
    region = regions[code]
    progress_text = f"{state['index'] + 1} / {len(state['codes'])}"

    text = (
        f"📜 <b>По порядку {progress_text}</b>\n\n"
        f"<b>{code}</b> — {region['name']}\n"
        f"Округ: {region.get('district', '—')}"
    )

    builder = InlineKeyboardBuilder()
    nav_buttons = []
    if state["index"] > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_ordered"))
    nav_buttons.append(InlineKeyboardButton(text="▶️ Дальше", callback_data="next_ordered"))
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="📚 К изучению", callback_data="go_study_menu"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"),)

    img_path = get_image_path(code)
    if img_path and is_cb:
        photo = FSInputFile(img_path)
        await msg.edit_media(InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"), reply_markup=builder.as_markup())
    elif img_path:
        photo = FSInputFile(img_path)
        await msg.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=builder.as_markup())
    elif is_cb:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data == "next_ordered")
async def next_ordered(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    state = user.get("ordered_state")
    if state:
        state["index"] += 1
        save_users(users)
    await show_ordered(callback)

# ========== ИГРА «СОСЕДИ» ==========
@dp.callback_query(F.data == "mode_neighbors")
async def start_neighbors(callback: types.CallbackQuery):
    await send_neighbors_question(callback)

async def send_neighbors_question(update):
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
    else:
        user_id = str(update.chat.id)

    idx = random.randint(1, len(ORDERED_CODES) - 2)
    left_code = ORDERED_CODES[idx - 1]
    right_code = ORDERED_CODES[idx + 1]
    correct_code = ORDERED_CODES[idx]

    left_name = regions[left_code]["name"]
    right_name = regions[right_code]["name"]

    other = [c for c in ALL_CODES if c != correct_code]
    wrong = random.sample(other, min(3, len(other)))
    options = wrong + [correct_code]
    random.shuffle(options)

    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(text=regions[opt]["name"], callback_data=f"neighbors_{correct_code}_{opt}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="📚 К изучению", callback_data="go_study_menu"))

    text = (
        f"🧩 <b>Игра «Соседи»</b>\n\n"
        f"{left_code} — <b>{left_name}</b>\n"
        f"❓ — <b>???</b>\n"
        f"{right_code} — <b>{right_name}</b>\n\n"
        f"Какой регион между ними?"
    )

    await bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data.startswith("neighbors_"))
async def handle_neighbors(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    correct_code = parts[1]
    chosen_code = parts[2]
    is_correct = (correct_code == chosen_code)

    update_stats(str(callback.from_user.id), correct=is_correct, mode="match", code=correct_code)

    if is_correct:
        await callback.answer(f"✅ Правильно! {correct_code} — {regions[correct_code]['name']}.", show_alert=True)
        await send_neighbors_question(callback)
    else:
        new_text = (
            f"❌ Неправильно.\n\n"
            f"{correct_code} — это {regions[correct_code]['name']}.\n"
            f"<i>{regions[correct_code]['facts']}</i>"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="▶️ Дальше", callback_data="mode_neighbors")
        builder.button(text="📚 К изучению", callback_data="go_study_menu")
        builder.adjust(1)

        img_path = get_image_path(correct_code)
        if img_path:
            photo = FSInputFile(img_path)
            await callback.message.reply_photo(photo, caption=new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await callback.message.reply(new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        await callback.answer()

# ========== РЕЖИМ: ПО ОКРУГАМ ==========
@dp.callback_query(F.data == "mode_district")
async def mode_district(callback: types.CallbackQuery):
    try:
        await callback.message.edit_text("🗺 Выбери федеральный округ:", reply_markup=district_menu_kb())
    except:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="🗺 Выбери федеральный округ:",
            reply_markup=district_menu_kb()
        )
    await callback.answer()

@dp.callback_query(F.data == "district_cards")
async def show_district_card(update):
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
        msg = update.message
    else:
        user_id = str(update.chat.id)
        msg = update

    _, user = get_user(user_id)
    state = user.get("district_state")
    if not state:
        return
    codes = state.get("codes", [])
    if state["index"] >= len(codes):
        district = state.get("district", "округ")
        text = f"✅ Все регионы округа «{district}» пройдены!"
        builder = InlineKeyboardBuilder()
        builder.button(text="🧪 Тест по округу", callback_data="district_test")
        builder.button(text="🗺 Выбрать другой", callback_data="mode_district")
        builder.button(text="📚 К изучению", callback_data="go_study_menu")
        try:
            await msg.edit_text(text, reply_markup=builder.as_markup())
        except:
            pass
        if isinstance(update, types.CallbackQuery):
            await update.answer()
        return

    code = codes[state["index"]]
    region = regions[code]
    progress_text = f"{state['index'] + 1} / {len(codes)}"

    text = (
        f"📖 <b>{state['district']} — {progress_text}</b>\n\n"
        f"Код: <b>{code}</b>\n"
        f"Регион: <b>{region['name']}</b>\n\n"
        f"💡 <i>{region['hint']}</i>\n"
        f"💡 <i>{region['hint2']}</i>\n\n"
        f"📌 {region['facts']}"
    )

    builder = InlineKeyboardBuilder()
    nav_buttons = []
    if state["index"] > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="prev_district_card"))
    nav_buttons.append(InlineKeyboardButton(text="▶️ Дальше", callback_data="next_district_card"))
    builder.row(*nav_buttons)
    builder.row(InlineKeyboardButton(text="🧪 Тест по округу", callback_data="district_test"))
    builder.row(
        InlineKeyboardButton(text="🗺 Выбрать другой", callback_data="mode_district"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"),
    )
    builder.adjust(1)

    img_path = get_image_path(code)
    try:
        if img_path:
            photo = FSInputFile(img_path)
            await msg.edit_media(InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"), reply_markup=builder.as_markup())
        else:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    except:
        pass

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data == "district_test")
async def district_test(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    state = user.get("district_state")
    if not state or not state.get("codes"):
        await callback.answer("Сначала выбери округ и посмотри карточки", show_alert=True)
        return
    # Отправляем новое сообщение для теста
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="Загрузка теста..."
    )
    await send_district_test_question(callback)

async def send_district_test_question(update):
    # Всегда отправляем новое сообщение
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
    else:
        user_id = str(update.chat.id)

    _, user = get_user(user_id)
    state = user.get("district_state")
    codes_pool = state.get("codes", [])

    code = random.choice(codes_pool)
    region = regions[code]

    other = [c for c in ALL_CODES if c != code]
    wrong = random.sample(other, min(3, len(other)))
    options = wrong + [code]
    random.shuffle(options)

    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(text=regions[opt]["name"], callback_data=f"distest_{code}_{opt}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🗺 Выбрать другой", callback_data="mode_district"))

    text = (
        f"🧪 <b>Тест: {state['district']}</b>\n\n"
        f"Код: <b>{code}</b>\n"
        f"<i>{region['hint']}</i>\n\n"
        f"Выбери регион:"
    )

    await bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data.startswith("district_"))
async def district_selected(callback: types.CallbackQuery):
    if callback.data in ("district_cards", "district_test", "district_back"):
        return
    
    district = callback.data.replace("district_", "")
    codes = DISTRICTS.get(district, [])
    if not codes:
        await callback.answer(f"Округ не найден: '{district}'", show_alert=True)
        return

    users, user = get_user(str(callback.from_user.id))
    user["district_state"] = {"district": district, "index": 0, "codes": codes.copy()}
    save_users(users)

    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Карточки округа", callback_data="district_cards")
    builder.button(text="🧪 Тест по округу", callback_data="district_test")
    builder.button(text="🗺 Выбрать другой", callback_data="mode_district")
    builder.row(
        InlineKeyboardButton(text="📚 К изучению", callback_data="go_study_menu"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"),
    )
    builder.adjust(1)

    await callback.message.edit_text(
        f"🗺 <b>{district}</b> — {len(codes)} регионов.\nВыбери действие:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()

@dp.callback_query(F.data == "next_district_card")
async def next_district_card(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    state = user.get("district_state")
    if not state:
        await callback.answer("Сначала выбери округ", show_alert=True)
        return
    state["index"] += 1
    save_users(users)
    await show_district_card(callback)

@dp.callback_query(F.data.startswith("distest_"))
async def handle_distest(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    correct_code = parts[1]
    chosen_code = parts[2]
    is_correct = (correct_code == chosen_code)

    update_stats(str(callback.from_user.id), correct=is_correct)

    if is_correct:
        await callback.answer(f"✅ Правильно! {correct_code} — {regions[correct_code]['name']}.", show_alert=True)
        await send_district_test_question(callback)
    else:
        new_text = (
            f"❌ Неправильно.\n\n"
            f"{correct_code} — это {regions[correct_code]['name']}.\n"
            f"<i>{regions[correct_code]['facts']}</i>"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="▶️ Дальше", callback_data="district_test")
        builder.button(text="🗺 Выбрать другой", callback_data="mode_district")
        builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"))
        builder.adjust(1)

        img_path = get_image_path(correct_code)
        if img_path:
            photo = FSInputFile(img_path)
            await callback.message.reply_photo(photo, caption=new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await callback.message.reply(new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        await callback.answer()

# ========== РЕЖИМ 1: УГАДАЙ ПО АССОЦИАЦИИ ==========
@dp.callback_query(F.data == "mode_quiz")
async def start_quiz(callback: types.CallbackQuery):
    await send_quiz_question(callback)

async def send_quiz_question(update):
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
        msg = update.message
        is_cb = True
    else:
        user_id = str(update.chat.id)
        msg = update
        is_cb = False

    code = random.choice(ALL_CODES)
    region = regions[code]

    other_codes = [c for c in ALL_CODES if c != code]
    wrong_codes = random.sample(other_codes, min(3, len(other_codes)))
    options = wrong_codes + [code]
    random.shuffle(options)

    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(text=f"{regions[opt]['name']}", callback_data=f"quiz_answer_{code}_{opt}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"))

    text = (
        f"🤔 <b>Угадай регион по ассоциации</b>\n\n"
        f"Код региона: <b>{code}</b>\n\n"
        f"🗣 <i>«{region['hint']}»</i>\n"
        f"🗣 <i>«{region['hint2']}»</i>\n\n"
        f"<b>Выбери правильное название:</b>"
    )

    users, user = get_user(user_id)
    user["quiz_state"] = {"code": code}
    save_users(users)

    blur_path = get_blur_path(code)
    if blur_path and is_cb:
        photo = FSInputFile(blur_path)
        await msg.edit_media(InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"), reply_markup=builder.as_markup())
    elif blur_path:
        photo = FSInputFile(blur_path)
        await msg.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=builder.as_markup())
    elif is_cb:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data.startswith("quiz_answer_"))
async def handle_quiz_answer(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    correct_code = parts[2]
    chosen_code = parts[3]
    is_correct = (correct_code == chosen_code)

    update_stats(str(callback.from_user.id), correct=is_correct, mode="quiz", code=correct_code)

    if is_correct:
        await callback.answer(f"✅ Правильно! {correct_code} — {regions[correct_code]['name']}.", show_alert=True)
        await send_quiz_question(callback)
    else:
        new_text = (
            f"❌ Неправильно.\n\n"
            f"{correct_code} — это {regions[correct_code]['name']}.\n"
            f"<i>{regions[correct_code]['facts']}</i>"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="▶️ Продолжить", callback_data="mode_quiz")
        builder.button(text="🏠 В главное меню", callback_data="to_menu")
        builder.adjust(1)

        img_path = get_image_path(correct_code)
        if img_path:
            photo = FSInputFile(img_path)
            await callback.message.reply_photo(photo, caption=new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await callback.message.reply(new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        await callback.answer()

# ========== РЕЖИМ 2: НАЙДИ ПАРУ ==========
@dp.callback_query(F.data == "mode_match")
async def start_match(callback: types.CallbackQuery):
    await send_match_question(callback)

async def send_match_question(update):
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
        msg = update.message
        is_cb = True
    else:
        user_id = str(update.chat.id)
        msg = update
        is_cb = False

    code = random.choice(ALL_CODES)
    other_codes = [c for c in ALL_CODES if c != code]
    wrong_codes = random.sample(other_codes, min(3, len(other_codes)))
    options = wrong_codes + [code]
    random.shuffle(options)

    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(text=f"{regions[opt]['name']}", callback_data=f"match_answer_{code}_{opt}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"))

    text = (
        f"🧩 <b>Найди пару</b>\n\n"
        f"Код региона: <b>{code}</b>\n\n"
        f"<b>Выбери правильное название:</b>"
    )

    users, user = get_user(user_id)
    user["match_state"] = {"code": code}
    save_users(users)

    blur_path = get_blur_path(code)
    if blur_path and is_cb:
        photo = FSInputFile(blur_path)
        await msg.edit_media(InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"), reply_markup=builder.as_markup())
    elif blur_path:
        photo = FSInputFile(blur_path)
        await msg.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=builder.as_markup())
    elif is_cb:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data.startswith("match_answer_"))
async def handle_match_answer(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    correct_code = parts[2]
    chosen_code = parts[3]
    is_correct = (correct_code == chosen_code)

    update_stats(str(callback.from_user.id), correct=is_correct, mode="match", code=correct_code)

    if is_correct:
        await callback.answer(f"✅ Правильно! {correct_code} — {regions[correct_code]['name']}.", show_alert=True)
        await send_match_question(callback)
    else:
        new_text = (
            f"❌ Неправильно.\n\n"
            f"{correct_code} — это {regions[correct_code]['name']}.\n"
            f"<i>{regions[correct_code]['facts']}</i>"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="▶️ Продолжить", callback_data="mode_match")
        builder.button(text="🏠 В главное меню", callback_data="to_menu")
        builder.adjust(1)

        img_path = get_image_path(correct_code)
        if img_path:
            photo = FSInputFile(img_path)
            await callback.message.reply_photo(photo, caption=new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await callback.message.reply(new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        await callback.answer()

# ========== РЕЖИМ 3: ВЕРНО / НЕВЕРНО ==========
@dp.callback_query(F.data == "mode_truefalse")
async def start_truefalse(callback: types.CallbackQuery):
    await send_truefalse_question(callback)

async def send_truefalse_question(update):
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
        msg = update.message
        is_cb = True
    else:
        user_id = str(update.chat.id)
        msg = update
        is_cb = False

    code = random.choice(ALL_CODES)
    region = regions[code]

    if random.random() < 0.5:
        shown_name = region["name"]
        correct_answer = True
    else:
        other_codes = [c for c in ALL_CODES if c != code]
        wrong_code = random.choice(other_codes)
        shown_name = regions[wrong_code]["name"]
        correct_answer = False

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=f"tf_{code}_{correct_answer}_true")
    builder.button(text="❌ Нет", callback_data=f"tf_{code}_{correct_answer}_false")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"))

    text = (
        f"⚡ <b>Верно или неверно?</b>\n\n"
        f"Код <b>{code}</b> — это <b>{shown_name}</b>?\n\n"
        f"<i>{region['hint']}</i>"
    )

    users, user = get_user(user_id)
    user["quiz_state"] = {"code": code}
    save_users(users)

    blur_path = get_blur_path(code)
    if blur_path and is_cb:
        photo = FSInputFile(blur_path)
        await msg.edit_media(InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"), reply_markup=builder.as_markup())
    elif blur_path:
        photo = FSInputFile(blur_path)
        await msg.answer_photo(photo, caption=text, parse_mode="HTML", reply_markup=builder.as_markup())
    elif is_cb:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data.startswith("tf_"))
async def handle_tf_answer(callback: types.CallbackQuery):
    if callback.data in ("tf_continue", "tf_to_menu"):
        if callback.data == "tf_continue":
            await send_truefalse_question(callback)
        else:
            await bot.send_message(chat_id=callback.from_user.id, text="🚗 Главное меню:", reply_markup=main_menu_kb())
            await callback.answer()
        return

    parts = callback.data.split("_")
    code = parts[1]
    correct_answer = parts[2] == "True"
    user_answer = parts[3] == "true"
    is_correct = (correct_answer == user_answer)

    update_stats(str(callback.from_user.id), correct=is_correct, mode="tf", code=code)

    if is_correct:
        await callback.answer(f"✅ Правильно! {code} — {regions[code]['name']}.", show_alert=True)
        await send_truefalse_question(callback)
    else:
        new_text = (
            f"❌ Неправильно.\n\n"
            f"{code} — это {regions[code]['name']}.\n"
            f"<i>{regions[code]['facts']}</i>"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="▶️ Продолжить", callback_data="tf_continue")
        builder.button(text="🏠 В главное меню", callback_data="tf_to_menu")
        builder.adjust(1)

        img_path = get_image_path(code)
        if img_path:
            photo = FSInputFile(img_path)
            await callback.message.reply_photo(photo, caption=new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await callback.message.reply(new_text, parse_mode="HTML", reply_markup=builder.as_markup())
        await callback.answer()

# ========== РЕЖИМ 4: ЭКЗАМЕН ==========
@dp.callback_query(F.data == "mode_exam")
async def start_exam(callback: types.CallbackQuery):
    _, user = get_user(str(callback.from_user.id))
    pct = progress_percent(user)
    if pct < 70:
        await callback.answer(f"🔒 Экзамен закрыт! Нужно 70%. У тебя: {pct:.1f}%", show_alert=True)
        return
    await send_exam_question(callback)

async def send_exam_question(update):
    if isinstance(update, types.CallbackQuery):
        user_id = str(update.from_user.id)
        msg = update.message
        is_cb = True
    else:
        user_id = str(update.chat.id)
        msg = update
        is_cb = False

    code = random.choice(ALL_CODES)
    region = regions[code]

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"))

    text = (
        f"📝 <b>ЭКЗАМЕН</b> — введи название вручную\n\n"
        f"Код: <b>{code}</b>\n"
        f"<i>{region['hint']}</i>\n\n"
        f"Напиши ответ текстом:"
    )

    users, user = get_user(user_id)
    user["exam_state"] = {"code": code}
    save_users(users)

    if is_cb:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.message()
async def handle_exam_answer(message: types.Message):
    users, user = get_user(str(message.chat.id))
    state = user.get("exam_state")
    if state is None:
        await message.answer("Используй меню. /start для перезапуска.", reply_markup=main_menu_kb())
        return

    code = state["code"]
    region = regions[code]
    user_answer = message.text.strip().lower()
    correct_names = [region["name"].lower()] + [a.lower() for a in region.get("aliases", [])]
    is_correct = any(name in user_answer or user_answer in name for name in correct_names)

    user["total"] += 1
    user["exam_total"] += 1
    if is_correct:
        user["correct"] += 1
        user["exam_correct"] += 1
    else:
        user["wrong"] += 1

    if code:
        eff = DOP_TO_MAIN.get(code, code)
        if eff not in user["region_stats"]:
            user["region_stats"][eff] = {"correct": 0, "total": 0}
        user["region_stats"][eff]["total"] += 1
        if is_correct:
            user["region_stats"][eff]["correct"] += 1

    user["exam_state"] = None
    save_users(users)

    if is_correct:
        await message.answer(f"✅ Правильно! Это {code} — {region['name']}.")
    else:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu"))
        await message.answer(
            f"❌ Неправильно. {code} — это {region['name']}.\n\n{region['facts']}",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )

    await asyncio.sleep(0.5)
    await send_exam_question(message)

@dp.callback_query(F.data == "district_back")
async def district_back(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    state = user.get("district_state")
    if not state:
        await callback.answer("Округ не выбран", show_alert=True)
        return
    
    district = state["district"]
    codes = state.get("codes", [])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📖 Карточки округа", callback_data="district_cards")
    builder.button(text="🧪 Тест по округу", callback_data="district_test")
    builder.button(text="🗺 Выбрать другой", callback_data="mode_district")
    builder.button(text="📚 К изучению", callback_data="go_study_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        f"🗺 <b>{district}</b> — {len(codes)} регионов.\nВыбери действие:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()

@dp.callback_query(F.data == "prev_district_card")
async def prev_district_card(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    state = user.get("district_state")
    if not state:
        await callback.answer("Сначала выбери округ", show_alert=True)
        return
    if state["index"] > 0:
        state["index"] -= 1
        save_users(users)
    await show_district_card(callback)

@dp.callback_query(F.data == "prev_card")
async def prev_card(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    state = user.get("ordered_state")
    if state and state["index"] > 0:
        state["index"] -= 1
        save_users(users)
    await show_card(callback)

@dp.callback_query(F.data == "prev_ordered")
async def prev_ordered(callback: types.CallbackQuery):
    users, user = get_user(str(callback.from_user.id))
    state = user.get("ordered_state")
    if state and state["index"] > 0:
        state["index"] -= 1
        save_users(users)
    await show_ordered(callback)

@dp.callback_query(F.data == "rating")
async def cb_rating(callback: types.CallbackQuery):
    users = load_users()
    ranking = []
    for uid, data in users.items():
        exam_total = data.get("exam_total", 0)
        exam_correct = data.get("exam_correct", 0)
        if exam_total > 0:
            pct = (exam_correct / exam_total) * 100
            ranking.append((uid, exam_correct, exam_total, pct))
    
    ranking.sort(key=lambda x: (-x[3], -x[2]))
    
    text = "🏆 <b>Рейтинг по экзамену</b>\n\n"
    if not ranking:
        text += "Пока никто не проходил экзамен."
    else:
        for i, (uid, correct, total, pct) in enumerate(ranking[:10], 1):
            try:
                chat = await bot.get_chat(uid)
                name = chat.first_name or uid
            except:
                name = uid
            text += f"{i}. {name}: {correct}/{total} ({pct:.0f}%)\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="rating")
    builder.button(text="🏠 В главное меню", callback_data="to_menu")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    except:
        pass
    await callback.answer()

# ========== ЗАПУСК ==========
async def health_check(request):
    return web.Response(text="OK")

async def main():
    IMAGES_DIR.mkdir(exist_ok=True)
    BLUR_DIR.mkdir(exist_ok=True)
    print(f"Бот запущен. Картинки: {IMAGES_DIR.absolute()}")
    print(f"Размытые превью: {BLUR_DIR.absolute()}")

    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    print("HTTP-сервер на порту 10000")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
