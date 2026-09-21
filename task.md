# Build an AI-Powered Indian Stock Market Research System

I already have an existing full-stack algo-trading project.

The existing technology stack is:

* Backend: FastAPI
* Frontend: Next.js + TypeScript
* Database: MySQL
* Backend architecture: Repository Pattern + Service Layer
* Secrets: `.env`
* Docker
* Python
* The project already has the foundations for algo trading, brokers, strategies, orders, positions, backtesting, etc.

Now extend the project by building a sophisticated **AI-powered Indian Stock Market Research System**.

The purpose of this module is to research the Indian equity market and identify stocks that have **strong intraday research characteristics** based on market data, liquidity, price action, volatility, technical indicators, news, corporate events, fundamentals, historical behavior, and risk.

IMPORTANT:

This is a **research and decision-support system**, not an automatic investment recommendation engine.

The system must NOT simply output:

```text
BUY THIS STOCK
```

Instead it should produce:

```text
Research Score: 84/100

Intraday Setup Quality: Strong
Liquidity: Excellent
Momentum: Strong
Volatility: Suitable
News Catalyst: Positive
Technical Structure: Strong
Risk: Medium

Potential Setup:
...
Invalidation:
...
Risks:
...

Evidence:
...
```

The final score must be explainable and backed by data.

---

# 1. Core Objective

Build a complete **Indian Stock Research Page** where the user can:

1. Scan the Indian equity market.
2. Find today's potentially interesting stocks.
3. Research individual stocks.
4. Collect market data.
5. Collect news.
6. Collect corporate announcements.
7. Collect financial results.
8. Analyze historical price behavior.
9. Analyze technical indicators.
10. Analyze liquidity.
11. Analyze volatility.
12. Analyze volume.
13. Analyze delivery data where available.
14. Analyze institutional/promoter/shareholding information.
15. Analyze corporate actions.
16. Analyze sector performance.
17. Analyze broader market conditions.
18. Verify collected information.
19. Detect conflicting information.
20. Generate a transparent score from 1–100.
21. Explain exactly why the stock received that score.
22. Show positive and negative factors.
23. Show source citations.
24. Show timestamp of every important data point.
25. Allow the user to manually inspect the complete research report.

---

# 2. IMPORTANT: Intraday Research Is Different From Long-Term Investing

Do NOT build this as a normal stock screener.

The system must distinguish between:

```text
Long-Term Investment Quality
```

and:

```text
Intraday Opportunity Quality
```

A company can have excellent fundamentals but poor intraday characteristics.

For intraday research, prioritize:

* Liquidity
* Bid/ask spread
* Volume
* Relative volume
* Price momentum
* Volatility
* ATR
* VWAP
* Opening range
* Gap
* Price structure
* Market trend
* Sector trend
* News catalysts
* Corporate announcements
* Institutional activity where available
* Historical intraday behavior
* Support/resistance
* Risk/reward
* Event risk
* Trading restrictions
* Surveillance status
* Circuit limits
* Slippage risk

---

# 3. Multi-Agent Architecture

Implement the research system as multiple specialized agents.

Do NOT create one giant LLM prompt.

Each agent should have:

```text
Input
↓
Research task
↓
Structured output
↓
Evidence
↓
Confidence
↓
Timestamp
↓
Source references
```

Agents should communicate using structured Pydantic schemas.

---

# 4. Agent 1 — Market Scanner

Name:

```text
MarketScannerAgent
```

Purpose:

Scan the Indian equity universe and identify candidate stocks.

Potential universe:

* NSE listed equities
* Nifty 50
* Nifty Next 50
* Nifty 100
* Nifty 200
* Nifty 500
* User-selected watchlist

Avoid automatically including extremely illiquid securities.

Scanner factors:

### Price

* Current price
* Previous close
* Gap %
* Day change %
* 5D return
* 20D return

### Volume

* Current volume
* Average volume
* Relative volume
* Volume spike

### Volatility

* ATR
* Historical volatility
* Intraday range
* Average daily range

### Technical

* EMA
* SMA
* RSI
* MACD
* VWAP
* Bollinger Bands
* ADX
* Supertrend
* Support/resistance

### Market behavior

* Gap up
* Gap down
* Breakout
* Breakdown
* Momentum
* Reversal
* VWAP reclaim
* VWAP rejection

The scanner should produce candidates such as:

