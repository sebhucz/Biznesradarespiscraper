import requests
from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep
import os

BASE_URL = "https://www.biznesradar.pl/wiadomosci/{}"
INPUT_FILE = "NCFOCUSNAZWY.txt"
OUTPUT_DIR = "wyniki"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "wiadomosci_spolek.txt")

CUTOFF_DATE = datetime(2025, 7, 1)
HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_date(date_str: str):
    """Konwertuje tekst daty do obiektu datetime."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def scrape_company(symbol: str) -> list[str]:
    """Pobiera krótkie info o wiadomościach (tytuł, data, link)."""
    url = BASE_URL.format(symbol)
    print(f"\n🔍 Sprawdzam spółkę: {symbol} ({url})")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        return [f"Błąd pobierania strony: {e}"]

    soup = BeautifulSoup(resp.text, "html.parser")
    records = soup.find_all("div", class_="record")

    results = []
    for record in records:
        footer = record.find("div", class_="record-footer")
        if not footer:
            continue

        # Sprawdzamy, czy to komunikat ESPI/EBI
        author = footer.find("a", class_="record-author")
        if not author or ("ESPI" not in author.text and "EBI" not in author.text):
            continue

        # Data
        date_tag = footer.find("span", class_="record-date")
        if not date_tag:
            continue
        date = parse_date(date_tag.text)
        if not date or date < CUTOFF_DATE:
            continue

        # Tytuł i link
        header = record.find("div", class_="record-header")
        if not header:
            continue
        link_tag = header.find("a")
        title = link_tag.text.strip() if link_tag else "[Brak tytułu]"
        link = link_tag["href"] if link_tag and "href" in link_tag.attrs else "[Brak linka]"

        results.append(f"- {title}\n  Data: {date.strftime('%Y-%m-%d %H:%M:%S')}\n  Link: {link}")

    if not results:
        return ["Brak komunikatów ESPI/EBI od 1 lipca 2025."]

    return results


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        companies = [line.strip() for line in f if line.strip()]

    all_results = []
    print(f"📄 Znaleziono {len(companies)} spółek do sprawdzenia...")

    for symbol in companies:
        company_data = scrape_company(symbol)
        block = f"\n=== {symbol} ===\n" + "\n".join(company_data)
        all_results.append(block)
        sleep(0.5)  # krótka pauza, by nie obciążać serwera

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_results))

    print(f"\n✅ Zapisano wyniki do pliku: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
