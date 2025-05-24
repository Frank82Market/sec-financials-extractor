# SEC Net Income TTM Extractor

Questo progetto permette di estrarre, filtrare e calcolare il **Net Income TTM** (Trailing Twelve Months) per aziende quotate, utilizzando i dati XBRL della SEC.

## Funzionalità principali

- Download automatico dei dati XBRL SEC tramite API pubblica
- Parsing e filtraggio intelligente dei facts (NetIncomeLoss, ProfitLoss, ecc.)
- Calcolo robusto del Net Income TTM anche in presenza di dati annuali su 10-Q
- Output dei risultati in file di testo
- Gestione automatica di casi particolari e fallback

## Struttura della cartella

```
progetto sec/
│
├── data/                # (ignorata da git) Dati di input (es: sp500_wikipedia.csv)
├── scripts/
│   ├── test/            # Script principali di estrazione e test
│   └── beckup/          # Script di backup
├── test_output/         # (ignorata da git) Output degli script
├── .env                 # (ignorato) Variabili d'ambiente (es. SEC_USER_AGENT)
├── .gitignore
├── README.md
└── requirements.txt
```

## Requisiti

- Python 3.8+
- Moduli: `requests`, `pandas`, `python-dotenv`

Installa le dipendenze con:
```sh
pip install -r requirements.txt
```

## Configurazione

1. **Crea un file `.env`** nella root del progetto con il tuo user agent SEC:
    ```
    SEC_USER_AGENT=la-tua-email@esempio.com
    ```

2. **Assicurati che il file `.env` sia incluso nel `.gitignore`** (già fatto).

## Utilizzo

Esegui uno degli script principali, ad esempio:
```sh
python scripts/test/test_chiamate_api_netincomettm.py
```

I risultati saranno salvati nella cartella `test_output/`.

## Note di sicurezza

- Nessun dato sensibile viene caricato su GitHub grazie al `.gitignore`.
- Non caricare mai il file `.env` o dati personali nel repository.

## Licenza

Tutti i diritti riservati.  
Questo progetto è distribuito solo per consultazione e studio.  
**Non è consentito l’uso, la modifica o la distribuzione senza il mio esplicito permesso scritto.**

Per richieste di utilizzo o collaborazione, contattami tramite GitHub.

---

**Per domande o suggerimenti, apri una issue!**