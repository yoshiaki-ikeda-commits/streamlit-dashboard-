import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from supabase import create_client

try:
    _url = st.secrets["SUPABASE_URL"]
    _key = st.secrets["SUPABASE_KEY"]
except Exception:
    from dotenv import load_dotenv
    load_dotenv()
    _url = os.getenv("SUPABASE_URL")
    _key = os.getenv("SUPABASE_KEY")

supabase = create_client(_url, _key)


def get_stores() -> pd.DataFrame:
    res = supabase.table("stores").select("*").execute()
    return pd.DataFrame(res.data)


def get_daily_sales(
    start_date: date, end_date: date, store_id: str | None = None
) -> pd.DataFrame:
    q = (
        supabase.table("daily_sales_summary")
        .select("*")
        .gte("date", start_date.isoformat())
        .lte("date", end_date.isoformat())
    )
    if store_id:
        q = q.eq("store_id", store_id)
    res = q.order("date").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def get_transactions(
    start_date: date, end_date: date, store_id: str | None = None
) -> pd.DataFrame:
    q = (
        supabase.table("transactions")
        .select("*")
        .gte("transaction_date", start_date.isoformat())
        .lte("transaction_date", end_date.isoformat())
    )
    if store_id:
        q = q.eq("store_id", store_id)
    res = q.order("transaction_date").execute()
    df = pd.DataFrame(res.data)
    if not df.empty and "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    return df


def get_product_rankings(
    start_date: date,
    end_date: date,
    store_id: str | None = None,
    limit: int = 20,
) -> pd.DataFrame:
    # Get transaction_ids in date range
    txns = get_transactions(start_date, end_date, store_id)
    if txns.empty:
        return pd.DataFrame()
    txn_ids = txns["transaction_id"].tolist()

    # Fetch details for those transactions (batch by 200)
    all_details = []
    for i in range(0, len(txn_ids), 200):
        batch = txn_ids[i : i + 200]
        res = (
            supabase.table("transaction_details")
            .select("product_id, product_name, quantity, subtotal")
            .in_("transaction_id", batch)
            .execute()
        )
        all_details.extend(res.data)

    df = pd.DataFrame(all_details)
    if df.empty:
        return df
    ranking = (
        df.groupby(["product_id", "product_name"])
        .agg(total_quantity=("quantity", "sum"), total_amount=("subtotal", "sum"))
        .reset_index()
        .sort_values("total_amount", ascending=False)
        .head(limit)
    )
    return ranking


def get_category_sales(
    start_date: date, end_date: date, store_id: str | None = None
) -> pd.DataFrame:
    txns = get_transactions(start_date, end_date, store_id)
    if txns.empty:
        return pd.DataFrame()
    txn_ids = txns["transaction_id"].tolist()

    all_details = []
    for i in range(0, len(txn_ids), 200):
        batch = txn_ids[i : i + 200]
        res = (
            supabase.table("transaction_details")
            .select("category_id, subtotal")
            .in_("transaction_id", batch)
            .execute()
        )
        all_details.extend(res.data)

    df = pd.DataFrame(all_details)
    if df.empty:
        return df

    # Get category names
    cats = supabase.table("categories").select("category_id, category_name").execute()
    cats_df = pd.DataFrame(cats.data)

    result = (
        df.groupby("category_id")
        .agg(total_amount=("subtotal", "sum"))
        .reset_index()
    )
    if not cats_df.empty:
        result = result.merge(cats_df, on="category_id", how="left")
        result["category_name"] = result["category_name"].fillna("不明")
    else:
        result["category_name"] = "不明"
    return result.sort_values("total_amount", ascending=False)


def get_hourly_sales(
    start_date: date, end_date: date, store_id: str | None = None
) -> pd.DataFrame:
    txns = get_transactions(start_date, end_date, store_id)
    if txns.empty:
        return txns
    txns["hour"] = txns["transaction_date"].dt.hour
    txns["weekday"] = txns["transaction_date"].dt.dayofweek  # 0=Mon
    hourly = (
        txns.groupby(["weekday", "hour"])
        .agg(total_amount=("total_amount", "sum"), count=("id", "count"))
        .reset_index()
    )
    return hourly