```json
{
  "symbol": "RELIANCE",
  "candidate_reason": [
    "Relative volume 2.1x",
    "Price above VWAP",
    "Strong sector momentum"
  ],
  "initial_score": 78
}
```

Do not make this score the final score.

---

# 5. Agent 2 — Data Research Agent

Name:

```text
MarketResearchAgent
```

For every candidate, collect comprehensive information.

Sources should have a hierarchy.

Prefer:

### Tier 1

Official sources:

* NSE
* BSE
* SEBI
* Company investor-relations pages
* Company filings
* Official exchange filings

### Tier 2

Reliable financial sources:

* Reuters
* Bloomberg
* Economic Times
* Moneycontrol
* Business Standard
* CNBC-TV18
* Financial Express

### Tier 3

Other sources

Use carefully and clearly mark them.

Never treat a random blog/social-media post as verified financial information.

The research agent should collect:

### Company

* Company name
* Sector
* Industry
* Market cap
* Listing
* Index membership

### Corporate

* Latest announcements
* Board meetings
* Results
* Dividends
* Bonus
* Split
* Buyback
* Fund raising
* M&A
* Management changes
* Regulatory actions
* Credit-rating changes

### Financial

* Revenue
* EBITDA
* EBITDA margin
* PAT
* EPS
* ROE
* ROCE
* Debt
* Cash
* Operating cash flow
* Free cash flow

### Shareholding

* Promoter holding
* FII holding
* DII holding
* Public holding
* Recent changes

### News

* Positive news
* Negative news
* Neutral news
* News timestamp
* News source
* Catalyst
* Expected impact

---

# 6. Agent 3 — Data Verification Agent

Name:

```text
DataVerificationAgent
```

This agent is extremely important.

Never trust a single source for critical information.

For every important claim:

```text
Source A
      ↓
Source B
      ↓
Source C
      ↓
Verification
```

Verify:

* Current price
* Volume
* Corporate announcements
* Financial results
* News
* Shareholding
* Corporate actions
* Management changes
* Regulatory events

Output:

```json
{
  "claim": "Company announced Q2 results",
  "status": "VERIFIED",
  "sources_checked": 3,
  "confidence": 0.96
}
```

Possible statuses:

```text
VERIFIED
PARTIALLY_VERIFIED
CONFLICTING
UNVERIFIED
STALE
```

If sources conflict, DO NOT hide the conflict.

Show:

```text
⚠ Conflicting information

Source A:
...

Source B:
...

Verification confidence:
61%
```

Also record:

```text
source_timestamp
retrieved_at
data_as_of
```

This is especially important for intraday research.

NSE itself states that company-uploaded information can be displayed without independent verification of adequacy, accuracy or veracity. Therefore, the verification layer must remain separate from the collection layer.

---

# 7. Agent 4 — Historical & Technical Analysis Agent

Name:

```text
HistoricalTechnicalAgent
```

Analyze the stock's historical behavior.

Use multiple timeframes:

```text
5 minute
15 minute
30 minute
1 hour
Daily
Weekly
```

Where data is available.

Calculate:

### Trend

* EMA 9
* EMA 20
* EMA 50
* EMA 100
* EMA 200
* SMA equivalents

### Momentum

* RSI
* MACD
* ROC
* ADX

### Volatility

* ATR
* Historical volatility
* Bollinger Band width

### Volume

* Relative volume
* Volume moving average
* Volume spikes
* Volume/price relationship

### Price action

* Higher highs
* Higher lows
* Lower highs
* Lower lows
* Breakouts
* Breakdowns
* Consolidation
* Range expansion
* Mean reversion

### Intraday

* Opening range
* Previous day high
* Previous day low
* Previous close
* VWAP
* Gap
* Gap fill history
* Intraday support/resistance

### Historical behavior

Analyze:

```text
How does this stock behave after a gap-up?

How often does a breakout continue?

How often does price reverse after crossing VWAP?

What is the average 15-minute move?

What is the average 30-minute move?

What is the average 1-hour move?

What is the historical probability of reaching X% after a particular setup?
```

Do NOT invent probabilities.

Only calculate them from sufficient historical data.

Include sample size:

```text
Pattern:
VWAP breakout

Occurrences:
183

Successful:
112

Historical success rate:
61.2%

Data period:
2023-01-01 to 2026-09-21
```

---

# 8. Agent 5 — Fundamental & Business Analysis Agent

