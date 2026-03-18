import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="貴金属価格計算機", page_icon="🥇", layout="centered")
st.title("🥇 貴金属買取価格 計算機")
st.caption("goldmrs.jp の買取価格をもとに計算します")

if st.button("🔄 価格を今すぐ更新"):
    st.cache_data.clear()

TARGET_URL = "https://goldmrs.jp/"

@st.cache_data(ttl=3600)  # 1時間キャッシュ
def fetch_prices():
    """goldmrs.jp から買取価格を取得する"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    res = requests.get(TARGET_URL, headers=headers, timeout=10)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")

    prices = {}
    update_date = ""

    # 更新日を探す
    for tag in soup.find_all(string=True):
        if "最終更新日" in str(tag):
            update_date = str(tag).strip()
            break

    # テキスト全体から価格パターンを抽出
    # 「品目名：￥XX,XXX」または「品目名 ￥XX,XXX」の形式を探す
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    gold_section = False
    platinum_section = False
    silver_section = False
    palladium_section = False

    gold_prices = {}
    platinum_prices = {}
    silver_prices = {}
    palladium_prices = {}

    i = 0
    while i < len(lines):
        line = lines[i]

        # セクション判定
        if "金買取" in line or "金の買取" in line:
            gold_section = True
            platinum_section = silver_section = palladium_section = False
        elif "プラチナ買取" in line:
            platinum_section = True
            gold_section = silver_section = palladium_section = False
        elif "シルバー買取" in line or "銀買取" in line:
            silver_section = True
            gold_section = platinum_section = palladium_section = False
        elif "パラジウム買取" in line:
            palladium_section = True
            gold_section = platinum_section = silver_section = False

        # 価格行を抽出（￥ が含まれる行）
        if "￥" in line or "¥" in line:
            price_str = line.replace(",", "").replace("￥", "").replace("¥", "").replace("/g", "").replace("円", "").strip()
            try:
                price = int(price_str)
                # 直前の行をラベルとして使う
                label = lines[i - 1].strip() if i > 0 else ""

                if gold_section and label:
                    gold_prices[label] = price
                elif platinum_section and label:
                    platinum_prices[label] = price
                elif silver_section and label:
                    silver_prices[label] = price
                elif palladium_section and label:
                    palladium_prices[label] = price
            except ValueError:
                pass

        i += 1

    prices = {
        "金": gold_prices,
        "プラチナ": platinum_prices,
        "シルバー": silver_prices,
        "パラジウム": palladium_prices,
    }
    return prices, update_date


# --- データ取得 ---
with st.spinner("価格情報を取得中..."):
    try:
        prices, update_date = fetch_prices()
        if update_date:
            st.success(f"✅ {update_date}")
        else:
            st.success(f"✅ 価格取得完了（{datetime.now().strftime('%Y/%m/%d %H:%M')}時点）")
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
            st.write(f"**{k}** : ¥{v:,}/g")
    else:
        st.write("データなし")

st.caption("※ 表示価格は参考値です。実際の買取価格は店舗にご確認ください。")
