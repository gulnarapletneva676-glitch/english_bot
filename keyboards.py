from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import random


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Начать урок"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Начать урок"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="ℹ️ Помощь")],
            [KeyboardButton(text="🔧 Админ-панель")],
        ],
        resize_keyboard=True
    )


def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="📖 Управление словами", callback_data="admin_words")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📈 Общая статистика", callback_data="admin_stats")],
    ])


def quiz_options(options: list, word_id: int) -> InlineKeyboardMarkup:
    """Shuffle and create answer buttons."""
    random.shuffle(options)
    buttons = []
    for opt in options:
        buttons.append([InlineKeyboardButton(
            text=opt["text"],
            callback_data=f"quiz_{word_id}_{opt['is_correct']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def after_lesson() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё урок", callback_data="start_lesson")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
    ])


def start_lesson_btn() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Начать тест!", callback_data="begin_quiz")],
    ])


def admin_user_actions(target_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_text = "✅ Разбанить" if is_banned else "🚫 Забанить"
    ban_cb = f"admin_unban_{target_id}" if is_banned else f"admin_ban_{target_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=ban_text, callback_data=ban_cb)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")],
    ])
