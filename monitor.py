import requests
import os
import json
from datetime import datetime
from decimal import Decimal

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
    params = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML', 'disable_web_page_preview': False}
    try:
        response = requests.post(url, params=params, timeout=10)
        if response.status_code == 200:
            print("✅ Уведомление отправлено в Telegram")
        else:
            print(f" Ошибка отправки: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")

def get_polymarket_market(condition_id):
    """Получаем информацию о рынке с Polymarket"""
    try:
        url = f"https://api.polymarket.com/conditons/{condition_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def get_market_details(market_slug):
    """Получаем детали рынка"""
    try:
        url = f"https://polymarket.com/{market_slug}"
        # Пока не можем парсить HTML, но можно использовать API
        return None
    except:
        pass
    return None

def get_transaction_details(tx_hash):
    """Получаем детали транзакции с Polymarket API"""
    try:
        url = "https://data-api.polymarket.com/transactions"
        params = {'hash': tx_hash}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]
    except:
        pass
    return None

def format_usdc(amount_wei):
    """Конвертируем wei в USDC (6 десятичных знаков)"""
    usdc_amount = int(amount_wei) / 1_000_000  # USDC имеет 6 decimals
    return f"${usdc_amount:,.2f}"

def get_position_name(outcome_index):
    """Определяем позицию YES/NO"""
    # На Polymarket обычно 0 = YES, 1 = NO, но может быть иначе
    outcomes = {0: "YES", 1: "NO", 2: "Outcome 3"}
    return outcomes.get(outcome_index, f"Outcome {outcome_index + 1}")

def get_transactions():
    """Получаем последние транзакции кошелька"""
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
        print(f"❌ Ошибка запроса к API: {e}")
    return []

def main():
    print(" Проверка новых сделок BYD77...")
    seen = load_seen()
    txs = get_transactions()
    POLYMARKET = "0x4d97dcd73ec5646b792f44472df76a9b62f0f7a2"
    new_found = False
    
    for tx in txs:
        if tx['hash'] not in seen and tx['to'].lower() == POLYMARKET.lower():
            seen.add(tx['hash'])
            new_found = True
            
            time_str = datetime.fromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S')
            tx_hash = tx['hash']
            value_usdc = format_usdc(tx['value'])
            
            # Пробуем получить детали с Polymarket API
            pm_details = get_transaction_details(tx_hash)
            
            message = f"""
🎯 <b>НОВАЯ СДЕЛКА BYD77!</b>

 <b>Время:</b> {time_str}
💰 <b>Сумма:</b> {value_usdc}
🔗 <b>Транзакция:</b> <a href="https://polygonscan.com/tx/{tx_hash}">Посмотреть</a>
"""
            
            if pm_details:
                # Если получили детали с Polymarket
                market_name = pm_details.get('market', 'Неизвестный рынок')
                side = pm_details.get('side', 'Unknown')
                shares = pm_details.get('shares', '0')
                price = pm_details.get('price', '0')
                
                # Форматируем цену (на Polymarket цена в диапазоне 0-1)
                try:
                    price_percent = f"{float(price) * 100:.1f}%"
                except:
                    price_percent = "N/A"
                
                message += f"""
📊 <b>Рынок:</b> {market_name[:100]}...
 <b>Позиция:</b> {'✅ YES' if side == 'YES' else '❌ NO'}
 <b>Вероятность:</b> {price_percent}
🔢 <b>Доли:</b> {shares}
"""
            else:
                # Если не получили детали, показываем базовую информацию
                message += f"""
️ <i>Детали ставки загружаются...</i>
🔍 <a href="https://polymarket.com">Проверить на Polymarket</a>
"""
            
            message += f"""

📱 <i>Мониторинг: @BYD77_monitor_bot</i>
"""
            
            send_telegram(message)
            print(f"✅ Отправлено: {tx_hash[:20]}...")
    
    save_seen(seen)
    
    if not new_found:
        print("️ Новых сделок нет")
    else:
        print(f"✅ Найдено новых сделок: {sum(1 for tx in txs if tx['hash'] in seen)}")

if __name__ == "__main__":
    main()
