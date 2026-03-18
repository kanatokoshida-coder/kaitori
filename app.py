import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="貴金属価格計算機", page_icon="🥇", layout="centered")
st.title("🥇 貴金属買取価格 計算機")
st.caption("goldmrs.jp の買取価格をもとに計算します")

PRICES_FILE = "prices.json"


def load_prices():
    """prices.json から価格データを読み込む"""
    if not os.path.exists(PRICES_FILE):
        return None
    with open(PRICES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# --- データ読み込み ---
data = load_prices()

if data is None:
    st.error("価格データ（prices.json）が見つかりません。GitHub Actionsの実行を確認してください。")
    st.stop()

prices = data["prices"]
update_date = data.get("update_date", "")
fetched_at = data.get("fetched_at", "")

if update_date:
    st.success(f"✅ 最終更新日: {update_date}")
elif fetched_at:
    st.success(f"✅ 価格取得日時: {fetched_at}")

# --- UI ---
col1, col2 = st.columns(2)

with col1:
    # 空のカテゴリを除外
    available_metals = {k: v for k, v in prices.items() if v}
    if not available_metals:
        st.error("価格データが空です。GitHub Actionsの実行を確認してください。")
        st.stop()
    metal = st.selectbox("貴金属の種類", list(available_metals.keys()))

with col2:
    metal_prices = available_metals[metal]
    grade = st.selectbox("品位・純度", list(metal_prices.keys()))

grams = st.number_input("グラム数", min_value=0.0, step=0.1, format="%.1f")

unit_price = metal_prices.get(grade, 0)

st.divider()

if grams > 0 and unit_price > 0:
    total = grams * unit_price
    if isinstance(unit_price, float):
        st.metric(
            label=f"{metal}（{grade}）の買取予想金額",
            value=f"¥{total:,.2f}",
            delta=f"単価 ¥{unit_price:,.2f}/g × {grams}g"
        )
    else:
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
    for k, v in metal_prices.items():
        if isinstance(v, float):
            st.write(f"**{k}** : ¥{v:,.2f}/g")
        else:
            st.write(f"**{k}** : ¥{v:,}/g")

st.caption("※ 表示価格は参考値です。実際の買取価格は店舗にご確認ください。")
st.caption("※ 価格はGitHub Actionsにより毎営業日 9:30 JST に自動更新されます。")