Name:

```text
FundamentalResearchAgent
```

This agent analyzes the business separately from the intraday setup.

Analyze:

### Business

* Business model
* Revenue segments
* Competitive position
* Industry
* Sector outlook
* Major customers where available
* Key risks

### Financial quality

* Revenue growth
* EBITDA growth
* PAT growth
* Margin trend
* ROE
* ROCE
* Debt/equity
* Interest coverage
* Cash flow
* Working capital

### Valuation

* PE
* PB
* EV/EBITDA
* PEG where meaningful
* Historical valuation
* Peer valuation

### Management

* Promoter holding
* Promoter pledge
* Management changes
* Related-party transactions
* Governance concerns
* Auditor changes
* Regulatory issues

Do not let fundamental quality dominate the intraday score.

Keep:

```text
Fundamental Score
```

separate from:

```text
Intraday Score
```

---

# 9. Agent 6 — News & Catalyst Agent

Name:

```text
NewsCatalystAgent
```

Analyze recent information.

Classify:

```text
POSITIVE
NEGATIVE
NEUTRAL
MIXED
```

Identify:

### Catalysts

* Earnings
* Order wins
* New contracts
* Product launches
* M&A
* Government orders
* Regulatory approvals
* Capacity expansion
* Management commentary
* Sector policy
* Commodity prices

### Risks

* Regulatory action
* Investigation
* Downgrade
* Debt concerns
* Promoter selling
* Weak earnings
* Guidance reduction
* Legal problems
* Corporate governance issues

Each news item should include:

```text
Headline
Source
Published time
Retrieved time
Company
Sentiment
Importance
Expected duration
Confidence
URL
```

Distinguish:

```text
FACT
ANALYSIS
OPINION
RUMOUR
```

Never present rumours as facts.

---

# 10. Agent 7 — Market & Risk Agent

Name:

```text
MarketRiskAgent
```

This agent looks beyond the individual stock.

Analyze:

### Market

* NIFTY trend
* BANK NIFTY trend
* India VIX
* Market breadth
* Advance/decline
* Index momentum
* Global market direction
* US market overnight movement
* Asian markets
* USD/INR
* Crude oil
* Gold where relevant
* Bond yields where relevant

### Sector

Determine:

```text
Sector trend
Sector relative strength
Sector momentum
Sector breadth
```

Compare:

```text
Stock
vs
Sector
vs
NIFTY
```

### Risk

Check:

* Liquidity
* Spread
* Average traded value
* Volatility
* Circuit limits
* ASM/GSM status where applicable
* Trading restrictions
* Event risk
* Corporate action risk
* Earnings proximity
* Unusual volume
* Unusual price movement

NSE surveillance measures can consider parameters including price/volume variation, volatility, market capitalization, delivery percentage, client concentration and PE. These should be incorporated into the risk research layer rather than ignored.

---

# 11. Agent 8 — Quantitative Scoring Agent

Name:

```text
QuantScoringAgent
```

Generate an overall:

```text
Research Score: 1–100
```

But DO NOT use an arbitrary LLM-generated number.

The score must be calculated from explicit components.

Suggested structure:

```text
Market Regime                  10 points
Liquidity                      15 points
Price Action                   15 points
Momentum                       10 points
Volume                         10 points
Volatility Suitability         10 points
Technical Setup                10 points
News/Catalyst                  10 points
Historical Setup Quality        5 points
Risk Penalty                    5 points
------------------------------------------
TOTAL                          100
```

Important:

The system must support configurable weights.

Do not hardcode these weights permanently.

Store them in configuration/database.

---

# 12. Score Components

## Liquidity Score

Consider:

* Average traded value
* Average volume
* Bid/ask spread
* Market depth where available
* Slippage

A highly liquid stock should generally score better for an intraday research universe.

---

## Price Action Score

Consider:

* Trend
* Breakout
* Breakdown
* VWAP
* Support/resistance
* Structure
* Gap behavior

---

## Momentum Score

Consider:

* RSI
* MACD
* ADX
* ROC
* Relative strength

---

## Volume Score

Consider:

```text
Current Volume / Average Volume
```

and:

```text
Relative Volume
```

Also detect:

```text
Price ↑ + Volume ↑
Price ↑ + Volume ↓
Price ↓ + Volume ↑
Price ↓ + Volume ↓
```

---

# 13. Volatility Score

Do NOT assume that maximum volatility is always good.

