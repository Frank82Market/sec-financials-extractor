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

def date_match_approx(start1, end1, start2, end2, tolleranza_giorni=2):
    from datetime import datetime
    s1 = datetime.strptime(start1, "%Y-%m-%d")
    e1 = datetime.strptime(end1, "%Y-%m-%d")
    s2 = datetime.strptime(start2, "%Y-%m-%d")
    e2 = datetime.strptime(end2, "%Y-%m-%d")
    return (
        abs((s1 - s2).days) <= tolleranza_giorni and
        abs((e1 - e2).days) <= tolleranza_giorni and
        s1.month == s2.month and
        e1.month == e2.month
    )

def calcola_ttm(filings):
    from datetime import datetime, timedelta
    import pandas as pd

    today = datetime.today()
    dodici_mesi_fa = today - timedelta(days=366)
    ventiquattro_mesi_fa = today - timedelta(days=730)

    filings_10k = [v for v in filings if v.get("form") == "10-K" and "end" in v]
    filings_10q = [v for v in filings if v.get("form") == "10-Q" and "end" in v]
    filings_10q = [v for v in filings_10q if datetime.strptime(v["end"], "%Y-%m-%d") >= ventiquattro_mesi_fa]

    # Prendi solo i 10-K annuali (12 mesi) con end negli ultimi 12 mesi
    filings_10k_recenti = [
        v for v in filings_10k
        if datetime.strptime(v["end"], "%Y-%m-%d") >= dodici_mesi_fa and
           350 <= (datetime.strptime(v["end"], "%Y-%m-%d") - datetime.strptime(v["start"], "%Y-%m-%d")).days <= 370
    ]
    if not filings_10k_recenti:
        return "NetIncomeTTM: Non calcolabile (nessun 10-K annuale negli ultimi 12 mesi)"

    # Prendi il 10-K più recente
    annuale = max(filings_10k_recenti, key=lambda x: x["end"])
    annuale_start = annuale["start"]
    annuale_end = annuale["end"]
    annuale_val = float(annuale["val"])

    # Trova tutti i 10-Q successivi al 10-K annuale
    filings_10q_successivi = sorted(
        [v for v in filings_10q if v["start"] > annuale_end],
        key=lambda x: x["start"]
    )

    # Se non ci sono 10-Q successivi, il TTM è il 10-K annuale
    if not filings_10q_successivi:
        return f"NetIncomeTTM: {int(annuale_val)}"

    ttm = annuale_val
    for q in filings_10q_successivi:
        q_val = float(q["val"])
        ttm += q_val
        # Trova il trimestre dello stesso periodo dell'anno precedente (match sia start che end)
        try:
            q_start_prev = (datetime.strptime(q["start"], "%Y-%m-%d") - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
            q_end_prev = (datetime.strptime(q["end"], "%Y-%m-%d") - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
            q_match = next(
                (v for v in filings_10q if date_match_approx(v["start"], v["end"], q_start_prev, q_end_prev)),
                None
            )
            if q_match:
                ttm -= float(q_match["val"])
            else:
                return "NetIncomeTTM: Non calcolabile (manca Q anno precedente)"
        except Exception:
            return "NetIncomeTTM: Non calcolabile (errore date)"
    return f"NetIncomeTTM: {int(ttm)}"

def ttm_calcolabile(ttm_result):
    return not ttm_result.startswith("NetIncomeTTM: Non calcolabile")

def stampa_blocco_netincome(cik_str, tipo, best_tag, best_values, output_file, ttm_result):
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
        if fiscal_year_end_prev and (fiscal_year_end_prev < end_dt <= fiscal_year_end_dt):
            if form == "10-K":
                filings_filtered.append(v)
            elif start and end and is_quarterly_period(start, end):
                filings_filtered.append(v)
        elif end_dt > fiscal_year_end_dt and end_dt <= today:
            if form == "10-K":
                filings_filtered.append(v)
            elif start and end and is_quarterly_period(start, end):
                filings_filtered.append(v)
    filings_filtered = deduplicate_by_period_keep_oldest(filings_filtered)
    output_file.write(f"\n[CIK: {cik_str}] {tipo}\n")
    for v in filings_filtered:
        output_file.write(
            f"  start: {v.get('start')}, end: {v.get('end')}, filed: {v.get('filed')}, form: {v.get('form', 'N/A')}, val: {v.get('val')}\n"
        )
    output_file.write(f"\n{ttm_result}\n")

def get_sec_values(cik_str, tag):
    headers = {"User-Agent": SEC_USER_AGENT}
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik_str}/us-gaap/{tag}.json"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return []
        data = response.json()
        if "units" in data and "USD" in data["units"]:
            return data["units"]["USD"]
    except Exception as e:
        return []
    return []

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
    dividend_tags = [
        "PreferredStockDividendsDeclared",
        "DividendsPaidPreferredStock",
        "DividendsPreferredStockCash"
    ]

    # Cerca i valori per BASIC e DILUTED
    values_basic = get_sec_values(cik_str, "NetIncomeLossAvailableToCommonStockholdersBasic")
    values_diluted = get_sec_values(cik_str, "NetIncomeLossAvailableToCommonStockholdersDiluted")

    # Cerca dividendi privilegiati con logica a cascata
    values_dividendi = []
    dividend_tag_used = None
    for tag in dividend_tags:
        vals = get_sec_values(cik_str, tag)
        if vals:
            values_dividendi = vals
            dividend_tag_used = tag
            break

    risultati = []

    # 1. Se trovi BASIC ufficiale, stampa solo BASIC (e DILUTED se vuoi), poi return
    if values_basic:
        ttm_basic = calcola_ttm(values_basic)
        if ttm_calcolabile(ttm_basic):
            risultati.append(("NetIncome BASIC", "NetIncomeLossAvailableToCommonStockholdersBasic", values_basic, ttm_basic))
        if values_diluted:
            ttm_diluted = calcola_ttm(values_diluted)
            if ttm_calcolabile(ttm_diluted):
                risultati.append(("NetIncome DILUTED", "NetIncomeLossAvailableToCommonStockholdersDiluted", values_diluted, ttm_diluted))
        if risultati:
            for tipo, best_tag, best_values, ttm in risultati:
                stampa_blocco_netincome(cik_str, tipo, best_tag, best_values, output_file, ttm)
            return  # <-- Qui il flusso si interrompe se hai BASIC ufficiale

    # 2. Se NON trovi BASIC ufficiale ma trovi DILUTED
    if values_diluted:
        ttm_diluted = calcola_ttm(values_diluted)
        if ttm_calcolabile(ttm_diluted):
            risultati.append(("NetIncome DILUTED", "NetIncomeLossAvailableToCommonStockholdersDiluted", values_diluted, ttm_diluted))
            basic_ricavato = []
            if values_dividendi:
                for v in values_diluted:
                    match = next((d for d in values_dividendi if d.get("start") == v.get("start") and d.get("end") == v.get("end")), None)
                    if match:
                        try:
                            val = float(v["val"]) - float(match["val"])
                            nuovo = v.copy()
                            nuovo["val"] = val
                            basic_ricavato.append(nuovo)
                        except Exception as e:
                            output_file.write(f"[ERRORE] Errore calcolo BASIC ricavato: {e}\n")
            if basic_ricavato:
                ttm_basic_ricavato = calcola_ttm(basic_ricavato)
                if ttm_calcolabile(ttm_basic_ricavato):
                    risultati.append((f"NetIncome BASIC (ricavato da DILUTED - dividendi, tag: {dividend_tag_used})",
                                      "NetIncomeLossAvailableToCommonStockholdersBasic", basic_ricavato, ttm_basic_ricavato))
            if risultati:
                for tipo, best_tag, best_values, ttm in risultati:
                    stampa_blocco_netincome(cik_str, tipo, best_tag, best_values, output_file, ttm)
                if not basic_ricavato:
                    output_file.write(
                        f"[CIK: {cik_str}] [INFO] Dividendi privilegiati non trovati o non disponibili per ricavare NetIncome BASIC. "
                        "NetIncomeTTM riportato è DILUTED.\n"
                    )
            return

    # 3. Fallback: logica classica, cerca il tag con più dati
    best_tag = None
    best_values = []
    for tag in tags:
        values = get_sec_values(cik_str, tag)
        if len(values) > len(best_values):
            best_tag = tag
            best_values = values
    if best_tag and best_values:
        ttm_fallback = calcola_ttm(best_values)
        stampa_blocco_netincome(cik_str, f"TAG SELEZIONATO: {best_tag}", best_tag, best_values, output_file, ttm_fallback)
    else:
        output_file.write(f"\n[CIK: {cik_str}] Nessun dato sufficiente trovato\n")

if __name__ == "__main__":
    import os
    df = pd.read_csv("data/sp500_wikipedia.csv")
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "output_netincome_sec.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        for i, row in df.head(5).iterrows():
            cik = row["CIK"]
            test_sec_netincome(cik, f)