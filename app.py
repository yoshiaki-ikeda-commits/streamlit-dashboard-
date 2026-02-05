import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from supabase_client import (
    get_stores,
    get_daily_sales,
    get_transactions,
    get_product_rankings,
    get_category_sales,
    get_hourly_sales,
)

# --------------- ページ設定 ---------------
st.set_page_config(
    page_title="スマレジ 売上ダッシュボード",
    page_icon="📊",
    layout="wide",
)

st.title("スマレジ 売上ダッシュボード（銀座）")

# --------------- サイドバー ---------------
st.sidebar.header("フィルター")

today = date.today()
default_start = today - timedelta(days=30)

col_s1, col_s2 = st.sidebar.columns(2)
start_date = col_s1.date_input("開始日", value=default_start)
end_date = col_s2.date_input("終了日", value=today)

# 店舗 - 銀座固定
stores_df = get_stores()
store_id = None
store_name = "銀座"
if not stores_df.empty:
    ginza = stores_df[stores_df["store_name"].str.contains("銀座", na=False)]
    if not ginza.empty:
        store_id = str(ginza.iloc[0]["store_id"])
        store_name = ginza.iloc[0]["store_name"]

# 前年同期間比較
try:
    prev_start = start_date.replace(year=start_date.year - 1)
except ValueError:
    prev_start = start_date.replace(year=start_date.year - 1, day=28)
try:
    prev_end = end_date.replace(year=end_date.year - 1)
except ValueError:
    prev_end = end_date.replace(year=end_date.year - 1, day=28)


# --------------- データ取得 (キャッシュ) ---------------
@st.cache_data(ttl=300)
def load_daily_sales(start, end, store):
    return get_daily_sales(start, end, store)


@st.cache_data(ttl=300)
def load_product_rankings(start, end, store, limit=20):
    return get_product_rankings(start, end, store, limit)


@st.cache_data(ttl=300)
def load_category_sales(start, end, store):
    return get_category_sales(start, end, store)


@st.cache_data(ttl=300)
def load_hourly_sales(start, end, store):
    return get_hourly_sales(start, end, store)


daily_df = load_daily_sales(start_date, end_date, store_id)
prev_daily_df = load_daily_sales(prev_start, prev_end, store_id)
products_df = load_product_rankings(start_date, end_date, store_id)
category_df = load_category_sales(start_date, end_date, store_id)
hourly_df = load_hourly_sales(start_date, end_date, store_id)


# --------------- ヘルパー ---------------
def fmt_yen(val):
    if pd.isna(val) or val == 0:
        return "¥0"
    return f"¥{val:,.0f}"


def calc_delta(current, previous):
    if previous == 0:
        return None
    return f"{(current - previous) / previous * 100:+.1f}%"


# --------------- KPI カード ---------------
st.markdown("---")

current_sales = daily_df["total_sales"].sum() if not daily_df.empty and "total_sales" in daily_df.columns else 0
prev_sales = prev_daily_df["total_sales"].sum() if not prev_daily_df.empty and "total_sales" in prev_daily_df.columns else 0

current_txns = daily_df["total_transactions"].sum() if not daily_df.empty and "total_transactions" in daily_df.columns else 0
prev_txns = prev_daily_df["total_transactions"].sum() if not prev_daily_df.empty and "total_transactions" in prev_daily_df.columns else 0

current_avg = current_sales / current_txns if current_txns > 0 else 0
prev_avg = prev_sales / prev_txns if prev_txns > 0 else 0

current_items = daily_df["total_items"].sum() if not daily_df.empty and "total_items" in daily_df.columns else 0
prev_items = prev_daily_df["total_items"].sum() if not prev_daily_df.empty and "total_items" in prev_daily_df.columns else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("売上合計", fmt_yen(current_sales), calc_delta(current_sales, prev_sales))
k2.metric("取引件数", f"{current_txns:,.0f}件", calc_delta(current_txns, prev_txns))
k3.metric("客単価", fmt_yen(current_avg), calc_delta(current_avg, prev_avg))
k4.metric("商品点数", f"{current_items:,.0f}点", calc_delta(current_items, prev_items))


