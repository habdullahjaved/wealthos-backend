"""
POST /insights
Body:  { "user_id": "<uuid>", "months": 3 }
Returns: monthly cashflow, category breakdown, top merchants, summary stats.

Uses pandas for aggregation server-side — this is the whole point of having
a Python backend instead of doing it in JS.
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from supabase import create_client, Client

router = APIRouter()

# ── Supabase client — created once, reused across requests ────────────────────

@lru_cache(maxsize=1)
def get_db() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


# ── Category colour palette ───────────────────────────────────────────────────

COLORS: dict[str, str] = {
    "Food & Dining":    "#34d399",
    "Transport":        "#60a5fa",
    "Shopping":         "#f472b6",
    "Bills & Utilities":"#a78bfa",
    "Entertainment":    "#fb923c",
    "Health":           "#2dd4bf",
    "Travel":           "#facc15",
    "Income":           "#4ade80",
    "Other":            "#94a3b8",
}


# ── Request / Response models ─────────────────────────────────────────────────

class InsightsRequest(BaseModel):
    user_id: str
    months: int = 3

    @field_validator("months")
    @classmethod
    def clamp_months(cls, v: int) -> int:
        return max(1, min(v, 12))

    @field_validator("user_id")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("user_id cannot be empty")
        return v.strip()


class MonthlyTotal(BaseModel):
    month: str       # "Jan 2025"
    income: float
    expenses: float
    net: float


class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    percentage: float
    color: str


class InsightsResponse(BaseModel):
    monthly_totals: list[MonthlyTotal]
    category_breakdown: list[CategoryBreakdown]
    top_merchants: list[dict]
    avg_daily_spend: float
    total_income: float
    total_expenses: float
    savings_rate: float


# ── Empty response helper ─────────────────────────────────────────────────────

def _empty() -> InsightsResponse:
    return InsightsResponse(
        monthly_totals=[],
        category_breakdown=[],
        top_merchants=[],
        avg_daily_spend=0.0,
        total_income=0.0,
        total_expenses=0.0,
        savings_rate=0.0,
    )


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=InsightsResponse)
async def get_insights(req: InsightsRequest) -> InsightsResponse:
    db = get_db()

    # Fetch all transactions for this user (service key bypasses RLS)
    result = (
        db.table("transactions")
        .select("date, description, category, amount")
        .eq("user_id", req.user_id)
        .order("date", desc=False)
        .execute()
    )

    if not result.data:
        return _empty()

    # ── Build DataFrame ──────────────────────────────────────────────────────
    df = pd.DataFrame(result.data)
    df["date"]   = pd.to_datetime(df["date"])
    df["amount"] = df["amount"].astype(float)

    # Filter to last N months
    cutoff = pd.Timestamp.now().normalize() - pd.DateOffset(months=req.months)
    df     = df[df["date"] >= cutoff].copy()

    if df.empty:
        return _empty()

    df["month"] = df["date"].dt.to_period("M")

    # ── Monthly totals ───────────────────────────────────────────────────────
    def _income(s: pd.Series)   -> float: return float(s[s > 0].sum())
    def _expenses(s: pd.Series) -> float: return float(s[s < 0].abs().sum())

    monthly = (
        df.groupby("month")["amount"]
        .agg(income=_income, expenses=_expenses)
        .reset_index()
        .sort_values("month")
    )
    monthly["net"] = monthly["income"] - monthly["expenses"]

    monthly_totals = [
        MonthlyTotal(
            month    = str(row["month"].strftime("%b %Y")),
            income   = round(row["income"],   2),
            expenses = round(row["expenses"], 2),
            net      = round(row["net"],      2),
        )
        for _, row in monthly.iterrows()
    ]

    # ── Category breakdown (expenses only) ────────────────────────────────────
    exp = df[df["amount"] < 0].copy()
    exp["amount"] = exp["amount"].abs()
    total_spent   = float(exp["amount"].sum()) or 1.0  # avoid div/0

    cat_totals = (
        exp.groupby("category")["amount"]
        .sum()
        .reset_index()
        .sort_values("amount", ascending=False)
    )

    category_breakdown = [
        CategoryBreakdown(
            category   = str(row["category"]),
            amount     = round(float(row["amount"]), 2),
            percentage = round(float(row["amount"]) / total_spent * 100, 1),
            color      = COLORS.get(str(row["category"]), "#94a3b8"),
        )
        for _, row in cat_totals.iterrows()
    ]

    # ── Top 5 merchants ───────────────────────────────────────────────────────
    merchant_df = (
        exp.groupby("description")["amount"]
        .agg(total="sum", count="count")
        .reset_index()
        .sort_values("total", ascending=False)
        .head(5)
        .rename(columns={"description": "merchant"})
    )
    # Convert numpy types to native Python so JSON serialization works
    top_merchants = [
        {
            "merchant": str(r["merchant"]),
            "total":    round(float(r["total"]), 2),
            "count":    int(r["count"]),
        }
        for _, r in merchant_df.iterrows()
    ]

    # ── Summary stats ─────────────────────────────────────────────────────────
    total_income   = round(float(df[df["amount"] > 0]["amount"].sum()), 2)
    total_expenses = round(float(exp["amount"].sum()), 2)
    savings_rate   = (
        round((total_income - total_expenses) / total_income * 100, 1)
        if total_income > 0 else 0.0
    )

    date_span       = max((df["date"].max() - df["date"].min()).days, 1)
    avg_daily_spend = round(total_expenses / date_span, 2)

    return InsightsResponse(
        monthly_totals     = monthly_totals,
        category_breakdown = category_breakdown,
        top_merchants      = top_merchants,
        avg_daily_spend    = avg_daily_spend,
        total_income       = total_income,
        total_expenses     = total_expenses,
        savings_rate       = savings_rate,
    )