#!/usr/bin/env python3
"""
Telegram Userbot Channel Forwarder with multiple source-target pairs and referral links.
Preserves formatting, emojis, and entities while removing URLs and appending referral links.

Now supports private target channels by using channel IDs (no '@' prefix).
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
from telethon.tl.types import (
    MessageEntityTextUrl, MessageEntityUrl,
    MessageEntityBold, MessageEntityItalic,
    MessageEntityCode, MessageEntityPre
)

# Flask keep-alive server
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=8081)

def keep_alive():
    Thread(target=run).start()

# Load environment variables
load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "28490021"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "e01e2bf792f3dc911ad7a8a760bfa613")
STRING_SESSION = os.getenv("STRING_SESSION", None)

SOURCE_CHANNELS = [c.strip() for c in os.getenv("SOURCE_CHANNELS", "").split(",") if c.strip()]
TARGET_CHANNELS = [c.strip() for c in os.getenv("TARGET_CHANNELS", "").split(",") if c.strip()]
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

URL_PATTERN = re.compile(r'https?://\S+')

channel_map = {
    SOURCE_CHANNELS[i]: (TARGET_CHANNELS[i], REFERRAL_LINKS[i])
    for i in range(len(SOURCE_CHANNELS))
}

msg_id_map = {}

def remove_urls_and_adjust_entities(text, entities):
    if not text:
        return None, None

    url_spans = []
    if entities:
        for ent in entities:
            if isinstance(ent, (MessageEntityTextUrl, MessageEntityUrl)):
                url_spans.append((ent.offset, ent.offset + ent.length))

    covered_spans = set()
    for start, end in url_spans:
        covered_spans.update(range(start, end))

    for match in URL_PATTERN.finditer(text):
        start, end = match.span()
        if not any(pos in covered_spans for pos in range(start, end)):
            url_spans.append((start, end))

    url_spans = sorted(url_spans, key=lambda x: x[0], reverse=True)

    cleaned_text = text
    for start, end in url_spans:
        cleaned_text = cleaned_text[:start] + cleaned_text[end:]

    adjusted_entities = []
    for ent in entities or []:
        if isinstance(ent, (MessageEntityTextUrl, MessageEntityUrl)):
            continue

        removed_before = 0
        for start, end in url_spans:
            if start < ent.offset:
                removed_before += (end - start)

        new_offset = ent.offset - removed_before
        if new_offset < 0:
            continue

        new_length = ent.length
        if new_offset + new_length > len(cleaned_text):
            new_length = len(cleaned_text) - new_offset
            if new_length <= 0:
                continue

        new_ent = type(ent)(
            offset=new_offset,
            length=new_length,
            **{k: v for k, v in vars(ent).items() if k not in ('offset', 'length')}
        )
        adjusted_entities.append(new_ent)

    cleaned_text = cleaned_text.strip()
    return cleaned_text if cleaned_text else None, adjusted_entities if adjusted_entities else None

def entities_to_markdown(text, entities):
    """
    Simple converter from Telegram entities to Markdown formatting.
    """
    if not entities:
        return text

    entities = sorted(entities, key=lambda e: e.offset, reverse=True)

    for ent in entities:
        start = ent.offset
        end = start + ent.length
        substring = text[start:end]

        if isinstance(ent, MessageEntityBold):
            md = f"**{substring}**"
        elif isinstance(ent, MessageEntityItalic):
            md = f"*{substring}*"
        elif isinstance(ent, MessageEntityCode):
            md = f"`{substring}`"
        elif isinstance(ent, MessageEntityPre):
            md = f"```\n{substring}\n```"
        elif isinstance(ent, MessageEntityTextUrl):
            md = f"[{substring}]({ent.url})"
        elif isinstance(ent, MessageEntityUrl):
            md = f"[{substring}]({substring})"
        else:
            md = substring

        text = text[:start] + md + text[end:]

    return text

async def send_preserving_entities(client, target, message, referral_link, reply_to_id=None):
    text = message.text or message.message or ""
    entities = message.entities

    cleaned_text, adjusted_entities = remove_urls_and_adjust_entities(text, entities)

    if cleaned_text:
        cleaned_text = cleaned_text.rstrip()
        md_text = entities_to_markdown(cleaned_text, adjusted_entities)
        full_text = f"{md_text}\n\nRegister: {referral_link}"
    else:
        full_text = f"Register: {referral_link}"

    sent_msg = await client.send_message(
        target,
        full_text,
        reply_to=reply_to_id,
        parse_mode='md'
    )
    return sent_msg

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def handler(event):
    message = event.message
    chat = await event.get_chat()
    source = chat.username or str(chat.id)

    preview_text = (message.text or "")[:30]
    logger.info(f"Message received from {source}: {preview_text}{'...' if len(message.text or '') > 30 else ''}")

    target, referral = channel_map.get(source, (None, None))
    if not target:
        logger.warning(f"No target mapping found for source {source}")
        return

    try:
        reply_to_id = None
        if message.reply_to_msg_id:
            reply_to_id = msg_id_map.get(message.reply_to_msg_id)

        if message.media:
            caption = message.text or message.message or ""
            caption_entities = message.entities
            cleaned_caption, adjusted_caption_entities = remove_urls_and_adjust_entities(caption, caption_entities)

            if cleaned_caption:
                md_caption = entities_to_markdown(cleaned_caption.rstrip(), adjusted_caption_entities)
                caption_full = f"{md_caption}\n\nRegister: {referral}"
            else:
                caption_full = f"Register: {referral}"

            sent_msg = await client.send_file(
                target,
                file=message.media,
                caption=caption_full,
                reply_to=reply_to_id,
                parse_mode='md'
            )
            logger.info(f"Forwarded media message from {source} to {target} preserving formatting")
        else:
            sent_msg = await send_preserving_entities(client, target, message, referral, reply_to_id)
            logger.info(f"Forwarded text message from {source} to {target} preserving formatting")

        if sent_msg:
            msg_id_map[message.id] = sent_msg.id

    except ChannelPrivateError:
        logger.error(f"Cannot access target channel {target}. Check membership and permissions.")
    except ChatAdminRequiredError:
        logger.error(f"User needs admin rights in the target channel {target}.")
    except FloodWaitError as e:
        logger.warning(f"Flood wait for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        logger.error(f"Error while forwarding message from {source}: {e}", exc_info=True)

# Uncomment the following handler to print chat info to get channel IDs (run once)
# @client.on(events.NewMessage())
# async def print_chat_id(event):
#     chat = await event.get_chat()
#     logger.info(f"Chat: {chat.title} ID: {chat.id} Username: {chat.username}")

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