# --------------- 日別売上推移 ---------------
st.markdown("---")
st.subheader("日別売上推移")

if not daily_df.empty and "total_sales" in daily_df.columns:
    fig_daily = go.Figure()
    fig_daily.add_trace(
        go.Scatter(
            x=daily_df["date"],
            y=daily_df["total_sales"],
            mode="lines+markers",
            name="当期",
            line=dict(color="#4F8BF9", width=2),
        )
    )
    if not prev_daily_df.empty and "total_sales" in prev_daily_df.columns:
        prev_plot = prev_daily_df.copy()
        date_shift = (start_date - prev_start).days
        prev_plot["date"] = prev_plot["date"] + timedelta(days=date_shift)
        fig_daily.add_trace(
            go.Scatter(
                x=prev_plot["date"],
                y=prev_plot["total_sales"],
                mode="lines",
                name="前年",
                line=dict(color="#CCCCCC", width=1, dash="dash"),
            )
        )
    fig_daily.update_layout(
        yaxis_title="売上 (¥)",
        xaxis_title="",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=30, b=0),
    )
    fig_daily.update_yaxes(tickformat=",")
    st.plotly_chart(fig_daily, use_container_width=True)
else:
    st.info("該当期間の売上データがありません")


# --------------- 月別売上サマリー ---------------
st.markdown("---")
st.subheader("月別売上サマリー")

if not daily_df.empty and "total_sales" in daily_df.columns:
    monthly = daily_df.copy()
    monthly["month"] = monthly["date"].dt.to_period("M").astype(str)
    monthly_agg = (
        monthly.groupby("month")
        .agg(total_sales=("total_sales", "sum"), total_transactions=("total_transactions", "sum"))
        .reset_index()
    )
    fig_monthly = px.bar(
        monthly_agg,
        x="month",
        y="total_sales",
        text_auto=True,
        labels={"month": "月", "total_sales": "売上 (¥)"},
        color_discrete_sequence=["#4F8BF9"],
    )
    fig_monthly.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    fig_monthly.update_yaxes(tickformat=",")
    fig_monthly.update_traces(texttemplate="%{y:,.0f}", textposition="outside")
    st.plotly_chart(fig_monthly, use_container_width=True)
else:
    st.info("月別データがありません")


# --------------- 商品ランキング / カテゴリ別売上 ---------------
st.markdown("---")
col_prod, col_cat = st.columns(2)

with col_prod:
    st.subheader("商品ランキング TOP20")
    if not products_df.empty:
        fig_prod = px.bar(
            products_df.head(20),
            y="product_name",
            x="total_amount",
            orientation="h",
            labels={"product_name": "", "total_amount": "売上 (¥)"},
            color_discrete_sequence=["#4F8BF9"],
        )
        fig_prod.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=500,
        )
        fig_prod.update_xaxes(tickformat=",")
        st.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.info("商品データがありません")

with col_cat:
    st.subheader("カテゴリ別売上")
    if not category_df.empty:
        fig_cat = px.pie(
            category_df,
            values="total_amount",
            names="category_name",
            hole=0.4,
        )
        fig_cat.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            height=500,
        )
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("カテゴリデータがありません")


# --------------- 曜日×時間帯ヒートマップ ---------------
st.markdown("---")
st.subheader("曜日 × 時間帯 売上ヒートマップ")

if not hourly_df.empty and "total_amount" in hourly_df.columns:
    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
    pivot = hourly_df.pivot_table(
        index="weekday", columns="hour", values="total_amount", aggfunc="sum", fill_value=0
    )
    pivot.index = [weekday_names[i] for i in pivot.index]

    fig_heat = px.imshow(
        pivot,
        labels=dict(x="時間", y="曜日", color="売上 (¥)"),
        color_continuous_scale="Blues",
        aspect="auto",
    )
    fig_heat.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("時間帯データがありません")


# --------------- フッター ---------------
st.markdown("---")
st.caption(f"データ期間: {start_date} 〜 {end_date} | 前年同期間: {prev_start} 〜 {prev_end}")
