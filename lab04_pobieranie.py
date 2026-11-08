"""
LAB 4 (analiza semantyczna), krok 0 - pobranie dodatkowego korpusu do sieci Kohonena.

Dlaczego osobny korpus? Zadanie wymaga przeanalizowania co najmniej 1000 rzeczowników
na podstawie ich wystąpień jako dopełnienie bliższe 100 czasowników przechodnich.
Korpus z lab 1 (ok. 150 tys. wyrazów, głównie historia i geografia Serbii) daje tylko
ok. 900 takich rzeczowników, w większości z jednym wystąpieniem - za mało, żeby sieć
mogła odróżnić pola znaczeniowe. Dlatego pobieramy ok. 8 mln znaków z artykułów
o RÓŻNEJ tematyce (jedzenie, zwierzęta, rośliny, ubrania, budynki, pojazdy, muzyka,
medycyna, sport, technika, gospodarka, wojsko...). Różnorodność tematów jest potrzebna,
żeby w korpusie w ogóle pojawiły się różne pola semantyczne.

Kroki:
  1. pobieramy artykuły z listy SEED_TITLES (po kilka z każdej dziedziny),
  2. z każdego z nich bierzemy kilka losowych linków do innych artykułów (ta sama dziedzina),
  3. pomijamy artykuły krótkie, listy, artykuły już obecne w korpusie z lab 1,
  4. kończymy po zebraniu TARGET_LENGTH znaków.

Wynik: dane/surowy_semantyka.txt (tekst) i dane/artykuly_semantyka.txt (lista artykułów).
Gotowy plik jest w repozytorium; skrypt pobiera od nowa tylko z opcją --od-nowa.
"""
import os
import random
import re
import sys
import time

from wspolne import ARTICLES_FILE, SEM_ARTICLES_FILE, SEM_RAW_FILE, setup_console

API_URL = "https://sr.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "NLP_Student_Project_Script/1.0 (studia_nlp@example.com) python-requests"}
TARGET_LENGTH = 8_000_000
MIN_ARTICLE_LENGTH = 4000
LINKS_PER_SEED = 12
MAX_TRIES_PER_SEED = 40   # ile linków danego artykułu najwyżej sprawdzamy
SEED = 7

