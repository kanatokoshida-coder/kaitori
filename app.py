import streamlit as st
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="貴金属価格計算機", page_icon="🥇", layout="centered")
st.title("🥇 貴金属買取価格 計算機")
st.caption("goldmrs.jp の買取価格をもとに計算します")

if st.button("🔄 価格を今すぐ更新"):
    st.cache_data.clear()

TARGET_URL = "https://goldmrs.jp/"


@st.cache_data(ttl=3600)
def fetch_prices():
    """goldmrs.jp から買取価格を取得する"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }
    res = requests.get(TARGET_URL, headers=headers, timeout=15)
    res.encoding = res.apparent_encoding
    html = res.text

    debug_info = f"HTMLサイズ: {len(html)}文字"

    gold_prices = {}
    platinum_prices = {}
    silver_prices = {}
    palladium_prices = {}

    update_date = ""
    m = re.search(r"最終更新日[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日)", html)
    if m:
        update_date = f"最終更新日: {m.group(1)}"

    # 方法1: JavaScriptのselectSet関数から価格を取得
    # .html("K24(純度100％)(27,388)").val("27,388") のようなパターン
    js_matches = re.findall(
        r'\.html\("(.+?)\((\d[\d,]*(?:\.\d+)?)\)"\)\.val\("(\d[\d,]*(?:\.\d+)?)"\)',
        html
    )
    for label, price_in_label, price_val in js_matches:
        label = label.strip().rstrip("(")
        price_str = price_val.replace(",", "")
        try:
            price = float(price_str) if "." in price_str else int(price_str)
        except ValueError:
            continue

        label_upper = label.upper()
        if re.search(r"[KＫ]\d|金歯|金パラ", label) or ("インゴット" in label and "Pt" not in label_upper and "プラチナ" not in label_upper and "SV" not in label_upper):
            if label not in gold_prices:
                gold_prices[label] = price
        elif re.search(r"PT|Pt|プラチナ", label):
            if label not in platinum_prices:
                platinum_prices[label] = price

    # 方法2: HTMLテキスト全体から「ラベル ￥価格」パターンを取得
    text_matches = re.findall(r'([^\n￥¥]{2,40})\s*[￥¥]([\d,]+(?:\.\d+)?)', html)
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

        label_upper = label.upper()
        # 金
        if re.search(r'[KＫ]\d|金歯|金パラ|メイプルコイン', label):
            if label not in gold_prices:
                gold_prices[label] = price
        elif "インゴット" in label and "Pt" not in label_upper and "SV" not in label_upper and "プラチナ" not in label_upper and "シルバー" not in label_upper:
            if label not in gold_prices:
                gold_prices[label] = price
        # プラチナ
        elif re.search(r'Pt|PT|プラチナ', label):
            if label not in platinum_prices:
                platinum_prices[label] = price
        # シルバー
        elif re.search(r'Sv|SV|シルバー', label):
            if label not in silver_prices:
                silver_prices[label] = price
        # パラジウム
        elif re.search(r'Pd|PD|パラジウム', label):
            if label not in palladium_prices:
                palladium_prices[label] = price

    prices = {
        "金": gold_prices,
        "プラチナ": platinum_prices,
        "シルバー": silver_prices,
        "パラジウム": palladium_prices,
    }
    return prices, update_date, debug_info


# --- データ取得 ---
with st.spinner("価格情報を取得中..."):
    try:
        prices, update_date, debug_info = fetch_prices()
        if update_date:
            st.success(f"✅ {update_date}")
        else:
            st.success(f"✅ 価格取得完了（{datetime.now().strftime('%Y/%m/%d %H:%M')}時点）")
        with st.expander("🔍 デバッグ情報（開発用）"):
            st.write(debug_info)
            for metal_name, metal_data in prices.items():
                st.write(f"**{metal_name}**: {len(metal_data)}件")
    except Exception as e:
        st.error(f"価格の取得に失敗しました: {e}")
        st.stop()

# --- UI ---
col1, col2 = st.columns(2)

with col1:
    metal = st.selectbox("貴金属の種類", list(prices.keys()))

with col2:
    metal_prices = prices[metal]
    if metal_prices:
        grade = st.selectbox("品位・純度", list(metal_prices.keys()))
    else:
        st.warning("価格情報が取得できませんでした")
        st.stop()

grams = st.number_input("グラム数", min_value=0.0, step=0.1, format="%.1f")

unit_price = metal_prices.get(grade, 0)

st.divider()

if grams > 0 and unit_price > 0:
    total = grams * unit_price
    st.metric(
        label=f"{metal}（{grade}）の買取予想金額",
        value=f"¥{total:,.0f}",
        delta=f"単価 ¥{unit_price:,}/g × {grams}g"
    )
else:
    st.info("グラム数を入力すると金額が表示されます")

st.divider()

# 価格一覧テーブルを表示
with st.expander(f"{metal}の買取価格一覧を見る"):
    if metal_prices:
        for k, v in metal_prices.items():
            if isinstance(v, float):
                st.write(f"**{k}** : ¥{v:,.2f}/g")
            else:
                st.write(f"**{k}** : ¥{v:,}/g")
    else:
        st.write("データなし")

st.caption("※ 表示価格は参考値です。実際の買取価格は店舗にご確認ください。")
