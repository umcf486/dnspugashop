import os
import logging
from flask import Flask, request
import requests

TOKEN = '8631736538:AAFkNgUY5QM4Gr8eqQsviUk6NxkLcZvT5yc'
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        if data and 'message' in data:
            chat_id = data['message']['chat']['id']
            text = data['message'].get('text')
            if text == '/start':
                url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
                requests.post(url, json={'chat_id': chat_id, 'text': 'سلام! ربات فعال است ✅'})
        return 'OK', 200
    except Exception as e:
        logging.error(f"Error: {e}")
        return 'OK', 200

@app.route('/')
def home():
    return 'ربات فعال است ✅'

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