# Artykuły startowe pogrupowane według dziedzin (pola semantyczne, które chcemy mieć w korpusie)
SEED_TITLES = {
    "jedzenie i napoje": ["Храна", "Хлеб", "Сир", "Месо", "Млеко", "Вино", "Пиво", "Кафа", "Чај", "Шећер",
                          "Со", "Јаје", "Мед", "Воће", "Поврће", "Кромпир", "Пшеница", "Кукуруз", "Пиринач",
                          "Јабука", "Грожђе", "Парадајз", "Чоколада", "Ракија", "Српска кухиња", "Кување",
                          "Италијанска кухиња", "Пица", "Супа", "Уље", "Со (кухиња)", "Риба (храна)"],
    "zwierzęta": ["Пас", "Мачка", "Коњ", "Говедо", "Овца", "Коза", "Свиња", "Кокошка", "Вук", "Медвед",
                  "Лисица", "Јелен", "Зец", "Лав", "Тигар", "Слон", "Орао", "Птице", "Рибе", "Змије",
                  "Пчела", "Мрави", "Инсекти", "Сисари", "Делфини", "Кит", "Ајкуле", "Сточарство", "Лов"],
    "rośliny": ["Биљке", "Дрво", "Шума", "Храст", "Бор", "Цвет", "Ружа", "Трава", "Пољопривреда",
                "Башта", "Семе", "Лист", "Гљиве", "Воћарство", "Виноградарство", "Ратарство"],
    "ubrania i przedmioty": ["Одећа", "Обућа", "Шешир", "Накит", "Злато", "Сребро", "Намештај", "Сат",
                             "Огледало", "Лампа", "Посуђе", "Текстил", "Вуна", "Кожа (материјал)", "Свила"],
    "budynki i miasto": ["Кућа", "Зграда", "Мост", "Дворац", "Тврђава", "Црква", "Џамија", "Храм",
                         "Архитектура", "Пут", "Улица", "Трг", "Град", "Село", "Школа", "Болница",
                         "Позориште", "Музеј", "Библиотека", "Стадион", "Аеродром", "Лука", "Бањa"],
    "transport": ["Аутомобил", "Аутобус", "Воз", "Железница", "Авион", "Брод", "Бицикл", "Мотоцикл",
                  "Камион", "Трамвај", "Метро", "Подморница", "Хеликоптер", "Ракета", "Саобраћај"],
    "muzyka i sztuka": ["Музика", "Гитара", "Клавир", "Виолина", "Бубањ", "Опера", "Песма", "Оркестар",
                        "Рок музика", "Џез", "Сликарство", "Скулптура", "Филм", "Фотографија", "Плес",
                        "Позоришна представа", "Роман", "Поезија", "Књига", "Новине", "Телевизија", "Радио"],
    "medycyna i ciało": ["Медицина", "Болест", "Лек", "Срце", "Мозак", "Крв", "Кост", "Кожа", "Око",
                         "Зуб", "Грип", "Рак (болест)", "Вакцина", "Антибиотик", "Хирургија", "Грипа",
                         "Дијабетес", "Пандемија ковида 19", "Витамин", "Здравље"],
    "sport": ["Спорт", "Фудбал", "Кошарка", "Одбојка", "Рукомет", "Тенис", "Ватерполо", "Пливање",
              "Атлетика", "Шах", "Бокс", "Скијање", "Светско првенство у фудбалу", "Лига шампиона УЕФА",
              "Новак Ђоковић", "Фудбалска репрезентација Србије", "Олимпијске игре"],
    "nauka i technika": ["Рачунар", "Телефон", "Мобилни телефон", "Интернет", "Софтвер", "Електрична енергија",
                         "Мотор са унутрашњим сагоревањем", "Машина", "Робот", "Сателит", "Нафта", "Угаљ",
                         "Гвожђе", "Бакар", "Челик", "Пластика", "Стакло", "Вода", "Ватра", "Светлост",
                         "Звук", "Магнетизам", "Хемијски елемент", "Математика", "Географија"],
    "gospodarka i polityka": ["Новац", "Банка", "Привреда", "Трговина", "Порез", "Динар", "Евро", "Фабрика",
                              "Индустрија", "Рударство", "Устав", "Закон", "Парламент", "Избори", "Влада",
                              "Демократија", "Суд", "Полиција", "Уједињене нације", "НАТО", "Европска унија"],
    "wojsko": ["Војска", "Оружје", "Пушка", "Топ", "Тенк", "Ратна морнарица", "Ратно ваздухопловство",
               "Битка", "Мач", "Штит", "Оклоп", "Барут", "Бомба", "Стогодишњи рат", "Наполеонови ратови"],
    "przyroda i geografia": ["Река", "Језеро", "Море", "Океан", "Планина", "Острво", "Пустиња", "Клима",
                             "Киша", "Снег", "Ветар", "Земљотрес", "Вулкан", "Камен", "Песак", "Сунце"],
    "rodzina i życie": ["Породица", "Брак", "Дете", "Мајка", "Отац", "Образовање", "Учитељ", "Студент",
                        "Посао", "Празник", "Божић", "Васкрс", "Слава (обичај)", "Свадба", "Игра", "Играчка"],
}


def api_get(params):
    import requests

    params = {"action": "query", "format": "json", "redirects": 1, **params}
    for attempt in range(5):
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # sieć bywa zawodna - kilka prób
            print(f"  [!] {e}; ponawiam...")
            time.sleep(3)
    return {}


def fetch_extract(title):
    data = api_get({"prop": "extracts", "titles": title, "explaintext": 1})
    for page_id, page in data.get("query", {}).get("pages", {}).items():
        if page_id.startswith("-"):
            return None, None, ""
        return page_id, page.get("title"), page.get("extract", "")
    return None, None, ""


