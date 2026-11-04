"""
Lab 4: Sieć Kohonena (SOM) dla rzeczowników opisanych kolokacjami z czasownikami przechodnimi.

1. Z korpusu sparsowanego przez lab04_parsowanie.py wyznaczamy relacje
   czasownik -> dopełnienie bliższe (relacja zależnościowa 'obj').
2. Wybieramy 100 czasowników przechodnich (najczęściej występujących z dopełnieniem)
   i 50 rzeczowników najczęściej będących ich dopełnieniem.
3. Każdy rzeczownik = wektor o 100 składowych: składowa i to liczba kolokacji
   rzeczownika z i-tym czasownikiem. 50 wektorów = zbiór treningowy.
4. Uczymy sieć Kohonena i pokazujemy, jak rzeczowniki układają się na mapie
   oraz które czasowniki (wymiary przestrzeni 100D) dominują w danym rejonie mapy.
5. Sprawdzamy, jak wynik zależy od wyboru czasowników (warianty A, B, C).
"""
import csv
import gzip
import json
import os
import sys
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

from lab01 import SERBIAN_ALPHABET

sys.stdout.reconfigure(encoding="utf-8")

PARSED_FILE = os.path.join("dane", "korpus_sparsowany.tsv.gz")
OUTPUT_DIR = os.path.join("wyniki", "lab04")
N_NOUNS = 50
N_VERBS = 100
WINDOW = 5            # okno dla wariantu C (kolokacje w oknie ±5 wyrazów)
SOM_ROWS, SOM_COLS = 10, 10
SOM_ITERATIONS = 20_000
SEED = 42
EXCLUDED_VERBS = {"бити", "хтети", "моћи", "морати", "требати"}  # posiłkowe / modalne
MIN_TRANSITIVITY = 0.2  # minimalny odsetek wystąpień czasownika z dopełnieniem
ALPHABET = set(SERBIAN_ALPHABET)
OUTLINE = [pe.withStroke(linewidth=2, foreground="white")]


# ---------------------------------------------------------------------------
# Wczytanie korpusu sparsowanego
# ---------------------------------------------------------------------------
def is_word(s):
    return bool(s) and set(s) <= ALPHABET


def load_sentences(path):
    """Zwraca listę zdań; zdanie = lista słowników (id, lemat, upos, head, deprel)."""
    sentences, current, current_id = [], [], None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            sid, wid, form, lemma, upos, head, deprel = line.rstrip("\n").split("\t")
            if sid != current_id and current:
                sentences.append(current)
                current = []
            current_id = sid
            current.append({"id": int(wid), "form": form, "lemma": lemma, "upos": upos,
                            "head": int(head), "deprel": deprel})
    if current:
        sentences.append(current)
    return sentences


def extract_relations(sentences):
    """
    Zwraca:
      obj_pairs   - Counter[(czasownik, rzeczownik)] dla relacji obj (z rozwinięciem
                    współrzędnych dopełnień: 'podigao crkvu i kuću' -> crkva, kuća)
      verb_freq   - Counter liczby wystąpień lematów czasowników
      noun_freq   - Counter liczby wystąpień lematów rzeczowników
      verb_objs   - Counter liczby dopełnień (dowolnej części mowy) dla czasownika
      window_pairs- Counter[(czasownik, rzeczownik)] współwystąpień w oknie ±WINDOW
    """
    obj_pairs, window_pairs = Counter(), Counter()
    verb_freq, noun_freq, verb_objs = Counter(), Counter(), Counter()

    for sent in sentences:
        by_id = {w["id"]: w for w in sent}
        for w in sent:
            if w["upos"] == "VERB" and is_word(w["lemma"]):
                verb_freq[w["lemma"]] += 1
            if w["upos"] == "NOUN" and is_word(w["lemma"]):
                noun_freq[w["lemma"]] += 1

        for w in sent:
            if w["deprel"] != "obj":
                continue
            head = by_id.get(w["head"])
            if not head or head["upos"] != "VERB" or not is_word(head["lemma"]):
                continue
            verb_objs[head["lemma"]] += 1
            # dopełnienie + rzeczowniki z nim współrzędne (deprel = conj)
            objects = [w] + [c for c in sent if c["deprel"] == "conj" and c["head"] == w["id"]]
            for o in objects:
                if o["upos"] == "NOUN" and is_word(o["lemma"]):
                    obj_pairs[(head["lemma"], o["lemma"])] += 1

        # wariant C: kolokacje w oknie (bez składni), liczone w obrębie zdania
        words = [w for w in sent if is_word(w["lemma"])]
        for i, w in enumerate(words):
            if w["upos"] != "VERB":
                continue
            for o in words[max(0, i - WINDOW): i + WINDOW + 1]:
                if o["upos"] == "NOUN":
                    window_pairs[(w["lemma"], o["lemma"])] += 1

    return obj_pairs, verb_freq, noun_freq, verb_objs, window_pairs


