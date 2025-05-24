import pandas as pd

url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
df = pd.read_html(url)[0]
df.to_csv("../data/sp500_wikipedia.csv", index=False)
print("File sp500_wikipedia.csv aggiornato con successo!")