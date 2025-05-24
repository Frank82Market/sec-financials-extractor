import os

INPUT_PATH = r"C:\Users\Fujitsu\Desktop\progetto sec\test_output\output_netincome_sec.txt"
OUTPUT_PATH = r"C:\Users\Fujitsu\Desktop\progetto sec\test_output\report_finale.txt"

# Funzione per organizzare i ticker in colonne da 10
def format_ticker_columns(ticker_list, col_size=10):
    if not ticker_list:
        return ""
    n_col = (len(ticker_list) + col_size - 1) // col_size
    columns = [[] for _ in range(n_col)]
    for idx, ticker in enumerate(ticker_list):
        columns[idx // col_size].append(ticker)
    # Trasponi per scrivere in colonne verticali
    max_len = max(len(col) for col in columns)
    lines = []
    for i in range(max_len):
        line = []
        for col in columns:
            if i < len(col):
                line.append(col[i])
            else:
                line.append("")
        lines.append("  ".join(t.ljust(8) for t in line))
    return "\n".join(lines)

# Parsing del file di output
def parse_output_file(path):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    categories = {
        "no_netincome": [],
        "only_basic": [],
        "basic_and_diluted": [],
        "only_diluted": []
    }

    ticker_info = {}  # ticker: {"basic": False, "diluted": False}

    current_ticker = None
    current_block_type = None

    for line in lines:
        if line.startswith("[CIK:"):
            # Estrai ticker
            try:
                current_ticker = line.split("][")[1].split("]")[0]
            except Exception:
                current_ticker = "UNKNOWN"
            # Estrai tipo blocco dalla stessa riga
            if "NetIncome BASIC" in line:
                current_block_type = "basic"
            elif "NetIncome DILUTED" in line:
                current_block_type = "diluted"
            else:
                current_block_type = None
            # Inizializza se nuovo ticker
            if current_ticker not in ticker_info:
                ticker_info[current_ticker] = {"basic": False, "diluted": False}
        elif "NetIncome BASIC" in line:
            current_block_type = "basic"
        elif "NetIncome DILUTED" in line:
            current_block_type = "diluted"
        elif "NetIncomeTTM:" in line:
            if "Non calcolabile" not in line and current_block_type and current_ticker:
                ticker_info[current_ticker][current_block_type] = True

    # Classifica i ticker
    for ticker, info in ticker_info.items():
        if info["basic"] and info["diluted"]:
            categories["basic_and_diluted"].append(ticker)
        elif info["basic"]:
            categories["only_basic"].append(ticker)
        elif info["diluted"]:
            categories["only_diluted"].append(ticker)
        else:
            categories["no_netincome"].append(ticker)

    return categories

def main():
    cats = parse_output_file(INPUT_PATH)

    # Ricava tutti i ticker unici presenti nel file di input
    unique_tickers = set()
    with open(INPUT_PATH, encoding="utf-8") as f:
        for line in f:
            if line.startswith("[CIK:"):
                try:
                    ticker = line.split("][")[1].split("]")[0]
                    unique_tickers.add(ticker)
                except Exception:
                    pass

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("REPORT FINALE NET INCOME TTM\n")
        f.write("="*80 + "\n\n")
        f.write(f"Totale ticker unici nel file: {len(unique_tickers)}\n\n")
        f.write(f"No Net Income TTM: {len(cats['no_netincome'])}\n")
        f.write(f"Only Net Income TTM BASIC: {len(cats['only_basic'])}\n")
        f.write(f"Net Income TTM BASIC & DILUTED: {len(cats['basic_and_diluted'])}\n")
        f.write(f"Only Net Income TTM DILUTED: {len(cats['only_diluted'])}\n\n")

        f.write("No Net Income TTM:\n")
        f.write(format_ticker_columns(cats["no_netincome"]) + "\n\n")
        f.write("Only Net Income TTM BASIC:\n")
        f.write(format_ticker_columns(cats["only_basic"]) + "\n\n")
        f.write("Net Income TTM BASIC & DILUTED:\n")
        f.write(format_ticker_columns(cats["basic_and_diluted"]) + "\n\n")
        f.write("Only Net Income TTM DILUTED:\n")
        f.write(format_ticker_columns(cats["only_diluted"]) + "\n\n")

if __name__ == "__main__":
    main()