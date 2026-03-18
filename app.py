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
    import re

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    res = requests.get(TARGET_URL, headers=headers, timeout=10)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")

    update_date = ""
    for tag in soup.find_all(string=True):
        if "最終更新日" in str(tag):
            update_date = str(tag).strip()
            break

    gold_prices = {}
    platinum_prices = {}
    silver_prices = {}
    palladium_prices = {}

    def classify_metal(label):
        """品目名から貴金属の種類を判定する"""
        label_upper = label.upper()
        if re.search(r"K\d|金歯|インゴット.*金|ゴールド|メイプル.*金|金.*メイプル", label):
            return "金"
        if re.search(r"PT|Pt|プラチナ", label):
            return "プラチナ"
        if re.search(r"SV|シルバー|銀", label):
            return "シルバー"
        if re.search(r"PD|Pd|パラジウム", label):
            return "パラジウム"
        return None

    def parse_price(text):
        """テキストから価格（数値）を抽出する"""
        text = text.replace(",", "").replace("，", "").replace("￥", "").replace("¥", "").replace("円", "").replace("/g", "").strip()
        m = re.search(r"([\d]+(?:\.\d+)?)", text)
        if m:
            val = m.group(1)
            return float(val) if "." in val else int(val)
        return None

    # すべての <li> を走査して価格を取得
    for li in soup.find_all("li"):
        text = li.get_text(" ", strip=True)
        if "￥" not in text and "¥" not in text:
            continue

        # 「ラベル ￥価格」形式を解析
        m = re.match(r"^(.+?)\s+[￥¥]([\d,，]+(?:\.\d+)?)", text)
        if not m:
            continue

        label = m.group(1).strip()
        price = parse_price(m.group(2))
        if not label or not price:
            continue

        metal = classify_metal(label)
        if metal == "金" and label not in gold_prices:
            gold_prices[label] = price
        elif metal == "プラチナ" and label not in platinum_prices:
            platinum_prices[label] = price
        elif metal == "シルバー" and label not in silver_prices:
            silver_prices[label] = price
        elif metal == "パラジウム" and label not in palladium_prices:
            palladium_prices[label] = price

    # デバッグ用：scriptタグから価格パターンを探す
    import re as re2
    debug_lines = []
    for script in soup.find_all("script"):
        src = script.string or ""
        # K24や価格っぽいパターンを探す
        matches = re2.findall(r'K\d+[^\n]{0,60}', src)
        for m in matches[:5]:
            debug_lines.append(m[:100])
        if matches:
            break
    if not debug_lines:
        debug_lines.append("scriptタグにもK24が見つかりませんでした")

    prices = {
        "金": gold_prices,
        "プラチナ": platinum_prices,
        "シルバー": silver_prices,
        "パラジウム": palladium_prices,
    }
    return prices, update_date, debug_lines


# --- データ取得 ---
with st.spinner("価格情報を取得中..."):
    try:
        prices, update_date, debug_lines = fetch_prices()
        if update_date:
            st.success(f"✅ {update_date}")
        else:
            st.success(f"✅ 価格取得完了（{datetime.now().strftime('%Y/%m/%d %H:%M')}時点）")
        with st.expander("🔍 デバッグ情報（開発用）"):
            st.write("￥を含むli要素：")
            for line in debug_lines[:30]:
                st.code(line)
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
