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

    update_date = ""

    # 更新日を探す
    for tag in soup.find_all(string=True):
        if "最終更新日" in str(tag):
            update_date = str(tag).strip()
            break

    # セクションキーワード
    SECTION_KEYS = {
        "金": ["金買取", "ゴールド", "金の買取"],
        "プラチナ": ["プラチナ買取", "Pt買取"],
        "シルバー": ["シルバー買取", "銀買取", "SV買取"],
        "パラジウム": ["パラジウム買取", "Pd買取"],
    }

    def detect_section(text):
        for metal, keywords in SECTION_KEYS.items():
            for kw in keywords:
                if kw in text:
                    return metal
        return None

    def parse_price(text):
        """テキストから価格（整数または小数）を抽出する"""
        import re
        text = text.replace(",", "").replace("，", "")
        m = re.search(r"[￥¥]?\s*([\d]+(?:\.\d+)?)", text)
        if m:
            val = m.group(1)
            return float(val) if "." in val else int(val)
        return None

    gold_prices = {}
    platinum_prices = {}
    silver_prices = {}
    palladium_prices = {}

    section_map = {
        "金": gold_prices,
        "プラチナ": platinum_prices,
        "シルバー": silver_prices,
        "パラジウム": palladium_prices,
    }

    current_section = None

    # ページ内の全要素を順番に走査
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "li", "tr"]):
        tag_text = tag.get_text(" ", strip=True)

        # 見出しでセクションを更新
        if tag.name in ["h1", "h2", "h3", "h4", "h5"]:
            detected = detect_section(tag_text)
            if detected:
                current_section = detected
            continue

        if current_section is None:
            continue

        target_dict = section_map[current_section]

        # <li> の場合：「K24(純度100％) ￥27,388」のような形式
        if tag.name == "li":
            if "￥" not in tag_text and "¥" not in tag_text and "円" not in tag_text:
                continue
            # ￥ または 円 で分割してラベルと価格を取得
            import re
            m = re.match(r"^(.+?)\s*[￥¥]\s*([\d,，]+(?:\.\d+)?)", tag_text)
            if m:
                label = m.group(1).strip()
                price = parse_price(m.group(2))
                if label and price and label not in target_dict:
                    target_dict[label] = price

        # <tr> の場合：<td>ラベル</td><td>￥価格</td>
        elif tag.name == "tr":
            tds = tag.find_all("td")
            if len(tds) >= 2:
                label = tds[0].get_text(strip=True)
                price_text = tds[1].get_text(strip=True)
                price = parse_price(price_text)
                if label and price and label not in target_dict:
                    target_dict[label] = price

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
