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

from wspolne import (CLEAN_FILE, PARSED_FILE, RAW_FILE, RESULTS_DIR, SEM_PARSED_FILE, SERBIAN_ALPHABET,
                     setup_console)

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
    train = read_csv("lab04", "zbior_treningowy.csv")
    verb_names = [v["czasownik"] for v in verbs]
    noun_names = [n["rzeczownik"] for n in nouns]
    check(4, "wybrano 100 różnych czasowników przechodnich i co najmniej 1000 różnych rzeczowników",
          len(set(verb_names)) == 100 and len(set(noun_names)) == len(noun_names) >= 1000,
          f"{len(verb_names)} czasowników, {len(noun_names)} rzeczowników")
    check(4, "każdy czasownik ma dopełnienie w ≥ 20% wystąpień (jest przechodni)",
          all(float(v["wspolczynnik_przechodniosci"]) >= 0.2 for v in verbs))
    check(4, "zbiór treningowy: wektory po 100 składowych, kolumny = wybrane czasowniki",
          len(train) == len(nouns) and [k for k in train[0] if k != "rzeczownik"] == verb_names)
    check(4, "suma wektora = liczba fraz VO rzeczownika",
          all(sum(int(v) for k, v in row.items() if k != "rzeczownik") == int(n["liczba_fraz_vo"])
              for row, n in zip(train, nouns)))
    # niezależne przeliczenie WSZYSTKICH składowych wprost z korpusów sparsowanych
    vo = Counter()
    for path in (PARSED_FILE, SEM_PARSED_FILE):
        if not os.path.exists(path):
            continue
        with gzip.open(path, "rt", encoding="utf-8") as f:
            sent, last = [], None
            for line in list(f) + ["KONIEC\t0\t\t\t\t0\t\n"]:
                sid, wid, form, lemma, upos, head, rel = line.rstrip("\n").split("\t")
                if sid != last and sent:
                    ids = {w[0]: w for w in sent}
                    for w in sent:
                        h = ids.get(w[3])
                        if w[4] == "obj" and h and h[2] == "VERB":
                            for o in [w] + [c for c in sent if c[4] == "conj" and c[3] == w[0]]:
                                if o[2] == "NOUN":
                                    vo[(h[1], o[1])] += 1
                    sent = []
                last = sid
                sent.append((int(wid), lemma, upos, int(head), rel))
    check(4, "wszystkie składowe wektorów = liczba fraz VO policzona niezależnie z korpusu",
          all(int(row[v]) == vo[(v, row["rzeczownik"])] for row in train for v in verb_names),
          f"{len(train) * 100} składowych")
    verb_set = set(verb_names)
    per_noun = Counter()
    for (v, n), c in vo.items():
        if v in verb_set and len(n) > 1 and set(n) <= ALPHA:
            per_noun[n] += c
    threshold = int(nouns[-1]["liczba_fraz_vo"])
    check(4, "wybrane rzeczowniki to te najczęściej będące dopełnieniem tych czasowników",
          all(per_noun[n] >= threshold for n in noun_names)
          and sum(1 for c in per_noun.values() if c > threshold) <= len(noun_names),
          f"próg: {threshold} fraz VO")
    neurons = read_csv("lab04", "neurony.csv")
    weights = read_csv("lab04", "wagi_neuronow.csv")
    assign = read_csv("lab04", "przypisanie_rzeczownikow.csv")
    check(4, "sieć Kohonena ma 50 neuronów, każdy rzeczownik trafił do dokładnie jednego",
          len(neurons) == len(weights) == 50 and sorted(a["rzeczownik"] for a in assign) == sorted(noun_names)
          and sum(int(n["liczba_rzeczownikow"]) for n in neurons) == len(noun_names))
    W = np.array([[float(r[v]) for v in verb_names] for r in weights])
    C = np.array([[int(r[v]) for v in verb_names] for r in train], float)
    X = np.log1p(C) * np.log(len(C) / np.maximum((C > 0).sum(axis=0), 1))  # log(1+x) · IDF
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    bmu = np.argmin(np.linalg.norm(X[:, None, :] - W[None], axis=2), axis=1)
    by_noun = {a["rzeczownik"]: int(a["neuron"]) for a in assign}
    check(4, "przypisanie do neuronów = najbliższy neuron (BMU) policzony od nowa z zapisanych wag",
          all(by_noun[r["rzeczownik"]] == b for r, b in zip(train, bmu)))
    dead = [int(n["neuron"]) for n in neurons if int(n["liczba_rzeczownikow"]) == 0]
    check(4, "lista neuronów martwych (bez żadnego rzeczownika) zgodna z podsumowaniem",
          sorted(dead) == sorted(summ["martwe_neurony"]), f"martwe: {len(dead)}")

    # ------------------------------------------------------------------ LAB 5
    import lab05_generator_svo as g
    import leksykon_svo as lx
    types = Counter(v["typ"] for v in lx.VERBS)
    check(5, "leksykon: ≥ 100 rzeczowników, ≥ 100 czasowników, ≥ 100 przymiotników",
          len(lx.NOUNS) >= 100 and len(lx.VERBS) >= 100 and len(lx.ADJECTIVES) >= 100,
          f"{len(lx.NOUNS)} / {len(lx.VERBS)} / {len(lx.ADJECTIVES)}")
    check(5, "czasowniki przechodnie, nieprzechodnie i zwrotne; przechodnie mają imiesłów bierny",
          all(types[t] > 0 for t in ("tr", "intr", "refl")) and all(v["pp"] for v in lx.VERBS if v["typ"] == "tr"),
          f"{types['tr']} / {types['intr']} / {types['refl']}")
    noun = {n["lemma"]: n for n in lx.NOUNS}
    det = {d[0]: d for d in lx.DETERMINERS}
    verb = {v["inf"]: g.Verb(v) for v in lx.VERBS}
    NP, PR, R = g.NounPhrase, g.Pronoun, g.realize
    golden = [
        (R(PR("1", "sg", "m"), verb["pročitati"], NP(noun["knjiga"], "sg", "novi", det["moj"]), "perfekat"),
         "Ja sam pročitao svoju novu knjigu."),
        (R(NP(noun["pas"], "sg", "veliki", det["naš"]), verb["jesti"], NP(noun["meso"]), "prezent"),
         "Naš veliki pas jede meso."),
        (R(PR("3", "sg", "m"), verb["videti"], PR("3", "sg", "f"), "perfekat"), "On ju je video."),
        (R(PR("3", "sg", "m"), verb["smejati"], None, "perfekat"), "On se smejao."),
        (R(PR("2", "sg", "f"), verb["videti"], NP(noun["pas"], "sg", None, det["taj"]), "perfekat",
           stype="pytające"), "Da li si ti videla tog psa?"),
        (R(NP(noun["devojka"], "pl", "mladi"), verb["pisati"], NP(noun["pismo"], "pl"), "futur I",
           polarity="przeczące"), "Mlade devojke neće pisati pisma."),
        (R(PR("2", "sg", "m"), verb["pročitati"], NP(noun["knjiga"]), "imperativ", mood="rozkazujący",
           polarity="przeczące"), "Ti nemoj pročitati knjigu!"),
        (R(PR("2", "pl", "m"), verb["čitati"], NP(noun["knjiga"]), "imperativ", mood="rozkazujący"),
         "Vi čitajte knjigu!"),
        (R(NP(noun["učitelj"]), verb["čitati"], NP(noun["pismo"]), "imperativ", mood="rozkazujący"),
         "Neka učitelj čita pismo!"),
        (R(PR("1", "pl", "f"), verb["kupiti"], NP(noun["kuća"], "sg", "stari", det["onaj"]), "potencijal I",
           mood="przypuszczający"), "Mi bismo kupile onu staru kuću."),
        (R(NP(noun["lovac"], "sg", None, det["jedan"]), verb["ubiti"], NP(noun["vuk"], "sg", "sivi"), "perfekat",
           voice="bierna"), "Sivi vuk je bio ubijen od strane jednog lovca."),
        (R(PR("1", "sg", "m"), verb["napisati"], NP(noun["pismo"]), "futur II"), "Ako ja budem napisao pismo…"),
        (R(PR("3", "pl", "m"), verb["doći"], None, "aorist"), "Oni dođoše."),
        (R(PR("1", "sg", "f"), verb["pisati"], NP(noun["pesma"]), "imperfekat"), "Ja pisah pesmu."),
        (R(NP(noun["pas"]), verb["lajati"], None, "pluskvamperfekat", polarity="przeczące"),
         "Pas nije bio lajao."),
        (R(PR("1", "sg", "m"), verb["umiti"], None, "potencijal II", mood="przypuszczający"),
         "Ja bih se bio umio."),
    ]
    bad = [f"{a} ≠ {b}" for a, b in golden if a != b]
    check(5, "zdania wzorcowe (sprawdzone ręcznie) generowane dokładnie",
          not bad, f"{len(golden) - len(bad)}/{len(golden)}" + (": " + "; ".join(bad) if bad else ""))
    check(5, "niemożliwe kombinacje są odrzucane (imperfekt dokonanych, bierna nieprzechodnich, "
             "pytający rozkazujący)",
          R(PR("1", "sg", "m"), verb["pročitati"], NP(noun["knjiga"]), "imperfekat") is None
          and R(PR("1", "sg", "m"), verb["spavati"], None, "prezent", voice="bierna") is None
          and R(PR("2", "sg", "m"), verb["čitati"], NP(noun["knjiga"]), "imperativ", mood="rozkazujący",
                stype="pytające") is None)
    gen = g.Generator(123)
    sents = [g.cyr(gen.sentence()[0]) for _ in range(2000)]
    allowed = ALPHA | {c.upper() for c in ALPHA} | set(" .?!…")
    check(5, "2000 losowych zdań: tylko cyrylica serbska, wielka litera na początku, znak końca zdania",
          all(set(x) <= allowed and x[0].isupper() and x[-1] in ".?!…" for x in sents))

    return checks


def main():
    setup_console()
    checks = run_checks()
    for lab, name, ok, info in checks:
        print(f"[{'OK  ' if ok else 'BŁĄD'}] lab {lab}: {name}" + (f"  ({info})" if info else ""))
    passed = sum(1 for _, _, ok, _ in checks if ok)
    print(f"\nZaliczone testy: {passed} / {len(checks)}")
    if passed < len(checks):
        raise SystemExit(1)  # kod błędu - uruchom_wszystko.py przerwie pracę


if __name__ == "__main__":
    main()