We need:

```text
Suitable Volatility
```

rather than:

```text
Highest Volatility
```

Analyze:

* ATR
* Historical volatility
* Intraday range
* Expected movement
* Spread
* Slippage

A stock with extreme volatility and poor liquidity should receive a risk penalty.

---

# 14. Historical Setup Score

This is different from general historical performance.

For example:

```text
Today's setup:
Gap Up + High Volume + Above VWAP
```

Search historical data for similar conditions.

Calculate:

```text
Occurrences
Positive outcomes
Negative outcomes
Average return
Median return
Maximum adverse excursion
Maximum favorable excursion
```

Only calculate statistics when sample size is adequate.

Show:

```text
Sample Size: 214
```

Never present a tiny sample as statistically reliable.

---

# 15. Risk Penalty

Apply penalties for:

```text
ASM/GSM
Poor liquidity
Extreme spread
Circuit proximity
Very high volatility
Upcoming result
Major corporate event
Regulatory action
Conflicting data
Unverified news
Large gap
Unusual price behavior
Low historical sample size
```

The risk layer should be capable of reducing a stock's overall score.

---

# 16. Agent 9 — Research Synthesizer

Name:

```text
ResearchSynthesizerAgent
```

This agent receives outputs from every other agent.

It should NOT invent new facts.

It should synthesize:

```text
Market
Technical
Historical
Fundamental
News
Liquidity
Risk
Verification
```

into one report.

Example:

```text
RELIANCE

Research Score
84 / 100

Data Confidence
93 / 100

Intraday Setup
Strong

Market Regime
Bullish

Sector
Positive

Liquidity
Excellent

Momentum
Strong

Volume
2.1x average

Volatility
Suitable

News Catalyst
Positive

Historical Setup
Favorable

Risk
Medium
```

Then:

```text
WHY THIS STOCK APPEARS ON THE RESEARCH LIST

1. Relative volume is significantly elevated.
2. Price is above VWAP.
3. Sector is outperforming the broader market.
4. Historical setups with similar conditions showed...
5. Recent verified company news indicates...
```

Then:

```text
RISKS

1. ...
2. ...
3. ...
```

Then:

```text
WHAT WOULD INVALIDATE THE SETUP

1. ...
2. ...
3. ...
```

Do NOT simply say:

```text
BUY
```

The report should present evidence and conditions so the user can make the final decision.

---

# 17. Research Page UI

Create a complete professional research dashboard.

Route:

```text
/research
```

The page should contain:

## Market Overview

```text
NIFTY
BANK NIFTY
INDIA VIX
Advance / Decline
Market Breadth
Market Regime
```

---

# 18. Top Research Candidates

Display a table:

```text
Rank
Symbol
Company
Price
Change %
Relative Volume
ATR
VWAP
Sector
Research Score
Confidence
Risk
Catalyst
```

Example:

```text
1
RELIANCE
₹XXXX
+2.1%
2.4x
1.8%
Above VWAP
Energy
84
93%
Medium
Positive
```

Do not call this "best stocks".

Use:

```text
Top Research Candidates
```

---

# 19. Score Breakdown

When clicking a stock:

```text
Overall Score       84

Liquidity           14/15
Price Action        13/15
Momentum             9/10
Volume               9/10
Volatility           8/10
Technical Setup      9/10
News                 8/10
Historical           4/5
Risk                 10/10
```

Show this visually.

Use radar/bar charts where useful.

---

# 20. Stock Research Detail Page

Route:

```text
/research/[symbol]
```

Sections:

### Overview

```text
Price
Change
Volume
Market Cap
Sector
Industry
```

### Intraday Setup

```text
Trend
VWAP
RSI
MACD
ATR
Relative Volume
Support
Resistance
```

### Historical Analysis

Charts:

```text
1D
1W
1M
6M
1Y
3Y
5Y
```

### Intraday Pattern Analysis

Show:

```text
5m
15m
30m
1h
```

### News

Show latest relevant news with timestamps.

### Corporate Events

Show:

```text
Results
Board Meetings
Dividends
Bonus
Split
Buyback
Fundraising
```

### Shareholding

Show:

```text
Promoter
FII
DII
Public
```

### Financials

Show:

```text
Revenue
EBITDA
PAT
Margins
ROE
ROCE
Debt
Cash Flow
```

### Risk

Show:

