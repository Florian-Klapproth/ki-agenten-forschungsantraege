```"""
Vereinfachte Seminarversion einer Literaturrecherche mit Semantic Scholar.

Voraussetzungen:
1. Python 3
2. Paket "requests"
3. Umgebungsvariable SEMANTIC_SCHOLAR_API_KEY
4. Datei "search_queries.txt" im gleichen Ordner

Die Datei search_queries.txt enthält einen Suchstring pro Zeile.
Leere Zeilen und Zeilen, die mit # beginnen, werden ignoriert.
"""

import os
import json
import csv
import time
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# Einstellungen
# ---------------------------------------------------------------------------

YEAR_FROM = 2015
RESULTS_PER_QUERY = 10
PAUSE_BETWEEN_REQUESTS = 5

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


# ---------------------------------------------------------------------------
# Suchstrings laden
# ---------------------------------------------------------------------------

def load_search_queries(filename):
    """Liest Suchstrings aus einer Textdatei ein."""

    queries = []

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            query = line.strip()

            if query and not query.startswith("#"):
                queries.append(query)

    return queries


# ---------------------------------------------------------------------------
# Semantic Scholar durchsuchen
# ---------------------------------------------------------------------------

def search_semantic_scholar(query, api_key):
    """Führt eine einfache Literaturrecherche bei Semantic Scholar durch."""

    params = {
        "query": query,
        "limit": RESULTS_PER_QUERY,
        "year": f"{YEAR_FROM}-",
        "fields": (
            "paperId,title,authors,year,abstract,"
            "citationCount,venue,url,externalIds"
        )
    }

    headers = {
        "x-api-key": api_key
    }

    try:
        response = requests.get(
            API_URL,
            params=params,
            headers=headers,
            timeout=30
        )
    except requests.RequestException as error:
        print(f"Netzwerkfehler: {error}")
        return []

    if response.status_code == 429:
        print("Rate Limit erreicht. Diese Suchanfrage wird übersprungen.")
        return []

    if response.status_code != 200:
        print(f"Fehler bei der API-Anfrage: {response.status_code}")
        return []

    data = response.json()
    results = []

    for paper in data.get("data", []):
        authors = [
            author.get("name")
            for author in paper.get("authors", [])
            if author.get("name")
        ]

        external_ids = paper.get("externalIds") or {}

        results.append({
            "paper_id": paper.get("paperId"),
            "title": paper.get("title"),
            "year": paper.get("year"),
            "authors": authors,
            "abstract": paper.get("abstract"),
            "citation_count": paper.get("citationCount"),
            "venue": paper.get("venue"),
            "doi": external_ids.get("DOI"),
            "url": paper.get("url"),
            "search_query": query
        })

    return results


# ---------------------------------------------------------------------------
# Dubletten entfernen
# ---------------------------------------------------------------------------

def remove_duplicates(results):
    """Entfernt doppelte Treffer anhand von DOI oder Titel."""

    seen = set()
    unique_results = []

    for paper in results:
        doi = paper.get("doi")
        title = paper.get("title")

        if doi:
            key = doi.lower().strip()
        elif title:
            key = title.lower().strip()
        else:
            continue

        if key not in seen:
            seen.add(key)
            unique_results.append(paper)

    return unique_results


# ---------------------------------------------------------------------------
# Ergebnisse speichern
# ---------------------------------------------------------------------------

def save_as_json(results, filename):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)


def save_as_csv(results, filename):
    fieldnames = [
        "title",
        "year",
        "authors",
        "venue",
        "citation_count",
        "doi",
        "url",
        "search_query",
        "abstract"
    ]

    with open(filename, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for paper in results:
            row = paper.copy()
            row["authors"] = "; ".join(row.get("authors") or [])

            writer.writerow({
                field: row.get(field)
                for field in fieldnames
            })


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main():
    script_directory = Path(__file__).resolve().parent
    query_file = script_directory / "search_queries.txt"

    if not query_file.exists():
        raise FileNotFoundError(
            "Die Datei search_queries.txt wurde nicht gefunden."
        )

    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    if not api_key:
        raise ValueError(
            "SEMANTIC_SCHOLAR_API_KEY wurde nicht gefunden."
        )

    queries = load_search_queries(query_file)

    if not queries:
        raise ValueError(
            "search_queries.txt enthält keine Suchstrings."
        )

    print(f"Geladene Suchstrings: {len(queries)}")

    all_results = []

    for number, query in enumerate(queries, start=1):
        print()
        print(f"Suche {number}/{len(queries)}")
        print(query)

        results = search_semantic_scholar(
            query=query,
            api_key=api_key
        )

        print(f"Gefundene Treffer: {len(results)}")
        all_results.extend(results)

        if number < len(queries):
            time.sleep(PAUSE_BETWEEN_REQUESTS)

    unique_results = remove_duplicates(all_results)

    print()
    print(f"Treffer insgesamt: {len(all_results)}")
    print(f"Nach Dublettenprüfung: {len(unique_results)}")

    json_file = script_directory / "semantic_scholar_results.json"
    csv_file = script_directory / "semantic_scholar_results.csv"

    save_as_json(unique_results, json_file)
    save_as_csv(unique_results, csv_file)

    print()
    print("Recherche abgeschlossen.")
    print(f"JSON: {json_file.name}")
    print(f"CSV:  {csv_file.name}")
```
if __name__ == "__main__":
    main()
