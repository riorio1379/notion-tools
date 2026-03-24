"""
price_alert.py
保有銘柄の価格を監視してMacに通知を送るスクリプト
使い方: python3 price_alert.py
バックグラウンド実行: nohup python3 price_alert.py &
"""

import subprocess
import time
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

import yfinance as yf

# ===== アラート設定 =====
ALERTS = [
    {"ticker": "CRCL", "condition": "above", "price": 129.0, "message": "💰 利確タイミング！CRCLが$129を超えました。指値売りを入れてください。"},
    {"ticker": "CRCL", "condition": "below", "price": 118.0, "message": "🚨 急落警告！CRCLが$118を下回りました。ストップロス発動を確認してください。"},
]

CHECK_INTERVAL = 300  # 5分ごとにチェック（秒）
# =======================

notified = set()  # 同じアラートを連続送信しない


def get_price(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d", interval="1m")
        if not hist.empty:
            return round(hist["Close"].iloc[-1], 2)
    except Exception as e:
        print(f"[{ticker}] 価格取得失敗: {e}")
    return None


def send_notification(title, message):
    script = f'display notification "{message}" with title "{title}" sound name "Ping"'
    subprocess.run(["osascript", "-e", script])


def check_alerts():
    for alert in ALERTS:
        ticker = alert["ticker"]
        price = get_price(ticker)
        if price is None:
            continue

        key = f"{ticker}_{alert['condition']}_{alert['price']}"
        triggered = (
            alert["condition"] == "above" and price >= alert["price"] or
            alert["condition"] == "below" and price <= alert["price"]
        )

        if triggered and key not in notified:
            print(f"[{datetime.now().strftime('%H:%M')}] アラート発火: {ticker} ${price} → {alert['message']}")
            send_notification(f"📈 株価アラート: {ticker}", alert["message"])
            notified.add(key)
        elif not triggered and key in notified:
            # 価格が戻ったらリセット（再度トリガーできるように）
            notified.discard(key)
        else:
            print(f"[{datetime.now().strftime('%H:%M')}] {ticker}: ${price} （アラート未発火）")


def run():
    print("=== 価格アラート監視開始 ===")
    for a in ALERTS:
        cond = "以上" if a["condition"] == "above" else "以下"
        print(f"  {a['ticker']}: ${a['price']}{cond} → 通知")
    print(f"チェック間隔: {CHECK_INTERVAL // 60}分\n終了: Ctrl+C\n")

    while True:
        try:
            check_alerts()
        except KeyboardInterrupt:
            print("\n監視を終了しました")
            break
        except Exception as e:
            print(f"エラー: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
