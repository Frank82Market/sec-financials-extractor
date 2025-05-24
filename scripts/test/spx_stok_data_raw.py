import pandas as pd
import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv("../.env")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")

def is_quarterly_period(start, end):
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        days = (end_dt - start_dt).days
        return 80 <= days <= 100  # circa 3 mesi
    except Exception:
        return False

def get_fiscal_year_end(best_values):
    filings_10k = [v for v in best_values if v.get("form", "N/A") == "10-K" and v.get("end")]
    if filings_10k:
        latest_10k = max(filings_10k, key=lambda x: x["end"])
        fiscal_year_end = latest_10k["end"]
        fiscal_year_end_dt = datetime.strptime(fiscal_year_end, "%Y-%m-%d")
        return fiscal_year_end_dt
    return None

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
            # Se la differenza tra i filed è > 92 giorni (~3 mesi), tieni il più vecchio
            if abs((filed_dt - prev_filed_dt).days) > 92:
                if filed_dt < prev_filed_dt:
                    dedup[key] = v
            else:
                # Se la differenza è <= 3 mesi, tieni comunque il più vecchio
                if filed_dt < prev_filed_dt:
                    dedup[key] = v
    return list(dedup.values())

def test_sec_netincome(cik, output_file):
    cik_str = str(cik).zfill(10)
    tags = [
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NetIncomeLossAvailableToCommonStockholdersDiluted",
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAttributableToParent",
        "NetIncomeLossAttributableToShareholders"
    ]
    headers = {"User-Agent": SEC_USER_AGENT}
    best_tag = None
    best_values = []
    for tag in tags:
        url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik_str}/us-gaap/{tag}.json"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
            data = response.json()
            if "units" in data and "USD" in data["units"]:
                values = data["units"]["USD"]
                if len(values) > len(best_values):
                    best_tag = tag
                    best_values = values
        except Exception as e:
            output_file.write(f"[ERRORE] {e}\n")

    if best_tag and best_values:
        fiscal_year_end_dt = get_fiscal_year_end(best_values)
        if fiscal_year_end_dt:
            fiscal_year_end_prev = fiscal_year_end_dt.replace(year=fiscal_year_end_dt.year - 1)
        else:
            fiscal_year_end_prev = None

        filings_filtered = []
        today = datetime.today()
        for v in best_values:
            form = v.get("form", "N/A")
            start = v.get("start")
            end = v.get("end")
            if not end:
                continue
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            # Filtra solo filing con end > fine anno fiscale precedente e <= fine anno fiscale corrente
            if fiscal_year_end_prev and (fiscal_year_end_prev < end_dt <= fiscal_year_end_dt):
                if form == "10-K":
                    filings_filtered.append(v)
                elif start and end and is_quarterly_period(start, end):
                    filings_filtered.append(v)
            # AGGIUNTA: includi anche tutti i filing con end > fiscal_year_end_dt e end <= oggi
            elif end_dt > fiscal_year_end_dt and end_dt <= today:
                if form == "10-K":
                    filings_filtered.append(v)
                elif start and end and is_quarterly_period(start, end):
                    filings_filtered.append(v)
        
        filings_filtered = deduplicate_by_period_keep_oldest(filings_filtered)
        
        output_file.write(f"\n[CIK: {cik_str}] TAG SELEZIONATO: {best_tag}\n")
        for v in filings_filtered:
            output_file.write(
                f"  start: {v.get('start')}, end: {v.get('end')}, filed: {v.get('filed')}, form: {v.get('form', 'N/A')}, val: {v.get('val')}\n"
            )
    else:
        output_file.write(f"\n[CIK: {cik_str}] Nessun dato sufficiente trovato\n")

if __name__ == "__main__":
    df = pd.read_csv("../data/sp500_wikipedia.csv")
    with open("output_netincome_sec.txt", "w", encoding="utf-8") as f:
        for i, row in df.head(5).iterrows():
            cik = row["CIK"]
            test_sec_netincome(cik, f)