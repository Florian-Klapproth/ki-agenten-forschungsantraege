#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Seminarversion: Open-Access-Volltexte aus Semantic-Scholar-Suchergebnissen laden.

Funktioniert unabhängig vom Forschungsthema. Unterstützt sowohl die bisherigen
normalisierten Suchergebnisse als auch typische JSON-Antworten der Semantic
Scholar API (Liste oder Objekt mit dem Feld "data" / "results" / "papers").

Installation (einmalig): python -m pip install requests beautifulsoup4
Aufruf:                python download_open_access_pdfs_seminar.py suchergebnisse.json
Optional:              python download_open_access_pdfs_seminar.py suchergebnisse.json pdfs manifest.json --limit 10

Wichtig: Das Skript sucht KEINE neuen Papers. Es lädt PDFs zu zuvor gefundenen
Treffern herunter, wenn die Eingabedaten Open-Access-Hinweise enthalten.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    sys.exit("Fehlende Pakete. Bitte ausführen: python -m pip install requests beautifulsoup4")

STOP = {"a", "an", "the", "of", "for", "and", "in", "on", "to", "with", "via",
        "from", "as", "by", "using", "use", "based", "study", "research", "article"}
OA_STATUSES = {"GOLD", "GREEN", "HYBRID", "BRONZE"}