# ---------------------------------------------------------------------------
# Sieć Kohonena (implementacja własna, numpy)
# ---------------------------------------------------------------------------
class KohonenSOM:
    def __init__(self, rows, cols, dim, seed=SEED):
        self.rows, self.cols, self.dim = rows, cols, dim
        self.rng = np.random.default_rng(seed)
        self.grid = np.array([(r, c) for r in range(rows) for c in range(cols)], dtype=float)
        self.weights = None

    def init_pca(self, data):
        """Inicjalizacja wag na płaszczyźnie dwóch pierwszych składowych głównych."""
        mean = data.mean(axis=0)
        _, s, vt = np.linalg.svd(data - mean, full_matrices=False)
        scale = s[:2] / np.sqrt(len(data))
        a = np.linspace(-1, 1, self.rows)[:, None, None] * scale[0] * vt[0]
        b = np.linspace(-1, 1, self.cols)[None, :, None] * scale[1] * vt[1]
        self.weights = (mean + a + b).reshape(-1, self.dim)

    def bmu(self, x):
        return int(np.argmin(np.linalg.norm(self.weights - x, axis=1)))

    def train(self, data, iterations, lr0=0.5, lr_end=0.01, sigma0=None, sigma_end=0.5):
        """Klasyczny algorytm Kohonena (uczenie on-line, sąsiedztwo gaussowskie)."""
        if self.weights is None:
            self.init_pca(data)
        sigma0 = sigma0 or max(self.rows, self.cols) / 2
        history = []
        for t in range(iterations):
            frac = t / iterations
            lr = lr0 * (lr_end / lr0) ** frac
            sigma = sigma0 * (sigma_end / sigma0) ** frac
            x = data[self.rng.integers(len(data))]
            b = self.bmu(x)
            d2 = np.sum((self.grid - self.grid[b]) ** 2, axis=1)
            h = np.exp(-d2 / (2 * sigma ** 2))
            self.weights += lr * h[:, None] * (x - self.weights)
            if t % (iterations // 50) == 0 or t == iterations - 1:
                history.append((t, self.quantization_error(data)))
        return history

    def quantization_error(self, data):
        return float(np.mean([np.min(np.linalg.norm(self.weights - x, axis=1)) for x in data]))

    def topographic_error(self, data):
        """Odsetek próbek, dla których 1. i 2. BMU nie są sąsiadami na siatce."""
        errors = 0
        for x in data:
            first, second = np.argsort(np.linalg.norm(self.weights - x, axis=1))[:2]
            if np.max(np.abs(self.grid[first] - self.grid[second])) > 1:
                errors += 1
        return errors / len(data)

    def u_matrix(self):
        w = self.weights.reshape(self.rows, self.cols, self.dim)
        u = np.zeros((self.rows, self.cols))
        for r in range(self.rows):
            for c in range(self.cols):
                d = [np.linalg.norm(w[r, c] - w[r + dr, c + dc])
                     for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1))
                     if 0 <= r + dr < self.rows and 0 <= c + dc < self.cols]
                u[r, c] = np.mean(d)
        return u

    def positions(self, data):
        return [divmod(self.bmu(x), self.cols) for x in data]


# ---------------------------------------------------------------------------
# Zbiór treningowy
# ---------------------------------------------------------------------------
def build_matrix(nouns, verbs, pairs):
    m = np.zeros((len(nouns), len(verbs)))
    vi = {v: j for j, v in enumerate(verbs)}
    ni = {n: i for i, n in enumerate(nouns)}
    for (v, n), c in pairs.items():
        if v in vi and n in ni:
            m[ni[n], vi[v]] += c
    return m


