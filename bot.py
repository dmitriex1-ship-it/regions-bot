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

# -------------------- КОНФИГ --------------------
TOKEN = "8937134974:AAG6W4nCKzr6dCRFdW9hs9G0vcLfDHDxiy0"
IMAGES_DIR = Path("images")
BLUR_DIR = Path("images_blur")
DATA_FILE = Path("regions_data.json")
USERS_FILE = Path("users.json")

# Маппинг дополнительных кодов на основные
DOP_TO_MAIN = {
    "95": "20", "116": "16", "123": "23", "138": "38",
    "150": "50", "152": "52", "154": "54", "161": "61",
    "174": "74", "178": "78", "186": "86", "777": "77",
}

# -------------------- ЗАГРУЗКА ДАННЫХ --------------------
with open(DATA_FILE, "r", encoding="utf-8") as f:
    regions = json.load(f)

ALL_CODES = list(regions.keys())

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
            "total": 0,
            "correct": 0,
            "wrong": 0,
            "hints_used": 0,
            "quiz_state": None,
            "match_state": None,
        }
        save_users(users)
    return users, users[user_id]

def update_stats(user_id: str, correct: bool, hint_used: bool = False):
    users, user = get_user(str(user_id))
    user["total"] += 1
    if correct:
        user["correct"] += 1
    else:
        user["wrong"] += 1
    if hint_used:
        user["hints_used"] += 1
    save_users(users)

# -------------------- ПОМОЩНИКИ --------------------
def get_effective_code(code: str) -> str:
    """Возвращает основной код, если есть доп. маппинг"""
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

# -------------------- КЛАВИАТУРЫ --------------------
def to_menu_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Угадай по ассоциации", callback_data="mode_quiz")],
            [InlineKeyboardButton(text="🧩 Найди пару", callback_data="mode_match")],
            [InlineKeyboardButton(text="⚡ Верно / Неверно", callback_data="mode_truefalse")],
            [InlineKeyboardButton(text="📝 Экзамен", callback_data="mode_exam")],
            [InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats")],
        ]
    )

def back_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_menu")]
        ]
    )

# -------------------- БОТ --------------------
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🚗 Привет! Я тренажёр кодов регионов России.\n\n"
        "Выбери режим тренировки:\n"
        "🎯 Угадай по ассоциации — викторина с картой-превью\n"
        "🧩 Найди пару — только код, без текстовых подсказок\n"
        "⚡ Верно/Неверно — быстрый блиц\n"
        "📝 Экзамен — ручной ввод (открывается при 70% успеха)",
        reply_markup=to_menu_kb(),
    )


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

    text += "<b>По режимам:</b>"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="stats")
    builder.button(text="🗑 Сбросить статистику", callback_data="reset_stats_confirm")
    builder.button(text="🏠 В главное меню", callback_data="to_menu")
    builder.adjust(1)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data == "reset_stats_confirm")
async def reset_stats_confirm(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, сбросить", callback_data="reset_stats_yes")
    builder.button(text="❌ Нет, отмена", callback_data="stats")
    builder.adjust(2)

    await callback.message.edit_text(
        "🗑 <b>Точно сбросить всю статистику?</b>\n\nЭто действие нельзя отменить.",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@dp.callback_query(F.data == "reset_stats_yes")
async def reset_stats_yes(callback: types.CallbackQuery):
    users = load_users()
    user_id = str(callback.from_user.id)
    users[user_id] = {
        "total": 0,
        "correct": 0,
        "wrong": 0,
        "hints_used": 0,
        "quiz_state": None,
        "match_state": None,
    }
    save_users(users)

    await callback.message.edit_text(
        "✅ <b>Статистика сброшена!</b>\n\nЭкзамен снова закрыт. Начинай заново.",
        parse_mode="HTML",
        reply_markup=back_kb(),
    )
    await callback.answer()

# ========== РЕЖИМ 1: УГАДАЙ ПО АССОЦИАЦИИ (с размытым превью) ==========
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
        builder.button(
            text=f"{regions[opt]['name']}",
            callback_data=f"quiz_answer_{code}_{opt}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(
        text="🏠 В главное меню",
        callback_data="to_menu",
    ))

    text = (
        f"🤔 <b>Угадай регион по ассоциации</b>\n\n"
        f"Код региона: <b>{code}</b>\n\n"
        f"🗣 <i>«{region['hint']}»</i>\n\n"
        f"<b>Выбери правильное название:</b>"
    )

    users, user = get_user(user_id)
    user["quiz_state"] = {"code": code}
    save_users(users)

    # Отправляем с размытой картинкой
    blur_path = get_blur_path(code)
    if blur_path and is_cb:
        photo = FSInputFile(blur_path)
        await msg.edit_media(
            InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
            reply_markup=builder.as_markup(),
        )
    elif blur_path:
        photo = FSInputFile(blur_path)
        await msg.answer_photo(
            photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
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

    update_stats(str(callback.from_user.id), correct=is_correct)

    region_name = regions[correct_code]["name"]
    if is_correct:
        await callback.answer(
            f"✅ Правильно! {correct_code} — это {region_name}.",
            show_alert=True,
        )
        await send_quiz_question(callback)
    else:
        new_text = (
            f"❌ Неправильно.\n\n"
            f"{correct_code} — это {region_name}.\n"
            f"<i>{regions[correct_code]['facts']}</i>"
        )

        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="▶️ Продолжить игру",
            callback_data="quiz_continue",
        ))
        builder.row(InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data="quiz_to_menu",
        ))

        img_path = get_image_path(correct_code)
        if img_path:
            photo = FSInputFile(img_path)
            await callback.message.reply_photo(
                photo,
                caption=new_text,
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )
        else:
            await callback.message.reply(
                new_text,
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )
        
