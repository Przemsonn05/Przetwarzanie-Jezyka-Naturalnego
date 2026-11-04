import os
import sys
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")  # zapis wykresów do plików bez otwierania okien
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from lab01 import SERBIAN_ALPHABET, clean_text

# Konsola Windows domyślnie nie obsługuje cyrylicy
sys.stdout.reconfigure(encoding="utf-8")

INPUT_FILE = "oczyszczony_serbski.txt"
OUTPUT_DIR = os.path.join("wyniki", "lab03")
COVERAGE_TARGET = 0.90
CORE_SIZE = 100


def load_words(filename):
    """Wczytuje korpus, czyści go tak samo jak w lab01 i dzieli na wyrazy."""
    with open(filename, encoding="utf-8") as f:
        text = clean_text(f.read())
    words = text.split()
    assert all(set(w) <= set(SERBIAN_ALPHABET) for w in words)
    return words


def section(title, report):
    lines = ["", "=" * 84, title, "=" * 84]
    print("\n".join(lines))
    report.extend(lines)


def emit(line, report):
    print(line)
    report.append(line)


# ---------------------------------------------------------------------------
# 1. Wyrazy pokrywające 90% tekstu
# ---------------------------------------------------------------------------
def coverage_analysis(words, counts, report):
    section(f"CZĘŚĆ 1: WYRAZY POKRYWAJĄCE {COVERAGE_TARGET:.0%} TEKSTU", report)

    total = len(words)
    ranked = counts.most_common()
    cumulative = np.cumsum([n for _, n in ranked]) / total
    needed = int(np.searchsorted(cumulative, COVERAGE_TARGET) + 1)

    hapax = sum(1 for _, n in ranked if n == 1)
    emit(f"Liczba wszystkich wyrazów (tokenów):         {total}", report)
    emit(f"Liczba różnych wyrazów (typów):              {len(ranked)}", report)
    emit(f"Wyrazy występujące tylko raz (hapax legomena): {hapax} "
         f"({hapax / len(ranked):.2%} słownika)", report)
    emit("", report)
    emit(f"Aby pokryć {COVERAGE_TARGET:.0%} tekstu potrzeba {needed} najczęstszych wyrazów,", report)
    emit(f"czyli {needed / len(ranked):.2%} wszystkich różnych wyrazów "
         f"(pokrycie dokładne: {cumulative[needed - 1]:.4%}).", report)
    emit("", report)

    emit("Ile wyrazów potrzeba do danego pokrycia:", report)
    for level in (0.25, 0.50, 0.75, 0.80, 0.90, 0.95, 0.99, 1.00):
        k = int(np.searchsorted(cumulative, level - 1e-12) + 1)
        emit(f"  {level:>5.0%} tekstu -> {k:>6} wyrazów ({k / len(ranked):>7.2%} słownika)", report)
    emit("", report)

    emit("Pierwsze 30 wyrazów z listy pokrywającej 90% tekstu:", report)
    header = f"{'Ranga':>5} | {'Wyraz':<18} | {'Liczność':>8} | {'Udział [%]':>10} | {'Pokrycie skum. [%]':>18}"
    emit(header, report)
    emit("-" * len(header), report)
    for i, (w, n) in enumerate(ranked[:30], 1):
        emit(f"{i:>5} | {w:<18} | {n:>8} | {n / total * 100:>10.4f} | {cumulative[i - 1] * 100:>18.4f}", report)
    emit(f"  ... (pełna lista {needed} wyrazów w pliku wyrazy_pokrycie_90.csv)", report)

    with open(os.path.join(OUTPUT_DIR, "wyrazy_pokrycie_90.csv"), "w", encoding="utf-8-sig") as f:
        f.write("ranga;wyraz;licznosc;udzial_procent;pokrycie_skumulowane_procent\n")
        for i, (w, n) in enumerate(ranked[:needed], 1):
            f.write(f"{i};{w};{n};{n / total * 100:.4f};{cumulative[i - 1] * 100:.4f}\n")

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ranks = np.arange(1, len(ranked) + 1)
    ax.plot(ranks, cumulative * 100, color="#2a6fdb", lw=2, label="pokrycie skumulowane")
    ax.axhline(COVERAGE_TARGET * 100, color="#d9534f", ls="--", lw=1)
    ax.axvline(needed, color="#d9534f", ls="--", lw=1)
    ax.scatter([needed], [cumulative[needed - 1] * 100], color="#d9534f", zorder=3,
               label=f"{needed} wyrazów → {COVERAGE_TARGET:.0%}")
    ax.set_xlabel("Liczba najczęstszych wyrazów")
    ax.set_ylabel("Pokrycie tekstu [%]")
    ax.set_title("Pokrycie tekstu przez najczęstsze wyrazy")
    ax.set_ylim(0, 101)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "pokrycie_tekstu.png"), dpi=150)
    plt.close(fig)

    return needed


