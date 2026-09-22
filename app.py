import io
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# AI-Powered Business Intelligence & Customer Risk Analytics
# Built for public Superstore-style transactional datasets.
# ============================================================

st.set_page_config(
    page_title="AI Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Professional theme ----------
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    [data-testid="stMetricValue"] {font-size: 1.55rem;}
    .app-card {
        padding: 1rem 1.15rem;
        border: 1px solid rgba(128,128,128,.22);
        border-radius: 12px;
        margin-bottom: .75rem;
    }
    .small-note {font-size: .86rem; color: #6b7280;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Dataset configuration ----------
DATA_DIR = Path(__file__).resolve().parent / "dataset"
DEFAULT_DATASET = DATA_DIR / "final_superstore.csv"

# Common names found in Tableau Sample Superstore and similar public datasets.
ALIASES = {
    "Order_ID": ["Order_ID", "Order ID", "OrderID"],
    "Customer_ID": ["Customer_ID", "Customer ID", "CustomerID"],
    "Order_Date": ["Order_Date", "Order Date", "OrderDate"],
    "Product": ["Product", "Product Name", "Product_Name", "ProductName"],
    "Category": ["Category"],
    "Quantity": ["Quantity", "Qty"],
    "Sales": ["Sales", "Revenue", "Amount"],
    "Profit": ["Profit", "Net Profit"],
    "Region": ["Region", "Area"],
    "Customer_Segment": ["Customer_Segment", "Segment", "Customer Segment"],
    "Sub_Category": ["Sub_Category", "Sub-Category", "Sub Category"],
    "Discount": ["Discount"],
    "State": ["State"],
    "City": ["City"],
    "Ship_Date": ["Ship_Date", "Ship Date", "ShipDate"],
}


def clean_col_name(value):
    return str(value).strip().lower().replace("-", " ").replace("_", " ")


def standardize_columns(df):
    """Map common public-dataset column names into the app's canonical names."""
    df = df.copy()
    lookup = {clean_col_name(c): c for c in df.columns}
    rename = {}

    for canonical, candidates in ALIASES.items():
        for candidate in candidates:
            key = clean_col_name(candidate)
            if key in lookup:
                rename[lookup[key]] = canonical
                break

    return df.rename(columns=rename)


@st.cache_data(show_spinner=False)
def load_csv_from_bytes(raw_bytes):
    for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
        try:
            return pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Could not decode the CSV file. Please save the dataset as "
        "CSV UTF-8 (Comma delimited) from Excel and try again."
    )


@st.cache_data(show_spinner=False)
def load_csv_from_path(path_str):
    for encoding in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
        try:
            return pd.read_csv(path_str, encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Could not decode the CSV file. Please save the dataset as "
        "CSV UTF-8 (Comma delimited) and try again."
    )


def load_dataset():
    uploaded = st.sidebar.file_uploader(
        "Upload approved CSV dataset",
        type=["csv"],
        help="Use your approved public dataset. The app will standardize common Superstore column names automatically.",
    )

    if uploaded is not None:
        raw = uploaded.getvalue()
        source = f"Uploaded: {uploaded.name}"
        return load_csv_from_bytes(raw), source

    if DEFAULT_DATASET.exists():
        source = f"Local: dataset/{DEFAULT_DATASET.name}"
        return load_csv_from_path(str(DEFAULT_DATASET)), source

    st.sidebar.warning(
        "No dataset found. Put your approved CSV at "
        "`dataset/final_superstore.csv` or upload it above."
    )
    return None, "No dataset"


def prepare_data(raw):
    df = standardize_columns(raw)

    required = [
        "Order_ID",
        "Customer_ID",
        "Order_Date",
        "Product",
        "Category",
        "Quantity",
        "Sales",
        "Profit",
        "Region",
        "Customer_Segment",
    ]
    missing = [c for c in required if c not in df.columns]

    quality = {
        "rows_before": len(df),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_required_columns": missing,
    }

    if missing:
        return None, quality, missing

    # Type conversion
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    if "Ship_Date" in df.columns:
        df["Ship_Date"] = pd.to_datetime(df["Ship_Date"], errors="coerce")

    for col in ["Quantity", "Sales", "Profit", "Discount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Keep a raw-quality snapshot before removing invalid analytical rows.
    quality["missing_values_before"] = int(df[required].isna().sum().sum())

    df = df.drop_duplicates().copy()
    df = df.dropna(subset=["Order_ID", "Customer_ID", "Order_Date", "Sales", "Profit"])

    # Business-friendly derived fields
    df["Month"] = df["Order_Date"].dt.to_period("M").astype(str)
    df["Year"] = df["Order_Date"].dt.year
    df["Profit_Margin"] = np.where(
        df["Sales"] != 0, df["Profit"] / df["Sales"] * 100, 0
    )

    if "Discount" not in df.columns:
        df["Discount"] = np.nan

    if "Ship_Date" in df.columns:
        df["Ship_Days"] = (df["Ship_Date"] - df["Order_Date"]).dt.days
    else:
        df["Ship_Days"] = np.nan

    quality["rows_after"] = len(df)
    quality["rows_removed"] = quality["rows_before"] - quality["rows_after"]
    quality["date_min"] = df["Order_Date"].min()
    quality["date_max"] = df["Order_Date"].max()

    return df, quality, []


def money(value):
    return f"₹{value:,.0f}"


def pct(value):
    return f"{value:.1f}%"


def safe_mom(monthly):
    if len(monthly) < 2:
        return np.nan
    previous = monthly["Sales"].iloc[-2]
    current = monthly["Sales"].iloc[-1]
    if previous == 0:
        return np.nan
    return (current / previous - 1) * 100


def risk_score(customers):
    """
    Transparent, rule-based customer risk score.
    This is not presented as a trained churn model because the public
    Superstore dataset normally has no observed churn label.
    """
    c = customers.copy()

    recency = c["Recency_Days"]
    orders = c["Orders"]
    sales = c["Sales"]

    recency_risk = recency.rank(pct=True).fillna(0) * 45
    frequency_risk = (1 - orders.rank(pct=True)).fillna(0) * 30
    value_risk = (1 - sales.rank(pct=True)).fillna(0) * 25

    c["Risk_Score"] = (recency_risk + frequency_risk + value_risk).clip(0, 100)

    c["Risk_Level"] = pd.cut(
        c["Risk_Score"],
        bins=[-0.01, 33, 66, 100.01],
        labels=["Low", "Medium", "High"],
    )
    return c


# ---------- Header ----------
st.title("📊 AI-Powered Business Intelligence")
st.caption(
    "A decision-support dashboard for sales performance, customer analytics, "
    "business drivers, risk signals, data quality and recommended actions."
)

data_raw, source = load_dataset()

if data_raw is None:
    st.info(
        "Add your approved public CSV as `dataset/final_superstore.csv` "
        "or upload it from the sidebar to start the dashboard."
    )
    st.stop()

data, quality, missing = prepare_data(data_raw)

if missing:
    st.error("The dataset is missing required fields:")
    st.write(", ".join(missing))
    st.markdown(
        "The app expects a Superstore-style dataset containing order, customer, "
        "date, product, category, quantity, sales, profit, region and segment fields."
    )
    st.stop()

# ---------- Sidebar ----------
st.sidebar.markdown("## 🎛️ Dashboard Controls")
st.sidebar.caption(source)

regions_all = sorted(data["Region"].dropna().astype(str).unique())
categories_all = sorted(data["Category"].dropna().astype(str).unique())
segments_all = sorted(data["Customer_Segment"].dropna().astype(str).unique())

regions = st.sidebar.multiselect("Region", regions_all, default=regions_all)
categories = st.sidebar.multiselect("Category", categories_all, default=categories_all)
segments = st.sidebar.multiselect(
    "Customer Segment", segments_all, default=segments_all
)

min_date = data["Order_Date"].min().date()
max_date = data["Order_Date"].max().date()
date_range = st.sidebar.date_input(
    "Order date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = data[
    data["Region"].astype(str).isin(regions)
    & data["Category"].astype(str).isin(categories)
    & data["Customer_Segment"].astype(str).isin(segments)
    & (data["Order_Date"].dt.date >= start_date)
    & (data["Order_Date"].dt.date <= end_date)
].copy()

st.sidebar.markdown("---")
st.sidebar.caption(
    "Submission note: use only the approved external/public dataset for the final submission."
)

if filtered.empty:
    st.warning("No records match the selected filters. Adjust the sidebar filters.")
    st.stop()

# ---------- Core KPIs ----------
revenue = filtered["Sales"].sum()
profit = filtered["Profit"].sum()
orders = filtered["Order_ID"].nunique()
customers = filtered["Customer_ID"].nunique()
quantity = filtered["Quantity"].sum()
aov = revenue / orders if orders else 0
margin = profit / revenue * 100 if revenue else 0

monthly = (
    filtered.groupby("Month", as_index=False)
    .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
    .sort_values("Month")
)
mom = safe_mom(monthly)

tabs = st.tabs(
    [
        "🏠 Executive Overview",
        "📈 Sales & Products",
        "👥 Customer Analytics",
        "🚨 Risk & Actions",
        "🧹 Data Quality",
    ]
)

# ============================================================
# TAB 1 — EXECUTIVE OVERVIEW
# ============================================================
with tabs[0]:
    st.subheader("Executive Overview")
    st.caption(
        f"Analysis period: {start_date} to {end_date} • "
        f"{len(filtered):,} transaction rows after cleaning"
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Revenue", money(revenue))
    c2.metric("Profit", money(profit))
    c3.metric("Orders", f"{orders:,}")
    c4.metric("Customers", f"{customers:,}")
    c5.metric("Avg Order Value", money(aov))
    c6.metric("Profit Margin", pct(margin))

    if not np.isnan(mom):
        st.caption(f"Latest month-over-month revenue change: **{mom:.1f}%**")

    st.plotly_chart(
        px.line(
            monthly,
            x="Month",
            y=["Sales", "Profit"],
            markers=True,
            title="Revenue and Profit Trend",
            labels={"value": "Amount", "Month": "Month", "variable": ""},
        ),
        use_container_width=True,
    )

    left, right = st.columns(2)

    category = (
        filtered.groupby("Category", as_index=False)
        .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        .sort_values("Sales", ascending=False)
    )
    region = (
        filtered.groupby("Region", as_index=False)
        .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        .sort_values("Sales", ascending=False)
    )

    with left:
        st.plotly_chart(
            px.bar(
                category,
                x="Category",
                y="Sales",
                title="Revenue by Category",
                text_auto=".2s",
            ),
            use_container_width=True,
        )

    with right:
        st.plotly_chart(
            px.bar(
                region,
                x="Region",
                y="Sales",
                title="Revenue by Region",
                text_auto=".2s",
            ),
            use_container_width=True,
        )

    st.markdown("### 🔎 Business Snapshot")
    best_cat = category.iloc[0] if len(category) else None
    best_reg = region.iloc[0] if len(region) else None
    loss_rows = filtered[filtered["Profit"] < 0]

    s1, s2, s3 = st.columns(3)
    if best_cat is not None:
        s1.success(
            f"**Largest category:** {best_cat['Category']} — {money(best_cat['Sales'])} revenue."
        )
    if best_reg is not None:
        s2.info(
            f"**Largest region:** {best_reg['Region']} — {money(best_reg['Sales'])} revenue."
        )
    s3.warning(
        f"**Loss-making rows:** {len(loss_rows):,} transactions have negative profit."
    )

# ============================================================
# TAB 2 — SALES & PRODUCTS
# ============================================================
with tabs[1]:
    st.subheader("Sales, Product & Business Driver Analysis")

    product = (
        filtered.groupby(["Product"], as_index=False)
        .agg(
            Sales=("Sales", "sum"),
            Profit=("Profit", "sum"),
            Quantity=("Quantity", "sum"),
            Orders=("Order_ID", "nunique"),
        )
        .sort_values("Sales", ascending=False)
    )
    product["Profit_Margin"] = np.where(
        product["Sales"] != 0, product["Profit"] / product["Sales"] * 100, 0
    )

    p1, p2 = st.columns(2)
    with p1:
        st.plotly_chart(
            px.bar(
                product.head(10),
                x="Sales",
                y="Product",
                orientation="h",
                title="Top 10 Products by Revenue",
                text_auto=".2s",
            ),
            use_container_width=True,
        )

    with p2:
        st.plotly_chart(
            px.bar(
                product.sort_values("Profit").head(10),
                x="Profit",
                y="Product",
                orientation="h",
                title="Lowest-Profit Products",
                text_auto=".2s",
            ),
            use_container_width=True,
        )

    st.markdown("### Profitability vs Revenue")
    st.plotly_chart(
        px.scatter(
            product,
            x="Sales",
            y="Profit",
            size="Quantity",
            hover_name="Product",
            hover_data=["Orders", "Profit_Margin"],
            title="Product Revenue vs Profit",
        ),
        use_container_width=True,
    )

    st.markdown("### Driver Analysis")
    driver_table = (
        filtered.groupby(["Category", "Region"], as_index=False)
        .agg(Sales=("Sales", "sum"), Profit=("Profit", "sum"))
        .sort_values("Sales", ascending=False)
    )
    driver_table["Profit_Margin"] = np.where(
        driver_table["Sales"] != 0,
        driver_table["Profit"] / driver_table["Sales"] * 100,
        0,
    )

    st.dataframe(
        driver_table.style.format(
            {"Sales": "₹{:,.0f}", "Profit": "₹{:,.0f}", "Profit_Margin": "{:.1f}%"}
        ),
        use_container_width=True,
        hide_index=True,
    )

    low_profit = product.sort_values("Profit_Margin").head(5)
    st.info(
        "Action signal: review products with weak profit margins before increasing "
        "their promotional exposure. Revenue volume alone does not guarantee profitability."
    )

# ============================================================
# TAB 3 — CUSTOMER ANALYTICS
# ============================================================
with tabs[2]:
    st.subheader("Customer Analytics & Value Segmentation")

    customers_df = (
        filtered.groupby("Customer_ID", as_index=False)
        .agg(
            Orders=("Order_ID", "nunique"),
            Sales=("Sales", "sum"),
            Profit=("Profit", "sum"),
            Last_Purchase=("Order_Date", "max"),
            Quantity=("Quantity", "sum"),
        )
    )

    as_of = filtered["Order_Date"].max()
    customers_df["Recency_Days"] = (
        as_of - customers_df["Last_Purchase"]
    ).dt.days
    customers_df["AOV"] = np.where(
        customers_df["Orders"] != 0,
        customers_df["Sales"] / customers_df["Orders"],
        0,
    )

    returning = int((customers_df["Orders"] > 1).sum())
    high_value = int(
        (customers_df["Sales"] >= customers_df["Sales"].quantile(0.75)).sum()
    )
    avg_value = customers_df["Sales"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Returning Customers", f"{returning:,}")
    c2.metric("High-Value Customers", f"{high_value:,}")
    c3.metric("Avg Customer Revenue", money(avg_value))
    c4.metric("Median Recency", f"{customers_df['Recency_Days'].median():.0f} days")

    st.plotly_chart(
        px.scatter(
            customers_df,
            x="Orders",
            y="Sales",
            size="Quantity",
            color="Recency_Days",
            hover_name="Customer_ID",
            hover_data=["Profit", "AOV"],
            title="Customer Value vs Purchase Frequency",
            labels={"Recency_Days": "Recency (days)"},
        ),
        use_container_width=True,
    )

    st.markdown("### Highest-Value Customers")
    st.dataframe(
        customers_df.sort_values("Sales", ascending=False)
        .head(20)
        .style.format(
            {
                "Sales": "₹{:,.0f}",
                "Profit": "₹{:,.0f}",
                "AOV": "₹{:,.0f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# TAB 4 — RISK & ACTIONS
# ============================================================
with tabs[3]:
    st.subheader("Customer Risk Signals & Recommended Actions")
    st.caption(
        "Risk is a transparent analytical proxy based on recency, purchase frequency "
        "and customer value. It is not a measured churn probability."
    )

    customers_df = risk_score(customers_df)

    high = customers_df[customers_df["Risk_Level"].astype(str) == "High"].sort_values(
        ["Sales", "Risk_Score"], ascending=[False, False]
    )
    medium = customers_df[
        customers_df["Risk_Level"].astype(str) == "Medium"
    ].sort_values("Risk_Score", ascending=False)

    r1, r2, r3 = st.columns(3)
    r1.metric("High-Risk Customers", f"{len(high):,}")
    r2.metric("Medium-Risk Customers", f"{len(medium):,}")
    r3.metric(
        "High-Risk Revenue at Stake",
        money(high["Sales"].sum()) if len(high) else "₹0",
    )

    if len(customers_df):
        risk_counts = (
            customers_df["Risk_Level"].value_counts()
            .rename_axis("Risk Level")
            .reset_index(name="Customers")
        )
        st.plotly_chart(
            px.bar(
                risk_counts,
                x="Risk Level",
                y="Customers",
                title="Customer Risk Distribution",
                text_auto=True,
            ),
            use_container_width=True,
        )

    st.markdown("### Priority Risk List")
    st.dataframe(
        high[
            [
                "Customer_ID",
                "Orders",
                "Sales",
                "Profit",
                "Recency_Days",
                "Risk_Score",
                "Risk_Level",
            ]
        ]
        .head(30)
        .style.format(
            {
                "Sales": "₹{:,.0f}",
                "Profit": "₹{:,.0f}",
                "Risk_Score": "{:.1f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### 🚨 Risk → Driver → Opportunity → Action")
    if len(high):
        st.error(
            f"**Risk:** {len(high):,} customers have a high analytical risk score."
        )
        st.warning(
            "**Drivers:** high recency, lower purchase frequency and/or relatively "
            "lower customer value within the filtered population."
        )
        st.success(
            "**Opportunity:** focus retention attention on high-value customers "
            "whose recent activity has weakened."
        )
        st.info(
            "**Recommended action:** create a targeted retention list, review each "
            "customer's purchase history, offer relevant products or service support, "
            "and track whether purchase activity improves."
        )
    else:
        st.success("No customers fall into the high-risk band under the current filters.")

    st.markdown("### 📌 Management Actions")
    action_table = pd.DataFrame(
        {
            "Signal": [
                "High recency + low frequency",
                "High revenue + weak profit",
                "Strong category/region concentration",
                "Negative-profit transactions",
            ],
            "Recommended Action": [
                "Run a targeted retention campaign and monitor repeat purchases.",
                "Review pricing, discounting, product cost and promotion strategy.",
                "Diversify growth efforts and investigate the underlying performance driver.",
                "Audit discount, pricing and product-level profitability.",
            ],
        }
    )
    st.dataframe(action_table, use_container_width=True, hide_index=True)

# ============================================================
# TAB 5 — DATA QUALITY
# ============================================================
with tabs[4]:
    st.subheader("🧹 Data Quality & Preparation")

    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Rows Before Cleaning", f"{quality['rows_before']:,}")
    q2.metric("Rows After Cleaning", f"{quality['rows_after']:,}")
    q3.metric("Duplicates Removed", f"{quality['duplicate_rows']:,}")
    q4.metric("Rows Removed", f"{quality['rows_removed']:,}")

    st.markdown("### Cleaning performed")
    st.markdown(
        """
        - Standardized common Superstore column names.
        - Converted dates to a consistent datetime format.
        - Converted numeric business measures to numeric types.
        - Removed duplicate rows.
        - Removed records missing essential order, customer, date, sales or profit fields.
        - Created Month, Year, Profit Margin and shipping-time fields where available.
        """
    )

    missing_table = (
        data.isna().sum()
        .sort_values(ascending=False)
        .rename("Missing Values")
        .reset_index()
        .rename(columns={"index": "Column"})
    )
    missing_table["Missing %"] = (
        missing_table["Missing Values"] / len(data) * 100
    )

    st.markdown("### Missing-value profile after cleaning")
    st.dataframe(
        missing_table.style.format({"Missing %": "{:.2f}%"}),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Dataset summary")
    st.write(
        {
            "Source": source,
            "Rows": len(data),
            "Columns": len(data.columns),
            "Date range": f"{data['Order_Date'].min().date()} → {data['Order_Date'].max().date()}",
            "Revenue": money(data["Sales"].sum()),
            "Profit": money(data["Profit"].sum()),
        }
    )

# ---------- Footer ----------
st.markdown("---")
st.caption(
    "AI Business Intelligence • Decision-support prototype • "
    "Risk scores are analytical proxies, not observed churn probabilities."
)
