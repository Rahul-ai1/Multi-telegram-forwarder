from telethon import TelegramClient, events
import re
import os

# Telegram API credentials
api_id = 28490021
api_hash = 'e01e2bf792f3dc911ad7a8a760bfa613'

# Channel info
source_channel = 'https://t.me/besttrade7555'
target_channel = 'https://t.me/Ram_Earning_club'

# Referral link
referral_link = "https://www.dreamwingo.in/#/register?invitationCode=26372407203"

# Process text: remove links, append referral
def process_text(text):
    if not text:
        return None
    text = re.sub(r'http\S+', '', text).strip()
    if text:
        text += f"\n\nRegister: {referral_link}"
    return text

# Create client
client = TelegramClient('forwarder_session', api_id, api_hash)

@client.on(events.NewMessage(chats=source_channel))
async def handler(event):
    message = event.message
    text = message.raw_text or ""
    edited_text = process_text(text)

    if message.media:
        await client.send_file(
            target_channel,
            file=message.media,
            caption=edited_text or None
        )
    else:
        if edited_text:
            await client.send_message(target_channel, edited_text)

print("Bot is running...")
client.start()
client.run_until_disconnected()