# ---------------------------------------------------------------------------
# 2. Prawo Zipfa
# ---------------------------------------------------------------------------
def zipf_analysis(counts, report):
    section("CZĘŚĆ 2: PRAWO ZIPFA", report)

    ranked = counts.most_common()
    freqs = np.array([n for _, n in ranked], dtype=float)
    ranks = np.arange(1, len(freqs) + 1)

    def fit(mask):
        """Dopasowanie f(r) = C / r^s metodą najmniejszych kwadratów w skali log-log."""
        x, y = np.log10(ranks[mask]), np.log10(freqs[mask])
        slope, intercept = np.polyfit(x, y, 1)
        r2 = 1 - np.sum((y - (slope * x + intercept)) ** 2) / np.sum((y - y.mean()) ** 2)
        return -slope, 10 ** intercept, r2

    s, C, r2 = fit(freqs > 0)
    predicted = C / ranks ** s
    # Wyrazy występujące raz tworzą długi poziomy "ogon", który zaniża wykładnik,
    # dlatego liczymy też dopasowanie tylko dla wyrazów z f >= 2
    no_hapax = freqs >= 2
    s2, C2, r2_2 = fit(no_hapax)

    emit("Prawo Zipfa: f(r) ≈ C / r^s, przy czym w wersji klasycznej s ≈ 1,", report)
    emit("czyli iloczyn r · f(r) powinien być w przybliżeniu stały.", report)
    emit("", report)
    emit("Dopasowanie (regresja liniowa log10 f = log10 C - s · log10 r):", report)
    emit(f"{'':<34} | {'s':>7} | {'C':>8} | {'R²':>6}", report)
    emit(f"{f'wszystkie wyrazy ({len(freqs)})':<34} | {s:>7.4f} | {C:>8.2f} | {r2:>6.4f}", report)
    emit(f"{f'bez hapaksów, f >= 2 ({no_hapax.sum()})':<34} | {s2:>7.4f} | {C2:>8.2f} | {r2_2:>6.4f}", report)
    emit("", report)

    emit("Sprawdzenie r · f(r) dla wybranych rang:", report)
    header = f"{'Ranga r':>7} | {'Wyraz':<18} | {'f(r)':>6} | {'r · f(r)':>9} | {'f model':>9} | {'f Zipf (s=1)':>12}"
    emit(header, report)
    emit("-" * len(header), report)
    f1 = freqs[0]
    sample = [r for r in (1, 2, 3, 4, 5, 10, 20, 30, 50, 100, 200, 500, 1000, 2000, 5000, 10000)
              if r <= len(ranked)]
    for r in sample:
        w, n = ranked[r - 1]
        emit(f"{r:>7} | {w:<18} | {n:>6} | {r * n:>9} | {predicted[r - 1]:>9.2f} | {f1 / r:>12.2f}", report)
    emit("", report)
    emit("Wniosek: w skali log-log zależność częstości od rangi jest w przybliżeniu", report)
    emit(f"liniowa (R² = {r2:.3f}), więc rozkład ma charakter potęgowy zgodny z prawem", report)
    if abs(s - 1) <= 0.1:
        emit(f"Zipfa. Wykładnik s = {s:.2f} ({s2:.2f} bez hapaksów) jest bliski klasycznej", report)
        emit("wartości 1, więc korpus dobrze spełnia prawo Zipfa. Niewielkie spłaszczenie", report)
        emit("rozkładu (s < 1) wynika z fleksyjności serbskiego (србија, србије, србији,", report)
        emit("србију... liczone osobno) i bogatego słownictwa tekstów encyklopedycznych.", report)
    else:
        emit(f"Zipfa. Wykładnik s = {s:.2f} ({s2:.2f} bez hapaksów) jest jednak wyraźnie", report)
        emit("różny od klasycznego 1. Przyczyny:", report)
        emit(f"  - mały korpus ({int(freqs.sum())} wyrazów), w którym {np.sum(freqs == 1)} wyrazów "
             f"({np.mean(freqs == 1):.0%}) występuje raz,", report)
        emit("  - serbski jest językiem fleksyjnym: jeden leksem ma wiele form (србија, србије,", report)
        emit("    србији, србију...), co rozprasza częstości na wiele rzadkich form,", report)
        emit("  - teksty encyklopedyczne mają bogate słownictwo (nazwy własne, terminy).", report)
    emit("Odchylenia widać też dla kilku pierwszych rang (słowa funkcyjne и, у, је)", report)
    emit("i w ogonie, gdzie wiele wyrazów ma tę samą małą częstość (schodki).", report)

    with open(os.path.join(OUTPUT_DIR, "zipf.csv"), "w", encoding="utf-8-sig") as f:
        f.write("ranga;wyraz;licznosc;ranga_razy_licznosc;licznosc_model\n")
        for r, ((w, n), p) in enumerate(zip(ranked, predicted), 1):
            f.write(f"{r};{w};{n};{r * n};{p:.4f}\n")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    ax = axes[0]
    ax.loglog(ranks, freqs, ".", ms=3, color="#2a6fdb", label="dane z korpusu")
    ax.loglog(ranks, predicted, color="#d9534f", lw=2,
              label=f"dopasowanie (wszystkie): f = {C:.0f} / r^{s:.3f}")
    ax.loglog(ranks[no_hapax], C2 / ranks[no_hapax] ** s2, color="#f0ad4e", lw=2,
              label=f"dopasowanie (f ≥ 2): f = {C2:.0f} / r^{s2:.3f}")
    ax.loglog(ranks, f1 / ranks, color="#5cb85c", lw=1.5, ls="--", label="Zipf klasyczny: f = f₁ / r")
    for r in (1, 2, 3, 5, 10):
        ax.annotate(ranked[r - 1][0], (r, freqs[r - 1]), textcoords="offset points",
                    xytext=(5, 3), fontsize=8)
    ax.set_xlabel("Ranga r (log)")
    ax.set_ylabel("Częstość f(r) (log)")
    ax.set_title("Prawo Zipfa – skala log-log")
    ax.grid(alpha=0.3, which="both")
    ax.legend()

    ax = axes[1]
    ax.semilogx(ranks, ranks * freqs, ".", ms=3, color="#2a6fdb")
    ax.set_xlabel("Ranga r (log)")
    ax.set_ylabel("r · f(r)")
    ax.set_title("Iloczyn rangi i częstości")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "prawo_zipfa.png"), dpi=150)
    plt.close(fig)

    return s, r2


