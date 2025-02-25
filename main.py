from bot import Bot
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8070)

# Start the Flask server in a separate thread
threading.Thread(target=run_flask, daemon=True).start()

# Start the bot
Bot().run()