```text
Liquidity Risk
Volatility Risk
Event Risk
Corporate Risk
Data Confidence
Market Risk
```

---

# 21. Evidence Panel

This is mandatory.

Every major AI-generated conclusion must have supporting evidence.

Example:

```text
WHY MOMENTUM SCORE = 9/10

✓ Price above 20 EMA
✓ Price above VWAP
✓ RSI = 64
✓ ADX = 27
✓ Relative volume = 2.3x

Sources:
NSE
Market Data Provider
Retrieved: 09:31:24 IST
```

For news:

```text
Source:
Reuters

Published:
09:12 IST

Retrieved:
09:14 IST

Verification:
Verified by 2 sources
```

---

# 22. Data Freshness

Every data point should have:

```text
data_as_of
retrieved_at
source
source_type
confidence
```

Show stale data clearly.

For example:

```text
⚠ Data is 35 minutes old
```

Do not allow stale market data to appear identical to live data.

---

# 23. Research Runs

Allow users to run:

```text
New Research Scan
```

Options:

```text
Market:
NSE

Universe:
NIFTY 50
NIFTY 100
NIFTY 500
Custom

Research Type:
Intraday

Time:
Current

Depth:
Quick
Standard
Deep
```

For Deep research:

```text
Run all agents
```

For Quick:

```text
Scanner
Technical
Risk
Scoring
```

---

# 24. Agent Status UI

Show live research progress:

```text
Research Run #1024

✓ Market Scanner
✓ Data Research
✓ Data Verification
✓ Historical Analysis
✓ Fundamental Analysis
✓ News Analysis
● Risk Analysis
○ Quant Scoring
○ Final Synthesis
```

Show:

```text
Started
Duration
Records analyzed
Sources checked
Conflicts found
```

---

# 25. Research History

Create:

```text
/research/history
```

Store previous research runs.

Allow comparison:

```text
Today's score
Yesterday's score
Score change
```

Example:

```text
RELIANCE

Yesterday: 72
Today:     84

Change: +12

Reason:

Relative volume increased
Sector momentum improved
New verified catalyst
```

---

# 26. Explain Score Changes

This is important.

If:

```text
Score = 84
```

and later:

```text
Score = 67
```

show:

```text
Score decreased by 17 points.

Reasons:

- Relative volume normalized
- Price lost VWAP
- Sector momentum weakened
- New negative news detected
- Volatility increased
```

---

# 27. Database Design

Create tables such as:

```text
research_runs
research_candidates
research_agent_runs
research_agent_outputs
research_sources
research_claims
research_verifications
research_scores
research_score_components
research_news
research_corporate_events
research_market_snapshots
research_sector_snapshots
research_historical_patterns
research_risk_events
```

Important fields:

```text
symbol
agent_name
run_id
source
source_url
retrieved_at
data_as_of
confidence
status
raw_data
structured_data
```

Use JSON columns where flexible agent output is necessary, but do NOT put the entire application database into JSON.

Important searchable fields should remain normalized.

---

# 28. Agent Orchestration

Create an orchestrator:

```text
ResearchOrchestrator
```

Flow:

```text
MarketScanner
       ↓
Candidate Selection
       ↓
Parallel Research
       ├── DataResearch
       ├── HistoricalTechnical
       ├── Fundamental
       ├── NewsCatalyst
       └── MarketRisk
       ↓
DataVerification
       ↓
QuantScoring
       ↓
ResearchSynthesizer
       ↓
Research Report
```

Run independent agents in parallel where possible.

Do not unnecessarily run them sequentially.

---

# 29. Agent Output Schema

Every agent should return something similar to:

```json
{
  "agent": "HistoricalTechnicalAgent",
  "symbol": "RELIANCE",
  "status": "SUCCESS",
  "confidence": 0.91,
  "timestamp": "2026-09-22T09:35:00+05:30",
  "findings": [],
  "metrics": {},
  "risks": [],
  "sources": [],
  "warnings": []
}
```

Use Pydantic models.

Do not pass arbitrary strings between agents where structured data is possible.

---

# 30. Source Management

Create a source registry.

Each source:

```text
name
type
priority
base_url
enabled
rate_limit
reliability_score
```

Example:

```text
NSE
BSE
SEBI
Company IR
Reuters
Economic Times
Business Standard
Moneycontrol
```

The system must respect:

* robots.txt
* API terms
* website terms
* rate limits
* copyright restrictions

