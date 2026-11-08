# Przetwarzanie języka naturalnego – język serbski

Programy z laboratoriów z przedmiotu *Przetwarzanie języka naturalnego* (dr inż. Mirosław Gajer).
Wszystkie analizy dotyczą języka serbskiego (cyrylica, 30 liter); teksty pochodzą z serbskiej Wikipedii.

📄 **Sprawozdanie:** [`sprawozdanie/sprawozdanie.pdf`](sprawozdanie/sprawozdanie.pdf)

## Realizacja zagadnień

### 1. Analiza statystyczna języka

| Wymaganie | Skrypt | Wynik |
|---|---|---|
| Korpus min. 100 000 wyrazów | `lab01.py` | 149 373 wyrazy (ok. 1 mln znaków z Wikipedii), wyłącznie 30 liter cyrylicy |
| Czy zachodzi prawo Zipfa | `lab03_wyrazy_zipf_graf.py` | tak: f(r) ≈ C / r^s, s = 0,96, R² = 0,97 (`wyniki/lab03/prawo_zipfa.png`, `zipf.csv`) |
| Wyrazy potrzebne do rozumienia 90% tekstu | `lab03_wyrazy_zipf_graf.py` | 11 148 wyrazów (`wyniki/lab03/wyrazy_pokrycie_90.csv`) |
| Rdzeń języka – 100 wyrazów o największej liczbie sąsiadów | `lab03_wyrazy_zipf_graf.py` | `wyniki/lab03/rdzen_100.csv`, `rdzen_grafu.png` |
| (dodatkowo) statystyka liter, entropia, kod Huffmana | `lab02_entropia_huffman.py` | H = 4,302 bit/znak, L = 4,337 bit/znak (efektywność 99,2%) |

### 2. Analiza syntaktyczna – generator zdań SVO

| Wymaganie | Realizacja |
|---|---|
| Generator zdań prostych SVO | `lab05_generator_svo.py` (gramatyka) + `leksykon_svo.py` (leksykon) |
| Podmiot: fraza rzeczownikowa lub zaimek osobowy | mianownik; zaimki ја, ти, он, она, оно, ми, ви, они, оне, она |
| Orzeczenie: czasowniki nieprzechodnie, przechodnie, zwrotne | 77 przechodnich, 24 nieprzechodnie, 19 zwrotnych (z *се*) |
| Wszystkie czasy | prezent, perfekat, aorist, imperfekat, pluskvamperfekat, futur I, futur II |
| Tryby: oznajmujący, pytający, przeczący, rozkazujący, przypuszczający | tryb oznajmujący / rozkazujący (imperativ, *нека* + prezent) / przypuszczający (potencijal I i II) × zdanie oznajmujące / pytające (*да ли*) × twierdzące / przeczące |
| Strona czynna i bierna | bierna: *бити* + imiesłów bierny, wykonawca *од стране* + dopełniacz |
| Dopełnienie: fraza rzeczownikowa lub zaimek osobowy | biernik (z biernikiem = dopełniaczem dla rzeczowników męskich żywotnych); zaimek w formie enklitycznej (*га, је, их…*) |
| Min. 100 rzeczowników, 100 czasowników, 100 przymiotników | 106 rzeczowników, 120 czasowników, 105 przymiotników |
| Fraza rzeczownikowa: [rodzajnik/zaimek] [przymiotnik] rzeczownik | serbski nie ma rodzajników – ich rolę pełnią *један* (≈ nieokreślony) i *тај* (≈ określony); dodatkowo zaimki wskazujące, dzierżawcze (z zwrotnym *свој*), nieokreślone i *сваки* |

Generator dba o zgodę w rodzaju, liczbie i przypadku, szyk enklityk na drugim miejscu w zdaniu
(*Ја сам га видео*, *Он се смејао*, *Да ли си је ти видела?*), dobór form nieregularnych oraz
ograniczenia znaczeniowe (pies je mięso, ale książka nie je psa). Przykładowe zdania
(losowe zdania na ekran: `python lab05_generator_svo.py -n 20 --lacinka`):

```
  1. Наш велики пас је појео свеже месо.  (Naš veliki pas je pojeo sveže meso.)
  2. Да ли ћете ви прочитати ову књигу?  (Da li ćete vi pročitati ovu knjigu?)
  3. Ти немој затворити тај прозор!  (Ti nemoj zatvoriti taj prozor!)
  4. Писмо би било написано од стране мог пријатеља.  (Pismo bi bilo napisano od strane mog prijatelja.)
  5. Ми се нисмо смејали.  (Mi se nismo smejali.)
```

### 3. Analiza semantyczna – sieć Kohonena

| Wymaganie | Realizacja |
|---|---|
| Min. 1000 rzeczowników | 1000 rzeczowników najczęściej będących dopełnieniem wybranych czasowników (każdy z co najmniej 4 frazami VO) |
| 100 czasowników przechodnich | czasowniki z dopełnieniem rzeczownikowym w ≥ 20% wystąpień (bez posiłkowych i modalnych) |
| Wektory 100 składowych = liczba fraz VO | analiza składniowa (stanza, relacja `obj`) – `wyniki/lab04/zbior_treningowy.csv`; przed uczeniem log(1+x) · IDF i normalizacja |
| Sieć Kohonena z 50 neuronami | własna implementacja (numpy), siatka 5 × 10 |
| Analiza klastrów: pola semantyczne, ich liczba, neurony martwe | 0 neuronów martwych; 35 klastrów jednorodnych → 33 pola semantyczne (np. trofea sportowe, substancje chemiczne, choroby i szkody, akty prawne, wojna i polityka, instytucje, prawa i status), 11 klastrów mieszanych (`wyniki/lab04/neurony.csv`, `mapa_kohonena.png`, rozdział 4 sprawozdania) |`wyniki/lab04/neurony.csv`, `mapa_kohonena.png`, rozdział 4 sprawozdania) |

