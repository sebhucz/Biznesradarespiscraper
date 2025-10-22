import requests
from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep
import os

BASE_URL = "https://www.biznesradar.pl/wiadomosci/{}"
INPUT_FILE = "NCFOCUSNAZWY.txt"
OUTPUT_DIR = "wyniki"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "wiadomosci_spolek.txt")

# tylko wiadomości po tej dacie
CUTOFF_DATE = datetime(2025, 7, 1)

HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_date(date_str: str) -> datetime | None:
    """Konwertuje datę z formatu np. '2025-08-18 09:44:22' na datetime"""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def get_article_content(link: str) -> str:
    """Pobiera treść artykułu z linka (pełny raport ESPI/EBI)."""
    try:
        resp = requests.get(link, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        return text if text else "[Brak treści raportu]"
    except Exception as e:
        return f"[Błąd pobierania treści: {e}]"


def scrape_company(symbol: str) -> list[str]:
    """Pobiera wiadomości dla jednej spółki."""
    url = BASE_URL.format(symbol)
    print(f"\n🔍 Przetwarzanie spółki: {symbol} ({url})")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return [f"Błąd pobierania strony {url}: {e}"]

    soup = BeautifulSoup(resp.text, "html.parser")
    records = soup.find_all("div", class_="record")

    results = []
    for record in records:
        footer = record.find("div", class_="record-footer")
        if not footer:
            continue

        # Sprawdzamy źródło (ESPI/EBI)
        author_tag = footer.find("a", class_="record-author")
        if not author_tag or "ESPI" not in author_tag.text and "EBI" not in author_tag.text:
            continue

        # Pobieramy datę
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

        # Treść raportu
        content = get_article_content(link)

        entry = (
            f"Tytuł: {title}\n"
            f"Data: {date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Link: {link}\n"
            f"Treść:\n{content}\n"
        )
        results.append(entry)
        sleep(1)  # niewielka pauza między zapytaniami

    return results if results else [f"Brak aktualnych komunikatów ESPI/EBI od 1 lipca 2025."]


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        companies = [line.strip() for line in f if line.strip()]

    all_results = []
    for symbol in companies:
        company_data = scrape_company(symbol)
        block = f"\n=== {symbol} ===\n" + "\n\n".join(company_data)
        all_results.append(block)
        sleep(1.5)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_results))

    print(f"\n✅ Zapisano wyniki do: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
