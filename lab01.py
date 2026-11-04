import os
import re
import time

import requests

API_URL = "https://sr.wikipedia.org/w/api.php"

# Wikipedia wymaga przedstawienia się w nagłówku. Inaczej szybko odrzuca zapytania (429)
HEADERS = {
    "User-Agent": "NLP_Student_Project_Script/1.0 (studia_nlp@example.com) python-requests"
}

# Długa lista artykułów z różnych dziedzin (historia, geografia, nauka, kultura),
# żeby korpus był duży i zróżnicowany
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


def api_get(params):
    """Zapytanie do API Wikipedii z obsługą błędu 429 (Too Many Requests)."""
    params = {"action": "query", "format": "json", "redirects": 1, **params}
    response = requests.get(API_URL, params=params, headers=HEADERS)
    if response.status_code == 429:
        print("\n[!] Otrzymano błąd 429. Czekam 5 sekund przed ponowieniem...")
        time.sleep(5)
        response = requests.get(API_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def linked_titles(title):
    """Zwraca tytuły artykułów, do których linkuje dany artykuł (zapas, gdy lista się skończy)."""
    data = api_get({"prop": "links", "titles": title, "plnamespace": 0, "pllimit": "max"})
    pages = data.get("query", {}).get("pages", {})
    return [link["title"] for page in pages.values() for link in page.get("links", [])]


def fetch_serbian_text(min_length=1_000_000, min_article_length=5000):
    """
    Pobiera artykuły z serbskiej Wikipedii z opóźnieniem i nagłówkiem User-Agent,
    aby uniknąć błędu 429 (Too Many Requests). Krótkie artykuły (szablonowe
    zalążki) są pomijane, a duplikaty (np. przez przekierowania) nie są liczone.
    Gdy lista TITLES się skończy, dobierane są artykuły linkowane z artykułu "Србија".
    """
    queue = list(TITLES)
    seen_pages = set()
    used_fallback = False
    parts, titles, length = [], [], 0

    print(f"Rozpoczynam pobieranie tekstu (cel: {min_length} znaków)...")

    while length < min_length:
        if not queue:
            if used_fallback:
                print("Skończyły się artykuły do pobrania.")
                break
            used_fallback = True
            queue = linked_titles("Србија")
            print(f"Lista artykułów wyczerpana - dobieram {len(queue)} artykułów linkowanych z 'Србија'")
            continue

        title = queue.pop(0)
        try:
            # Opóźnienie 1.5 sekundy przed każdym strzałem, aby nie spamować API
            time.sleep(1.5)
            data = api_get({"prop": "extracts", "titles": title, "explaintext": 1})

            for page_id, page in data.get("query", {}).get("pages", {}).items():
                extract = page.get("extract", "")
                if page_id in seen_pages or len(extract) < min_article_length:
                    continue
                seen_pages.add(page_id)
                parts.append(extract)
                titles.append(page.get("title"))
                length += len(extract) + 1
                print(f"Pobrano: {length} / {min_length} znaków  ({page.get('title')})")

        except Exception as e:
            print(f"Wystąpił błąd podczas pobierania artykułu '{title}': {e}")

    print(f"Pobrano {len(seen_pages)} artykułów.")
    return " ".join(parts), titles

# Serbski alfabet (cyrylica) - 30 liter
SERBIAN_ALPHABET = "абвгдђежзијклљмнњопрстћуфхцчџш"

def clean_text(text):
    """
    Czyści tekst z interpunkcji, liczb, znaków specjalnych oraz wszystkich znaków
    spoza serbskiego alfabetu (łacinka, greka, indeksy górne typu '²' itp.).
    Zostają tylko wyrazy złożone z liter serbskiej cyrylicy oddzielone spacją.
    """
    cleaned = text.lower()
    cleaned = re.sub(f'[^{SERBIAN_ALPHABET}]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def main():
    raw_text, titles = fetch_serbian_text(1_000_000)
    
    if len(raw_text) == 0:
        print("Nie udało się pobrać żadnego tekstu.")
        return

    with open("surowy_serbski.txt", "w", encoding="utf-8") as f:
        f.write(raw_text)

    # Lista pobranych artykułów (wykorzystywana w sprawozdaniu)
    os.makedirs("dane", exist_ok=True)
    with open(os.path.join("dane", "artykuly.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(titles) + "\n")

    print("\nOczyszczanie tekstu...")
    cleaned_text = clean_text(raw_text)
    
    filename = "oczyszczony_serbski.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
        
    print(f"Zakończono sukcesem! Oczyszczony tekst został zapisany w pliku: {filename}")
    print(f"Długość po oczyszczeniu: {len(cleaned_text)} znaków.")

if __name__ == "__main__":
    main()