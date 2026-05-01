import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "123456789").split(",") if x.strip()]

# Количество слов в одном уроке
WORDS_PER_LESSON = 5

# Количество вариантов ответа в тесте
TEST_OPTIONS = 4

# Минимальная задержка между словами (секунды)
WORD_DISPLAY_DELAY = 2
