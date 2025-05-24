#!/usr/bin/env python3
"""
Telegram Userbot Channel Forwarder with multiple source-target pairs and referral links.
Preserves formatting, emojis, and entities while removing URLs and appending referral links.
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
from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
from telethon.tl.types import MessageEntityBold, MessageEntityItalic, MessageEntityCode, MessageEntityPre  # common entity types

# Flask keep-alive server
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "28490021"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "e01e2bf792f3dc911ad7a8a760bfa613")
STRING_SESSION = os.getenv("STRING_SESSION", None)

SOURCE_CHANNELS = [c.strip().lstrip('@') for c in os.getenv("SOURCE_CHANNELS", "").split(",") if c.strip()]
TARGET_CHANNELS = [c.strip().lstrip('@') for c in os.getenv("TARGET_CHANNELS", "").split(",") if c.strip()]
REFERRAL_LINKS = [r.strip() for r in os.getenv("REFERRAL_LINKS", "").split(",") if r.strip()]

# Validation
if not STRING_SESSION:
    print("ERROR: STRING_SESSION not set in .env")
    exit(1)

if not (len(SOURCE_CHANNELS) == len(TARGET_CHANNELS) == len(REFERRAL_LINKS)):
    print("ERROR: SOURCE_CHANNELS, TARGET_CHANNELS and REFERRAL_LINKS counts must be equal.")
    exit(1)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# URL regex pattern (backup to catch URLs not marked by entities)
URL_PATTERN = re.compile(r'https?://\S+')

# Mapping source_channel -> (target_channel, referral_link)
channel_map = {
    SOURCE_CHANNELS[i]: (TARGET_CHANNELS[i], REFERRAL_LINKS[i])
    for i in range(len(SOURCE_CHANNELS))
}

# In-memory message ID mapping for reply chaining
msg_id_map = {}

def remove_urls_and_adjust_entities(text, entities):
    """
    Remove URLs from text and adjust entities to preserve formatting & emojis.
    Removes entities corresponding to URLs and adjusts offsets of others.
    """
    if not text:
        return None, None

    # Collect URL spans from entities
    url_spans = []
    if entities:
        for ent in entities:
            if isinstance(ent, (MessageEntityTextUrl, MessageEntityUrl)):
                url_spans.append((ent.offset, ent.offset + ent.length))

    # Also catch URLs not marked by entities (rare but possible)
    # We only remove URLs in text that are not covered by entities (to avoid double removal)
    covered_spans = set()
    for start, end in url_spans:
        covered_spans.update(range(start, end))

    # Find URLs in text using regex that are NOT covered by entities
    for match in URL_PATTERN.finditer(text):
        start, end = match.span()
        if not any(pos in covered_spans for pos in range(start, end)):
            url_spans.append((start, end))

    # Sort spans reverse so we remove from end to start without messing up indices
    url_spans = sorted(url_spans, key=lambda x: x[0], reverse=True)

    cleaned_text = text
    for start, end in url_spans:
        cleaned_text = cleaned_text[:start] + cleaned_text[end:]

    # Adjust entities after removals
    adjusted_entities = []
    for ent in entities or []:
        # Skip URL entities because we removed their text
        if isinstance(ent, (MessageEntityTextUrl, MessageEntityUrl)):
            continue

        # Calculate how many characters removed before this entity's offset
        removed_before = 0
        for start, end in url_spans:
            if start < ent.offset:
                removed_before += (end - start)

        new_offset = ent.offset - removed_before
        if new_offset < 0:
            # Entity completely removed or shifted out of range
            continue

        # Adjust length if entity goes beyond new text length
        new_length = ent.length
        if new_offset + new_length > len(cleaned_text):
            new_length = len(cleaned_text) - new_offset
            if new_length <= 0:
                continue

        # Clone entity with updated offset and length - entities are immutable, create new instance
        # We do this by copying all fields but updating offset and length
        new_ent = type(ent)(
            offset=new_offset,
            length=new_length,
            **{k: getattr(ent, k) for k in ent.__slots__ if k not in ('offset', 'length')}
        )
        adjusted_entities.append(new_ent)

    cleaned_text = cleaned_text.strip()
    return cleaned_text if cleaned_text else None, adjusted_entities if adjusted_entities else None


async def send_preserving_entities(client, target, message, referral_link, reply_to_id=None):
    """
    Send message text/media preserving formatting & emojis,
    removing URLs and appending referral link.
    """
    text = message.text or message.message or ""
    entities = message.entities

    cleaned_text, adjusted_entities = remove_urls_and_adjust_entities(text, entities)

    # Build the full text cleanly with referral link appended
    if cleaned_text:
        # Ensure no trailing spaces or newlines at end of cleaned_text
        cleaned_text = cleaned_text.rstrip()
        full_text = f"{cleaned_text}\n\nRegister: {referral_link}"
    else:
        full_text = f"Register: {referral_link}"

    sent_msg = await client.send_message(
        target,
        full_text,
        entities=adjusted_entities,
        reply_to=reply_to_id,
        parse_mode=None
    )
    return sent_msg


@client.on(events.NewMessage(chats=[f"@{c}" for c in SOURCE_CHANNELS]))
async def handler(event):
    message = event.message
    chat = await event.get_chat()
    source = chat.username or str(chat.id)

    preview_text = (message.text or "")[:30]
    logger.info(f"Message received from @{source}: {preview_text}{'...' if len(message.text or '') > 30 else ''}")

    target, referral = channel_map.get(source, (None, None))
    if not target:
        logger.warning(f"No target mapping found for source @{source}")
        return

    try:
        reply_to_id = None
        if message.reply_to_msg_id:
            reply_to_id = msg_id_map.get(message.reply_to_msg_id)

        if message.media:
            # For media, process caption similarly preserving formatting & entities
            caption = message.text or message.message or ""
            caption_entities = message.entities
            cleaned_caption, adjusted_caption_entities = remove_urls_and_adjust_entities(caption, caption_entities)

            if cleaned_caption:
                caption_full = f"{cleaned_caption.rstrip()}\n\nRegister: {referral}"
            else:
                caption_full = f"Register: {referral}"

            sent_msg = await client.send_file(
                f"@{target}",
                file=message.media,
                caption=caption_full,
                caption_entities=adjusted_caption_entities,
                reply_to=reply_to_id
            )
            logger.info(f"Forwarded media message from @{source} to @{target} preserving formatting")
        else:
            sent_msg = await send_preserving_entities(client, f"@{target}", message, referral, reply_to_id)
            logger.info(f"Forwarded text message from @{source} to @{target} preserving formatting")

        if sent_msg:
            msg_id_map[message.id] = sent_msg.id

    except ChannelPrivateError:
        logger.error(f"Cannot access target channel @{target}. Check membership and permissions.")
    except ChatAdminRequiredError:
        logger.error(f"User needs admin rights in the target channel @{target}.")
    except FloodWaitError as e:
        logger.warning(f"Flood wait for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Error while forwarding message from @{source}: {e}", exc_info=True)

async def main():
    logger.info("Starting Telegram userbot...")
    logger.info(f"Monitoring source channels: {SOURCE_CHANNELS}")
    logger.info(f"Forwarding to target channels: {TARGET_CHANNELS}")
    logger.info(f"Using referral links: {REFERRAL_LINKS}")

    keep_alive()

    await client.start()
    logger.info("Userbot connected to Telegram!")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
