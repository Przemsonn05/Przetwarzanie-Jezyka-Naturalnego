"""
Niezależne sprawdzenie wyników wszystkich laboratoriów.

Skrypt NIE korzysta z funkcji z lab01-lab04: każdą wartość liczy od nowa, w najprostszy
możliwy sposób, i porównuje ją z plikami wynikowymi. Jeśli wszystkie testy wypiszą OK,
wyniki w folderze wyniki/ są poprawne i spójne z korpusem.

Uruchomienie: python sprawdz_wyniki.py
"""
import csv
import gzip
import heapq
import json
import math
import os
import unicodedata
from collections import Counter, defaultdict

import numpy as np

from wspolne import CLEAN_FILE, PARSED_FILE, RAW_FILE, RESULTS_DIR, SERBIAN_ALPHABET, setup_console

ALPHA = set(SERBIAN_ALPHABET)


def read_csv(*path):
    with open(os.path.join(RESULTS_DIR, *path), encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def run_checks():
    """Zwraca listę (lab, opis testu, wynik True/False, szczegóły)."""
    checks = []

    def check(lab, name, ok, info=""):
        checks.append((lab, name, bool(ok), str(info)))

    # ------------------------------------------------------------------ LAB 1
    text = open(CLEAN_FILE, encoding="utf-8").read()
    raw = open(RAW_FILE, encoding="utf-8").read()
    chars = set(text)
    words = text.split(" ")
    check(1, "w korpusie są tylko litery serbskiego alfabetu i spacje", chars <= ALPHA | {" "})
    check(1, "brak cyfr (także np. ², ½)", not any(unicodedata.category(c).startswith("N") for c in chars))
    check(1, "brak interpunkcji i symboli", not any(unicodedata.category(c)[0] in "PS" for c in chars))
    check(1, "brak liter łacińskich i greckich",
          not any(("LATIN" in unicodedata.name(c, "") or "GREEK" in unicodedata.name(c, "")) for c in chars))
    check(1, "wszystkie litery są małe", text == text.lower())
    check(1, "brak podwójnych spacji, nowych linii i spacji na brzegach",
          "  " not in text and "\n" not in text and text == text.strip())
    check(1, "występują wszystkie 30 liter alfabetu", ALPHA <= chars, f"{len(ALPHA & chars)}/30")
    check(1, "tekst surowy zawierał znaki, które usunięto",
          any(not (c in ALPHA or c.isspace()) for c in raw.lower()))

    # ------------------------------------------------------------------ LAB 2
    for fname, corpus in (("statystyka_litery.csv", text.replace(" ", "")),
                          ("statystyka_litery_spacja.csv", text)):
        variant = "same litery" if "spacja" not in fname else "litery + spacja"
        rows = read_csv("lab02", fname)
        cnt, n = Counter(corpus), len(corpus)
        sym = {(" " if r["znak"] == "spacja" else r["znak"]): r for r in rows}
        check(2, f"[{variant}] liczności liter zgodne z korpusem",
              set(sym) == set(cnt) and all(int(sym[c]["licznosc"]) == k for c, k in cnt.items()))
        total = sum(float(r["udzial_procent"]) for r in rows)
        check(2, f"[{variant}] udziały procentowe sumują się do 100%", abs(total - 100) < 0.01, f"{total:.4f}%")
        H = -sum(k / n * math.log2(k / n) for k in cnt.values())
        codes = [r["kod_huffmana"] for r in rows]
        L = sum(cnt[c] / n * len(sym[c]["kod_huffmana"]) for c in cnt)
        check(2, f"[{variant}] kod Huffmana jest prefiksowy (żaden kod nie jest początkiem innego)",
              not any(a != b and b.startswith(a) for a in codes for b in codes))
        check(2, f"[{variant}] nierówność Krafta: suma 2^(-długość) = 1",
              abs(sum(2 ** -len(c) for c in codes) - 1) < 1e-12)
        heap = list(cnt.values())
        heapq.heapify(heap)
        cost = 0
        while len(heap) > 1:
            a, b = heapq.heappop(heap), heapq.heappop(heap)
            cost += a + b
            heapq.heappush(heap, a + b)
        check(2, f"[{variant}] średnia długość L jest minimalna (= niezależny Huffman)",
              abs(cost / n - L) < 1e-9, f"L = {L:.4f}")
        check(2, f"[{variant}] H ≤ L < H + 1", H <= L < H + 1, f"H = {H:.4f}, L = {L:.4f}")

    # ------------------------------------------------------------------ LAB 3
    wc = Counter(words)
    T = len(words)
    freqs = sorted(wc.values(), reverse=True)
    acc, k = 0, 0
    while acc < 0.9 * T:
        acc += freqs[k]
        k += 1
    cov = read_csv("lab03", "wyrazy_pokrycie_90.csv")
    check(3, "lista 90% ma minimalną długość (bez ostatniego wyrazu < 90%)",
          len(cov) == k and sum(int(r["licznosc"]) for r in cov[:-1]) < 0.9 * T, f"{len(cov)} wyrazów")
    check(3, "liczności wyrazów na liście 90% zgodne z korpusem",
          all(wc[r["wyraz"]] == int(r["licznosc"]) for r in cov))
    zipf = read_csv("lab03", "zipf.csv")
    check(3, "tabela Zipfa obejmuje wszystkie wyrazy, r·f policzone poprawnie",
          len(zipf) == len(wc) and all(int(r["ranga"]) * int(r["licznosc"]) == int(r["ranga_razy_licznosc"])
                                       for r in zipf))
    r = np.arange(1, len(freqs) + 1)
    s = -np.polyfit(np.log10(r), np.log10(np.array(freqs, float)), 1)[0]
    check(3, "wykładnik Zipfa w raporcie zgodny z obliczonym",
          f"{s:.4f}" in open(os.path.join(RESULTS_DIR, "lab03", "raport.txt"), encoding="utf-8").read(),
          f"s = {s:.4f}")
    succ, pred = defaultdict(set), defaultdict(set)
    for a, b in zip(words, words[1:]):
        if a != b:
            succ[a].add(b)
            pred[b].add(a)
    deg = {w: len(succ[w] | pred[w]) for w in wc}
    core = read_csv("lab03", "rdzen_100.csv")
    check(3, "rdzeń: 100 różnych wyrazów", len({c["wyraz"] for c in core}) == 100)
    check(3, "rdzeń: liczby sąsiadów, krawędzi wychodzących i wchodzących poprawne",
          all(deg[c["wyraz"]] == int(c["liczba_sasiadow"]) and len(succ[c["wyraz"]]) == int(c["krawedzie_wychodzace"])
              and len(pred[c["wyraz"]]) == int(c["krawedzie_wchodzace"]) for c in core))
    thr = sorted(deg.values(), reverse=True)[99]
    check(3, "rdzeń to faktycznie 100 wyrazów o największej liczbie sąsiadów",
          all(int(c["liczba_sasiadow"]) >= thr for c in core), f"próg: {thr} sąsiadów")

    # ------------------------------------------------------------------ LAB 4
    summ = json.load(open(os.path.join(RESULTS_DIR, "lab04", "podsumowanie.json"), encoding="utf-8"))
    verbs = read_csv("lab04", "czasowniki_przechodnie.csv")
    nouns = read_csv("lab04", "rzeczowniki.csv")
    train = read_csv("lab04", "wariant_A_zbior_treningowy.csv")
    verb_names = [v["czasownik"] for v in verbs]
    check(4, "wybrano 100 różnych czasowników i 50 różnych rzeczowników",
          len(set(verb_names)) == 100 and len({n["rzeczownik"] for n in nouns}) == 50)
    check(4, "każdy czasownik ma dopełnienie w ≥ 20% wystąpień (jest przechodni)",
          all(float(v["wspolczynnik_przechodniosci"]) >= 0.2 for v in verbs))
    check(4, "zbiór treningowy: 50 wektorów po 100 składowych",
          len(train) == 50 and all(len(r) - 1 == 100 for r in train))
    check(4, "kolumny zbioru treningowego = wybrane czasowniki",
          [k for k in train[0] if k != "rzeczownik"] == verb_names)
    check(4, "suma wektora = liczba wystąpień rzeczownika jako dopełnienia",
          all(sum(int(v) for k, v in row.items() if k != "rzeczownik") == int(n["liczba_jako_dopelnienie"])
              for row, n in zip(train, nouns)))
    # niezależne przeliczenie kilku składowych wprost z korpusu sparsowanego
    sent, obj = [], Counter()
    with gzip.open(PARSED_FILE, "rt", encoding="utf-8") as f:
        last = None
        for line in f:
            sid, wid, form, lemma, upos, head, rel = line.rstrip("\n").split("\t")
            if sid != last and sent:
                ids = {w[0]: w for w in sent}
                for w in sent:
                    if w[4] == "obj" and w[2] == "NOUN" and ids.get(w[3], (0, 0, ""))[2] == "VERB":
                        obj[(ids[w[3]][1], w[1])] += 1
                sent = []
            last = sid
            sent.append((int(wid), lemma, upos, int(head), rel))
    row = {r["rzeczownik"]: r for r in train}
    sample = [("донети", "одлука"), ("освојити", "медаља"), ("прогласити", "независност"), ("водити", "рат")]
    check(4, "wybrane składowe wektorów zgodne z korpusem sparsowanym (bez współrzędnych)",
          all(int(row[n][v]) >= obj[(v, n)] > 0 for v, n in sample),
          ", ".join(f"{v}+{n}: {row[n][v]}" for v, n in sample))
    A = summ["warianty"]["A"]
    check(4, "sieć Kohonena: każdy rzeczownik ma neuron na siatce 10×10",
          len(A["pozycje"]) == 50 and all(0 <= p[0] < 10 and 0 <= p[1] < 10 for p in A["pozycje"].values()))
    check(4, "sieć Kohonena: błąd topograficzny = 0 (sąsiedztwo zachowane)", A["blad_topograficzny"] == 0)

    return checks


def main():
    setup_console()
    checks = run_checks()
    for lab, name, ok, info in checks:
        print(f"[{'OK  ' if ok else 'BŁĄD'}] lab {lab}: {name}" + (f"  ({info})" if info else ""))
    passed = sum(1 for _, _, ok, _ in checks if ok)
    print(f"\nZaliczone testy: {passed} / {len(checks)}")


if __name__ == "__main__":
    main()
