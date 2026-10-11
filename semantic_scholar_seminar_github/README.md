# Literaturrecherche mit Semantic Scholar – Seminaranleitung

Mit zwei Python-Skripten recherchieren Sie Literatur zu **Ihrem eigenen Forschungsthema** und laden anschließend verfügbare **Open-Access-Volltexte** herunter.

## 1. Voraussetzungen

- **Python 3** ist installiert.
- Sie besitzen einen eigenen **Semantic-Scholar-API-Key**.
- Sie benötigen die Python-Pakete `requests` und `beautifulsoup4`.

## 2. Projektordner anlegen

Öffnen Sie das **Terminal** (Mac) oder **PowerShell** (Windows) und erstellen Sie einen Ordner auf dem Desktop.

**Mac:**

```bash
mkdir -p ~/Desktop/semantic_scholar_seminar
cd ~/Desktop/semantic_scholar_seminar
```

**Windows (PowerShell):**

```powershell
mkdir "$HOME\Desktop\semantic_scholar_seminar"
cd "$HOME\Desktop\semantic_scholar_seminar"
```

Legen Sie darin folgende Dateien ab (die beiden Python-Skripte finden Sie im GitHub-Repository):

```text
semantic_scholar_seminar/
├── README.md
├── literatursuche.py
├── download_open_access_pdfs_seminar.py
└── search_queries.txt
```

Falls Ihr Desktop an einem anderen Speicherort liegt (z. B. OneDrive), passen Sie den Ordnerpfad entsprechend an.

## 3. API-Key dauerhaft einrichten

**Mac (zsh):**

1. Im Terminal `nano ~/.zshrc` eingeben.
2. Am Dateiende folgende Zeile ergänzen (Platzhalter ersetzen):

   ```bash
   export SEMANTIC_SCHOLAR_API_KEY="HIER_IHREN_API_KEY_EINFÜGEN"
   ```

3. Mit **Ctrl + O**, **Enter**, **Ctrl + X** speichern und schließen.
4. Einstellungen laden: `source ~/.zshrc`

**Windows (PowerShell):**

```powershell
[Environment]::SetEnvironmentVariable("SEMANTIC_SCHOLAR_API_KEY", "HIER_IHREN_API_KEY_EINFÜGEN", "User")
```

Danach **PowerShell schließen und neu öffnen** und wieder in den Projektordner wechseln.

**Sicherheit:** Ihren API-Key **niemals in Python-Dateien, die README oder GitHub** eintragen. Die obigen Varianten speichern ihn lokal im Klartext; vermeiden Sie das Teilen der entsprechenden Einstellungen.

## 4. Python-Pakete installieren

**Mac:**

```bash
python3 -m pip install requests beautifulsoup4
```

**Windows:**

```powershell
py -m pip install requests beautifulsoup4
```

> Falls die Paketinstallation wegen einer verwalteten Python-Umgebung scheitert, verwenden Sie eine virtuelle Umgebung (`python3 -m venv .venv` auf Mac bzw. `py -m venv .venv` auf Windows) und installieren Sie die Pakete darin.

## 5. Suchstrings eintragen und Literatur recherchieren

Erstellen bzw. bearbeiten Sie die Datei **`search_queries.txt`** mit einem Texteditor. Tragen Sie **einen Suchstring pro Zeile** ein, beispielsweise:

```text
"generative AI" "critical thinking"
"ChatGPT" "higher education"
```

Leere Zeilen und mit `#` beginnende Zeilen werden übersprungen.

**Literaturrecherche starten** (im Projektordner):

| Mac | Windows |
|---|---|
| `python3 literatursuche.py` | `py literatursuche.py` |

Das Skript legt zwei Dateien an:

- **`semantic_scholar_results.csv`** – Trefferliste, z. B. für Excel.
- **`semantic_scholar_results.json`** – Trefferliste für das Download-Skript, inklusive verfügbarer Open-Access-PDF-Links.

Voreinstellung: **höchstens 10 Treffer je Suchstring ab 2015**. Die Einstellungen `RESULTS_PER_QUERY` und `YEAR_FROM` können im Recherche-Skript angepasst werden.

## 6. Open-Access-Volltexte herunterladen

Starten Sie im **gleichen Projektordner** das zweite Skript:

| Mac | Windows |
|---|---|
| `python3 download_open_access_pdfs_seminar.py semantic_scholar_results.json` | `py download_open_access_pdfs_seminar.py semantic_scholar_results.json` |

Es entstehen:

- **`paper_reader_corpus/`** – heruntergeladene PDF-Volltexte.
- **`paper_reader_fulltext_manifest_downloaded.json`** – Metadaten und Downloadstatus für den späteren Paper-Reader-Agenten.

**Optionaler Test mit höchstens fünf geeigneten Treffern:**

```bash
python3 download_open_access_pdfs_seminar.py semantic_scholar_results.json --limit 5
```

Unter Windows im letzten Befehl `python3` durch `py` ersetzen.

**Hinweis:** Nicht jeder Treffer hat einen frei zugänglichen PDF-Volltext. Das Download-Skript lädt nur Dateien mit passenden Open-Access-Hinweisen und PDF-Link herunter; Fehlschläge werden im Manifest dokumentiert. Die Recherche mit Semantic Scholar allein ersetzt keine vollständige systematische Literaturrecherche.

## Wenn etwas nicht funktioniert

- **`SEMANTIC_SCHOLAR_API_KEY wurde nicht gefunden`**: Key wie in Schritt 3 setzen und neues Terminal öffnen.
- **`No module named requests`**: Pakete aus Schritt 4 installieren.
- **`search_queries.txt wurde nicht gefunden`**: Dateinamen und Projektordner prüfen.
- **`429 / Rate Limit`**: API-Abfragelimit erreicht; später erneut versuchen. Das Recherche-Skript überspringt die betroffene Anfrage.
- **Keine PDFs heruntergeladen**: Prüfen, ob die JSON-Datei die Felder `pdf_url` und `is_open_access` enthält und ob Open-Access-Volltexte verfügbar sind.
