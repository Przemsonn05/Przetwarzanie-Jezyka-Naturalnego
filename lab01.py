"""
LAB 1 - wybór języka i przygotowanie korpusu.

Język: serbski (cyrylica). Tekst pobieramy z serbskiej Wikipedii, a potem czyścimy:
zostawiamy WYŁĄCZNIE wyrazy złożone z 30 liter serbskiego alfabetu.

Kroki:
  1. pobranie artykułów z Wikipedii (do ok. 1 mln znaków) -> dane/surowy_serbski.txt
  2. czyszczenie: małe litery, każdy znak spoza alfabetu -> spacja, zwinięcie spacji
     -> dane/oczyszczony_serbski.txt
  3. raport: jakie znaki usunięto i ile ich było -> wyniki/lab01/

Uruchomienie:
  python lab01.py            # czyści już pobrany tekst (bez łączenia z internetem)
  python lab01.py --pobierz  # pobiera artykuły od nowa (Wikipedia mogła się zmienić!)
"""
import csv
import os
import re
import sys
import time
import unicodedata
from collections import Counter

from wspolne import (ARTICLES_FILE, CLEAN_FILE, DATA_DIR, RAW_FILE, SERBIAN_ALPHABET,
                     report_to, results_dir)

API_URL = "https://sr.wikipedia.org/w/api.php"
TARGET_LENGTH = 1_000_000      # ile znaków tekstu chcemy pobrać
MIN_ARTICLE_LENGTH = 5000      # krótsze artykuły to zwykle szablonowe zalążki - pomijamy je

# Wikipedia wymaga przedstawienia się w nagłówku, inaczej szybko odrzuca zapytania (błąd 429)
HEADERS = {"User-Agent": "NLP_Student_Project_Script/1.0 (studia_nlp@example.com) python-requests"}

# Lista artykułów z różnych dziedzin (pobierane po kolei, aż zbierzemy TARGET_LENGTH znaków)
TITLES = [
    "Србија", "Историја_Србије", "Београд", "Нови_Сад", "Ниш", "Крагујевац",
    "Војводина", "Косово_и_Метохија", "Црна_Гора", "Босна_и_Херцеговина",
    "Хрватска", "Југославија", "Социјалистичка_Федеративна_Република_Југославија",
    "Краљевина_Југославија", "Краљевина_Србија", "Српско_царство",
    "Немањићи", "Стефан_Немања", "Свети_Сава", "Стефан_Душан", "Косовска_битка",
    "Кнез_Лазар", "Први_српски_устанак", "Други_српски_устанак", "Карађорђе",
    "Милош_Обреновић", "Балкански_ратови", "Први_светски_рат", "Други_светски_рат",
    "Српска_православна_црква", "Српски_језик", "Српска_ћирилица", "Вук_Стефановић_Караџић",
    "Доситеј_Обрадовић", "Иво_Андрић", "Петар_II_Петровић_Његош", "Бранислав_Нушић",
    "Никола_Тесла", "Михајло_Пупин", "Милутин_Миланковић", "Јосип_Броз_Тито",
    "Дунав", "Сава", "Морава", "Балканско_полуострво", "Европа", "Европска_унија",
    "Римско_царство", "Византијско_царство", "Османско_царство", "Аустроугарска",
    "Русија", "Немачка", "Француска", "Италија", "Грчка", "Сједињене_Америчке_Државе",
    "Француска_револуција", "Хладни_рат", "Стари_Египат", "Стара_Грчка",
    "Математика", "Физика", "Хемија", "Биологија", "Астрономија", "Сунчев_систем",
    "Земља", "Месец", "Еволуција", "Ћелија", "Атом", "Рачунар", "Интернет",
    "Филозофија", "Музика", "Књижевност", "Фудбал", "Кошарка", "Олимпијске_игре",
]


