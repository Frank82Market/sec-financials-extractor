import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv("../.env")
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT")
CIK = "0000091142"  # AOS (CIK a 10 cifre)

headers = {"User-Agent": SEC_USER_AGENT}
url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"

output_dir = "C:/Users/Fujitsu/Desktop/progetto sec/test_output"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "aos_test.txt")

today = datetime.today()
twentyfour_months_ago = today - timedelta(days=730)

with open(output_path, "w", encoding="utf-8") as fout:
    fout.write(f"Analisi TUTTI I FACTS per AOS (CIK: {CIK}) negli ultimi 24 mesi (10-K e 10-Q):\n\n")
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    facts = data.get("facts", {}).get("us-gaap", {})
    for tag, tagdata in facts.items():
        for unit, values in tagdata.get("units", {}).items():
            for v in values:
                form = v.get("form", "")
                if form not in ("10-K", "10-Q"):
                    continue
                end = v.get("end")
                if not end:
                    continue
                end_dt = datetime.strptime(end, "%Y-%m-%d")
                if end_dt < twentyfour_months_ago:
                    continue
                fout.write(
                    f"Tag: {tag} | Unit: {unit} | Form: {form} | start: {v.get('start')} | end: {end} | filed: {v.get('filed')} | val: {v.get('val')}\n"
                )