import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
import pandas as pd

# --- Configurazione ---
load_dotenv("../.env")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")
CIK = "000091142"  # AOS (deve essere a 10 cifre)
CIK = CIK.zfill(10)

headers = {"User-Agent": SEC_USER_AGENT}
url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"

# --- Tag da cercare (come nel tuo script) ---
tags = [
    "NetIncomeLossAvailableToCommonStockholdersBasic",
    "NetIncomeLossAvailableToCommonStockholdersDiluted",
    "NetIncomeLoss",
    "ProfitLoss",
    "NetIncomeLossAttributableToParent",
    "NetIncomeLossAttributableToShareholders"
]

def get_best_tag_and_values(facts):
    best_tag = None
    best_values = []
    for tag in tags:
        if tag in facts and "USD" in facts[tag].get("units", {}):
            values = [
                v for v in facts[tag]["units"]["USD"]
                if v.get("form") in ("10-K", "10-Q") and v.get("end")
            ]
            if len(values) > len(best_values):
                best_tag = tag
                best_values = values
    return best_tag, best_values

def deduplicate_by_period_keep_oldest(filings):
    dedup = {}
    for v in filings:
        key = (v.get("start"), v.get("end"))
        filed = v.get("filed")
        if not filed:
            continue
        filed_dt = datetime.strptime(filed, "%Y-%m-%d")
        if key not in dedup:
            dedup[key] = v
        else:
            prev_filed = dedup[key].get("filed")
            prev_filed_dt = datetime.strptime(prev_filed, "%Y-%m-%d")
            if abs((filed_dt - prev_filed_dt).days) > 92:
                if filed_dt < prev_filed_dt:
                    dedup[key] = v
            else:
                if filed_dt < prev_filed_dt:
                    dedup[key] = v
    return list(dedup.values())

def is_quarterly_period(start, end):
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        days = (end_dt - start_dt).days
        return 80 <= days <= 100
    except Exception:
        return False

def calcola_ttm(filings):
    today = datetime.today()
    dodici_mesi_fa = today - timedelta(days=366)
    ventiquattro_mesi_fa = today - timedelta(days=730)

    filings_10k = [v for v in filings if v.get("form") == "10-K" and "end" in v]
    filings_10q = [v for v in filings if v.get("form") == "10-Q" and "end" in v]
    filings_10q = [v for v in filings_10q if datetime.strptime(v["end"], "%Y-%m-%d") >= ventiquattro_mesi_fa]

    filings_10k_recenti = [
        v for v in filings_10k
        if datetime.strptime(v["end"], "%Y-%m-%d") >= dodici_mesi_fa and
           350 <= (datetime.strptime(v["end"], "%Y-%m-%d") - datetime.strptime(v["start"], "%Y-%m-%d")).days <= 370
    ]
    if not filings_10k_recenti:
        return "NetIncomeTTM: Non calcolabile (nessun 10-K annuale negli ultimi 12 mesi)"

    annuale = max(filings_10k_recenti, key=lambda x: x["end"])
    annuale_end = annuale["end"]
    annuale_val = float(annuale["val"])

    filings_10q_successivi = sorted(
        [v for v in filings_10q if v["start"] > annuale_end],
        key=lambda x: x["start"]
    )

    if not filings_10q_successivi:
        return f"NetIncomeTTM: {int(annuale_val)}"

    ttm = annuale_val
    for q in filings_10q_successivi:
        q_val = float(q["val"])
        ttm += q_val
        try:
            q_start_prev = (datetime.strptime(q["start"], "%Y-%m-%d") - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
            q_end_prev = (datetime.strptime(q["end"], "%Y-%m-%d") - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
            q_match = next(
                (v for v in filings_10q if
                 abs((datetime.strptime(v["start"], "%Y-%m-%d") - datetime.strptime(q_start_prev, "%Y-%m-%d")).days) <= 7 and
                 abs((datetime.strptime(v["end"], "%Y-%m-%d") - datetime.strptime(q_end_prev, "%Y-%m-%d")).days) <= 7 and
                 datetime.strptime(v["start"], "%Y-%m-%d").month == datetime.strptime(q_start_prev, "%Y-%m-%d").month and
                 datetime.strptime(v["end"], "%Y-%m-%d").month == datetime.strptime(q_end_prev, "%Y-%m-%d").month
                ),
                None
            )
            if q_match:
                ttm -= float(q_match["val"])
            else:
                return "NetIncomeTTM: Non calcolabile (manca Q anno precedente)"
        except Exception:
            return "NetIncomeTTM: Non calcolabile (errore date)"
    return f"NetIncomeTTM: {int(ttm)}"

if __name__ == "__main__":
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    facts = data.get("facts", {}).get("us-gaap", {})

    best_tag, best_values = get_best_tag_and_values(facts)
    if not best_tag or not best_values:
        print("Nessun dato NetIncome trovato per AOS.")
        exit()

    # Ordina per end decrescente e prendi gli ultimi 8 trimestri
    best_values = sorted(best_values, key=lambda x: x["end"], reverse=True)
    best_values = best_values[:8]
    best_values = deduplicate_by_period_keep_oldest(best_values)
    best_values = sorted(best_values, key=lambda x: x["end"])

    print(f"Tag selezionato: {best_tag}")
    for v in best_values:
        print(f"  start: {v.get('start')}, end: {v.get('end')}, filed: {v.get('filed')}, form: {v.get('form')}, val: {v.get('val')}")

    ttm_result = calcola_ttm(best_values)
    print(f"\n{ttm_result}")