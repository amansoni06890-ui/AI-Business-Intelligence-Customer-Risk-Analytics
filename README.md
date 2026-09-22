# AI-Powered Business Intelligence & Customer Risk Analytics

A Streamlit decision-support dashboard for analyzing a public Superstore-style
transaction dataset.

## Features
- Executive KPI dashboard
- Revenue and profit trends
- Category and regional analysis
- Product profitability and driver analysis
- Customer value and purchase-frequency analysis
- Transparent customer risk scoring
- Recommended business actions
- Data-quality and cleaning page
- Sidebar filters for region, category, segment and date range
- Automatic column-name standardization for common Tableau Superstore formats

## Project structure
```text
AI_Business_Intelligence_Project/
├── app.py
├── requirements.txt
├── README.md
├── Project_Report.docx
└── dataset/
    └── final_superstore.csv
```

## Run locally
```powershell
cd "C:\Users\91700\Downloads\AI_Business_Intelligence_Project"
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Dataset
Place your approved public CSV at:

`dataset/final_superstore.csv`

The app is designed to work with common Tableau Sample Superstore column
names such as `Order ID`, `Customer ID`, `Order Date`, `Product Name`,
`Category`, `Quantity`, `Sales`, `Profit`, `Region`, and `Segment`.

## Important methodology note
The customer risk page uses a transparent analytical proxy based on recency,
purchase frequency and customer value. It should not be described as a
validated churn-prediction model because the usual public Superstore dataset
does not contain an observed churn/retention outcome.

## Suggested project narrative
Data → Cleaning → KPIs → Trends → Drivers → Customer Value → Risk Signals
→ Opportunities → Recommended Actions.
