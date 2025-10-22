import requests
from bs4 import BeautifulSoup
from datetime import datetime
from time import sleep
import os
import re

BASE_URL = "https://www.biznesradar.pl/wiadomosci/{}"
INPUT_FILE = "NCFOCUSNAZWY.txt"
OUTPUT_DIR = "wyniki"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "wiadomosci_spolek.txt")

CUTOFF_DATE = datetime(2025, 7, 1)
HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_date(date_str: str):
    """Konwertuje tekst daty do datetime."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def get_report_text(link: str) -> str:
    """
    Pobiera pełną treść raportu z https://espiebi.pap.pl/node/xxxx.
    """
    match = re.search(r"/node/(\d+)", link)
    if not match:
        return "[Brak numeru raportu w linku]"
    node_id = match.group(1)
    report_url = f"https://espiebi.pap.pl/node/{node_id}"

    try:
        resp = requests.get(report_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return f"[Błąd pobierania raportu {report_url}: {e}]"

    soup = BeautifulSoup(resp.text, "html.parser")
    td = soup.find("td", colspan="11")
    if not td:
        return "[Nie znaleziono treści raportu]"
    
    # Tekst z <br> i czyszczenie
    text = td.get_text(separator="\n", strip=True)
    return text


def scrape_company(symbol: str) -> list[str]:
    """Pobiera tytuł, datę, link i treść raportu dla danej spółki."""
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

        author = footer.find("a", class_="record-author")
        if not author or ("ESPI" not in author.text and "EBI" not in author.text):
            continue

        date_tag = footer.find("span", class_="record-date")
        if not date_tag:
            continue
        date = parse_date(date_tag.text)
        if not date or date < CUTOFF_DATE:
            continue

        header = record.find("div", class_="record-header")
        if not header:
            continue
        link_tag = header.find("a")
        title = link_tag.text.strip() if link_tag else "[Brak tytułu]"
        link = link_tag["href"] if link_tag and "href" in link_tag.attrs else "[Brak linka]"

        print(f"  📄 Pobieram raport: {title}")
        report_text = get_report_text(link)

        entry = (
            f"Tytuł: {title}\n"
            f"Data: {date.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Link: {link}\n"
            f"Treść raportu:\n{report_text}\n"
        )
        results.append(entry)
        sleep(1.0)  # mała przerwa między raportami

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
        block = f"\n=== {symbol} ===\n" + "\n\n".join(company_data)
        all_results.append(block)
        sleep(1.5)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_results))

    print(f"\n✅ Zapisano wyniki do pliku: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
