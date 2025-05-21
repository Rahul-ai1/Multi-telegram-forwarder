#!/usr/bin/env python3
"""
Telegram Channel Message Forwarder

This script monitors a source Telegram channel for new messages,
removes any links in the message text, adds a referral link,
and forwards the modified message to a target channel.
"""

import os
import re
import logging
import asyncio
import sys
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, ChatAdminRequiredError, FloodWaitError
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get credentials from environment variables with fallbacks to the provided values
API_ID = int(os.getenv("TELEGRAM_API_ID", "28490021"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "e01e2bf792f3dc911ad7a8a760bfa613")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7570183181:AAHuq5azJ5R0JA_sv2LRzRiYkSejtmWHwtk")

# Channel information
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "besttrade7555")
TARGET_CHANNEL = os.getenv("TARGET_CHANNEL", "Ram_Earning_club")

# Referral link
REFERRAL_LINK = os.getenv("REFERRAL_LINK", "https://www.dreamwingo.in/#/register?invitationCode=26372407203")

# Remove the @ if present in channel usernames
SOURCE_CHANNEL = SOURCE_CHANNEL.lstrip('@')
TARGET_CHANNEL = TARGET_CHANNEL.lstrip('@')

# Regular expression to match URLs
URL_PATTERN = re.compile(r'(https?://\S+)')

# Process text: remove links, append referral
def process_text(text):
    """
    Process the message text:
    1. Remove any URLs
    2. Append the referral link
    
    Args:
        text (str): The original message text
        
    Returns:
        str: The processed text with referral link appended
    """
    if not text:
        return None
        
    # Remove URLs
    text = URL_PATTERN.sub('', text).strip()
    
    # Add referral link if text is not empty
    if text:
        text += f"\n\nRegister: {REFERRAL_LINK}"
        
    return text

async def main():
    """Main function to run the Telegram forwarder bot"""
    # Create client session
    client = TelegramClient('forwarder_session', API_ID, API_HASH)
    
    # Register event handler before starting the client
    @client.on(events.NewMessage(chats=f"@{SOURCE_CHANNEL}"))
    async def handler(event):
        """Handle new messages from the source channel"""
        message = event.message
        text = message.text or ""
        
        try:
            edited_text = process_text(text)
            
            logger.info(f"Processing message: {text[:30]}{'...' if len(text) > 30 else ''}")
            
            if message.media:
                await client.send_file(
                    f"@{TARGET_CHANNEL}",
                    file=message.media,
                    caption=edited_text if edited_text else ""
                )
                logger.info("Forwarded media message with edited caption")
            else:
                if edited_text:
                    await client.send_message(f"@{TARGET_CHANNEL}", edited_text)
                    logger.info("Forwarded text message with edits")
                
        except ChannelPrivateError:
            logger.error(f"Cannot access the target channel @{TARGET_CHANNEL}. Make sure the bot is a member.")
        except ChatAdminRequiredError:
            logger.error(f"Bot needs admin rights in the target channel @{TARGET_CHANNEL} to send messages.")
        except FloodWaitError as e:
            logger.warning(f"Rate limit exceeded. Waiting for {e.seconds} seconds before retrying.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Error forwarding message: {e}", exc_info=True)

    try:
        logger.info("Starting Telegram Forwarder Bot...")
        logger.info(f"Monitoring source channel: @{SOURCE_CHANNEL}")
        logger.info(f"Forwarding to target channel: @{TARGET_CHANNEL}")
        logger.info(f"Referral link being used: {REFERRAL_LINK}")
        
        # Connect to Telegram with bot token
        # Non-awaitable version for client.start
        client.start(bot_token=BOT_TOKEN)
        logger.info("Bot successfully connected to Telegram!")
        
        # Use the synchronous version for running until disconnected
        client.run_until_disconnected()
        return client
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        # For non-async entry point, we don't use asyncio.run
        # Create the client and start it
        client = TelegramClient('forwarder_session', API_ID, API_HASH)
        
        # Register event handler for messages
        @client.on(events.NewMessage(chats=f"@{SOURCE_CHANNEL}"))
        async def handler(event):
            """Handle new messages from the source channel"""
            message = event.message
            text = message.text or ""
            
            try:
                edited_text = process_text(text)
                
                logger.info(f"Processing message: {text[:30]}{'...' if len(text) > 30 else ''}")
                
                if message.media:
                    await client.send_file(
                        f"@{TARGET_CHANNEL}",
                        file=message.media,
                        caption=edited_text if edited_text else ""
                    )
                    logger.info("Forwarded media message with edited caption")
                else:
                    if edited_text:
                        await client.send_message(f"@{TARGET_CHANNEL}", edited_text)
                        logger.info("Forwarded text message with edits")
                    
            except ChannelPrivateError:
                logger.error(f"Cannot access the target channel @{TARGET_CHANNEL}. Make sure the bot is a member.")
            except ChatAdminRequiredError:
                logger.error(f"Bot needs admin rights in the target channel @{TARGET_CHANNEL} to send messages.")
            except FloodWaitError as e:
                logger.warning(f"Rate limit exceeded. Waiting for {e.seconds} seconds before retrying.")
            except Exception as e:
                logger.error(f"Error forwarding message: {e}", exc_info=True)
        
        logger.info("Starting Telegram Forwarder Bot...")
        logger.info(f"Monitoring source channel: @{SOURCE_CHANNEL}")
        logger.info(f"Forwarding to target channel: @{TARGET_CHANNEL}")
        logger.info(f"Referral link being used: {REFERRAL_LINK}")
        
        # Start the client
        client.start(bot_token=BOT_TOKEN)
        logger.info("Bot successfully connected to Telegram!")
        
        # Run the client until disconnected
        client.run_until_disconnected()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
