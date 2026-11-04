# Przetwarzanie języka naturalnego – korpus języka serbskiego

Programy z laboratoriów 1–4 z przedmiotu *Przetwarzanie języka naturalnego*. Wszystkie analizy
dotyczą korpusu języka serbskiego (cyrylica, 30 liter), pobranego z serbskiej Wikipedii.

📄 **Sprawozdanie:** [`sprawozdanie/sprawozdanie.pdf`](sprawozdanie/sprawozdanie.pdf)

## Co robi każde laboratorium

| Lab | Skrypt | Zadanie | Najważniejszy wynik |
|---|---|---|---|
| 1 | `lab01.py` | pobranie ok. 1 mln znaków z Wikipedii; usunięcie interpunkcji, cyfr, symboli i znaków spoza alfabetu | 149 373 wyrazy, wyłącznie z 30 liter cyrylicy |
| 2 | `lab02_entropia_huffman.py` | udział procentowy liter (prawdopodobieństwa), entropia, kody Huffmana, porównanie z entropią | H = 4,302 bit/znak, L Huffmana = 4,337 bit/znak (efektywność 99,2%) |
| 3 | `lab03_wyrazy_zipf_graf.py` | wyrazy pokrywające 90% tekstu, prawo Zipfa, graf wyrazów sąsiadujących, rdzeń (100 wyrazów o największej liczbie sąsiadów) | 11 148 wyrazów pokrywa 90% tekstu; wykładnik Zipfa s = 0,96 |
| 4 | `lab04_parsowanie.py` | analiza składniowa korpusu (stanza): lematy, części mowy, relacje czasownik → dopełnienie | 3 890 par czasownik–dopełnienie |
| 4 | `lab04_kohonen.py` | 100 czasowników przechodnich, 50 rzeczowników, wektory 100-wymiarowe, sieć Kohonena 10×10, porównanie wyboru czasowników | mapa rzeczowników pogrupowanych wg czasowników, błąd topograficzny 0% |

Pliki pomocnicze:

- `wspolne.py` – alfabet serbski i ścieżki do plików (wspólne dla wszystkich skryptów),
- `sprawdz_wyniki.py` – niezależne sprawdzenie wszystkich wyników (35 testów),
- `generuj_sprawozdanie.py` + `slownik.py` – sprawozdanie PDF (słownik zawiera polskie znaczenia serbskich wyrazów w tabelach),
- `uruchom_wszystko.py` – uruchamia wszystkie etapy po kolei.

## Uruchomienie

```bash
pip install -r requirements.txt
python uruchom_wszystko.py
```

Albo krok po kroku:

```bash
python lab01.py                    # czyszczenie korpusu (z opcją --pobierz: pobranie tekstu od nowa)
python lab02_entropia_huffman.py   # -> wyniki/lab02/
python lab03_wyrazy_zipf_graf.py   # -> wyniki/lab03/
python lab04_parsowanie.py         # -> dane/korpus_sparsowany.tsv.gz (z opcją --od-nowa: parsowanie od nowa)
python lab04_kohonen.py            # -> wyniki/lab04/
python sprawdz_wyniki.py           # testy poprawności
python generuj_sprawozdanie.py     # -> sprawozdanie/sprawozdanie.pdf
```

Pobrany tekst i wynik analizy składniowej są już w repozytorium (`dane/`), więc pełne przeliczenie
trwa kilka minut i nie wymaga internetu. Pobranie tekstu od nowa (`lab01.py --pobierz`) może dać
nieco inny korpus, bo artykuły w Wikipedii się zmieniają. Parsowanie od nowa
(`lab04_parsowanie.py --od-nowa`) trwa 30–90 minut na CPU i przy pierwszym uruchomieniu pobiera
model stanza dla serbskiego (ok. 400 MB). Model był uczony na serbskiej łacince, dlatego tekst jest
transliterowany z cyrylicy na łacinkę, a wynik przepisywany z powrotem na cyrylicę.

## Struktura repozytorium

```
lab01.py … lab04_kohonen.py         programy laboratoriów
wspolne.py                          wspólne ustawienia
sprawdz_wyniki.py                   testy poprawności
uruchom_wszystko.py                 uruchomienie całości
generuj_sprawozdanie.py, slownik.py generowanie sprawozdania
dane/
  surowy_serbski.txt                tekst pobrany z Wikipedii
  oczyszczony_serbski.txt           korpus po oczyszczeniu
  artykuly.txt                      lista pobranych artykułów
  korpus_sparsowany.tsv.gz          korpus po analizie składniowej
wyniki/
  lab01/                            raport czyszczenia, lista usuniętych znaków
  lab02/                            statystyka liter i kody Huffmana (CSV), wykresy
  lab03/                            lista 90%, tabela Zipfa, rdzeń, stopnie węzłów, wykresy
  lab04/                            czasowniki, rzeczowniki, zbiory treningowe, mapy Kohonena
sprawozdanie/
  sprawozdanie.pdf                  sprawozdanie końcowe
  rysunki/                          rysunki pomocnicze sprawozdania
```

Plik `wyniki/lab03/graf_sasiedztwa.gexf` (cały graf, 14 MB, do otwarcia w programie Gephi)
nie jest w repozytorium – tworzy go `lab03_wyrazy_zipf_graf.py`.