def normalize(counts):
    """log(1 + liczność), a następnie normalizacja wektora do długości 1."""
    x = np.log1p(counts)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return np.divide(x, norms, out=np.zeros_like(x), where=norms > 0)


# ---------------------------------------------------------------------------
# Wykresy
# ---------------------------------------------------------------------------
def offsets(n):
    """Rozsuwa etykiety kilku rzeczowników trafiających do tego samego neuronu."""
    if n == 1:
        return [(0, 0)]
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False) + np.pi / 2
    return list(zip(0.28 * np.cos(ang), 0.28 * np.sin(ang)))


def plot_map(som, nouns, data, verbs, title, path):
    pos = som.positions(data)
    u = som.u_matrix()
    dominant = np.argmax(som.weights, axis=1).reshape(som.rows, som.cols)

    fig, ax = plt.subplots(figsize=(13, 12))
    im = ax.imshow(u, cmap="Greys", origin="upper", vmin=u.min() - 0.5 * (u.max() - u.min()))
    plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02, label="U-macierz (odległość do sąsiednich neuronów)")
    for r in range(som.rows):
        for c in range(som.cols):
            ax.text(c, r + 0.42, verbs[dominant[r, c]], ha="center", va="bottom",
                    fontsize=6.5, color="#0b4f9c", path_effects=OUTLINE)
    cells = defaultdict(list)
    for noun, p in zip(nouns, pos):
        cells[p].append(noun)
    for (r, c), group in cells.items():
        for noun, (dx, dy) in zip(group, offsets(len(group))):
            ax.text(c + dx, r - 0.05 + dy, noun, ha="center", va="center", fontsize=8.5,
                    fontweight="bold", color="#b2182b",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
    ax.set_xticks(range(som.cols))
    ax.set_yticks(range(som.rows))
    ax.set_title(title + "\nczerwone: rzeczowniki w zwycięskich neuronach, "
                 "niebieskie: czasownik o największej wadze neuronu", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_component_planes(som, nouns, data, verbs, verb_idx, path, title):
    pos = som.positions(data)
    n = len(verb_idx)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.6, rows * 3.5))
    for ax, j in zip(axes.flat, verb_idx):
        plane = som.weights[:, j].reshape(som.rows, som.cols)
        ax.imshow(plane, cmap="viridis", origin="upper")
        for noun, (r, c) in zip(nouns, pos):
            if data[nouns.index(noun), j] > 0:
                ax.text(c, r, noun, ha="center", va="center", fontsize=5.5, color="black",
                        path_effects=OUTLINE)
        ax.set_title(verbs[j], fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_matrix(counts, nouns, verbs, path, title):
    fig, ax = plt.subplots(figsize=(18, 9))
    im = ax.imshow(np.log1p(counts), aspect="auto", cmap="magma_r")
    ax.set_yticks(range(len(nouns)))
    ax.set_yticklabels(nouns, fontsize=7)
    ax.set_xticks(range(len(verbs)))
    ax.set_xticklabels(verbs, fontsize=6, rotation=90)
    plt.colorbar(im, ax=ax, fraction=0.02, pad=0.01, label="log(1 + liczba kolokacji)")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_pca(data, nouns, verbs, path, title, n_arrows=15):
    """Rzut 100-wymiarowej przestrzeni na 2 składowe główne; strzałki = osie czasowników."""
    centered = data - data.mean(axis=0)
    _, s, vt = np.linalg.svd(centered, full_matrices=False)
    xy = centered @ vt[:2].T
    expl = s ** 2 / np.sum(s ** 2)
    fig, ax = plt.subplots(figsize=(11, 9))
    ax.scatter(xy[:, 0], xy[:, 1], s=18, color="#b2182b")
    for (x, y), noun in zip(xy, nouns):
        ax.annotate(noun, (x, y), xytext=(3, 2), textcoords="offset points", fontsize=8)
    load = vt[:2].T
    strongest = np.argsort(-np.linalg.norm(load, axis=1))[:n_arrows]
    scale = np.abs(xy).max() / np.abs(load[strongest]).max() * 0.9
    for j in strongest:
        ax.arrow(0, 0, load[j, 0] * scale, load[j, 1] * scale, color="#1f6fb4", alpha=0.6,
                 width=0.002, head_width=0.015, length_includes_head=True)
        ax.text(load[j, 0] * scale * 1.07, load[j, 1] * scale * 1.07, verbs[j], color="#1f6fb4", fontsize=8)
    ax.axhline(0, color="#ccc", lw=0.8)
    ax.axvline(0, color="#ccc", lw=0.8)
    ax.set_xlabel(f"PC1 ({expl[0]:.1%} wariancji)")
    ax.set_ylabel(f"PC2 ({expl[1]:.1%} wariancji)")
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_learning(histories, path):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for name, hist in histories.items():
        t, qe = zip(*hist)
        ax.plot(t, qe, label=f"wariant {name}")
    ax.set_xlabel("Iteracja")
    ax.set_ylabel("Błąd kwantyzacji")
    ax.set_title("Przebieg uczenia sieci Kohonena")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Pomocnicze
# ---------------------------------------------------------------------------
def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)


