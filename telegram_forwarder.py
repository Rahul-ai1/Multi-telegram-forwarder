#!/usr/bin/env python3
"""
Telegram Userbot Channel Forwarder

Monitors a source channel using a user session,
removes links, adds a referral, and forwards to a target channel.
Handles reply chaining and preserves formatting.
"""

from flask import Flask
from threading import Thread
import os
import re
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, ChatAdminRequiredError, FloodWaitError
from dotenv import load_dotenv
from telethon.sessions import StringSession

# Flask server to keep Replit alive
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram credentials (User session, no bot token!)
API_ID = int(os.getenv("TELEGRAM_API_ID", "28490021"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "e01e2bf792f3dc911ad7a8a760bfa613")

# Channels and referral
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "besttrade7555").lstrip('@')
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "Ram_Earning_club").lstrip('@')
REFERRAL_LINK = os.getenv("REFERRAL_LINK", "https://www.dreamwingo.in/#/register?invitationCode=26372407203")

# URL removal regex
URL_PATTERN = re.compile(r'(https?://\S+)')

# In-memory map of source_msg_id → target_msg_id
msg_id_map = {}

def process_text(text):
    """Removes URLs and appends referral link."""
    if not text:
        return None
    text = URL_PATTERN.sub('', text).strip()
    if text:
        text += f"\n\nRegister: {REFERRAL_LINK}"
    return text

async def main():
    STRING_SESSION = os.getenv("STRING_SESSION", None)
    if not STRING_SESSION:
        logger.error("No STRING_SESSION found in environment. Please set it in .env")
        exit(1)

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

    @client.on(events.NewMessage(chats=f"@{SOURCE_CHANNEL}"))
    async def handler(event):
        message = event.message
        text = message.text or message.message or ""
        reply_to = message.reply_to_msg_id

        logger.info(f"New message received: {text[:30]}{'...' if len(text) > 30 else ''}")

        try:
            edited_text = process_text(text)

            # Safe snippet for logging processed text
            if edited_text:
                snippet = edited_text[:30] + ("..." if len(edited_text) > 30 else "")
            else:
                snippet = "None"
            logger.info(f"Processed text: {snippet}")

            # Try to map reply in target channel
            target_reply_id = None
            if reply_to and reply_to in msg_id_map:
                target_reply_id = msg_id_map[reply_to]

            # Forward media or text with reply
            if message.media:
                sent = await client.send_file(
                    f"@{TARGET_CHANNEL}",
                    file=message.media,
                    caption=edited_text or "",
                    reply_to=target_reply_id
                )
                logger.info("Forwarded media message with reply and caption")
            else:
                if edited_text:
                    sent = await client.send_message(
                        f"@{TARGET_CHANNEL}",
                        edited_text,
                        reply_to=target_reply_id
                    )
                    logger.info("Forwarded text message with reply")

            # Save source → target message ID mapping
            if sent:
                msg_id_map[message.id] = sent.id
                logger.info(f"Mapped source_msg_id {message.id} → target_msg_id {sent.id}")

        except ChannelPrivateError:
            logger.error(f"Cannot access the target channel @{TARGET_CHANNEL}. Make sure you're a member.")
        except ChatAdminRequiredError:
            logger.error(f"User needs admin rights in the target channel @{TARGET_CHANNEL}.")
        except FloodWaitError as e:
            logger.warning(f"Rate limit exceeded. Waiting {e.seconds} seconds.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error forwarding message: {e}", exc_info=True)

    try:
        logger.info("Starting Telegram Userbot...")
        logger.info(f"Monitoring source channel: @{SOURCE_CHANNEL}")
        logger.info(f"Forwarding to target channel: @{TARGET_CHANNEL}")
        logger.info(f"Referral link being used: {REFERRAL_LINK}")

        keep_alive()
        await client.start()
        logger.info("Userbot successfully connected to Telegram!")
        await client.run_until_disconnected()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