@dp.callback_query(F.data == "quiz_continue")
async def quiz_continue(callback: types.CallbackQuery):
    await send_quiz_question(callback)

@dp.callback_query(F.data == "quiz_to_menu")
async def quiz_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="🚗 Выбери режим тренировки:",
        reply_markup=to_menu_kb(),
    )
    await callback.answer()

# ========== ПОКАЗ ПОЛНОЙ КАРТИНКИ ПО НАЖАТИЮ НА РАЗМЫТУЮ ==========
@dp.callback_query(F.data.startswith("show_full_"))
async def show_full_image(callback: types.CallbackQuery):
    code = callback.data.replace("show_full_", "")
    img_path = get_image_path(code)
    if img_path:
        photo = FSInputFile(img_path)
        await callback.message.reply_photo(
            photo,
            caption=f"🗺 <b>{code} — {regions[code]['name']}</b>\n\n<i>{regions[code]['facts']}</i>",
            parse_mode="HTML",
        )
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
    region = regions[code]

    other_codes = [c for c in ALL_CODES if c != code]
    wrong_codes = random.sample(other_codes, min(3, len(other_codes)))
    options = wrong_codes + [code]
    random.shuffle(options)

    builder = InlineKeyboardBuilder()
    for opt in options:
        builder.button(
            text=f"{regions[opt]['name']}",
            callback_data=f"match_answer_{code}_{opt}",
        )
    builder.adjust(1)

    builder.row(InlineKeyboardButton(
        text="🏠 В главное меню",
        callback_data="to_menu",
    ))

    text = (
        f"🧩 <b>Найди пару</b>\n\n"
        f"Код региона: <b>{code}</b>\n\n"
        f"<b>Выбери правильное название:</b>"
    )

    users, user = get_user(user_id)
    user["match_state"] = {"code": code}
    save_users(users)

    # Отправляем с размытой картинкой
    blur_path = get_blur_path(code)
    if blur_path and is_cb:
        photo = FSInputFile(blur_path)
        await msg.edit_media(
            InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
            reply_markup=builder.as_markup(),
        )
    elif blur_path:
        photo = FSInputFile(blur_path)
        await msg.answer_photo(
            photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
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

    update_stats(str(callback.from_user.id), correct=is_correct)

    region_name = regions[correct_code]["name"]
    if is_correct:
        await callback.answer(
            f"✅ Правильно! {correct_code} — это {region_name}.",
            show_alert=True,
        )
        await send_match_question(callback)
    else:
        new_text = (
            f"❌ Неправильно.\n\n"
            f"{correct_code} — это {region_name}.\n"
            f"<i>{regions[correct_code]['facts']}</i>"
        )

        img_path = get_image_path(correct_code)
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="▶️ Продолжить игру",
            callback_data="match_continue",
        ))
        builder.row(InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data="match_to_menu",
        ))

        if img_path:
            photo = FSInputFile(img_path)
            await callback.message.reply_photo(
                photo,
                caption=new_text,
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )
        else:
            await callback.message.reply(
                new_text,
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )

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

    builder.row(InlineKeyboardButton(
        text="🏠 В главное меню",
        callback_data="to_menu",
    ))

    text = (
        f"⚡ <b>Верно или неверно?</b>\n\n"
        f"Код <b>{code}</b> — это <b>{shown_name}</b>?\n\n"
        f"<i>{region['hint']}</i>"
    )

    users, user = get_user(user_id)
    user["quiz_state"] = {"code": code}
    save_users(users)

    # Отправляем с размытой картинкой
    blur_path = get_blur_path(code)
    if blur_path and is_cb:
        photo = FSInputFile(blur_path)
        await msg.edit_media(
            InputMediaPhoto(media=photo, caption=text, parse_mode="HTML"),
            reply_markup=builder.as_markup(),
        )
    elif blur_path:
        photo = FSInputFile(blur_path)
        await msg.answer_photo(
            photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
        )
    elif is_cb:
        await msg.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await msg.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

    if isinstance(update, types.CallbackQuery):
        await update.answer()

