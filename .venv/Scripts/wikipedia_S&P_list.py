import pandas as pd

# URL Wikipedia con la lista aggiornata S&P 500
url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Estrazione delle tabelle HTML presenti nella pagina
tables = pd.read_html(url)

# Di solito la prima tabella contiene i dati delle aziende
sp500_df = tables[0]

# Pulizia nomi colonne
sp500_df.columns = [col.strip().replace(" ", "_") for col in sp500_df.columns]

# Salvataggio CSV
output_path = "C:\Users\Fujitsu\Desktop\progetto sec\.venv\cartella file\sp500_wikipedia.csv"
sp500_df.to_csv(output_path, index=False)

print(f"✅ File salvato in: {output_path}")
