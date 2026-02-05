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
        .gte("sales_date", start_date.isoformat())
        .lte("sales_date", end_date.isoformat())
    )
    if store_id:
        q = q.eq("store_id", store_id)
    res = q.order("sales_date").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        df["sales_date"] = pd.to_datetime(df["sales_date"])
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
    q = (
        supabase.table("transaction_details")
        .select("product_id, products(product_name), quantity, amount")
        .gte("created_at", start_date.isoformat())
        .lte("created_at", end_date.isoformat())
    )
    if store_id:
        q = q.eq("store_id", store_id)
    res = q.execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return df
    if "products" in df.columns:
        df["product_name"] = df["products"].apply(
            lambda x: x.get("product_name", "") if isinstance(x, dict) else ""
        )
        df = df.drop(columns=["products"])
    ranking = (
        df.groupby(["product_id", "product_name"])
        .agg(total_quantity=("quantity", "sum"), total_amount=("amount", "sum"))
        .reset_index()
        .sort_values("total_amount", ascending=False)
        .head(limit)
    )
    return ranking


def get_category_sales(
    start_date: date, end_date: date, store_id: str | None = None
) -> pd.DataFrame:
    q = (
        supabase.table("transaction_details")
        .select("category_id, categories(category_name), amount")
        .gte("created_at", start_date.isoformat())
        .lte("created_at", end_date.isoformat())
    )
    if store_id:
        q = q.eq("store_id", store_id)
    res = q.execute()
    df = pd.DataFrame(res.data)
    if df.empty:
        return df
    if "categories" in df.columns:
        df["category_name"] = df["categories"].apply(
            lambda x: x.get("category_name", "") if isinstance(x, dict) else ""
        )
        df = df.drop(columns=["categories"])
    result = (
        df.groupby(["category_id", "category_name"])
        .agg(total_amount=("amount", "sum"))
        .reset_index()
        .sort_values("total_amount", ascending=False)
    )
    return result


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
        .agg(total_amount=("total", "sum"), count=("id", "count"))
        .reset_index()
    )
    return hourly
