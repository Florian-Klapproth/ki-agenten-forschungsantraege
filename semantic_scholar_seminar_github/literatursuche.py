#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vereinfachte Literaturrecherche mit Semantic Scholar für einen Workshop.

Voraussetzungen: Python 3, requests, SEMANTIC_SCHOLAR_API_KEY,
search_queries.txt (ein Suchstring je Zeile) im selben Ordner.

Die Ausgabe enthält auch Open-Access-PDF-Metadaten und kann direkt mit
'download_open_access_pdfs_seminar.py' weiterverarbeitet werden.
"""

import os
import json
import csv
import time
from pathlib import Path

import requests

YEAR_FROM = 2015
RESULTS_PER_QUERY = 10
PAUSE_BETWEEN_REQUESTS = 5
API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def load_search_queries(filename):
    """Liest Suchstrings ein; überspringt leere Zeilen und Kommentare (#)."""
    queries = []
    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            query = line.strip()
            if query and not query.startswith("#"):
                queries.append(query)
    return queries


def search_semantic_scholar(query, api_key):
    """Sucht Literatur und übernimmt auch Open-Access-PDF-Informationen."""
    params = {
        "query": query,
        "limit": RESULTS_PER_QUERY,
        "year": f"{YEAR_FROM}-",
        "fields": (
            "paperId,title,authors,year,abstract,"
            "citationCount,venue,url,externalIds,"
            "isOpenAccess,openAccessPdf"
        ),
    }
    headers = {"x-api-key": api_key}

    try:
        response = requests.get(
            API_URL, params=params, headers=headers, timeout=30
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

    try:
        data = response.json()
    except ValueError:
        print("Fehler: Ungültige JSON-Antwort der API.")
        return []

    results = []
    for paper in data.get("data", []):
        authors = [
            author.get("name")
            for author in paper.get("authors") or []
            if author.get("name")
        ]
        external_ids = paper.get("externalIds") or {}
        open_access_pdf = paper.get("openAccessPdf") or {}
        pdf_url = open_access_pdf.get("url")
        is_open_access = paper.get("isOpenAccess") is True
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
            "search_query": query,
            "is_open_access": is_open_access,
            "pdf_url": pdf_url,
            "fulltext_status": (
                "open_access_pdf_available" if pdf_url and (is_open_access or open_access_pdf)
                else "no_open_access_pdf"
            ),
        })
    return results


def remove_duplicates(results):
    """Entfernt Dubletten anhand DOI oder Titel (wie in der Seminarvorlage)."""
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


def save_as_json(results, filename):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)


def save_as_csv(results, filename):
    fieldnames = [
        "title", "year", "authors", "venue", "citation_count", "doi", "url",
        "search_query", "abstract", "is_open_access", "pdf_url",
    ]
    with open(filename, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for paper in results:
            row = paper.copy()
            row["authors"] = "; ".join(row.get("authors") or [])
            writer.writerow({field: row.get(field) for field in fieldnames})


def main():
    script_directory = Path(__file__).resolve().parent
    query_file = script_directory / "search_queries.txt"
    if not query_file.exists():
        raise FileNotFoundError("Die Datei search_queries.txt wurde nicht gefunden.")

    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if not api_key:
        raise ValueError("SEMANTIC_SCHOLAR_API_KEY wurde nicht gefunden.")

    queries = load_search_queries(query_file)
    if not queries:
        raise ValueError("search_queries.txt enthält keine Suchstrings.")

    print(f"Geladene Suchstrings: {len(queries)}")
    all_results = []
    for number, query in enumerate(queries, start=1):
        print(f"\nSuche {number}/{len(queries)}\n{query}")
        results = search_semantic_scholar(query=query, api_key=api_key)
        print(f"Gefundene Treffer: {len(results)}")
        all_results.extend(results)
        if number < len(queries):
            time.sleep(PAUSE_BETWEEN_REQUESTS)

    unique_results = remove_duplicates(all_results)
    print(f"\nTreffer insgesamt: {len(all_results)}")
    print(f"Nach Dublettenprüfung: {len(unique_results)}")
    json_file = script_directory / "semantic_scholar_results.json"
    csv_file = script_directory / "semantic_scholar_results.csv"
    save_as_json(unique_results, json_file)
    save_as_csv(unique_results, csv_file)
    print(f"\nRecherche abgeschlossen.\nJSON: {json_file.name}\nCSV:  {csv_file.name}")


if __name__ == "__main__":
    main()
