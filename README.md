# Przetwarzanie języka naturalnego – korpus języka serbskiego

Programy z laboratoriów 1–4 z przedmiotu *Przetwarzanie języka naturalnego*. Wszystkie analizy
dotyczą korpusu języka serbskiego (cyrylica), pobranego z serbskiej Wikipedii.
Sprawozdanie: [`sprawozdanie/sprawozdanie.pdf`](sprawozdanie/sprawozdanie.pdf).

| Lab | Skrypt | Zadanie |
|---|---|---|
| 1 | `lab01.py` | pobranie ok. 1 mln znaków z sr.wikipedia.org; czyszczenie: zostają tylko wyrazy z 30 liter serbskiej cyrylicy |
| 2 | `lab02_entropia_huffman.py` | udział procentowy liter, entropia, kody Huffmana i ich porównanie z entropią |
| 3 | `lab03_wyrazy_zipf_graf.py` | wyrazy pokrywające 90% tekstu, prawo Zipfa, graf wyrazów sąsiadujących i jego rdzeń (100 wyrazów o największej liczbie sąsiadów) |
| 4 | `lab04_parsowanie.py` | analiza składniowa korpusu (stanza): lematy, części mowy, relacje zależnościowe |
| 4 | `lab04_kohonen.py` | 100 czasowników przechodnich i 50 rzeczowników; wektory kolokacji (100 składowych); sieć Kohonena; porównanie wariantów wyboru czasowników |
| – | `generuj_sprawozdanie.py` | generuje sprawozdanie PDF z wyników (`slownik.py` – polskie znaczenia wyrazów w tabelach) |

## Uruchomienie

```bash
pip install -r requirements.txt

python lab01.py                    # pobiera korpus (zapisuje surowy_serbski.txt i oczyszczony_serbski.txt)
python lab02_entropia_huffman.py   # wyniki -> wyniki/
python lab03_wyrazy_zipf_graf.py   # wyniki -> wyniki/lab03/
python lab04_parsowanie.py         # ok. 1,5 h na CPU; wynik -> dane/korpus_sparsowany.tsv.gz
python lab04_kohonen.py            # wyniki -> wyniki/lab04/
python generuj_sprawozdanie.py     # -> sprawozdanie/sprawozdanie.pdf
```

Repozytorium zawiera już pobrany korpus i korpus sparsowany, więc każdy krok od lab02 można
uruchomić bez pobierania danych i bez parsowania. `lab01.py` pobiera aktualną wersję artykułów,
więc jego ponowne uruchomienie może dać nieco inny korpus.

`lab04_parsowanie.py` przy pierwszym uruchomieniu pobiera model stanza dla serbskiego (ok. 400 MB).
Model był trenowany na serbskiej łacince, dlatego tekst jest transliterowany z cyrylicy na łacinkę,
a lematy są po analizie przepisywane z powrotem na cyrylicę.

## Struktura

```
lab01.py ... lab04_kohonen.py      programy
generuj_sprawozdanie.py, slownik.py sprawozdanie PDF
surowy_serbski.txt                 tekst pobrany z Wikipedii
oczyszczony_serbski.txt            korpus po oczyszczeniu
dane/artykuly.txt                  lista pobranych artykułów
dane/korpus_sparsowany.tsv.gz      korpus po analizie składniowej (zdanie, nr, forma, lemat, UPOS, nadrzędnik, relacja)
wyniki/                            lab02: raport.txt, statystyki liter i kody Huffmana (CSV)
wyniki/lab03/                      lab03: raport, CSV, wykresy (graf_sasiedztwa.gexf nie jest w repozytorium – 14 MB, generowany skryptem)
wyniki/lab04/                      lab04: wybrane czasowniki i rzeczowniki, zbiory treningowe, mapy Kohonena
sprawozdanie/sprawozdanie.pdf      sprawozdanie końcowe
```
