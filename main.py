import sys
import logging
import asyncio
import os

from telethon import TelegramClient, events
from aiohttp import web
import config

# ================= LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ================= DIRS =================
os.makedirs(config.SESSION_DIR, exist_ok=True)
os.makedirs(config.LOG_DIR, exist_ok=True)

# ================= CHECK CREDS =================
if not config.API_ID or not config.API_HASH:
    logger.error("API_ID or API_HASH missing")
    sys.exit(1)

# ================= CLIENT =================
client = TelegramClient(
    config.SESSION_FILE,
    config.API_ID,
    config.API_HASH
)

# ================= CACHE =================
processed_messages = set()

# ================= APPROVED CHECK =================
def is_approved(text: str) -> bool:
    if not text:
        return False
    for keyword in config.APPROVED_KEYWORDS:
        if keyword.lower() in text.lower():
            return True
    return False

# ================= EVENT HANDLER =================
@client.on(events.NewMessage(chats=config.MONITORED_GROUPS))
@client.on(events.MessageEdited(chats=config.MONITORED_GROUPS))
async def handler(event):
    try:
        sender = await event.get_sender()
        if sender and sender.is_self:
            return

        text = event.message.text or event.message.raw_text

        if is_approved(text):
            chat_id = event.chat_id
            msg_id = event.id

            if (chat_id, msg_id) in processed_messages:
                return

            await client.send_message(
                config.TARGET_CHANNEL,
                text,
                file=event.message.media
            )

            processed_messages.add((chat_id, msg_id))
            logger.info(f"Approved message forwarded: {msg_id}")

    except Exception as e:
        logger.error(f"Handler error: {e}")

# ================= HEALTH SERVER (Koyeb Fix) =================
async def health_server():
    async def handle(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", handle)

    port = int(os.environ.get("PORT", 8000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info(f"Health server running on port {port}")

# ================= MAIN =================
async def main():
    print("Starting Power Bot...")
    logger.info("Starting Power Bot")

    await client.start(phone=config.PHONE_NUMBER)

    # 🔥 VERY IMPORTANT FOR KOYEB
    await health_server()

    print("Bot is running. Monitoring groups...")
    logger.info("Bot is running and monitoring groups.")

    await client.run_until_disconnected()

# ================= RUN =================
if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped")
