"""
Wspólne ustawienia wszystkich laboratoriów: alfabet serbski i ścieżki do plików.
Dzięki temu każdy skrypt korzysta z tych samych plików i nie trzeba powtarzać nazw.
"""
import os
import sys

# Serbski alfabet (cyrylica) - 30 liter, w kolejności alfabetycznej
SERBIAN_ALPHABET = "абвгдђежзијклљмнњопрстћуфхцчџш"

DATA_DIR = "dane"
RESULTS_DIR = "wyniki"

RAW_FILE = os.path.join(DATA_DIR, "surowy_serbski.txt")          # tekst pobrany z Wikipedii
CLEAN_FILE = os.path.join(DATA_DIR, "oczyszczony_serbski.txt")   # korpus po oczyszczeniu (lab 1)
ARTICLES_FILE = os.path.join(DATA_DIR, "artykuly.txt")           # lista pobranych artykułów
PARSED_FILE = os.path.join(DATA_DIR, "korpus_sparsowany.tsv.gz") # korpus po analizie składniowej (lab 4)

# Korpus dodatkowy do analizy semantycznej (sieć Kohonena): ok. 1000 rzeczowników wymaga
# znacznie większej liczby fraz czasownik-dopełnienie, niż daje korpus podstawowy.
SEM_RAW_FILE = os.path.join(DATA_DIR, "surowy_semantyka.txt")
SEM_ARTICLES_FILE = os.path.join(DATA_DIR, "artykuly_semantyka.txt")
SEM_PARSED_FILE = os.path.join(DATA_DIR, "korpus_sparsowany_semantyka.tsv.gz")


def results_dir(name):
    """Zwraca (i w razie potrzeby tworzy) folder na wyniki danego laboratorium, np. wyniki/lab02."""
    path = os.path.join(RESULTS_DIR, name)
    os.makedirs(path, exist_ok=True)
    return path


def setup_console():
    """Konsola Windows domyślnie nie wyświetla cyrylicy - przełączamy ją na UTF-8."""
    sys.stdout.reconfigure(encoding="utf-8")


class Tee:
    """Wypisuje tekst na konsolę i jednocześnie zapisuje go do pliku raportu."""

    def __init__(self, path):
        self.file = open(path, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, text):
        self.stdout.write(text)
        self.file.write(text)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def report_to(path):
    """Od tego momentu wszystko, co wypisuje print(), trafia też do pliku `path`."""
    setup_console()
    sys.stdout = Tee(path)
