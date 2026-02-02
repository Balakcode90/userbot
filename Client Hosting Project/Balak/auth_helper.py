import os
import sys
import asyncio
import json
from telethon import TelegramClient
import config

async def send_code():
    # Initialize client with the same session file main.py uses
    client = TelegramClient(config.SESSION_FILE, config.API_ID, config.API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print(f"Sending code to {config.PHONE_NUMBER}...")
        try:
            # This sends the code
            sent = await client.send_code_request(config.PHONE_NUMBER)
            # We need to save phone_code_hash to use it later
            # Also save the session itself which is updated by connect()
            with open('pvn/auth_state.json', 'w') as f:
                json.dump({'phone_code_hash': sent.phone_code_hash}, f)
            print("Code sent successfully.")
        except Exception as e:
            print(f"Failed to send code: {e}")
    else:
        print("Already authorized.")
    
    await client.disconnect()

async def login(code, password=None):
    client = TelegramClient(config.SESSION_FILE, config.API_ID, config.API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        try:
            if not os.path.exists('pvn/auth_state.json'):
                print("No auth state found. Please run send_code first.")
                sys.exit(1)
                
            with open('pvn/auth_state.json', 'r') as f:
                data = json.load(f)
                phone_code_hash = data['phone_code_hash']
            
            print(f"Signing in with code {code}...")
            try:
                await client.sign_in(config.PHONE_NUMBER, code, phone_code_hash=phone_code_hash)
            except Exception as e:
                if "Two-steps verification" in str(e) or "password" in str(e).lower():
                    if password:
                        print("2FA required, using provided password...")
                        await client.sign_in(password=password)
                    else:
                        print("2FA Password required. Please provide password as third argument.")
                        sys.exit(1)
                else:
                    raise e
            print("Login successful!")
        except Exception as e:
            print(f"Login failed: {e}")
            sys.exit(1)
    else:
        print("Already authorized.")
    
    await client.disconnect()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auth_helper.py [send_code|login] [code] [password]")
        sys.exit(1)
    
    action = sys.argv[1]
    if action == "send_code":
        # Ensure directory for session exists
        os.makedirs(config.SESSION_DIR, exist_ok=True)
        asyncio.run(send_code())
    elif action == "login":
        if len(sys.argv) < 3:
            print("Missing code")
            sys.exit(1)
        code = sys.argv[2]
        password = sys.argv[3] if len(sys.argv) > 3 else None
        asyncio.run(login(code, password))
