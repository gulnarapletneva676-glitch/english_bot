import logging
import asyncio
from aiogram import Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS, WORDS_PER_LESSON, TEST_OPTIONS
from database import Database
from keyboards import (
    main_menu, admin_menu, admin_panel, quiz_options,
    after_lesson, start_lesson_btn, admin_user_actions
)

logger = logging.getLogger(__name__)


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_word_english = State()
    waiting_word_russian = State()
    waiting_word_category = State()
    waiting_ban_id = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def get_menu(user_id: int):
    return admin_menu() if is_admin(user_id) else main_menu()


def register_handlers(dp: Dispatcher, db: Database):

    # ─────────────────────────────────────────
    # START
    # ─────────────────────────────────────────
    @dp.message(Command("start"))
    async def cmd_start(msg: Message):
        if await db.is_banned(msg.from_user.id):
            await msg.answer("🚫 Ты заблокирован.")
            return
        await db.register_user(
            msg.from_user.id,
            msg.from_user.username or "",
            msg.from_user.full_name or ""
        )
        text = (
            "👋 <b>Привет!</b> Добро пожаловать в English Trainer!\n\n"
            "📖 Я помогу тебе выучить английские слова.\n"
            "Каждый урок: <b>5 слов</b> → запоминание → <b>тест</b>.\n\n"
            "Жми <b>📚 Начать урок</b>, чтобы поехали!"
        )
        await msg.answer(text, reply_markup=get_menu(msg.from_user.id), parse_mode="HTML")

    # ─────────────────────────────────────────
    # PROFILE
    # ─────────────────────────────────────────
    @dp.message(lambda m: m.text == "👤 Профиль")
    async def cmd_profile(msg: Message):
        if await db.is_banned(msg.from_user.id):
            return
        user = await db.get_user(msg.from_user.id)
        if not user:
            await msg.answer("Сначала нажми /start")
            return
        total = await db.get_total_words()
        percent = round(user["words_learned"] / total * 100) if total else 0
        bar_filled = int(percent / 10)
        bar = "🟩" * bar_filled + "⬜" * (10 - bar_filled)
        role = "👑 Администратор" if is_admin(msg.from_user.id) else "👤 Пользователь"
        text = (
            f"<b>📋 Профиль</b>\n\n"
            f"🆔 ID: <code>{user['user_id']}</code>\n"
            f"👤 Имя: {user['full_name']}\n"
            f"🎭 Роль: {role}\n"
            f"📅 Дата регистрации: {user['registered_at'][:10]}\n\n"
            f"📚 Выучено слов: <b>{user['words_learned']}</b> / {total}\n"
            f"{bar} {percent}%"
        )
        await msg.answer(text, parse_mode="HTML")

    # ─────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────
    @dp.message(lambda m: m.text == "📊 Статистика")
    async def cmd_stats(msg: Message):
        if await db.is_banned(msg.from_user.id):
            return
        user = await db.get_user(msg.from_user.id)
        if not user:
            await msg.answer("Сначала нажми /start")
            return
        total = await db.get_total_words()
        text = (
            f"<b>📊 Твоя статистика</b>\n\n"
            f"✅ Выучено слов: <b>{user['words_learned']}</b>\n"
            f"📖 Всего слов в словаре: <b>{total}</b>\n"
            f"🎯 Прогресс: <b>{round(user['words_learned'] / total * 100) if total else 0}%</b>"
        )
        await msg.answer(text, parse_mode="HTML")

    # ─────────────────────────────────────────
    # HELP
    # ─────────────────────────────────────────
    @dp.message(lambda m: m.text == "ℹ️ Помощь")
    async def cmd_help(msg: Message):
        text = (
            "<b>ℹ️ Как работает бот</b>\n\n"
            "1️⃣ Нажми <b>📚 Начать урок</b>\n"
            "2️⃣ Бот покажет тебе 5 слов с переводами — запомни их!\n"
            "3️⃣ Потом нажми <b>✅ Начать тест!</b>\n"
            "4️⃣ Выбери правильный перевод для каждого слова\n"
            "5️⃣ В конце увидишь результат и выученные слова попадут в твой прогресс\n\n"
            "<b>Команды:</b>\n"
            "/start — перезапустить бота\n"
        )
        await msg.answer(text, parse_mode="HTML")

    # ─────────────────────────────────────────
    # LESSON START
    # ─────────────────────────────────────────
    @dp.message(lambda m: m.text == "📚 Начать урок")
    async def cmd_start_lesson(msg: Message):
        if await db.is_banned(msg.from_user.id):
            return
        await _start_lesson(msg.bot, msg.chat.id, msg.from_user.id, db)

    @dp.callback_query(lambda c: c.data == "start_lesson")
    async def cb_start_lesson(call: CallbackQuery):
        await call.answer()
        await _start_lesson(call.bot, call.message.chat.id, call.from_user.id, db)

    async def _start_lesson(bot: Bot, chat_id: int, user_id: int, db: Database):
        words = await db.get_random_words(user_id, WORDS_PER_LESSON)
        if not words:
            await bot.send_message(chat_id, "🎉 Ты выучил все слова! Скоро добавим новые.")
            return

        # Build lesson card
        lines = ["📖 <b>Слова на сегодня — запомни!</b>\n"]
        for i, w in enumerate(words, 1):
            lines.append(f"{i}. <b>{w['english']}</b> — {w['russian']}")
        lines.append("\nЧерез несколько секунд нажми кнопку чтобы начать тест 👇")
        text = "\n".join(lines)

        lesson_msg = await bot.send_message(
            chat_id, text,
            parse_mode="HTML",
            reply_markup=start_lesson_btn()
        )
        word_ids = [w["id"] for w in words]
        await db.save_session(user_id, word_ids, lesson_msg.message_id)

    @dp.callback_query(lambda c: c.data == "begin_quiz")
    async def cb_begin_quiz(call: CallbackQuery):
        await call.answer()
        user_id = call.from_user.id
        session = await db.get_session(user_id)
        if not session:
            await call.message.answer("Сначала начни урок 📚")
            return

        # Delete lesson card
        try:
            await call.bot.delete_message(call.message.chat.id, session["lesson_msg_id"])
        except Exception:
            pass

        await _send_quiz_question(call.bot, call.message.chat.id, user_id, db, session, 0, 0)

    # ─────────────────────────────────────────
    # QUIZ
    # ─────────────────────────────────────────
    async def _send_quiz_question(bot: Bot, chat_id: int, user_id: int, db: Database, session, index: int, correct: int):
        word_ids = [int(x) for x in session["lesson_word_ids"].split(",")]

        if index >= len(word_ids):
            # Lesson finished
            await _finish_lesson(bot, chat_id, user_id, db, word_ids, correct, len(word_ids))
            return

        word_id = word_ids[index]
        word = await db.get_word_by_id(word_id)
        exclude_ids = [word_id]

        wrong_translations = await db.get_random_translations(exclude_ids, TEST_OPTIONS - 1)
        options = [{"text": word["russian"], "is_correct": 1}]
        for t in wrong_translations:
            options.append({"text": t, "is_correct": 0})

        progress = f"❓ Вопрос {index + 1}/{len(word_ids)}"
        text = f"{progress}\n\n<b>{word['english']}</b>\n\nКак переводится это слово?"

        quiz_msg = await bot.send_message(
            chat_id, text,
            parse_mode="HTML",
            reply_markup=quiz_options(options, word_id)
        )
        await db.update_session_index(user_id, index, correct)
        await db.update_session_msg_id(user_id, quiz_msg.message_id)

    @dp.callback_query(lambda c: c.data.startswith("quiz_"))
    async def cb_quiz_answer(call: CallbackQuery):
        await call.answer()
        parts = call.data.split("_")
        word_id = int(parts[1])
        is_correct = int(parts[2])
        user_id = call.from_user.id

        session = await db.get_session(user_id)
        if not session:
            return

        index = session["current_test_index"]
        correct = session["correct_answers"]
        word_ids = [int(x) for x in session["lesson_word_ids"].split(",")]

        # Delete quiz message
        try:
            await call.bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

        if is_correct:
            correct += 1
            feedback = await call.bot.send_message(call.message.chat.id, "✅ <b>Правильно!</b>", parse_mode="HTML")
        else:
            word = await db.get_word_by_id(word_id)
            feedback = await call.bot.send_message(
                call.message.chat.id,
                f"❌ <b>Неверно.</b> Правильный ответ: <b>{word['russian']}</b>",
                parse_mode="HTML"
            )

        await asyncio.sleep(1.2)
        try:
            await call.bot.delete_message(call.message.chat.id, feedback.message_id)
        except Exception:
            pass

        await db.update_session_index(user_id, index + 1, correct)
        session_updated = await db.get_session(user_id)
        await _send_quiz_question(call.bot, call.message.chat.id, user_id, db, session_updated, index + 1, correct)

    async def _finish_lesson(bot: Bot, chat_id: int, user_id: int, db: Database, word_ids: list, correct: int, total: int):
        # Mark all words as learned
        for wid in word_ids:
            await db.mark_word_learned(user_id, wid)
        await db.delete_session(user_id)

        percent = round(correct / total * 100)
        if percent == 100:
            emoji = "🏆"
            grade = "Отлично! Ты знаешь все слова!"
        elif percent >= 60:
            emoji = "👍"
            grade = "Хороший результат! Продолжай!"
        else:
            emoji = "💪"
            grade = "Не сдавайся, повторяй снова!"

        text = (
            f"{emoji} <b>Урок завершён!</b>\n\n"
            f"✅ Правильных ответов: <b>{correct}/{total}</b> ({percent}%)\n"
            f"📚 Новых слов в копилке: <b>+{total}</b>\n\n"
            f"{grade}"
        )
        await bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=after_lesson())

    @dp.callback_query(lambda c: c.data == "main_menu")
    async def cb_main_menu(call: CallbackQuery):
        await call.answer()
        await call.message.answer("🏠 Главное меню", reply_markup=get_menu(call.from_user.id))

    # ─────────────────────────────────────────
    # ADMIN PANEL
    # ─────────────────────────────────────────
    @dp.message(lambda m: m.text == "🔧 Админ-панель" and is_admin(m.from_user.id))
    async def cmd_admin(msg: Message):
        await msg.answer("🔧 <b>Админ-панель</b>", parse_mode="HTML", reply_markup=admin_panel())

    @dp.callback_query(lambda c: c.data == "admin_stats" and is_admin(c.from_user.id))
    async def cb_admin_stats(call: CallbackQuery):
        await call.answer()
        stats = await db.get_stats()
        text = (
            f"<b>📈 Статистика бота</b>\n\n"
            f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
            f"🚫 Заблокировано: <b>{stats['banned']}</b>\n"
            f"📖 Слов в словаре: <b>{stats['total_words']}</b>\n"
            f"✅ Всего изучений: <b>{stats['total_learned']}</b>"
        )
        await call.message.answer(text, parse_mode="HTML")

    @dp.callback_query(lambda c: c.data == "admin_users" and is_admin(c.from_user.id))
    async def cb_admin_users(call: CallbackQuery):
        await call.answer()
        users = await db.get_all_users()
        lines = ["<b>👥 Пользователи (последние 20):</b>\n"]
        for u in users[:20]:
            ban = " 🚫" if u["is_banned"] else ""
            lines.append(
                f"• <code>{u['user_id']}</code> | {u['full_name'] or 'Без имени'}{ban} — {u['words_learned']} слов"
            )
        lines.append("\n💡 Чтобы забанить: /ban <code>ID</code>\nЧтобы разбанить: /unban <code>ID</code>")
        await call.message.answer("\n".join(lines), parse_mode="HTML")

    @dp.callback_query(lambda c: c.data == "admin_words" and is_admin(c.from_user.id))
    async def cb_admin_words(call: CallbackQuery):
        await call.answer()
        total = await db.get_total_words()
        text = (
            f"<b>📖 Управление словами</b>\n\n"
            f"Сейчас в словаре: <b>{total}</b> слов\n\n"
            f"Добавить слово: /addword\n"
            f"Удалить слово: /delword <code>ID</code>"
        )
        await call.message.answer(text, parse_mode="HTML")

    @dp.callback_query(lambda c: c.data == "admin_broadcast" and is_admin(c.from_user.id))
    async def cb_admin_broadcast(call: CallbackQuery, state: FSMContext):
        await call.answer()
        await call.message.answer("📢 Введи текст рассылки:")
        await state.set_state(AdminStates.waiting_broadcast)

    @dp.message(AdminStates.waiting_broadcast)
    async def process_broadcast(msg: Message, state: FSMContext):
        if not is_admin(msg.from_user.id):
            return
        users = await db.get_all_users()
        sent, failed = 0, 0
        for u in users:
            if u["is_banned"]:
                continue
            try:
                await msg.bot.send_message(u["user_id"], f"📢 <b>Сообщение от администратора:</b>\n\n{msg.text}", parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
        await state.clear()
        await msg.answer(f"✅ Отправлено: {sent}\n❌ Ошибок: {failed}")

    @dp.message(Command("ban"))
    async def cmd_ban(msg: Message):
        if not is_admin(msg.from_user.id):
            return
        parts = msg.text.split()
        if len(parts) < 2:
            await msg.answer("Использование: /ban <id>")
            return
        try:
            target_id = int(parts[1])
            await db.ban_user(target_id, True)
            await msg.answer(f"🚫 Пользователь {target_id} заблокирован.")
        except ValueError:
            await msg.answer("Неверный ID.")

    @dp.message(Command("unban"))
    async def cmd_unban(msg: Message):
        if not is_admin(msg.from_user.id):
            return
        parts = msg.text.split()
        if len(parts) < 2:
            await msg.answer("Использование: /unban <id>")
            return
        try:
            target_id = int(parts[1])
            await db.ban_user(target_id, False)
            await msg.answer(f"✅ Пользователь {target_id} разблокирован.")
        except ValueError:
            await msg.answer("Неверный ID.")

    @dp.message(Command("addword"))
    async def cmd_addword(msg: Message, state: FSMContext):
        if not is_admin(msg.from_user.id):
            return
        await msg.answer("Введи слово на английском:")
        await state.set_state(AdminStates.waiting_word_english)

    @dp.message(AdminStates.waiting_word_english)
    async def process_word_english(msg: Message, state: FSMContext):
        if not is_admin(msg.from_user.id):
            return
        await state.update_data(english=msg.text.strip().lower())
        await msg.answer("Теперь введи перевод на русском:")
        await state.set_state(AdminStates.waiting_word_russian)

    @dp.message(AdminStates.waiting_word_russian)
    async def process_word_russian(msg: Message, state: FSMContext):
        if not is_admin(msg.from_user.id):
            return
        await state.update_data(russian=msg.text.strip().lower())
        await msg.answer("Введи категорию (или нажми /skip для 'general'):")
        await state.set_state(AdminStates.waiting_word_category)

    @dp.message(Command("skip"), AdminStates.waiting_word_category)
    async def skip_category(msg: Message, state: FSMContext):
        data = await state.get_data()
        await db.add_word(data["english"], data["russian"], "general")
        await state.clear()
        await msg.answer(f"✅ Слово <b>{data['english']}</b> добавлено!", parse_mode="HTML")

    @dp.message(AdminStates.waiting_word_category)
    async def process_word_category(msg: Message, state: FSMContext):
        if not is_admin(msg.from_user.id):
            return
        data = await state.get_data()
        await db.add_word(data["english"], data["russian"], msg.text.strip().lower())
        await state.clear()
        await msg.answer(f"✅ Слово <b>{data['english']}</b> добавлено!", parse_mode="HTML")

    @dp.message(Command("delword"))
    async def cmd_delword(msg: Message):
        if not is_admin(msg.from_user.id):
            return
        parts = msg.text.split()
        if len(parts) < 2:
            await msg.answer("Использование: /delword <id>")
            return
        try:
            word_id = int(parts[1])
            word = await db.get_word_by_id(word_id)
            if not word:
                await msg.answer("Слово не найдено.")
                return
            await db.delete_word(word_id)
            await msg.answer(f"🗑 Слово <b>{word['english']}</b> удалено.", parse_mode="HTML")
        except ValueError:
            await msg.answer("Неверный ID.")