# ---------------------------------------------------------------------------
# 1. Pobieranie tekstu z Wikipedii
# ---------------------------------------------------------------------------
def api_get(params):
    """Jedno zapytanie do API Wikipedii; przy błędzie 429 czekamy 5 s i próbujemy ponownie."""
    import requests  # potrzebne tylko przy pobieraniu

    params = {"action": "query", "format": "json", "redirects": 1, **params}
    response = requests.get(API_URL, params=params, headers=HEADERS)
    if response.status_code == 429:
        print("[!] Błąd 429 (za dużo zapytań). Czekam 5 sekund...")
        time.sleep(5)
        response = requests.get(API_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def linked_titles(title):
    """Tytuły artykułów, do których linkuje dany artykuł (zapas, gdyby lista TITLES się skończyła)."""
    data = api_get({"prop": "links", "titles": title, "plnamespace": 0, "pllimit": "max"})
    pages = data.get("query", {}).get("pages", {})
    return [link["title"] for page in pages.values() for link in page.get("links", [])]


def fetch_serbian_text(min_length=TARGET_LENGTH):
    """
    Pobiera kolejne artykuły (sam tekst, bez kodu wiki), aż uzbiera `min_length` znaków.
    Między zapytaniami robi przerwę 1,5 s, żeby nie obciążać serwera.
    Zwraca (tekst, lista_tytułów).
    """
    queue = list(TITLES)
    seen_pages = set()
    used_fallback = False
    parts, titles, length = [], [], 0

    print(f"Pobieram tekst z serbskiej Wikipedii (cel: {min_length} znaków)...")
    while length < min_length:
        if not queue:
            if used_fallback:
                print("Skończyły się artykuły do pobrania.")
                break
            used_fallback = True
            queue = linked_titles("Србија")
            continue

        title = queue.pop(0)
        try:
            time.sleep(1.5)
            data = api_get({"prop": "extracts", "titles": title, "explaintext": 1})
            for page_id, page in data.get("query", {}).get("pages", {}).items():
                extract = page.get("extract", "")
                if page_id in seen_pages or len(extract) < MIN_ARTICLE_LENGTH:
                    continue  # duplikat (przekierowanie) albo zbyt krótki artykuł
                seen_pages.add(page_id)
                parts.append(extract)
                titles.append(page.get("title"))
                length += len(extract) + 1
                print(f"  pobrano: {length:>9} / {min_length} znaków  ({page.get('title')})")
        except Exception as e:
            print(f"Błąd przy pobieraniu artykułu '{title}': {e}")

    print(f"Pobrano {len(titles)} artykułów.")
    return " ".join(parts), titles


# ---------------------------------------------------------------------------
# 2. Czyszczenie tekstu
# ---------------------------------------------------------------------------
def clean_text(text):
    """
    Zostawia tylko wyrazy z liter serbskiego alfabetu:
      - zamienia wielkie litery na małe,
      - KAŻDY znak spoza alfabetu (cyfra, interpunkcja, łacinka, greka, symbol, nowa linia...)
        zamienia na spację,
      - kilka spacji z rzędu zwija do jednej.
    """
    cleaned = text.lower()
    cleaned = re.sub(f"[^{SERBIAN_ALPHABET}]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def char_category(ch):
    """Opisuje po polsku, do jakiej grupy należy znak usuwany z tekstu."""
    if ch.isspace():
        return "białe znaki (spacje, nowe linie)"
    cat = unicodedata.category(ch)
    if cat.startswith("N"):
        return "cyfry i liczby (np. 1, 2, ²)"
    if cat.startswith("P"):
        return "interpunkcja (. , ( ) – „ ” % ...)"
    if cat.startswith("S"):
        return "symbole (= + ° € ...)"
    if cat.startswith("L"):
        name = unicodedata.name(ch, "")
        if "LATIN" in name:
            return "litery łacińskie"
        if "GREEK" in name:
            return "litery greckie"
        if "CYRILLIC" in name:
            return "cyrylica spoza alfabetu serbskiego"
        return "litery innych alfabetów"
    return "inne znaki"


def cleaning_report(raw, cleaned):
    """Wypisuje, co zostało usunięte, i sprawdza, czy w korpusie zostały tylko litery i spacje."""
    lower = raw.lower()
    removed = Counter(ch for ch in lower if ch not in SERBIAN_ALPHABET)
    by_category = Counter()
    examples = {}
    for ch, n in removed.most_common():
        cat = char_category(ch)
        by_category[cat] += n
        examples.setdefault(cat, []).append(ch)
    uppercase = sum(1 for ch in raw if ch.isupper() and ch.lower() in SERBIAN_ALPHABET)

    print("=" * 80)
    print("CZYSZCZENIE KORPUSU")
    print("=" * 80)
    print(f"Tekst surowy:          {len(raw):>9} znaków")
    print(f"Korpus po czyszczeniu: {len(cleaned):>9} znaków, {len(cleaned.split())} wyrazów")
    print(f"Wielkie litery zamienione na małe: {uppercase}")
    print()
    print("Usunięte (zamienione na spację) znaki spoza alfabetu:")
    print(f"  {'grupa znaków':<38} | {'liczba':>8} | najczęstsze przykłady")
    for cat, n in by_category.most_common():
        sample = " ".join(repr(c)[1:-1] for c in examples[cat][:12])
        print(f"  {cat:<38} | {n:>8} | {sample}")
    print()

    letters_left = set(cleaned) - {" "}
    ok_alphabet = letters_left <= set(SERBIAN_ALPHABET)
    ok_spaces = "  " not in cleaned and cleaned == cleaned.strip()
    print("Kontrola wyniku:")
    print(f"  tylko litery serbskiego alfabetu i spacje:  {'TAK' if ok_alphabet else 'NIE'}")
    print(f"  brak podwójnych spacji i spacji na brzegach: {'TAK' if ok_spaces else 'NIE'}")
    print(f"  występuje {len(letters_left)} z 30 liter alfabetu")
    return by_category, removed


def main():
    report_to(os.path.join(results_dir("lab01"), "raport.txt"))
    os.makedirs(DATA_DIR, exist_ok=True)

    if "--pobierz" in sys.argv or not os.path.exists(RAW_FILE):
        raw_text, titles = fetch_serbian_text()
        if not raw_text:
            print("Nie udało się pobrać żadnego tekstu.")
            return
        with open(RAW_FILE, "w", encoding="utf-8") as f:
            f.write(raw_text)
        with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(titles) + "\n")
    else:
        print(f"Używam pobranego wcześniej tekstu z {RAW_FILE} "
              "(uruchom z opcją --pobierz, aby pobrać go od nowa).\n")
        with open(RAW_FILE, encoding="utf-8") as f:
            raw_text = f.read()

    cleaned_text = clean_text(raw_text)
    with open(CLEAN_FILE, "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    _, removed = cleaning_report(raw_text, cleaned_text)
    with open(os.path.join(results_dir("lab01"), "usuniete_znaki.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["znak", "kod_unicode", "grupa", "liczba"])
        for ch, n in removed.most_common():
            w.writerow([repr(ch)[1:-1], f"U+{ord(ch):04X}", char_category(ch), n])

    print(f"\nKorpus zapisano w {CLEAN_FILE}, raport w wyniki/lab01/.")


if __name__ == "__main__":
    main()