Do not build a scraper that aggressively bypasses anti-bot systems.

Prefer official APIs, downloadable datasets, RSS feeds, public filings and permitted sources where available.

---

# 31. Source Reliability

Create:

```text
Source Reliability Score
```

Example:

```text
Official exchange      1.00
Regulator              1.00
Company filing         0.95
Major news provider    0.90
Financial portal       0.80
Other                  0.50
```

These should be configurable.

Do not assume a source is accurate merely because it has a high reliability score.

Use it as one factor in verification.

---

# 32. Conflict Detection

If:

```text
Source A = Revenue ₹10,000 Cr
Source B = Revenue ₹9,800 Cr
```

detect:

```text
CONFLICT
```

Do not silently select one.

Show:

```text
Conflicting values detected.

Source A:
₹10,000 Cr

Source B:
₹9,800 Cr

Resolution:
Awaiting verification
```

---

# 33. Confidence System

Separate:

```text
Research Score
```

from:

```text
Data Confidence
```

Example:

```text
Research Score: 87/100
Data Confidence: 61/100
```

This means:

> The available evidence appears favorable, but the underlying data has limited confidence.

This distinction is very important.

---

# 34. Backtesting Research Scores

Eventually create a system that evaluates whether historical research scores actually had predictive value.

Store:

```text
research_score
timestamp
stock
market_condition
subsequent_5m_return
subsequent_15m_return
subsequent_30m_return
subsequent_1h_return
maximum_favorable_excursion
maximum_adverse_excursion
```

Then calculate historical performance of score buckets:

```text
Score 90-100
Score 80-89
Score 70-79
Score 60-69
```

Do NOT assume that a higher score means a higher probability of profit until this has been empirically tested.

---

# 35. Avoid Look-Ahead Bias

This is critical.

When backtesting research:

Only use information that was actually available at that historical timestamp.

Do NOT allow:

```text
Today's closing price
Tomorrow's news
Later corporate announcement
Future financial result
```

to influence an earlier historical score.

The research engine must support:

```text
as_of_timestamp
```

for all historical research.

---

# 36. Avoid Survivorship Bias

Do not only backtest today's surviving companies.

Where feasible, maintain historical universe membership.

Document limitations if historical constituent data is unavailable.

---

# 37. Market Regime Detection

Add a dedicated market-regime component.

Classify conditions such as:

```text
Strong Bullish
Bullish
Range
Bearish
Strong Bearish
High Volatility
Low Volatility
```

But make the classification rule-based and explainable.

Example:

```text
NIFTY > EMA20
NIFTY > EMA50
Breadth > 60%
VIX moderate
```

Then:

```text
Market Regime:
Bullish
Confidence:
82%
```

Do not use regime labels without showing the underlying factors.

---

# 38. Sector Rotation

Create a sector dashboard.

Track:

```text
IT
Banking
Financial Services
Energy
Pharma
Auto
FMCG
Metals
Realty
Telecom
etc.
```

Show:

```text
Sector
1D return
5D return
Relative strength
Volume
Breadth
Momentum
```

Then compare each candidate stock to its sector.

---

# 39. Event Calendar

Create an event calendar for:

```text
Results
Board Meetings
Corporate Actions
Dividends
Splits
Bonus
Buybacks
Major announcements
```

Warn when an intraday candidate has a major event risk.

---

# 40. Risk Alerts

Create warnings:

```text
⚠ Low liquidity

⚠ Extreme volatility

⚠ Upcoming results

⚠ Corporate event

⚠ Surveillance measure

⚠ Conflicting data

⚠ Low historical sample

⚠ Large spread

⚠ Data stale

⚠ Unverified news
```

These warnings must be visible on the research page.

---

# 41. Research Score Should Never Be Just an LLM Opinion

The LLM may:

* summarize
* classify
* explain
* compare
* identify relationships
* extract information

But numerical values should come from deterministic calculations wherever possible.

For example:

```text
RSI
ATR
Volume
Relative Volume
Returns
Drawdown
PE
ROE
Debt
Historical success rate
```

must come from actual data/calculation.

The LLM should not invent these values.

---

# 42. Architecture

Maintain this separation:

```text
Data Layer
    ↓
Data Normalization
    ↓
Research Agents
    ↓
Verification
    ↓
Quantitative Scoring
    ↓
Research Synthesis
    ↓
Frontend
```

