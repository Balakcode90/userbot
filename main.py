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
            return True
    return False

@client.on(events.NewMessage(chats=config.MONITORED_GROUPS))
@client.on(events.MessageEdited(chats=config.MONITORED_GROUPS))
async def handler(event):
    try:
        # Get sender
        sender = await event.get_sender()
        
        # Allow Bot API bots and Userbots, block only self
        if sender and sender.is_self:
            return

        # Extract full message text safely
        text = event.message.text or event.message.raw_text
        
        # Detect Approved results
        if is_approved(text):
            chat_id = event.chat_id
            message_id = event.id
            
            # Prevent duplicate posting
            if (chat_id, message_id) in processed_messages:
                return

            logger.info(f"Approved message detected in {chat_id} from {sender.id}")
            
            # Post FULL message content to private channel
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

# --- HEALTH SERVER LOGIC FOR KOYEB ---
# Koyeb requires a TCP/HTTP health check to keep a web service alive.
# Without this, the service will be marked as unhealthy and restarted or stopped.
async def handle_health_check(reader, writer):
    """
    Handles incoming HTTP requests for the health check.
    Returns a 200 OK response with a plain text body.
    """
    try:
        # Consume the request headers (not used but good practice to read)
        data = await reader.read(1024)
        
        # Construct a minimal HTTP 200 OK response
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 2\r\n"
            "Connection: close\r\n"
            "\r\n"
            "OK"
        )
        
        writer.write(response.encode('utf-8'))
        await writer.drain()
    except Exception as e:
        logger.error(f"Health check error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def start_health_server(host='0.0.0.0', port=8000):
    """
    Starts a minimal asynchronous TCP server to act as an HTTP health endpoint.
    This runs in parallel with the Telegram bot's event loop.
    """
    server = await asyncio.start_server(handle_health_check, host, port)
    addr = server.sockets[0].getsockname()
    logger.info(f"Health server listening on {addr}")
    
    async with server:
        await server.serve_forever()

async def main():
    print("Starting Power Bot with Health Server...")
    logger.info("Starting Power Bot and Health Server")
    
    # Start the health server in the background
    # This ensures Koyeb's health checks pass while the bot is initializing
    health_task = asyncio.create_task(start_health_server())
    
    # Start the Telegram client
    # This handles authentication and event processing
    await client.start(phone=config.PHONE_NUMBER)
    
    print("Bot is running. Monitoring groups...")
    logger.info("Bot is running and monitoring groups.")
    
    # Run both the client and health server concurrently
    # run_until_disconnected() keeps the main loop alive
    try:
        await client.run_until_disconnected()
    finally:
        # Cleanup tasks if the bot stops
        health_task.cancel()
        try:
            await health_task
        except asyncio.CancelledError:
            pass

if __name__ == '__main__':
    # Automatically install requirements
    try:
        import telethon
    except ImportError:
        print("Installing requirements...")
        import subprocess
        import sys
        requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])

    try:
        # Use the existing event loop from Telethon's client
        client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
    except Exception as e:
        logger.critical(f"Critical error in main: {e}")
