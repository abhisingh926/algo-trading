"""Reference data for the NIFTY 50 research universe.

Exchange tokens (Dhan security ids) come from Dhan's public instrument master (api-scrip-master.csv), fetched
2026-09-22. Sector labels are a static classification maintained by hand. Index membership changes over time
and this list is NOT versioned, so historical universes are not reconstructed (survivorship bias): review it
against NSE's published constituents and edit it with the research universe API before relying on it.
"""

from __future__ import annotations

UNIVERSE_NAME = "NIFTY50"
AS_OF_NOTE = "Approximate NIFTY 50 constituents as known when this list was written; verify against NSE."

# (symbol, company, exchange token, tick size in INR, sector)
NIFTY50: tuple[tuple[str, str, str, float, str], ...] = (
    ("ADANIENT", "Adani Enterprises", "25", 0.1, "Infrastructure"),
    ("ADANIPORTS", "Adani Ports & SEZ", "15083", 0.1, "Infrastructure"),
    ("APOLLOHOSP", "Apollo Hospitals", "157", 0.5, "Healthcare"),
    ("ASIANPAINT", "Asian Paints", "236", 0.1, "Materials"),
    ("AXISBANK", "Axis Bank", "5900", 0.1, "Banking"),
    ("BAJAJ-AUTO", "Bajaj Auto", "16669", 1.0, "Auto"),
    ("BAJAJFINSV", "Bajaj Finserv", "16675", 0.1, "Financial Services"),
    ("BAJFINANCE", "Bajaj Finance", "317", 0.1, "Financial Services"),
    ("BEL", "Bharat Electronics", "383", 0.05, "Capital Goods"),
    ("BHARTIARTL", "Bharti Airtel", "10604", 0.1, "Telecom"),
    ("CIPLA", "Cipla", "694", 0.1, "Pharma"),
    ("COALINDIA", "Coal India", "20374", 0.05, "Energy"),
    ("DRREDDY", "Dr Reddys Laboratories", "881", 0.1, "Pharma"),
    ("EICHERMOT", "Eicher Motors", "910", 0.5, "Auto"),
    ("ETERNAL", "Eternal", "5097", 0.05, "Consumer"),
    ("GRASIM", "Grasim Industries", "1232", 0.1, "Materials"),
    ("HCLTECH", "HCL Technologies", "7229", 0.1, "IT"),
    ("HDFCBANK", "HDFC Bank", "1333", 0.05, "Banking"),
    ("HDFCLIFE", "HDFC Life Insurance", "467", 0.05, "Financial Services"),
    ("HINDALCO", "Hindalco Industries", "1363", 0.1, "Metals"),
    ("HINDUNILVR", "Hindustan Unilever", "1394", 0.1, "FMCG"),
    ("ICICIBANK", "ICICI Bank", "4963", 0.1, "Banking"),
    ("INDIGO", "Interglobe Aviation", "11195", 0.5, "Aviation"),
    ("INFY", "Infosys", "1594", 0.1, "IT"),
    ("ITC", "ITC", "1660", 0.05, "FMCG"),
    ("JIOFIN", "Jio Financial Services", "18143", 0.01, "Financial Services"),
    ("JSWSTEEL", "JSW Steel", "11723", 0.1, "Metals"),
    ("KOTAKBANK", "Kotak Bank", "1922", 0.05, "Banking"),
    ("LT", "Larsen & Toubro", "11483", 0.1, "Capital Goods"),
    ("M&M", "Mahindra & Mahindra", "2031", 0.1, "Auto"),
    ("MARUTI", "Maruti Suzuki", "10999", 1.0, "Auto"),
    ("MAXHEALTH", "Max Healthcare Institute", "22377", 0.1, "Healthcare"),
    ("NESTLEIND", "Nestle", "17963", 0.1, "FMCG"),
    ("NTPC", "NTPC", "11630", 0.05, "Power"),
    ("ONGC", "Oil & Natural Gas Corporation", "2475", 0.01, "Energy"),
    ("POWERGRID", "Power Grid Corporation of India", "14977", 0.05, "Power"),
    ("RELIANCE", "Reliance Industries", "2885", 0.1, "Energy"),
    ("SBILIFE", "SBI Life Insurance", "21808", 0.1, "Financial Services"),
    ("SBIN", "State Bank of India", "3045", 0.1, "Banking"),
    ("SHRIRAMFIN", "Shriram Finance", "4306", 0.1, "Financial Services"),
    ("SUNPHARMA", "Sun Pharmaceutical", "3351", 0.1, "Pharma"),
    ("TATACONSUM", "Tata Consumer Products", "3432", 0.1, "FMCG"),
    ("TATASTEEL", "Tata Steel", "3499", 0.01, "Metals"),
    ("TCS", "Tata Consultancy Services", "11536", 0.1, "IT"),
    ("TECHM", "Tech Mahindra", "13538", 0.1, "IT"),
    ("TITAN", "Titan", "3506", 0.5, "Consumer"),
    ("TMPV", "Tata Motors Passenger Vehicles", "3456", 0.05, "Auto"),
    ("TRENT", "Trent", "1964", 0.1, "Consumer"),
    ("ULTRACEMCO", "UltraTech Cement", "11532", 1.0, "Materials"),
    ("WIPRO", "Wipro", "3787", 0.01, "IT"),
)

# (symbol, name, exchange token). Indices are stored with segment INDEX.
INDICES: tuple[tuple[str, str, str], ...] = (
    ("NIFTY", "NIFTY 50", "13"),
    ("BANKNIFTY", "NIFTY BANK", "25"),
    ("INDIAVIX", "INDIA VIX", "21"),
)