Never:

```text
Raw Web Page
    ↓
LLM
    ↓
BUY
```

---

# 43. Research API

Create endpoints:

```text
POST /api/v1/research/run

GET /api/v1/research/runs

GET /api/v1/research/runs/{id}

GET /api/v1/research/candidates

GET /api/v1/research/candidates/{symbol}

GET /api/v1/research/{symbol}

GET /api/v1/research/{symbol}/history

GET /api/v1/research/{symbol}/news

GET /api/v1/research/{symbol}/technical

GET /api/v1/research/{symbol}/fundamentals

GET /api/v1/research/{symbol}/risk

GET /api/v1/research/{symbol}/sources

GET /api/v1/research/{symbol}/score-history
```

---

# 44. Frontend Navigation

Add:

```text
Dashboard
Trading
Strategies
Orders
Positions
Backtesting

Research
   ├── Market Overview
   ├── Today's Candidates
   ├── Stock Research
   ├── Sector Analysis
   ├── News & Catalysts
   ├── Event Calendar
   └── Research History

Risk
Settings
```

---

# 45. Today's Research Page

Make this the primary page.

At the top:

```text
INDIAN MARKET RESEARCH

Market Status:
OPEN

Market Regime:
Bullish

NIFTY:
...

BANK NIFTY:
...

INDIA VIX:
...

Advance:
...

Decline:
...
```

Then:

```text
TOP RESEARCH CANDIDATES
```

with sortable columns.

Filters:

```text
Score > 80
Liquidity > X
Relative Volume > X
Sector
Market Cap
Price range
Volatility
Risk
Catalyst
```

---

# 46. Stock Detail Research

When user clicks:

```text
RELIANCE
```

show the entire research report on one page.

Sections:

```text
Overview
Score
Score Breakdown
Market Context
Technical Analysis
Intraday Setup
Historical Behavior
News
Corporate Events
Fundamentals
Shareholding
Sector
Risk
Data Verification
Sources
Agent Findings
```

Use tabs where appropriate, but keep important information visible without excessive navigation.

---

# 47. Agent Trace

Allow the user to inspect:

```text
Agent 1 → findings
Agent 2 → findings
Agent 3 → verification
Agent 4 → historical analysis
Agent 5 → fundamentals
Agent 6 → news
Agent 7 → risk
Agent 8 → score
Agent 9 → synthesis
```

This makes the AI system auditable.

---

# 48. Research Report Export

Allow:

```text
Export PDF
Export JSON
Export CSV
```

The PDF should include:

```text
Stock
Timestamp
Research Score
Confidence
Market regime
Technical
Fundamental
News
Risk
Historical analysis
Sources
Warnings
```

---

# 49. Notifications

Later support:

```text
Telegram
Discord
Email
```

Examples:

```text
Research score crossed 85

New high-confidence catalyst detected

Major negative news detected

Risk status changed

Stock entered top research candidates
```

Do NOT automatically send trade orders based on these alerts.

---

# 50. Scheduled Research

Create background jobs for:

### Pre-market

Before market opens:

```text
Global markets
Overnight news
Corporate events
Gap candidates
Market regime
Sector rotation
```

### Market open

```text
Opening range
Volume
Gap
Momentum
VWAP
```

### Intraday

Periodically refresh:

```text
Price
Volume
News
Market regime
Score
Risk
```

### Post-market

Generate:

```text
Daily research report
```

---

# 51. Pre-Market Research

Create a dedicated pre-market report:

```text
Global Market Summary

Indian Market Setup

Major Corporate News

Results Today

Board Meetings

Corporate Actions

Gap Candidates

High Relative Volume Watchlist

Sector Strength

Potential Risk Events
```

---

# 52. Post-Market Research

At the end of the day:

```text
What happened?

Which candidates performed?

Which scores were accurate?

Which signals failed?

What caused the failure?

Was the market regime classification correct?

Did news change the outcome?
```

Store this for future model improvement.

---

# 53. Research Learning Loop

Eventually implement:

```text
Research
   ↓
Prediction/Score
   ↓
Market Outcome
   ↓
Evaluation
   ↓
Model/Weight Analysis
   ↓
Improved Research
```

But do NOT allow the system to automatically change production scoring weights.

Any weight change should require explicit approval.

---

# 54. Important Missing Features To Include

I specifically want the system to include these items because they are easy to miss:

