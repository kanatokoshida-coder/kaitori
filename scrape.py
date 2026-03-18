"""goldmrs.jp から貴金属買取価格をスクレイピングしてJSONに保存する"""
import requests
import re
import json
from datetime import datetime

TARGET_URL = "https://goldmrs.jp/"
OUTPUT_FILE = "prices.json"


def fetch_and_save():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }
    res = requests.get(TARGET_URL, headers=headers, timeout=15)
    res.encoding = res.apparent_encoding
    html = res.text

    gold_prices = {}
    platinum_prices = {}
    silver_prices = {}
    palladium_prices = {}

    update_date = ""
    m = re.search(r"最終更新日[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日)", html)
    if m:
        update_date = m.group(1)

    # 方法1: JavaScriptのselectSet関数から価格を取得
    js_gold = re.findall(
        r'\.html\("(.+?)\((\d[\d,]*(?:\.\d+)?)\)"\)\.val\("(\d[\d,]*(?:\.\d+)?)"\)',
        html
    )

    current_metal = None
    for line in html.splitlines():
        if "flg == 1" in line:
            current_metal = "金"
        elif "flg == 2" in line:
            current_metal = "プラチナ"

        m = re.search(r'\.html\("(.+?)\((\d[\d,]*(?:\.\d+)?)\)"\)\.val\("(\d[\d,]*(?:\.\d+)?)"\)', line)
        if m and current_metal:
            label = m.group(1).strip().rstrip("(")
            price_str = m.group(3).replace(",", "")
            try:
                price = float(price_str) if "." in price_str else int(price_str)
                if current_metal == "金" and label not in gold_prices:
                    gold_prices[label] = price
                elif current_metal == "プラチナ" and label not in platinum_prices:
                    platinum_prices[label] = price
            except ValueError:
                pass

    # 方法2: HTMLテキストから「ラベル ￥価格」パターンを取得
    text_matches = re.findall(r'([^\n￥¥<>]{2,40})\s*[￥¥]([\d,]+(?:\.\d+)?)', html)
    for label, price_str in text_matches:
        label = re.sub(r'<[^>]+>', '', label).strip()
        if not label or len(label) > 40:
            continue

        price_str_clean = price_str.replace(",", "")
        try:
            price = float(price_str_clean) if "." in price_str_clean else int(price_str_clean)
        except ValueError:
            continue

        if price < 1:
            continue

        # シルバー
        if re.search(r'Sv|SV|シルバー', label):
            if label not in silver_prices:
                silver_prices[label] = price
        # パラジウム
        elif re.search(r'Pd|PD|パラジウム', label):
            if label not in palladium_prices:
                palladium_prices[label] = price

    data = {
        "update_date": update_date,
        "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "prices": {
            "金": gold_prices,
            "プラチナ": platinum_prices,
            "シルバー": silver_prices,
            "パラジウム": palladium_prices,
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in data["prices"].values())
    print(f"保存完了: {total}件の価格を取得 ({OUTPUT_FILE})")
    print(f"更新日: {update_date}")
    for metal, prices in data["prices"].items():
        print(f"  {metal}: {len(prices)}件")


if __name__ == "__main__":
    fetch_and_save()
