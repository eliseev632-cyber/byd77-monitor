import requests
import os
import json
from datetime import datetime

# НАСТРОЙКИ
WALLET = "0x88a132c7b2d1901d783ce3307adb36c78428618d"
API_KEY = "4D8XAFU2PMJEMWXEYJ98FSFFVRQKRTM6P3"
TELEGRAM_TOKEN = "8773525298:AAGm7xIUg9YaqsKD51v53AMxd1Ymt1NK-w"
CHAT_ID = "1115922324"
STATE_FILE = "seen_txs.json"

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(seen), f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
    try:
        requests.post(url, params=params, timeout=10)
    except Exception as e:
        print(f"Ошибка отправки в Telegram: {e}")

def get_transactions():
    url = "https://api.etherscan.io/api"
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': WALLET,
        'startblock': 0,
        'endblock': 99999999,
        'page': 1,
        'offset': 20,
        'sort': 'desc',
        'apikey': API_KEY,
        'chainId': 137
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get('status') == '1':
            return data.get('result', [])
    except Exception as e:
        print(f"Ошибка запроса к API: {e}")
    return []

def main():
    seen = load_seen()
    txs = get_transactions()
    POLYMARKET = "0x4d97dcd73ec5646b792f44472df76a9b62f0f7a2"
    new_found = False
    
    for tx in txs:
        if tx['hash'] not in seen and tx['to'].lower() == POLYMARKET.lower():
            seen.add(tx['hash'])
            new_found = True
            time_str = datetime.fromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
            
            message = f"""
🎯 <b>НОВАЯ СДЕЛКА BYD77!</b>

⏰ <b>Время:</b> {time_str}
🔗 <b>Транзакция:</b> <a href="https://polygonscan.com/tx/{tx['hash']}">Посмотреть в блокчейне</a>
💰 <b>Сумма:</b> {tx['value']} wei
✅ <b>Статус:</b> {'Успешно' if tx['isError'] == '0' else 'Ошибка'}
            """
            send_telegram(message)
    
    save_seen(seen)
    print("Проверка завершена." + (" Найдены новые сделки!" if new_found else " Новых сделок нет."))

if __name__ == "__main__":
    main()
