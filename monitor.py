import requests
import os
import json
from datetime import datetime

# ==== НАСТРОЙКИ (берутся из GitHub Secrets / переменных окружения) ====
# ВАЖНО: больше НЕ храним токены прямо в коде. Задай их в
# Settings -> Secrets and variables -> Actions репозитория.
WALLET = os.environ.get("WALLET", "0x88a132c7b2d1901d783ce3307adb36c78428618d").lower()
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]      # обязателен
CHAT_ID = os.environ["CHAT_ID"]                    # обязателен
STATE_FILE = "seen_txs.json"

# Сколько последних действий запрашивать за один проход
ACTIVITY_LIMIT = 100
# Какие типы активности считать «ставкой» и слать в Telegram
NOTIFY_TYPES = {"TRADE"}   # при желании добавь "SPLIT", "MERGE", "REDEEM" и т.п.


def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()


def save_seen(seen):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, data=params, timeout=15)
        if r.status_code == 200:
            print("Уведомление отправлено в Telegram")
        else:
            print(f"Ошибка отправки Telegram: {r.status_code} {r.text}")
    except Exception as e:
        print(f"Ошибка Telegram: {e}")


def get_activity():
    """Берём реальную активность кошелька напрямую с Polymarket Data API.

    Именно этот источник показывает сделки. Etherscan txlist по EOA НЕ подходит:
    Polymarket торгует через прокси-кошелёк (Safe) и релеер, поэтому ставки
    не видны как обычные транзакции 'от кошелька к контракту Polymarket'.
    """
    url = "https://data-api.polymarket.com/activity"
    params = {
        "user": WALLET,
        "limit": ACTIVITY_LIMIT,
        "sortDirection": "DESC",
    }
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            return r.json()
        print(f"Ошибка Polymarket API: {r.status_code}")
    except Exception as e:
        print(f"Ошибка запроса к Polymarket: {e}")
    return []


def format_trade(a):
    ts = datetime.fromtimestamp(int(a.get("timestamp", 0))).strftime("%Y-%m-%d %H:%M:%S")
    title = a.get("title") or "Неизвестный рынок"
    outcome = a.get("outcome") or "?"
    side = (a.get("side") or "").upper()
    side_label = {"BUY": "КУПИЛ (BUY)", "SELL": "ПРОДАЛ (SELL)"}.get(side, side or "TRADE")

    usdc = a.get("usdcSize", 0) or 0
    shares = a.get("size", 0) or 0
    price = a.get("price", 0) or 0
    try:
        price_pct = f"{float(price) * 100:.1f}%"
    except (TypeError, ValueError):
        price_pct = "N/A"

    tx = a.get("transactionHash", "")
    slug = a.get("eventSlug") or a.get("slug") or ""
    pm_link = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"

    return (
        f"НОВАЯ СДЕЛКА BYD77\n\n"
        f"Рынок: {title}\n"
        f"Исход: {outcome}\n"
        f"{side_label}\n"
        f"Сумма: ${float(usdc):,.2f}\n"
        f"Доли: {float(shares):,.2f}\n"
        f"Цена: {price_pct}\n"
        f"Время: {ts}\n"
        f'<a href="https://polygonscan.com/tx/{tx}">Транзакция</a> · '
        f'<a href="{pm_link}">Рынок на Polymarket</a>\n\n'
        f"@BYD77_monitor_bot"
    )


def main():
    print("Проверка новых сделок BYD77...")
    seen = load_seen()
    activity = get_activity()

    def key(a):
        return f"{a.get('transactionHash','')}:{a.get('asset','')}:{a.get('side','')}"

    first_run = len(seen) == 0

    new_items = []
    for a in activity:
        if a.get("type") not in NOTIFY_TYPES:
            continue
        k = key(a)
        if k in seen:
            continue
        seen.add(k)
        new_items.append(a)

    if first_run:
        save_seen(seen)
        print(f"Первый запуск: запомнил {len(seen)} событий, уведомления не слал.")
        send_telegram("Бот BYD77 запущен и следит за кошельком. Жду новые сделки.")
        return

    for a in sorted(new_items, key=lambda x: int(x.get("timestamp", 0))):
        send_telegram(format_trade(a))

    save_seen(seen)

    if new_items:
        print(f"Найдено и отправлено новых сделок: {len(new_items)}")
    else:
        print("Новых сделок нет")


if __name__ == "__main__":
    main()