def section(title):
    print("\n" + "=" * 90 + "\n" + title + "\n" + "=" * 90)


def map_distances(positions):
    p = np.array(positions, dtype=float)
    d = np.linalg.norm(p[:, None] - p[None], axis=2)
    return d[np.triu_indices(len(p), 1)]


def nearest_on_map(positions, k=5):
    p = np.array(positions, dtype=float)
    d = np.linalg.norm(p[:, None] - p[None], axis=2)
    np.fill_diagonal(d, np.inf)
    return [set(np.argsort(row, kind="stable")[:k]) for row in d]


def run_variant(name, description, nouns, verbs, pairs, summary):
    section(f"WARIANT {name}: {description}")
    counts = build_matrix(nouns, verbs, pairs)
    data = normalize(counts)
    nonzero = np.count_nonzero(counts)
    empty_nouns = [n for n, row in zip(nouns, counts) if row.sum() == 0]
    print(f"Zbiór treningowy: {counts.shape[0]} wektorów × {counts.shape[1]} składowych")
    print(f"Suma kolokacji: {int(counts.sum())}, niezerowe składowe: {nonzero} "
          f"({nonzero / counts.size:.1%} macierzy)")
    if empty_nouns:
        print(f"Rzeczowniki bez żadnej kolokacji z tymi czasownikami: {', '.join(empty_nouns)}")

    som = KohonenSOM(SOM_ROWS, SOM_COLS, len(verbs))
    history = som.train(data, SOM_ITERATIONS)
    qe, te = som.quantization_error(data), som.topographic_error(data)
    pos = som.positions(data)
    print(f"Sieć {SOM_ROWS}×{SOM_COLS}, {SOM_ITERATIONS} iteracji: "
          f"błąd kwantyzacji = {qe:.4f}, błąd topograficzny = {te:.2%}")

    cells = defaultdict(list)
    for noun, p in zip(nouns, pos):
        cells[p].append(noun)
    print(f"Zajęte neurony: {len(cells)} / {SOM_ROWS * SOM_COLS}")
    print("Neurony z więcej niż jednym rzeczownikiem (najbliżej siebie w przestrzeni 100D):")
    for p, group in sorted(cells.items(), key=lambda x: -len(x[1])):
        if len(group) > 1:
            print(f"  neuron {p}: {', '.join(group)}")

    prefix = os.path.join(OUTPUT_DIR, f"wariant_{name}")
    write_csv(f"{prefix}_zbior_treningowy.csv", ["rzeczownik"] + verbs,
              [[n] + [int(c) for c in row] for n, row in zip(nouns, counts)])
    rows = []
    for i, (noun, (r, c)) in enumerate(zip(nouns, pos)):
        top = np.argsort(-counts[i])[:5]
        rows.append([noun, r, c, int(counts[i].sum()),
                     ", ".join(f"{verbs[j]}({int(counts[i, j])})" for j in top if counts[i, j] > 0)])
    write_csv(f"{prefix}_mapa.csv", ["rzeczownik", "wiersz", "kolumna", "liczba_kolokacji",
                                     "najczestsze_czasowniki"], rows)

    plot_map(som, nouns, data, verbs, f"Sieć Kohonena – wariant {name}: {description}",
             f"{prefix}_mapa.png")
    top_verbs = list(np.argsort(-counts.sum(axis=0))[:16])
    plot_component_planes(som, nouns, data, verbs, top_verbs, f"{prefix}_plaszczyzny.png",
                          f"Wariant {name}: płaszczyzny składowych dla 16 czasowników o największej "
                          "liczbie kolokacji (jasny kolor = duża waga neuronu w tym wymiarze)")
    plot_matrix(counts, nouns, verbs, f"{prefix}_macierz.png",
                f"Wariant {name}: zbiór treningowy (50 rzeczowników × 100 czasowników)")
    plot_pca(data, nouns, verbs, f"{prefix}_pca.png",
             f"Wariant {name}: rzut przestrzeni 100D na 2 składowe główne (strzałki = czasowniki)")

    summary["warianty"][name] = {
        "opis": description, "czasowniki": verbs, "suma_kolokacji": int(counts.sum()),
        "niezerowe": nonzero, "gestosc": nonzero / counts.size, "puste_rzeczowniki": empty_nouns,
        "blad_kwantyzacji": qe, "blad_topograficzny": te, "zajete_neurony": len(cells),
        "grupy": [g for g in cells.values() if len(g) > 1],
        "pozycje": {n: list(p) for n, p in zip(nouns, pos)},
    }
    return pos, history


