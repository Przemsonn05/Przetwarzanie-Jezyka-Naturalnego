"""
Uruchamia po kolei wszystkie etapy: lab 1 -> lab 5, sprawdzenie wyników i sprawozdanie PDF.

Pobieranie tekstów (lab 1, lab 4) i parsowanie (lab 4) są pomijane, jeśli ich wyniki już
istnieją w folderze dane/ - dzięki temu całość trwa kilka minut zamiast kilku godzin.
"""
import subprocess
import sys
import time

from wspolne import setup_console

setup_console()

STEPS = [
    ("Lab 1: czyszczenie korpusu", "lab01.py"),
    ("Lab 2: statystyka liter, entropia, Huffman", "lab02_entropia_huffman.py"),
    ("Lab 3: pokrycie 90%, prawo Zipfa, graf", "lab03_wyrazy_zipf_graf.py"),
    ("Lab 4: pobranie korpusu do analizy semantycznej", "lab04_pobieranie.py"),
    ("Lab 4: analiza składniowa korpusów", "lab04_parsowanie.py"),
    ("Lab 4: sieć Kohonena - klasyfikator semantyczny rzeczowników", "lab04_kohonen.py"),
    ("Lab 5: generator zdań SVO", "lab05_generator_svo.py"),
    ("Sprawdzenie wyników", "sprawdz_wyniki.py"),
    ("Sprawozdanie PDF", "generuj_sprawozdanie.py"),
]

for title, script in STEPS:
    print(f"\n### {title} ({script})", flush=True)
    start = time.time()
    result = subprocess.run([sys.executable, script], capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(result.stdout[-2000:], result.stderr[-2000:])
        sys.exit(f"Błąd w {script} - przerwano.")
    print(f"    gotowe w {time.time() - start:.0f} s")

print("\nWszystkie etapy zakończone. Sprawozdanie: sprawozdanie/sprawozdanie.pdf")