```text
✓ Market regime
✓ Sector strength
✓ Liquidity
✓ Bid/ask spread
✓ Relative volume
✓ ATR
✓ VWAP
✓ Gap analysis
✓ Support/resistance
✓ Historical intraday patterns
✓ News
✓ Corporate announcements
✓ Results
✓ Corporate actions
✓ Shareholding
✓ Promoter pledge
✓ Institutional activity where available
✓ Fundamentals
✓ Valuation
✓ Regulatory risk
✓ Surveillance status
✓ Event risk
✓ Data freshness
✓ Data confidence
✓ Source verification
✓ Conflicting information
✓ Historical sample size
✓ Slippage
✓ Transaction costs
✓ Look-ahead bias protection
✓ Survivorship bias protection
✓ Research score history
✓ Score calibration
✓ Agent traceability
✓ Audit trail
```

---

# 55. Security

Follow the existing project security architecture.

Never expose:

```text
API keys
API secrets
Broker tokens
LLM keys
Database passwords
```

to the frontend.

Use `.env`.

Create:

```text
.env.example
```

and update `.gitignore`.

---

# 56. Performance

Do not run expensive LLM research for every stock in the entire Indian market.

Use a funnel:

```text
~2000 stocks
      ↓
Quantitative pre-filter
      ↓
~200 stocks
      ↓
Technical/liquidity filter
      ↓
~50 stocks
      ↓
News + research agents
      ↓
~10-20 candidates
      ↓
Deep research
      ↓
Final candidates
```

This will reduce:

* API costs
* LLM costs
* execution time
* unnecessary scraping
* database load

---

# 57. Caching

Cache:

```text
Market data
News
Corporate events
Financial data
Technical indicators
```

Do not repeatedly fetch identical data.

Use Redis where appropriate.

---

# 58. Rate Limiting

Implement source-specific rate limits.

Never aggressively scrape websites.

Prefer:

```text
Official APIs
Official feeds
Public exchange data
RSS
Permitted endpoints
```

Respect terms of service.

---

# 59. Observability

Integrate with the existing monitoring system if available.

Track:

```text
research_run_duration
agent_duration
agent_failure_rate
sources_checked
verification_conflicts
LLM_tokens
LLM_cost
research_runs
data_fetch_errors
stale_data_count
```

Each research run should have a unique:

```text
research_run_id
```

for complete tracing.

---

# 60. Testing

Write tests for:

### Agents

```text
Scanner
Verifier
Technical
Fundamental
News
Risk
Scoring
Synthesizer
```

### Scoring

Test that:

```text
Higher liquidity → appropriate score increase

Extreme risk → score reduction

Missing data → confidence reduction

Conflicting data → confidence reduction

Stale data → warning

Insufficient historical sample → warning
```

### Historical analysis

Test:

```text
No look-ahead bias
Correct timestamp filtering
Correct sample calculation
```

### API

Test all research endpoints.

### Frontend

Test:

```text
Research list
Stock detail
Score breakdown
Agent status
Filters
Research history
```

---

# 61. Final Deliverable

Implement the complete research system inside the existing project.

Do not create a separate unrelated application.

Reuse:

* Existing authentication
* Existing database setup
* Existing repository architecture
* Existing Docker setup
* Existing API conventions
* Existing frontend components
* Existing logging/observability

First inspect the current codebase before making changes.

Do not overwrite existing functionality.

Before implementation:

1. Inspect current project structure.
2. Identify existing models.
3. Identify existing broker architecture.
4. Identify existing strategy architecture.
5. Identify existing Celery/background workers.
6. Identify existing frontend layout.
7. Identify existing API conventions.
8. Identify existing environment configuration.
9. Prepare an implementation plan.
10. Then implement incrementally.

After implementation:

```text
Run backend tests
Run frontend lint
Run TypeScript checks
Run migrations
Start Docker services
Test API endpoints
Test frontend
Test a complete research run
Test Paper Trading safety
Verify secrets are not exposed
```

At the end provide:

```text
1. Files created
2. Files modified
3. Database migrations
4. New environment variables
5. New API endpoints
6. New frontend pages
7. Agent architecture
8. Scoring methodology
9. Data sources
10. How to run research
11. How to run tests
12. Known limitations
13. Future improvements
```

The final result should be a **real, auditable, multi-agent Indian stock market research platform**, not a mock UI and not an LLM that randomly assigns stock scores.
