from flask import Flask
from threading import Thread
import subprocess
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def run_runner():
    subprocess.run(["python", "runner.py"])

# Start Flask in one thread and runner.py in another
if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_runner()