@dp.callback_query(F.data.startswith("tf_"))
async def handle_tf_answer(callback: types.CallbackQuery):
    if callback.data == "tf_continue":
        await send_truefalse_question(callback)
        return
    if callback.data == "tf_to_menu":
        await bot.send_message(
            chat_id=callback.from_user.id,
            text="🚗 Выбери режим тренировки:",
            reply_markup=to_menu_kb(),
        )
        await callback.answer()
        return

    parts = callback.data.split("_")
    code = parts[1]
    correct_answer = parts[2] == "True"
    user_answer = parts[3] == "true"

    is_correct = (correct_answer == user_answer)
    update_stats(str(callback.from_user.id), correct=is_correct)

    region_name = regions[code]["name"]
    if is_correct:
        await callback.answer(
            f"✅ Правильно! {code} — это {region_name}.",
            show_alert=True,
        )
        await send_truefalse_question(callback)
    else:
        new_text = (
            f"❌ Неправильно.\n\n"
            f"{code} — это {region_name}.\n"
            f"<i>{regions[code]['facts']}</i>"
        )

        img_path = get_image_path(code)
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text="▶️ Продолжить игру",
            callback_data="tf_continue",
        ))
        builder.row(InlineKeyboardButton(
            text="🏠 В главное меню",
            callback_data="tf_to_menu",
        ))

        if img_path:
            photo = FSInputFile(img_path)
            await callback.message.reply_photo(
                photo,
                caption=new_text,
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )
        else:
            await callback.message.reply(
                new_text,
                parse_mode="HTML",
                reply_markup=builder.as_markup(),
            )

# ========== РЕЖИМ 4: ЭКЗАМЕН ==========
@dp.callback_query(F.data == "mode_exam")
async def start_exam(callback: types.CallbackQuery):
    _, user = get_user(str(callback.from_user.id))
    pct = progress_percent(user)

    if pct < 70:
        await callback.answer(
            f"🔒 Экзамен закрыт! Нужно 70% правильных ответов. У тебя: {pct:.1f}%",
            show_alert=True,
        )
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
    builder.row(InlineKeyboardButton(
        text="🏠 В главное меню",
        callback_data="to_menu",
    ))

    text = (
        f"📝 <b>ЭКЗАМЕН</b> — введи название вручную\n\n"
        f"Код: <b>{code}</b>\n"
        f"Подсказка: <i>{region['hint']}</i>\n\n"
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
        await message.answer(
            "Используй кнопки меню для навигации. Напиши /start, чтобы начать заново.",
            reply_markup=to_menu_kb(),
        )
        return

    code = state["code"]
    region = regions[code]
    user_answer = message.text.strip().lower()
    correct_names = [region["name"].lower()]

    is_correct = any(name in user_answer or user_answer in name for name in correct_names)

    update_stats(str(message.chat.id), correct=is_correct)

    if is_correct:
        await message.answer(f"✅ Правильно! Это действительно {code} — {region['name']}.")
    else:
        await message.answer(f"❌ Неправильно. {code} — это {region['name']}.\n\n<i>{region['facts']}</i>")

    user["exam_state"] = None
    save_users(users)

    await asyncio.sleep(1)
    await send_exam_question(message)
    
@dp.callback_query(F.data == "match_continue")
async def match_continue(callback: types.CallbackQuery):
    await send_match_question(callback)

@dp.callback_query(F.data == "match_to_menu")
async def match_to_menu(callback: types.CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="🚗 Выбери режим тренировки:",
        reply_markup=to_menu_kb(),
    )
    await callback.answer()

@dp.callback_query(F.data == "to_menu")
async def to_menu(callback: types.CallbackQuery):
    await bot.send_message(
        chat_id=callback.from_user.id,
        text="🚗 Выбери режим тренировки:",
        reply_markup=to_menu_kb(),
    )
    await callback.answer()
    
# ========== ЗАПУСК ==========
async def main():
    IMAGES_DIR.mkdir(exist_ok=True)
    BLUR_DIR.mkdir(exist_ok=True)
    print(f"Бот запущен. Картинки: {IMAGES_DIR.absolute()}")
    print(f"Размытые превью: {BLUR_DIR.absolute()}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