class Tee:
    """Wypisuje na konsolę i jednocześnie zapisuje do pliku raportu."""
    def __init__(self, path):
        self.file = open(path, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, text):
        self.stdout.write(text)
        self.file.write(text)

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sys.stdout = Tee(os.path.join(OUTPUT_DIR, "raport.txt"))
    if not os.path.exists(PARSED_FILE):
        sys.exit(f"Brak pliku {PARSED_FILE} - najpierw uruchom lab04_parsowanie.py")

    section("ANALIZA KORPUSU")
    sentences = load_sentences(PARSED_FILE)
    obj_pairs, verb_freq, noun_freq, verb_objs, window_pairs = extract_relations(sentences)
    n_tokens = sum(len(s) for s in sentences)
    print(f"Zdania: {len(sentences)}, tokeny: {n_tokens}")
    print(f"Różne czasowniki: {len(verb_freq)}, różne rzeczowniki: {len(noun_freq)}")
    print(f"Relacje czasownik -> dopełnienie rzeczownikowe: {sum(obj_pairs.values())}")

    # Czasowniki przechodnie: najczęściej występujące z dopełnieniem rzeczownikowym,
    # przy czym dopełnienie musi mieć co najmniej MIN_TRANSITIVITY wystąpień czasownika
    # (odrzuca błędy parsera, np. orzecznik przy постати 'stać się' oznaczony jako obj)
    noun_obj_per_verb = Counter()
    for (v, n), c in obj_pairs.items():
        noun_obj_per_verb[v] += c
    rejected = [v for v, _ in noun_obj_per_verb.most_common(N_VERBS)
                if v not in EXCLUDED_VERBS and verb_objs[v] < MIN_TRANSITIVITY * verb_freq[v]]
    transitive = [v for v, _ in noun_obj_per_verb.most_common()
                  if v not in EXCLUDED_VERBS and verb_objs[v] >= MIN_TRANSITIVITY * verb_freq[v]][:N_VERBS]
    print(f"Odrzucone jako nieprzechodnie (dopełnienie w < {MIN_TRANSITIVITY:.0%} wystąpień): "
          + ", ".join(f"{v} ({verb_objs[v] / verb_freq[v]:.0%})" for v in rejected))
    noun_obj = Counter()
    for (v, n), c in obj_pairs.items():
        if v in transitive:
            noun_obj[n] += c
    nouns = [n for n, _ in noun_obj.most_common(N_NOUNS)]

    section(f"WYBRANE CZASOWNIKI PRZECHODNIE ({N_VERBS})")
    rows = []
    for i, v in enumerate(transitive, 1):
        ratio = min(1.0, verb_objs[v] / verb_freq[v]) if verb_freq[v] else 0
        rows.append([i, v, noun_obj_per_verb[v], verb_objs[v], verb_freq[v], f"{ratio:.3f}"])
    print(f"{'Lp':>3} | {'czasownik':<14} | {'obj-rzecz.':>10} | {'obj-wszyst.':>11} | "
          f"{'wystąpienia':>11} | {'przechodniość':>13}")
    for r in rows[:30]:
        print(f"{r[0]:>3} | {r[1]:<14} | {r[2]:>10} | {r[3]:>11} | {r[4]:>11} | {r[5]:>13}")
    print(f"  ... (pełna lista w czasowniki_przechodnie.csv)")
    write_csv(os.path.join(OUTPUT_DIR, "czasowniki_przechodnie.csv"),
              ["lp", "czasownik", "dopelnienia_rzeczownikowe", "dopelnienia_wszystkie",
               "wystapienia", "wspolczynnik_przechodniosci"], rows)

    section(f"WYBRANE RZECZOWNIKI ({N_NOUNS})")
    rows = [[i, n, noun_obj[n], noun_freq[n]] for i, n in enumerate(nouns, 1)]
    print(f"{'Lp':>3} | {'rzeczownik':<14} | {'jako dopełnienie':>16} | {'wystąpienia':>11}")
    for r in rows:
        print(f"{r[0]:>3} | {r[1]:<14} | {r[2]:>16} | {r[3]:>11}")
    write_csv(os.path.join(OUTPUT_DIR, "rzeczowniki.csv"),
              ["lp", "rzeczownik", "liczba_jako_dopelnienie", "wystapienia"], rows)

    summary = {
        "zdania": len(sentences), "tokeny": n_tokens, "rozne_czasowniki": len(verb_freq),
        "rozne_rzeczowniki": len(noun_freq), "relacje_obj": sum(obj_pairs.values()),
        "rzeczowniki": nouns, "som": {"wiersze": SOM_ROWS, "kolumny": SOM_COLS,
                                      "iteracje": SOM_ITERATIONS, "okno_C": WINDOW},
        "warianty": {},
    }

    # Wariant A: 100 najczęstszych czasowników przechodnich, kolokacje składniowe (obj)
    pos_a, hist_a = run_variant("A", "100 czasowników przechodnich, kolokacje czasownik–dopełnienie",
                                nouns, transitive, obj_pairs, summary)
    # Wariant B: 100 najczęstszych czasowników w korpusie (bez względu na przechodniość)
    frequent = [v for v, _ in verb_freq.most_common() if v not in EXCLUDED_VERBS][:N_VERBS]
    pos_b, hist_b = run_variant("B", "100 najczęstszych czasowników, kolokacje czasownik–dopełnienie",
                                nouns, frequent, obj_pairs, summary)
    # Wariant C: te same czasowniki co w A, ale kolokacje w oknie ±5 wyrazów
    pos_c, hist_c = run_variant("C", f"100 czasowników przechodnich, kolokacje w oknie ±{WINDOW} wyrazów",
                                nouns, transitive, window_pairs, summary)

    plot_learning({"A": hist_a, "B": hist_b, "C": hist_c}, os.path.join(OUTPUT_DIR, "uczenie.png"))

    section("PORÓWNANIE WARIANTÓW – czy wynik zależy od wyboru czasowników?")
    common = len(set(transitive) & set(frequent))
    print(f"Wspólne czasowniki w A i B: {common} / {N_VERBS}")
    comparison = {}
    positions = {"A": pos_a, "B": pos_b, "C": pos_c}
    for x, y in (("A", "B"), ("A", "C"), ("B", "C")):
        rho = spearmanr(map_distances(positions[x]), map_distances(positions[y])).statistic
        nx_, ny_ = nearest_on_map(positions[x]), nearest_on_map(positions[y])
        overlap = np.mean([len(a & b) / 5 for a, b in zip(nx_, ny_)])
        comparison[f"{x}-{y}"] = {"spearman": float(rho), "wspolni_sasiedzi": float(overlap)}
        print(f"  {x} vs {y}: korelacja Spearmana odległości na mapie = {rho:.3f}, "
              f"wspólni sąsiedzi (5 najbliższych) = {overlap:.1%}")
    summary["porownanie"] = comparison
    summary["wspolne_czasowniki_AB"] = common

    with open(os.path.join(OUTPUT_DIR, "podsumowanie.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nZapisano wyniki w folderze '{OUTPUT_DIR}':")
    for name in sorted(os.listdir(OUTPUT_DIR)):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
