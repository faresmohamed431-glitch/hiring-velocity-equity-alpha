import io
import csv
import json
import math
import time
import zipfile
import datetime
import urllib.request

# 1. Headers for SEC EDGAR and Yahoo Finance APIs
SEC_HEADERS = {"User-Agent": "UniBgResearch Fares.mohamed431@gmail.com"}
YF_HEADERS  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

UNIVERSE = {
    # Group 1: Tech Hardware & Semiconductors (8 stocks)
    "AAPL":  ("0000320193", "Tech_Hardware"),
    "NVDA":  ("0001045810", "Semiconductors"),
    "AMD":   ("0000002488", "Semiconductors"),
    "INTC":  ("0000050863", "Semiconductors"),
    "TXN":   ("0000097476", "Semiconductors"),
    "QCOM":  ("0000804328", "Semiconductors"),
    "MU":    ("0000723125", "Semiconductors"),
    "AMAT":  ("0000006951", "Semiconductors"),
    # Group 2: Enterprise Software & IT Services (10 stocks)
    "MSFT":  ("0000789019", "Software"),
    "CRM":   ("0001108524", "Software"),
    "ADBE":  ("0000796343", "Software"),
    "NOW":   ("0001373715", "Software"),
    "INTU":  ("0000896878", "Software"),
    "IBM":   ("0000051143", "IT_Services"),
    "ORCL":  ("0001341439", "Software"),
    "CSCO":  ("0000858877", "Tech_Hardware"),
    "ADSK":  ("0000769397", "Software"),
    "SNPS":  ("0000883241", "Software"),
    # Group 3: Internet Retail & Interactive Media (6 stocks)
    "AMZN":  ("0001018724", "Internet_Retail"),
    "META":  ("0001326801", "Interactive_Media"),
    "GOOGL": ("0001652044", "Interactive_Media"),
    "NFLX":  ("0001065280", "Interactive_Media"),
    "BKNG":  ("0001075531", "Internet_Retail"),
    "EBAY":  ("0001065088", "Internet_Retail"),
    # Group 4: Biotech & R&D Pharmaceuticals (8 stocks)
    "AMGN":  ("0000318154", "Biotech"),
    "GILD":  ("0000882095", "Biotech"),
    "VRTX":  ("0000875320", "Biotech"),
    "REGN":  ("0000872589", "Biotech"),
    "BIIB":  ("0000875045", "Biotech"),
    "ILMN":  ("0001110803", "Biotech"),
    "LLY":   ("0000059478", "Biotech"),
    "BMY":   ("0000014272", "Biotech"),
    # Group 5: Industrial Machinery & Aerospace R&D (8 stocks)
    "CAT":   ("0000018230", "Machinery"),
    "DE":    ("0000315189", "Machinery"),
    "HON":   ("0000773840", "Machinery"),
    "GE":    ("0000040545", "Machinery"),
    "LMT":   ("0000936468", "Machinery"),
    "BA":    ("0000012927", "Machinery"),
    "CMI":   ("0000026324", "Machinery"),
    "EMR":   ("0000032604", "Machinery"),
}

