import sys
import logging
import asyncio
import os
from telethon import TelegramClient, events
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs(config.SESSION_DIR, exist_ok=True)
os.makedirs(config.LOG_DIR, exist_ok=True)

# Check for credentials
if not config.API_ID or not config.API_HASH:
    logger.error("API_ID and API_HASH must be set in environment variables or .env file")
    print("Please set API_ID and API_HASH environment variables.")
    sys.exit(1)

# Initialize Client
client = TelegramClient(
    config.SESSION_FILE,
    config.API_ID,
    config.API_HASH
)

# Deduplication cache: (chat_id, message_id)
processed_messages = set()

def is_approved(text):
    if not text:
        return False
    
    # Check for keywords
    for keyword in config.APPROVED_KEYWORDS:
        if keyword in text:
            # check for false positives if needed, but requirements say "Ignore Declined / Failed / Processing"
            # which is implicit if we only look for Approved. 
            # However, ensure we don't pick up "Not Approved" if that was a thing, 
            # but the task list is specific about the positive match.
            return True
    return False

@client.on(events.NewMessage(chats=config.MONITORED_GROUPS))
@client.on(events.MessageEdited(chats=config.MONITORED_GROUPS))
async def handler(event):
    try:
        # Get sender
        sender = await event.get_sender()
        
        # 2. Allow Bot API bots and Userbots, block only self
        if sender and sender.is_self:
            return

        # 4. Extract full message text safely
        text = event.message.text or event.message.raw_text
        
        # 5. Detect Approved results
        if is_approved(text):
            chat_id = event.chat_id
            message_id = event.id
            
            # 8. Prevent duplicate posting
            # For edited messages, we might have processed the "NewMessage" version if it was already approved?
            # Or if it changed from Processing -> Approved.
            # If we already processed this message ID as approved, skip.
            if (chat_id, message_id) in processed_messages:
                return

            logger.info(f"Approved message detected in {chat_id} from {sender.id}")
            
            # 7. Post FULL message content to private channel
            # Send as NEW message (no forward tag)
            try:
                await client.send_message(
                    config.TARGET_CHANNEL,
                    text,
                    file=event.message.media
                )
                
                # Mark as processed
                processed_messages.add((chat_id, message_id))
                
                # Log success
                logger.info(f"Forwarded Approved message {message_id} to channel {config.TARGET_CHANNEL}")
                
            except Exception as e:
                logger.error(f"Failed to send message to target channel: {e}")

    except Exception as e:
        logger.error(f"Error processing event: {e}")

async def main():
    print("Starting Power Bot...")
    logger.info("Starting Power Bot")
    
    # Start the client
    # This will prompt for phone number and code on first run if not authorized
    # If the user has 2FA enabled but wants to login with just code,
    # we use the standard start() which handles interactive password prompt if needed.
    await client.start(phone=config.PHONE_NUMBER)
    
    print("Bot is running. Monitoring groups...")
    logger.info("Bot is running and monitoring groups.")
    
    # Run until disconnected
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Automatically install requirements
    try:
        import telethon
        import dotenv
    except ImportError:
        print("Installing requirements...")
        import subprocess
        import sys
        requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])

    try:
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
