# Research spec v2: what changed and what it means

Compares the updated specification against the code that is built and deployed today.
The old spec is kept at `docs/spec_research_v1.md`. **`task.md` on disk is still v1**; the v2 text
was pasted into chat and has not been saved to a file.

## Already covered by phase 1

Scanner, historical and technical agent, verification agent (statuses, conflicts, independence rule),
market and sector risk agent, deterministic scoring with database-stored weights and an approval flow,
synthesizer that invents nothing, market regime with factors, sector rotation, historical pattern
statistics with sample-size rules and MFE/MAE, look-ahead protection through `as_of`, documented
survivorship-bias limitation, source registry, run history with explained score changes, agent progress UI,
evidence panel, data freshness, research pages, JSON and CSV export, and the test suite.

## New in v2, buildable now with no new credentials

| Item | Spec section | Note |
|---|---|---|
| **Risk Score 0 to 100** as a third headline number | 22 | Today risk is a LEVEL (low/medium/high). v2 wants a number where higher means more risk. Changes existing scoring and UI |
| **Post-Market Calibration Agent** and its storage | 34, 38 | Measures forward 5m/15m/30m/1h returns, MFE and MAE against each score, then reports by score bucket. The stored candles already make this possible. This is the only way to answer "does the score mean anything" |
| **Research Quality Agent** | 37 | Post-run checks: every claim sourced, verification ran, stale data, thin samples, no unsupported claims |
| **Entity resolution (`InstrumentResolver`)** | 45 | Canonical mapping across RELIANCE, RELIANCE.NS and ISIN. The `isin` column already exists |
| **Source registry capability flags** | 6 | `supports_market_data`, `supports_news`, `supports_filings`, `supports_fundamentals`, `supports_derivatives` |
| **Endpoints** `/verification` and `/agent-trace` | 40 | The data is already stored; only the routes are missing |
| **Background jobs** | 41 | pre-market, market scan, score refresh, post-market calibration |
| **PDF export** | 51 | JSON and CSV exist |
| **Data freshness labels** LIVE / RECENT / STALE | 30 | Freshness is computed; the three-level label is not shown |
| **Extra filters and columns** | 26, 27 | Data-freshness column, market cap, liquidity, F&O availability |
| **FINNIFTY**, F&O universe | 16, 8 | Needs the instrument list, not a new subscription |

## New in v2, blocked on data or keys

| Item | Spec section | Blocked on |
|---|---|---|
| **Derivatives Agent** (futures, OI, options chain, PCR, IV) | 15 | An options and futures data feed. Marked mandatory in v2 |
| **News & Catalyst Agent** and **news deduplication** | 14, 44 | A news source, plus an LLM for classification |
| **Fundamental & Business Agent** | 13 | A fundamentals vendor |
| **Data Research Agent** (company, corporate events, shareholding) | 9 | Exchange filings or a vendor |
| **Event calendar** | 20 | Corporate-events data |
| **LLM synthesis layer** | 3, 25 | An LLM key. Numbers stay deterministic either way |
| **1-minute timeframe** | 11 | A real provider |
| **Tier 3 and 4 sources** in the registry | 5, 54 | Licensing decisions, one adapter each |

## Tables and endpoints still missing

Tables: `research_news`, `research_corporate_events`, `research_derivatives_snapshots`,
`research_calibration_results`, `research_data_quality_events`.
Endpoints: `/{symbol}/corporate-events`, `/{symbol}/derivatives`, `/{symbol}/verification`, `/{symbol}/agent-trace`.

## Unchanged constraints worth restating

The core principle in v2 is the same as v1: deterministic numbers, LLM only for summarising and explaining,
no guaranteed predictions, no automatic conversion of a score into a trading instruction, and scoring weights
never change without explicit approval.
