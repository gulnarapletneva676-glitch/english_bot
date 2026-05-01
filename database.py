import aiosqlite
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
DB_PATH = "english_bot.db"


class Database:
    def __init__(self):
        self.db_path = DB_PATH

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    registered_at TEXT NOT NULL,
                    words_learned INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    english TEXT NOT NULL,
                    russian TEXT NOT NULL,
                    category TEXT DEFAULT 'general'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER,
                    word_id INTEGER,
                    learned_at TEXT,
                    PRIMARY KEY (user_id, word_id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (word_id) REFERENCES words(id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    user_id INTEGER PRIMARY KEY,
                    lesson_word_ids TEXT,
                    current_test_index INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    lesson_msg_id INTEGER
                )
            """)
            await db.commit()
            await self._seed_words(db)
            logger.info("Database initialized.")

    async def _seed_words(self, db):
        count = await db.execute("SELECT COUNT(*) FROM words")
        row = await count.fetchone()
        if row[0] > 0:
            return

        words = [
            # A1 Basic
            ("apple", "яблоко", "food"), ("book", "книга", "objects"), ("cat", "кошка", "animals"),
            ("dog", "собака", "animals"), ("house", "дом", "places"), ("water", "вода", "food"),
            ("sun", "солнце", "nature"), ("moon", "луна", "nature"), ("tree", "дерево", "nature"),
            ("car", "машина", "transport"), ("bus", "автобус", "transport"), ("train", "поезд", "transport"),
            ("school", "школа", "places"), ("city", "город", "places"), ("country", "страна", "places"),
            ("mother", "мать", "family"), ("father", "отец", "family"), ("brother", "брат", "family"),
            ("sister", "сестра", "family"), ("friend", "друг", "people"),
            # A2
            ("beautiful", "красивый", "adjectives"), ("strong", "сильный", "adjectives"),
            ("happy", "счастливый", "adjectives"), ("sad", "грустный", "adjectives"),
            ("fast", "быстрый", "adjectives"), ("slow", "медленный", "adjectives"),
            ("big", "большой", "adjectives"), ("small", "маленький", "adjectives"),
            ("hot", "горячий", "adjectives"), ("cold", "холодный", "adjectives"),
            ("morning", "утро", "time"), ("evening", "вечер", "time"), ("night", "ночь", "time"),
            ("yesterday", "вчера", "time"), ("tomorrow", "завтра", "time"),
            ("always", "всегда", "adverbs"), ("never", "никогда", "adverbs"),
            ("often", "часто", "adverbs"), ("sometimes", "иногда", "adverbs"),
            ("already", "уже", "adverbs"),
            # B1
            ("experience", "опыт", "general"), ("knowledge", "знание", "general"),
            ("opportunity", "возможность", "general"), ("challenge", "вызов", "general"),
            ("success", "успех", "general"), ("failure", "неудача", "general"),
            ("decision", "решение", "general"), ("problem", "проблема", "general"),
            ("solution", "решение", "general"), ("improvement", "улучшение", "general"),
            ("relationship", "отношения", "people"), ("communication", "общение", "people"),
            ("responsibility", "ответственность", "people"), ("achievement", "достижение", "people"),
            ("confidence", "уверенность", "people"), ("patience", "терпение", "people"),
            ("courage", "смелость", "people"), ("wisdom", "мудрость", "people"),
            ("freedom", "свобода", "abstract"), ("justice", "справедливость", "abstract"),
            # B2
            ("acknowledge", "признавать", "verbs"), ("accomplish", "достигать", "verbs"),
            ("demonstrate", "демонстрировать", "verbs"), ("establish", "устанавливать", "verbs"),
            ("evaluate", "оценивать", "verbs"), ("implement", "внедрять", "verbs"),
            ("negotiate", "переговаривать", "verbs"), ("persuade", "убеждать", "verbs"),
            ("recommend", "рекомендовать", "verbs"), ("summarize", "резюмировать", "verbs"),
            ("significant", "значительный", "adjectives"), ("essential", "необходимый", "adjectives"),
            ("innovative", "инновационный", "adjectives"), ("comprehensive", "всесторонний", "adjectives"),
            ("efficient", "эффективный", "adjectives"), ("flexible", "гибкий", "adjectives"),
            ("ambitious", "амбициозный", "adjectives"), ("reliable", "надёжный", "adjectives"),
            ("sophisticated", "сложный", "adjectives"), ("transparent", "прозрачный", "adjectives"),
        ]

        await db.executemany(
            "INSERT INTO words (english, russian, category) VALUES (?, ?, ?)",
            words
        )
        await db.commit()
        logger.info(f"Seeded {len(words)} words into database.")

    # ---- USERS ----

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            return await cur.fetchone()

    async def register_user(self, user_id: int, username: str, full_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username, full_name, registered_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, username, full_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            await db.commit()

    async def get_all_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM users ORDER BY registered_at DESC")
            return await cur.fetchall()

    async def ban_user(self, user_id: int, ban: bool):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if ban else 0, user_id))
            await db.commit()

    async def is_banned(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return bool(user and user["is_banned"])

    # ---- WORDS ----

    async def get_random_words(self, user_id: int, count: int) -> list:
        """Get words the user hasn't learned yet."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("""
                SELECT w.* FROM words w
                WHERE w.id NOT IN (
                    SELECT word_id FROM user_progress WHERE user_id = ?
                )
                ORDER BY RANDOM()
                LIMIT ?
            """, (user_id, count))
            rows = await cur.fetchall()
            if len(rows) < count:
                # Reset if all words learned
                cur2 = await db.execute("SELECT * FROM words ORDER BY RANDOM() LIMIT ?", (count,))
                rows = await cur2.fetchall()
            return [dict(r) for r in rows]

    async def get_random_translations(self, exclude_ids: list, count: int) -> list:
        """Get wrong answer options for quiz."""
        async with aiosqlite.connect(self.db_path) as db:
            placeholders = ",".join("?" * len(exclude_ids))
            cur = await db.execute(
                f"SELECT russian FROM words WHERE id NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT ?",
                (*exclude_ids, count)
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows]

    async def mark_word_learned(self, user_id: int, word_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO user_progress (user_id, word_id, learned_at)
                VALUES (?, ?, ?)
            """, (user_id, word_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            await db.execute("""
                UPDATE users SET words_learned = words_learned + 1
                WHERE user_id = ? AND NOT EXISTS (
                    SELECT 1 FROM user_progress WHERE user_id = ? AND word_id = ?
                )
            """, (user_id, user_id, word_id))
            await db.execute("""
                UPDATE users SET words_learned = (
                    SELECT COUNT(*) FROM user_progress WHERE user_id = ?
                ) WHERE user_id = ?
            """, (user_id, user_id))
            await db.commit()

    async def get_total_words(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM words")
            row = await cur.fetchone()
            return row[0]

    # ---- SESSIONS ----

    async def save_session(self, user_id: int, word_ids: list, lesson_msg_id: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            ids_str = ",".join(str(i) for i in word_ids)
            await db.execute("""
                INSERT OR REPLACE INTO user_sessions
                (user_id, lesson_word_ids, current_test_index, correct_answers, lesson_msg_id)
                VALUES (?, ?, 0, 0, ?)
            """, (user_id, ids_str, lesson_msg_id))
            await db.commit()

    async def get_session(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM user_sessions WHERE user_id = ?", (user_id,))
            return await cur.fetchone()

    async def update_session_index(self, user_id: int, index: int, correct: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE user_sessions SET current_test_index = ?, correct_answers = ?
                WHERE user_id = ?
            """, (index, correct, user_id))
            await db.commit()

    async def update_session_msg_id(self, user_id: int, msg_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE user_sessions SET lesson_msg_id = ? WHERE user_id = ?", (msg_id, user_id))
            await db.commit()

    async def delete_session(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM user_sessions WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_word_by_id(self, word_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM words WHERE id = ?", (word_id,))
            return await cur.fetchone()

    async def add_word(self, english: str, russian: str, category: str = "general"):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO words (english, russian, category) VALUES (?, ?, ?)",
                (english, russian, category)
            )
            await db.commit()

    async def delete_word(self, word_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM words WHERE id = ?", (word_id,))
            await db.execute("DELETE FROM user_progress WHERE word_id = ?", (word_id,))
            await db.commit()

    async def get_stats(self):
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cur.fetchone())[0]
            cur = await db.execute("SELECT COUNT(*) FROM words")
            total_words = (await cur.fetchone())[0]
            cur = await db.execute("SELECT COUNT(*) FROM user_progress")
            total_learned = (await cur.fetchone())[0]
            cur = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
            banned = (await cur.fetchone())[0]
            return {
                "total_users": total_users,
                "total_words": total_words,
                "total_learned": total_learned,
                "banned": banned,
            }