Korpus z punktu 1 (historia i geografia Serbii) daje za mało fraz VO na 1000 rzeczowników, dlatego
`lab04_pobieranie.py` pobiera dodatkowo ok. 8 mln znaków z artykułów o różnej tematyce (jedzenie,
zwierzęta, rośliny, ubrania, budynki, transport, muzyka, medycyna, sport, technika, gospodarka, wojsko…).

## Skrypty

| Skrypt | Zadanie | Wynik |
|---|---|---|
| `lab01.py` | pobranie ok. 1 mln znaków z Wikipedii, czyszczenie (tylko litery alfabetu) | `dane/oczyszczony_serbski.txt`, `wyniki/lab01/` |
| `lab02_entropia_huffman.py` | udział liter, entropia, kody Huffmana | `wyniki/lab02/` |
| `lab03_wyrazy_zipf_graf.py` | pokrycie 90%, prawo Zipfa, graf sąsiedztwa, rdzeń | `wyniki/lab03/` |
| `lab04_pobieranie.py` | pobranie korpusu do analizy semantycznej | `dane/surowy_semantyka.txt` |
| `lab04_parsowanie.py` | analiza składniowa obu korpusów (stanza), równolegle | `dane/korpus_sparsowany*.tsv.gz` |
| `lab04_kohonen.py` | wybór czasowników i rzeczowników, wektory VO, sieć Kohonena, analiza klastrów | `wyniki/lab04/` |
| `lab05_generator_svo.py` | generator zdań SVO (leksykon w `leksykon_svo.py`) | `wyniki/lab05/` |
| `sprawdz_wyniki.py` | niezależne sprawdzenie wszystkich wyników (testy) | wypisuje OK / BŁĄD |
| `generuj_sprawozdanie.py` | sprawozdanie PDF (`slownik.py` – polskie znaczenia wyrazów w tabelach) | `sprawozdanie/sprawozdanie.pdf` |
| `uruchom_wszystko.py` | uruchamia wszystkie etapy po kolei | – |
| `wspolne.py` | alfabet serbski i ścieżki do plików | – |

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
python lab04_pobieranie.py         # -> dane/surowy_semantyka.txt (z opcją --od-nowa: pobranie od nowa)
python lab04_parsowanie.py         # -> dane/korpus_sparsowany*.tsv.gz (z opcją --od-nowa: parsowanie od nowa)
python lab04_kohonen.py            # -> wyniki/lab04/
python lab05_generator_svo.py      # -> wyniki/lab05/ (raport, leksykon, pełne odmiany, 200 losowych zdań)
python lab05_generator_svo.py -n 20 --lacinka   # 20 losowych zdań na ekran
python sprawdz_wyniki.py           # testy poprawności
python generuj_sprawozdanie.py     # -> sprawozdanie/sprawozdanie.pdf
```

Pobrane teksty i wyniki analizy składniowej są już w repozytorium (`dane/`), więc pełne
przeliczenie trwa kilka minut i nie wymaga internetu. Pobranie tekstów od nowa może dać nieco
inne korpusy, bo artykuły w Wikipedii się zmieniają. Parsowanie od nowa
(`lab04_parsowanie.py --od-nowa`) trwa kilka godzin na CPU (przerwane wznawia się od brakujących
porcji) i przy pierwszym uruchomieniu pobiera model stanza dla serbskiego (ok. 400 MB). Model był
uczony na serbskiej łacince, dlatego tekst jest transliterowany z cyrylicy na łacinkę, a wynik
przepisywany z powrotem na cyrylicę.

## Struktura repozytorium

```
lab01.py … lab05_generator_svo.py   programy laboratoriów
leksykon_svo.py                     leksykon generatora SVO
wspolne.py                          wspólne ustawienia
sprawdz_wyniki.py                   testy poprawności
uruchom_wszystko.py                 uruchomienie całości
generuj_sprawozdanie.py, slownik.py generowanie sprawozdania
dane/
  surowy_serbski.txt                tekst pobrany z Wikipedii (korpus podstawowy)
  oczyszczony_serbski.txt           korpus po oczyszczeniu
  artykuly.txt                      lista pobranych artykułów
  korpus_sparsowany.tsv.gz          korpus podstawowy po analizie składniowej
  surowy_semantyka.txt              korpus dodatkowy do analizy semantycznej
  artykuly_semantyka.txt            lista jego artykułów (z dziedziną)
  korpus_sparsowany_semantyka.tsv.gz  korpus dodatkowy po analizie składniowej
wyniki/
  lab01/                            raport czyszczenia, lista usuniętych znaków
  lab02/                            statystyka liter i kody Huffmana (CSV), wykresy
  lab03/                            lista 90%, tabela Zipfa, rdzeń, stopnie węzłów, wykresy
  lab04/                            czasowniki, rzeczowniki, zbiór treningowy, wagi i zawartość neuronów, mapa
  lab05/                            leksykon (CSV), pełne odmiany, losowe zdania
sprawozdanie/
  sprawozdanie.pdf                  sprawozdanie końcowe
  rysunki/                          rysunki pomocnicze sprawozdania
```

Plik `wyniki/lab03/graf_sasiedztwa.gexf` (cały graf, 14 MB, do otwarcia w programie Gephi)
nie jest w repozytorium – tworzy go `lab03_wyrazy_zipf_graf.py`.