def read_results(path):
    """Akzeptiert JSON-Liste oder eine typische API-Antwort mit Trefferliste."""
    with path.open(encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        data = next((data[key] for key in ("data", "results", "papers")
                     if isinstance(data.get(key), list)), None)
    if not isinstance(data, list):
        raise ValueError("Erwartet wird eine JSON-Liste oder ein Objekt mit 'data', 'results' oder 'papers' als Liste.")
    return [record for record in data if isinstance(record, dict)]


def normalize(raw):
    """Vereinheitlicht die Feldnamen beider Semantic-Scholar-Datenformate."""
    oa = raw.get("openAccessPdf") or raw.get("open_access_pdf") or {}
    if not isinstance(oa, dict):
        oa = {}

    authors = []
    for author in raw.get("authors") or []:
        name = author.get("name", "") if isinstance(author, dict) else str(author)
        if name:
            authors.append(name)

    external_ids = raw.get("externalIds") or {}
    if not isinstance(external_ids, dict):
        external_ids = {}

    pdf_url = raw.get("pdf_url") or oa.get("url")
    oa_flag = raw.get("isOpenAccess") is True or raw.get("is_open_access") is True
    oa_flag = (oa_flag or raw.get("fulltext_status") == "open_access_pdf_available"
               or (oa.get("status") or "").upper() in OA_STATUSES
               or bool(oa.get("url")))

    return {
        "paper_id": raw.get("paper_id") or raw.get("paperId"),
        "title": raw.get("title") or "Ohne Titel",
        "authors": authors,
        "year": raw.get("year"),
        "venue": raw.get("venue"),
        "doi": raw.get("doi") or external_ids.get("DOI"),
        "abstract": raw.get("abstract"),
        "pdf_url": pdf_url,
        "oa_evidence": bool(oa_flag),
    }


def clean(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def pdf_filename(paper):
    author = paper["authors"][0].split()[-1] if paper["authors"] else "Unbekannt"
    words = [word for word in re.findall(r"[A-Za-z0-9]+", paper["title"])
             if word.lower() not in STOP]
    label = clean(f"{author}_{paper['year'] or 'oJ'}_{'_'.join(words[:5])}")[:85]
    # Eindeutige Endung, auch bei gleichen Autor:innen/Jahren/Titelanfängen
    unique = paper["doi"] or paper["paper_id"] or paper["pdf_url"] or paper["title"]
    suffix = hashlib.sha256(str(unique).encode("utf-8")).hexdigest()[:8]
    return f"{label or 'Paper'}_{suffix}.pdf"


def valid_web_url(url):
    return isinstance(url, str) and urlparse(url).scheme in ("http", "https")


def is_real_pdf(response):
    # Der PDF-Dateiheader ist zuverlässiger als ein HTTP-Content-Type allein.
    return b"%PDF-" in response.content[:1024]


def pdf_link_from_html(response):
    """Wenn ein Link zunächst auf einer Landingpage landet, dort PDF suchen."""
    content_type = (response.headers.get("Content-Type") or "").lower()
    if "html" not in content_type and not response.text.lstrip().lower().startswith(("<!doctype", "<html")):
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    for key in ("citation_pdf_url", "eprints.document_url", "wkhealth_pdf_url"):
        tag = soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            candidate = urljoin(response.url, tag["content"])
            if valid_web_url(candidate):
                return candidate
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        label = tag.get_text(" ", strip=True).lower()
        if href.lower().endswith(".pdf") or "/pdf" in href.lower() or ("download" in href.lower() and "pdf" in label):
            candidate = urljoin(response.url, href)
            if valid_web_url(candidate):
                return candidate
    return None


def get_session():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Seminar OA literature downloader)"})
    retries = Retry(total=2, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                    respect_retry_after_header=True)
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


def save_pdf(session, paper, output_file):
    """Speichert nur tatsächlich als PDF erkannte Antworten; meldet den Status."""
    url = paper["pdf_url"]
    try:
        response = session.get(url, timeout=40, allow_redirects=True)
        response.raise_for_status()
        if is_real_pdf(response):
            output_file.write_bytes(response.content)
            return "downloaded", f"PDF gespeichert; Quelle: {response.url}"
        followup = pdf_link_from_html(response)
        if followup:
            second = session.get(followup, timeout=40, allow_redirects=True)
            second.raise_for_status()
            if is_real_pdf(second):
                output_file.write_bytes(second.content)
                return "downloaded", f"PDF über Landingpage gespeichert; Quelle: {second.url}"
        kind = "doi_landing_page_only" if urlparse(url).netloc.lower() == "doi.org" else "manual_check_required"
        return kind, "Landingpage gefunden, aber kein eindeutig abrufbares PDF."
    except requests.RequestException as exc:
        return "download_failed", f"Netzwerk-/HTTP-Fehler: {exc}"
    except OSError as exc:
        return "download_failed", f"Dateifehler: {exc}"


def main():
    parser = argparse.ArgumentParser(description="Open-Access-PDFs aus Semantic-Scholar-Treffern herunterladen")
    parser.add_argument("source", type=Path, help="JSON-Datei mit Semantic-Scholar-Suchergebnissen")
    parser.add_argument("outdir", nargs="?", type=Path, default=Path("paper_reader_corpus"),
                        help="Zielordner für PDFs (Standard: paper_reader_corpus)")
    parser.add_argument("manifest", nargs="?", type=Path,
                        default=Path("paper_reader_fulltext_manifest_downloaded.json"),
                        help="Ausgabedatei für bibliografische Daten und Downloadstatus")
    parser.add_argument("--limit", type=int, default=None,
                        help="Optional: nur die ersten N Open-Access-Kandidaten verarbeiten")
    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit muss mindestens 1 sein")
    try:
        raw_results = read_results(args.source)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(f"Eingabedatei konnte nicht gelesen werden: {exc}")

    papers = [normalize(record) for record in raw_results]
    # Nur Kandidaten mit einem PDF-Link UND positivem OA-Hinweis.
    candidates = [p for p in papers if p["oa_evidence"] and valid_web_url(p["pdf_url"])]
    skipped = len(papers) - len(candidates)

    # Eventuell mehrfach vorhandene Treffer (Suchstring-Überlappungen) entfernen.
    seen = set()
    unique_papers = []
    for p in candidates:
        key = str(p["paper_id"] or p["doi"] or p["pdf_url"])
        if key not in seen:
            seen.add(key)
            unique_papers.append(p)
    duplicates = len(candidates) - len(unique_papers)
    if args.limit is not None:
        unique_papers = unique_papers[:args.limit]

    args.outdir.mkdir(parents=True, exist_ok=True)
    session = get_session()
    manifest = []
    for index, paper in enumerate(unique_papers, 1):
        filename = pdf_filename(paper)
        entry = {key: paper[key] for key in (
            "paper_id", "title", "authors", "year", "venue", "doi", "abstract", "pdf_url")}
        entry.update({"id": index, "local_pdf_filename": filename,
                      "download_status": "manual_check_required", "note": ""})
        output_path = args.outdir / filename
        already_downloaded = False
        if output_path.is_file():
            with output_path.open("rb") as existing:
                already_downloaded = existing.read(5) == b"%PDF-"
        if already_downloaded:
            status, note = "downloaded", "Bereits vorhanden; erneuter Download ausgelassen."
        else:
            status, note = save_pdf(session, paper, output_path)
            time.sleep(0.5)
        entry["download_status"] = status
        entry["note"] = note
        manifest.append(entry)
        print(f"[{index}/{len(unique_papers)}] {status}: {paper['title'][:65]}")

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    counts = Counter(item["download_status"] for item in manifest)
    print(f"\nTreffer in der Eingabedatei: {len(papers)}")
    print(f"Ohne geeigneten OA-PDF-Nachweis/-Link: {skipped}")
    print(f"Doppelte Treffer entfernt: {duplicates}")
    print(f"Verarbeitete Kandidaten: {len(manifest)}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    print(f"PDF-Ordner: {args.outdir}")
    print(f"Manifest:   {args.manifest}")
    print("Hinweis: OA-Metadaten ersetzen keine Prüfung der konkreten Nutzungsrechte.")


if __name__ == "__main__":
    main()