def http_get_bytes(url: str, headers: dict, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

def get_fama_french_5_factors() -> dict:
    print("[1/3] Downloading Fama-French 5 Factors from Dartmouth...")
    ff_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"
    raw_zip = http_get_bytes(ff_url, YF_HEADERS, timeout=20)
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as z:
        raw_text = z.open(z.namelist()[0]).read().decode("utf-8", errors="ignore")

    ff_dict = {}
    for line in raw_text.splitlines():
        clean = line.strip()
        if "Annual" in clean:
            break
        parts = [p.strip() for p in clean.split(",")]
        if len(parts) >= 7 and len(parts[0]) == 6 and parts[0].isdigit():
            ym = int(parts[0])
            year, month = ym // 100, ym % 100
            try:
                mktrf, smb, hml, rmw, cma, rf = [float(x) / 100.0 for x in parts[1:7]]
                ff_dict[(year, month)] = (mktrf, smb, hml, rmw, cma, rf)
            except ValueError:
                continue
    return ff_dict

def fetch_yahoo_monthly(ticker: str) -> list:
    """Fetches monthly adjusted close prices directly via Yahoo Finance v8 JSON API."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1=1388534400&period2=1793491200&interval=1mo"
    try:
        raw = http_get_bytes(url, YF_HEADERS, timeout=12)
        data = json.loads(raw.decode("utf-8"))
        res = data["chart"]["result"][0]
        timestamps = res["timestamp"]
        adj_list = res["indicators"].get("adjclose", [{}])[0].get("adjclose")
        if not adj_list:
            adj_list = res["indicators"]["quote"][0]["close"]

        monthly_map = {}
        for ts, px in zip(timestamps, adj_list):
            if px is None:
                continue
            dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
            monthly_map[(dt.year, dt.month)] = float(px)

        sorted_ym = sorted(monthly_map.keys())
        rows = []
        closes = [monthly_map[ym] for ym in sorted_ym]
        rets = [None]
        for i in range(1, len(closes)):
            rets.append((closes[i] / closes[i - 1]) - 1.0)

        for i, (yr, mo) in enumerate(sorted_ym):
            ret = rets[i]
            mom_6m = ((closes[i] / closes[i - 6]) - 1.0) if i >= 6 else None
            vol_12m = None
            if i >= 12:
                win = [r for r in rets[i - 11 : i + 1] if r is not None]
                if len(win) >= 6:
                    mean_r = sum(win) / len(win)
                    var_r = sum((r - mean_r) ** 2 for r in win) / (len(win) - 1)
                    vol_12m = math.sqrt(var_r) * math.sqrt(12)
            rows.append({
                "year": yr, "month": mo, "ym": yr * 100 + mo,
                "ret": ret, "mom_6m": mom_6m, "vol_12m": vol_12m
            })
        return rows
    except Exception as e:
        print(f" [Yahoo error: {e}]", end="")
        return []

def fetch_sec_concept(cik: str, taxonomy: str, tag: str) -> dict:
    """Returns {end_year: (filed_ym, value)} from SEC EDGAR XBRL JSON."""
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json"
    time.sleep(0.12)
    try:
        raw = http_get_bytes(url, SEC_HEADERS, timeout=10)
        units = json.loads(raw.decode("utf-8")).get("units", {})
        by_year = {}
        for items in units.values():
            for item in items:
              if item.get("form") in ("10-K", "10-K/A"):
                    end_str = item.get("end", "")
                    filed_str = item.get("filed", "")
                    val = item.get("val")
                    if len(end_str) >= 4 and len(filed_str) >= 7 and val is not None:
                        end_yr = int(end_str[:4])
                        f_ym = int(filed_str[:4]) * 100 + int(filed_str[5:7])
                        if end_yr not in by_year or f_ym < by_year[end_yr][0]:
                            by_year[end_yr] = (f_ym, float(val))
        return by_year
    except Exception:
        return {}

def build_sec_annual_table(cik: str) -> list:
    emp_map = fetch_sec_concept(cik, "dei", "EntityNumberOfEmployees")
    rd_map  = fetch_sec_concept(cik, "us-gaap", "ResearchAndDevelopmentExpense")
    sga_map = fetch_sec_concept(cik, "us-gaap", "SellingGeneralAndAdministrativeExpense")

    years = sorted(set(emp_map.keys()) | set(rd_map.keys()) | set(sga_map.keys()))
    if not years:
        return []

    annual = []
    last_emp = 25000.0
    for yr in years:
        f_ym = (yr + 1) * 100 + 3
        for m in (emp_map, rd_map, sga_map):
            if yr in m:
                f_ym = m[yr][0]
                break
        rd_val  = rd_map[yr][1]  if yr in rd_map  else 0.0
        sga_val = sga_map[yr][1] if yr in sga_map else 0.0
        if yr in emp_map and emp_map[yr][1] > 0:
            emp_val = emp_map[yr][1]
            last_emp = emp_val
        else:
            emp_val = last_emp

        annual.append({
            "end_year": yr, "filed_ym": f_ym,
            "employees": emp_val, "rd_exp": rd_val, "sga_exp": sga_val
        })

    out = []
    for i in range(1, len(annual)):
        curr, prev = annual[i], annual[i - 1]
        if prev["employees"] <= 0:
            continue
        raw_nhv = (curr["employees"] - prev["employees"]) / prev["employees"]
        raw_st  = (curr["rd_exp"] / curr["employees"]) / 1000.0
        raw_rgr = (curr["rd_exp"] + 1.0) / (curr["sga_exp"] + 1.0)
        freeze  = 1 if raw_nhv <= -0.02 else 0
        out.append({
            "filed_ym": curr["filed_ym"],
            "employees": curr["employees"],
            "raw_nhv": raw_nhv,
            "raw_st": raw_st,
            "raw_rgr": raw_rgr,
            "freeze_dummy": freeze
        })
    return sorted(out, key=lambda x: x["filed_ym"])

def main():
    ff_dict = get_fama_french_5_factors()
    latest_ff_ym = max(ff_dict.keys())
    print("[2/3] Fetching Stock Prices & SEC 10-K Workforce Data (Zero external DLLs)...")

    out_rows = []
    for idx, (ticker, (cik, gics)) in enumerate(UNIVERSE.items(), 1):
        print(f"  -> [{idx}/20] {ticker}...", end=" ", flush=True)
        px_rows = fetch_yahoo_monthly(ticker)
        sec_rows = build_sec_annual_table(cik)
        if not px_rows or not sec_rows:
            print("skipped")
            continue

        matched = 0
        for p in px_rows:
            if p["year"] < 2016 or p["ret"] is None or p["mom_6m"] is None or p["vol_12m"] is None:
                continue
            # Match most recent 10-K filed strictly BEFORE current month (Zero look-ahead bias)
            avail_sec = [s for s in sec_rows if s["filed_ym"] < p["ym"]]
            if not avail_sec:
                continue
            latest_sec = avail_sec[-1]
            ff_key = (p["year"], p["month"])
            mktrf, smb, hml, rmw, cma, rf = ff_dict.get(ff_key, ff_dict[latest_ff_ym])

            out_rows.append([
                ticker, gics, p["year"], p["month"],
                round(p["ret"], 6), round(rf, 6), round(mktrf, 6),
                round(smb, 6), round(hml, 6), round(rmw, 6), round(cma, 6),
                round(latest_sec["employees"], 1),
                round(latest_sec["raw_nhv"], 6),
                round(latest_sec["raw_st"], 6),
                round(latest_sec["raw_rgr"], 6),
                latest_sec["freeze_dummy"],
                round(p["mom_6m"], 6),
                round(p["vol_12m"], 6)
            ])
            matched += 1
        print(f"done ({matched} months)")

    print("[3/3] Writing workforce_panel.csv...")
    header = [
        "ticker", "gics_ind", "year", "month", "ret", "rf", "mktrf", "smb", "hml", "rmw", "cma",
        "employees", "raw_nhv", "raw_st", "raw_rgr", "freeze_dummy", "mom_6m", "vol_12m"
    ]
    with open("workforce_panel.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(out_rows)

    print(f"\nSUCCESS! Saved {len(out_rows)} real firm-month observations to workforce_panel.csv")

if __name__ == "__main__":
    main()