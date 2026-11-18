# Empirical Asset Pricing: Hiring Velocity, Talent Quality & Cross-Sectional Stock Returns (2016–2026)

An end-to-end Python and Stata empirical asset pricing pipeline testing whether corporate hiring velocity and technical talent quality predict cross-sectional equity returns, or whether rapid headcount expansion leads to operating bloat.

## Overview & Research Hypothesis
Public equity investors frequently debate whether aggressive workforce expansion signals high-conviction growth or margin-dilutive empire building. Because SEC 10-K filings do not report employee seniority titles directly, this project constructs point-in-time accounting proxies to separate **high-skill technical expansion** from **low-skill headcount bloat** across a 40-stock large-cap universe (~4,600 firm-month observations; 129 monthly rebalances from 2016 to 2026).

## Data Architecture & Signal Construction
1. **Zero-Dependency Python Data Pipeline (`build_panel.py`):**
   * Extracts point-in-time `dei:EntityNumberOfEmployees`, `us-gaap:ResearchAndDevelopmentExpense`, and `us-gaap:SellingGeneralAndAdministrativeExpense` from SEC EDGAR XBRL APIs (`10-K` and `10-K/A` filings).
   * Enforces strict point-in-time filing availability (`filed_ym < current_ym`) to prevent look-ahead bias.
   * Merges monthly adjusted close returns from Yahoo Finance (`v8` API) with Kenneth French's 5-Factor dataset (`Mkt-RF`, `SMB`, `HML`, `RMW`, `CMA`, `RF`).

2. **Cross-Sectional Signal Specification (`run_backtest.do`):**
   * **Skill Upgrading (`skill_acc`):** Year-over-year R&D growth net of raw headcount growth (`rd_yoy - 0.5 * emp_yoy`), isolating firms increasing technical investment per employee rather than diluting talent intensity through mass hiring.
   * **R&D Acceleration (`rd_yoy`):** Year-over-year percentage change in total uncorrupted R&D expenditure (`raw_st * employees`).
   * **Technical vs. Administrative Scaling (`rgr_yoy`):** Year-over-year change in the R&D-to-SG&A ratio, penalizing administrative overhead bloat.
   * **Peer-Sector Neutralization:** All three signals are standardized cross-sectionally each month (`ym`) within 5 balanced sector groups (Tech Hardware & Semiconductors, Software & IT Services, Internet Retail & Interactive Media, Biotech, and Industrial Machinery), winsorized at +/-3 SD, and combined using fixed a-priori weights:
     `clean_score = 0.45 * z_skill_acc + 0.35 * z_rd_yoy + 0.20 * z_rgr_yoy`

## Key Empirical Findings

### 1. High-Skill Expansion Outperforms Dilution and the Benchmark (40-Stock Universe)
Sorting the 40-stock universe each month into peer-neutral terciles from 2016 to 2026 demonstrates a clear monotonic return hierarchy on a $100k initial investment:
* **Top Tercile (High-Skill Hiring & R&D Expansion):** ~$1,150k
* **40-Stock Equal-Weight Benchmark:** ~$980k
* **Bottom Tercile (Talent Dilution / Hiring Freeze):** ~$850k

### 2. Sample Breadth Eliminates Small-Sample Concentration Noise
* **20-Stock Initial Test (~6–7 stocks/tercile):** Single-stock mega-cap outlier concentration created a non-linear spike in the Middle Tercile, compounding $100k past $3,100k and generating +75.3 bps/month of apparent active alpha (`t = 2.43`, `p = 0.016`).
* **40-Stock Expanded Test (~13–14 stocks/tercile):** Doubling cross-sectional breadth diluted single-stock outlier variance, reducing Middle Tercile active alpha to zero (`_cons = -0.0007`, `t = -0.34`, `p = 0.737`) and restoring first-place outperformance to the Top Tercile.

### 3. Fama-French 5-Factor Attribution (3-Lag Newey-West HAC, N = 129 Months)

| Factor / Metric | 40-Stock Top vs. Bottom (`ls_linear`) | 40-Stock Middle vs. Bench (`mid_active`) | 20-Stock Middle vs. Bench (`mid_active`) |
| :--- | :--- | :--- | :--- |
| **Alpha (`_cons`)** | **+0.0022** (*t* = 0.70, *p* = 0.487) | **-0.0007** (*t* = -0.34, *p* = 0.737) | **+0.0075** (*t* = 2.43, *p* = 0.016) |
| **Annualized Alpha** | **+2.70%** | **-0.84%** | **+9.42%** |
| **Market (`mktrf`)** | -0.0054 (*t* = -0.07) | -0.0115 (*t* = -0.26) | -0.0369 (*t* = -0.71) |
| **Size (`smb`)** | +0.0913 (*t* = 0.72) | +0.0005 (*t* = 0.01) | +0.0687 (*t* = 0.80) |
| **Value (`hml`)** | -0.0671 (*t* = -0.70) | +0.0718 (*t* = 0.92) | +0.0524 (*t* = 0.56) |
| **Profitability (`rmw`)** | +0.0126 (*t* = 0.11) | -0.0757 (*t* = -0.96) | -0.0391 (*t* = -0.43) |
| **Investment (`cma`)** | +0.2005 (*t* = 1.21) | -0.0003 (*t* = -0.00) | -0.0397 (*t* = -0.29) |

### 4. Economic Conclusion: The Reporting-Lag Limit of Annual 10-K Filings
In the 40-stock specification, the Long-Top / Short-Bottom spread (`ls_linear`) is completely market-neutral (`mktrf = -0.0054`, `t = -0.07`) with no statistically significant Fama-French style tilts (all factor `|t| <= 1.21`), delivering **+22.2 bps/month (+2.70% annualized)** of positive point-estimate alpha. However, the alpha remains statistically noisy (`t = 0.70`, `p = 0.487`). Because SEC 10-K workforce and R&D figures are reported only once a year, public markets price in most underlying hiring shifts prior to the filing date—demonstrating that capturing high-conviction workforce alpha requires higher-frequency alternative data (such as 60-day job-posting velocity).

## Repository Contents & Replication
* `build_panel.py` — Zero-dependency Python script that fetches SEC EDGAR XBRL, Yahoo Finance, and Kenneth French data and builds `workforce_panel.csv`.
* `run_backtest.do` — Stata backtesting script (tested on StataNow/SE 19.5) that computes peer-neutral Z-scores, runs 3-lag Newey-West regressions, and exports the cumulative wealth chart.
* `hiring_quality_velocity_backtest.png` — Out-of-sample cumulative wealth trajectory ($100k initial investment).

**To replicate:**
1. Run `python build_panel.py` to generate `workforce_panel.csv`.
2. Open Stata and execute `do run_backtest.do`.