# ---------------------------------------------------------------------------
# 3. Graf wyrazów sąsiadujących i jego rdzeń
# ---------------------------------------------------------------------------
def neighbour_graph(words, counts, report):
    section("CZĘŚĆ 3: GRAF WYRAZÓW SĄSIADUJĄCYCH I RDZEŃ", report)

    # Węzeł = wyraz, krawędź = dwa wyrazy wystąpiły w tekście obok siebie.
    # Krawędzie wychodzące z węzła liczymy w wersji skierowanej (następniki)
    # oraz nieskierowanej (wszyscy różni sąsiedzi – poprzednicy i następniki).
    successors = defaultdict(set)
    predecessors = defaultdict(set)
    edge_weights = Counter()
    for a, b in zip(words, words[1:]):
        if a == b:
            continue  # pomijamy pętle (ten sam wyraz dwa razy z rzędu)
        successors[a].add(b)
        predecessors[b].add(a)
        edge_weights[tuple(sorted((a, b)))] += 1

    vocab = set(words)
    neighbours = {w: successors[w] | predecessors[w] for w in vocab}
    degree = {w: len(neighbours[w]) for w in vocab}
    out_degree = {w: len(successors[w]) for w in vocab}
    in_degree = {w: len(predecessors[w]) for w in vocab}

    n_edges_directed = sum(out_degree.values())
    n_edges_undirected = len(edge_weights)
    emit(f"Liczba węzłów (różnych wyrazów):              {len(vocab)}", report)
    emit(f"Liczba krawędzi skierowanych (a → b):         {n_edges_directed}", report)
    emit(f"Liczba krawędzi nieskierowanych (a — b):      {n_edges_undirected}", report)
    emit(f"Średnia liczba sąsiadów węzła:                {np.mean(list(degree.values())):.3f}", report)
    emit(f"Mediana liczby sąsiadów:                      {np.median(list(degree.values())):.0f}", report)
    emit(f"Maksymalna liczba sąsiadów:                   {max(degree.values())}", report)
    emit("", report)

    core = sorted(vocab, key=lambda w: (-degree[w], -counts[w], w))[:CORE_SIZE]
    core_set = set(core)

    emit(f"RDZEŃ – {CORE_SIZE} wyrazów o największej liczbie sąsiadów:", report)
    header = (f"{'Lp':>3} | {'Wyraz':<16} | {'Sąsiedzi':>8} | {'Wychodzące':>10} | "
              f"{'Wchodzące':>9} | {'Liczność':>8} | {'Ranga częst.':>12}")
    emit(header, report)
    emit("-" * len(header), report)
    freq_rank = {w: i for i, (w, _) in enumerate(counts.most_common(), 1)}
    for i, w in enumerate(core, 1):
        emit(f"{i:>3} | {w:<16} | {degree[w]:>8} | {out_degree[w]:>10} | "
             f"{in_degree[w]:>9} | {counts[w]:>8} | {freq_rank[w]:>12}", report)
    emit("", report)

    # Właściwości rdzenia
    core_tokens = sum(counts[w] for w in core)
    top_freq = {w for w, _ in counts.most_common(CORE_SIZE)}
    core_edges = [(a, b) for (a, b) in edge_weights if a in core_set and b in core_set]
    max_edges = CORE_SIZE * (CORE_SIZE - 1) // 2
    bigrams = list(zip(words, words[1:]))
    touching = sum(1 for a, b in bigrams if a in core_set or b in core_set)
    emit("Właściwości rdzenia:", report)
    emit(f"  Pokrycie tekstu przez wyrazy rdzenia:        {core_tokens / len(words):.2%}", report)
    emit(f"  Wspólne wyrazy z top-{CORE_SIZE} najczęstszymi:      "
         f"{len(core_set & top_freq)} / {CORE_SIZE}", report)
    emit(f"  Krawędzie wewnątrz rdzenia:                  {len(core_edges)} "
         f"(gęstość {len(core_edges) / max_edges:.2%})", report)
    emit(f"  Pary sąsiadów z co najmniej 1 wyrazem rdzenia: {touching / len(bigrams):.2%}", report)
    only_degree = sorted(core_set - top_freq, key=lambda w: -degree[w])
    only_freq = sorted(top_freq - core_set, key=lambda w: -counts[w])
    emit(f"  W rdzeniu, ale nie w top-{CORE_SIZE} częstości:  {', '.join(only_degree) or '-'}", report)
    emit(f"  W top-{CORE_SIZE} częstości, ale nie w rdzeniu:  {', '.join(only_freq) or '-'}", report)
    corr = np.corrcoef(np.log([degree[w] for w in vocab if degree[w] > 0]),
                       np.log([counts[w] for w in vocab if degree[w] > 0]))[0, 1]
    emit(f"  Korelacja log(liczba sąsiadów) ~ log(liczność): {corr:.4f}", report)
    emit("", report)
    emit("Wniosek: rdzeń tworzą głównie krótkie słowa funkcyjne (spójniki, przyimki,", report)
    emit("formy czasownika 'бити', zaimki), które łączą się z bardzo wieloma różnymi", report)
    emit("wyrazami. Liczba sąsiadów jest silnie skorelowana z częstością wyrazu.", report)

    # Pliki wynikowe
    with open(os.path.join(OUTPUT_DIR, "rdzen_100.csv"), "w", encoding="utf-8-sig") as f:
        f.write("lp;wyraz;liczba_sasiadow;krawedzie_wychodzace;krawedzie_wchodzace;licznosc;ranga_czestosci\n")
        for i, w in enumerate(core, 1):
            f.write(f"{i};{w};{degree[w]};{out_degree[w]};{in_degree[w]};{counts[w]};{freq_rank[w]}\n")

    with open(os.path.join(OUTPUT_DIR, "stopnie_wezlow.csv"), "w", encoding="utf-8-sig") as f:
        f.write("wyraz;liczba_sasiadow;krawedzie_wychodzace;krawedzie_wchodzace;licznosc\n")
        for w in sorted(vocab, key=lambda w: (-degree[w], w)):
            f.write(f"{w};{degree[w]};{out_degree[w]};{in_degree[w]};{counts[w]}\n")

    G = nx.Graph()
    for w in vocab:
        G.add_node(w, licznosc=counts[w], sasiedzi=degree[w], rdzen=w in core_set)
    for (a, b), n in edge_weights.items():
        G.add_edge(a, b, weight=n)
    nx.write_gexf(G, os.path.join(OUTPUT_DIR, "graf_sasiedztwa.gexf"))

    # Wykres rozkładu stopni
    deg_counts = Counter(degree.values())
    ks = np.array(sorted(deg_counts))
    nk = np.array([deg_counts[k] for k in ks])
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.loglog(ks, nk, "o", ms=4, color="#2a6fdb")
    ax.set_xlabel("Liczba sąsiadów k (log)")
    ax.set_ylabel("Liczba wyrazów o k sąsiadach (log)")
    ax.set_title("Rozkład liczby sąsiadów w grafie wyrazów")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "rozklad_stopni.png"), dpi=150)
    plt.close(fig)

    # Wizualizacja rdzenia (podgraf 100 wyrazów)
    H = G.subgraph(core).copy()
    pos = nx.spring_layout(H, seed=42, k=0.9, weight=None)
    sizes = np.array([degree[w] for w in H.nodes()])
    widths = np.array([H[a][b]["weight"] for a, b in H.edges()])
    fig, ax = plt.subplots(figsize=(14, 14))
    nx.draw_networkx_edges(H, pos, ax=ax, alpha=0.15,
                           width=0.3 + 2.5 * widths / widths.max(), edge_color="#888888")
    nx.draw_networkx_nodes(H, pos, ax=ax, node_size=30 + 1500 * sizes / sizes.max(),
                           node_color=sizes, cmap="viridis", alpha=0.85)
    nx.draw_networkx_labels(H, pos, ax=ax, font_size=8)
    ax.set_title(f"Rdzeń grafu: {CORE_SIZE} wyrazów o największej liczbie sąsiadów\n"
                 "(wielkość węzła = liczba sąsiadów w całym grafie, grubość krawędzi = liczba wystąpień pary)")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "rdzen_grafu.png"), dpi=130)
    plt.close(fig)

    return core


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report = []

    words = load_words(INPUT_FILE)
    counts = Counter(words)

    needed = coverage_analysis(words, counts, report)
    s, r2 = zipf_analysis(counts, report)
    core = neighbour_graph(words, counts, report)

    section("PODSUMOWANIE", report)
    emit(f"  Wyrazy pokrywające {COVERAGE_TARGET:.0%} tekstu: {needed} z {len(counts)}", report)
    emit(f"  Prawo Zipfa: s = {s:.4f}, R² = {r2:.4f}", report)
    emit(f"  Rdzeń grafu ({CORE_SIZE} wyrazów), pierwsze 10: {', '.join(core[:10])}", report)

    with open(os.path.join(OUTPUT_DIR, "raport.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report).lstrip())

    print(f"\nZapisano wyniki w folderze '{OUTPUT_DIR}':")
    for name in sorted(os.listdir(OUTPUT_DIR)):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
