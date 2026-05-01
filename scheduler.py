import asyncio
import logging
from datetime import datetime
from aiogram import Bot
from database import Database

logger = logging.getLogger(__name__)


async def daily_reminder(bot: Bot, db: Database):
    """Send daily reminder to all users at 10:00."""
    while True:
        now = datetime.now()
        # Check if it's around 10:00 AM
        if now.hour == 10 and now.minute == 0:
            logger.info("Sending daily reminders...")
            users = await db.get_all_users()
            sent = 0
            for user in users:
                if user["is_banned"]:
                    continue
                try:
                    await bot.send_message(
                        user["user_id"],
                        "🌅 <b>Доброе утро!</b>\n\nВремя учить английские слова! Нажми 📚 <b>Начать урок</b>.",
                        parse_mode="HTML"
                    )
                    sent += 1
                    await asyncio.sleep(0.05)  # Avoid flood
                except Exception as e:
                    logger.warning(f"Could not send reminder to {user['user_id']}: {e}")
            logger.info(f"Sent reminders to {sent} users.")
            await asyncio.sleep(60)  # Wait a minute to avoid double-sending
        else:
            await asyncio.sleep(30)  # Check every 30 seconds


async def start_scheduler(bot: Bot, db: Database):
    asyncio.create_task(daily_reminder(bot, db))
    logger.info("Scheduler started.")
