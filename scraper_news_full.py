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
    Pobiera właściwą treść raportu z espiebi.pap.pl.
    Działa niezależnie od tego, czy 'Treść raportu:' występuje w <b>, <p> lub zagnieżdżonej tabeli,
    oraz pomija puste wiersze między etykietą a faktyczną treścią.
    """
    match = re.search(r"/node/(\d+)", link)
    if not match:
        return "[Brak numeru raportu w linku]"
    node_id = match.group(1)
    report_url = f"https://espiebi.pap.pl/node/{node_id}"

    try:
        resp = requests.get(report_url, headers=HEADERS, timeout=25)
        resp.raise_for_status()
    except Exception as e:
        return f"[Błąd pobierania raportu {report_url}: {e}]"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Szukamy <td> zawierającego tekst "Treść raportu" (również wewnątrz <b>, <p>, <span>)
    label_td = soup.find("td", string=lambda t: t and "Treść raportu" in t)
    if not label_td:
        label_td = soup.find("td", lambda t: t and "Treść raportu" in t.get_text())

    if not label_td:
        return "[Nie znaleziono etykiety 'Treść raportu']"

    # Przechodzimy do kolejnych wierszy aż znajdziemy <td colspan=...> z treścią
    tr = label_td.find_parent("tr")
    next_tr = tr
    content_td = None

    while next_tr:
        next_tr = next_tr.find_next_sibling("tr")
        if not next_tr:
            break
        candidate = next_tr.find("td", attrs={"colspan": True})
        if candidate and candidate.get_text(strip=True):
            content_td = candidate
            break

    if not content_td:
        return "[Nie znaleziono komórki z treścią raportu]"

    # Konwersja <br> → nowa linia
    text = content_td.get_text(separator="\n", strip=True)
    return text or "[Brak treści w raporcie]"


def scrape_company(symbol: str) -> list[str]:
    """Pobiera tytuł, datę, link i treść raportu dla danej spółki."""
    url = BASE_URL.format(symbol)
    print(f"\n🔍 Sprawdzam spółkę: {symbol} ({url})")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
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
        sleep(1.0)

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