def fetch_links(title):
    data = api_get({"prop": "links", "titles": title, "plnamespace": 0, "pllimit": "max"})
    pages = data.get("query", {}).get("pages", {})
    return [link["title"] for p in pages.values() for link in p.get("links", [])]


def good_link(title):
    """Odrzucamy listy, lata, daty i ujednoznacznienia - zwykle mało zdań z czasownikami."""
    return not (re.search(r"\d", title) or "(вишезначна" in title
                or title.startswith(("Списак", "Листа", "Категорија", "Шаблон")))


def main():
    setup_console()
    if os.path.exists(SEM_RAW_FILE) and "--od-nowa" not in sys.argv:
        print(f"Korpus dodatkowy już istnieje: {SEM_RAW_FILE} (opcja --od-nowa pobiera go ponownie)")
        return

    rng = random.Random(SEED)
    known = set()
    if os.path.exists(ARTICLES_FILE):
        known = {t.strip() for t in open(ARTICLES_FILE, encoding="utf-8")}

    # Zapis przyrostowy: każdy artykuł od razu trafia do plików roboczych, więc przerwane
    # pobieranie po ponownym uruchomieniu wznawia się (pomija pobrane artykuły i przejrzane seedy).
    part_raw, part_titles, part_seeds = SEM_RAW_FILE + ".czesc", SEM_ARTICLES_FILE + ".czesc", SEM_RAW_FILE + ".seedy"
    if "--od-nowa" in sys.argv:
        for path in (part_raw, part_titles, part_seeds):
            if os.path.exists(path):
                os.remove(path)
    done_titles = set()
    length = 0
    if os.path.exists(part_titles):
        done_titles = {line.split("\t", 1)[1].strip() for line in open(part_titles, encoding="utf-8") if "\t" in line}
        length = len(open(part_raw, encoding="utf-8").read())
        print(f"Wznawiam: {len(done_titles)} artykułów, {length} znaków")
    done_seeds = set(open(part_seeds, encoding="utf-8").read().split("\n")) if os.path.exists(part_seeds) else set()

    def take(title, domain):
        nonlocal length
        if length >= TARGET_LENGTH or title in done_titles or title in known:
            return False
        time.sleep(0.4)
        page_id, real_title, text = fetch_extract(title)
        if not page_id or real_title in done_titles or real_title in known or len(text) < MIN_ARTICLE_LENGTH:
            return False
        done_titles.add(real_title)
        with open(part_raw, "a", encoding="utf-8") as f:
            f.write(("\n" if length else "") + text)
        with open(part_titles, "a", encoding="utf-8") as f:
            f.write(f"{domain}\t{real_title}\n")
        length += len(text) + 1
        print(f"  {length:>9} / {TARGET_LENGTH}  [{domain}] {real_title}", flush=True)
        return True

    # runda 1: artykuły startowe; runda 2: losowe linki z nich (dziedziny przeplatane)
    seeds = [(d, t) for d, ts in SEED_TITLES.items() for t in ts]
    for domain, title in seeds:
        take(title, domain)
    rng.shuffle(seeds)
    for domain, title in seeds:
        if length >= TARGET_LENGTH:
            break
        if title in done_seeds:
            continue
        links = [l for l in fetch_links(title) if good_link(l)]
        rng.shuffle(links)
        added = 0
        for link in links[:MAX_TRIES_PER_SEED]:  # linki to często krótkie zalążki - ograniczamy próby
            if added >= LINKS_PER_SEED or length >= TARGET_LENGTH:
                break
            added += take(link, domain)
        with open(part_seeds, "a", encoding="utf-8") as f:
            f.write(title + "\n")

    os.replace(part_raw, SEM_RAW_FILE)
    os.replace(part_titles, SEM_ARTICLES_FILE)
    if os.path.exists(part_seeds):
        os.remove(part_seeds)
    print(f"Pobrano {len(done_titles)} artykułów, {length} znaków -> {SEM_RAW_FILE}")


if __name__ == "__main__":
    main()
