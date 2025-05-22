import subprocess
import time
import os
from dotenv import load_dotenv
import traceback
import requests

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # Use numeric ID (like "123456789") or your @username
LOG_FILE = "crash.log"

def send_telegram_message(text):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": ADMIN_CHAT_ID, "text": text[:4096]},
        )
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def send_telegram_document(file_path):
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        return
    try:
        with open(file_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
                data={"chat_id": ADMIN_CHAT_ID},
                files={"document": f},
            )
    except Exception as e:
        print(f"Failed to send crash log: {e}")

while True:
    try:
        print("🚀 Starting bot...")
        subprocess.run(["python", "telegram_forwarder.py"], check=True)
    except subprocess.CalledProcessError as e:
        error_text = traceback.format_exc()
        print("💥 Bot crashed. Logging error and notifying admin.")
        with open(LOG_FILE, "w") as f:
            f.write(str(e))
        send_telegram_message("🚨 Bot crashed!\n\n" + str(e))
        send_telegram_document(LOG_FILE)
    except Exception as e:
        print("❌ Unexpected crash:")
        traceback.print_exc()
        with open(LOG_FILE, "w") as f:
            f.write(traceback.format_exc())
        send_telegram_message("🚨 Bot crashed with unexpected error:\n\n" + traceback.format_exc())
        send_telegram_document(LOG_FILE)

    print("🔄 Restarting in 5 seconds...")
    time.sleep(5)
