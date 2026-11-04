"""
LAB 2 - statystyka liter, entropia i kodowanie Huffmana.

Kroki:
  1. sprawdzenie, że w korpusie zostały tylko litery serbskiego alfabetu (i spacje),
  2. tabela: ile razy występuje każda litera i jaki ma udział procentowy -> prawdopodobieństwo p,
  3. entropia tekstu  H = -suma(p * log2 p)  [bit na znak],
  4. kody Huffmana dla każdej litery i średnia długość kodu  L = suma(p * długość_kodu),
  5. porównanie L z entropią H (powinno być H <= L < H + 1).

Liczymy dwa warianty: same litery (30 symboli) oraz litery ze spacją (31 symboli).
Wyniki: wyniki/lab02/ (raport.txt, tabele CSV, wykresy PNG).
"""
import heapq
import math
import os
from collections import Counter

import matplotlib

matplotlib.use("Agg")  # wykresy zapisujemy do plików, bez otwierania okien
import matplotlib.pyplot as plt

from wspolne import CLEAN_FILE, SERBIAN_ALPHABET, report_to, results_dir

OUTPUT_DIR = results_dir("lab02")


# ---------------------------------------------------------------------------
# Obliczenia
# ---------------------------------------------------------------------------
def verify_corpus(text):
    """Zwraca znaki, które NIE są literą serbskiego alfabetu ani spacją (powinno być pusto)."""
    return Counter(ch for ch in text if ch not in SERBIAN_ALPHABET and ch != " ")


def letter_statistics(text):
    """Lista (znak, liczność, prawdopodobieństwo) posortowana od najczęstszego znaku."""
    counts = Counter(text)
    total = sum(counts.values())
    stats = [(ch, n, n / total) for ch, n in counts.items()]
    stats.sort(key=lambda x: (-x[1], x[0]))
    return stats, total


def entropy(stats):
    """Entropia Shannona: H = -suma(p * log2 p). Średnia ilość informacji na jeden znak [bit]."""
    return -sum(p * math.log2(p) for _, _, p in stats if p > 0)


def huffman_codes(stats, steps=None):
    """
    Algorytm Huffmana:
      - każdy znak to osobne "drzewko" o wadze równej liczbie wystąpień,
      - w pętli bierzemy DWA drzewka o najmniejszych wagach i łączymy je w jedno
        (lewej gałęzi dopisujemy na początku kodu 0, prawej 1),
      - kończymy, gdy zostanie jedno drzewo. Częste znaki są łączone późno,
        więc dostają krótkie kody, a rzadkie - długie.
    Kolejka priorytetowa (heapq) zawsze oddaje drzewko o najmniejszej wadze.
    Jeśli podano listę `steps`, zapisujemy w niej kolejne połączenia (do przykładu w sprawozdaniu).
    """
    heap = [(n, i, {ch: ""}) for i, (ch, n, _) in enumerate(stats)]
    heapq.heapify(heap)
    counter = len(heap)  # rozstrzyga remisy wag, żeby wynik był zawsze ten sam

    if len(heap) == 1:
        return {ch: "0" for ch in heap[0][2]}

    while len(heap) > 1:
        w1, _, left = heapq.heappop(heap)
        w2, _, right = heapq.heappop(heap)
        if steps is not None:
            steps.append(("".join(left), w1, "".join(right), w2, w1 + w2))
        merged = {ch: "0" + code for ch, code in left.items()}
        merged.update({ch: "1" + code for ch, code in right.items()})
        heapq.heappush(heap, (w1 + w2, counter, merged))
        counter += 1

    return heap[0][2]


def huffman_decode(bits, codes):
    """Dekodowanie: czytamy bity, aż uzbierany ciąg będzie czyimś kodem (kod jest prefiksowy)."""
    reverse = {code: ch for ch, code in codes.items()}
    out, buf = [], ""
    for b in bits:
        buf += b
        if buf in reverse:
            out.append(reverse[buf])
            buf = ""
    return "".join(out)


# ---------------------------------------------------------------------------
# Wydruk i zapis wyników
# ---------------------------------------------------------------------------
def show(ch):
    return "␣ (spacja)" if ch == " " else ch


def analyze(text, title):
    """Pełna analiza jednego wariantu: tabela, entropia, kody Huffmana, porównanie."""
    stats, total = letter_statistics(text)
    H = entropy(stats)
    codes = huffman_codes(stats)
    L = sum(p * len(codes[ch]) for ch, _, p in stats)
    H_max = math.log2(len(stats))          # entropia, gdyby wszystkie znaki były równie częste
    fixed_len = math.ceil(H_max)           # kod o stałej długości (każdy znak tyle samo bitów)

    print("=" * 84)
    print(title)
    print("=" * 84)
    print(f"Liczba znaków: {total}, liczba różnych symboli: {len(stats)}\n")
    header = (f"{'Lp':>3} | {'Znak':<11} | {'Liczność':>8} | {'Udział [%]':>10} | {'p':>8} | "
              f"{'-log2 p':>8} | {'Kod Huffmana':<14} | {'Dł.':>3}")
    print(header)
    print("-" * len(header))
    for i, (ch, n, p) in enumerate(stats, 1):
        print(f"{i:>3} | {show(ch):<11} | {n:>8} | {p * 100:>10.4f} | {p:>8.5f} | "
              f"{-math.log2(p):>8.4f} | {codes[ch]:<14} | {len(codes[ch]):>3}")
    print("-" * len(header))
    print(f"    | {'SUMA':<11} | {total:>8} | {100:>10.4f} | {1:>8.5f} |\n")

    # Kodujemy cały tekst i dekodujemy go z powrotem - musi wyjść to samo
    encoded = "".join(codes[ch] for ch in text)
    decoded_ok = huffman_decode(encoded, codes) == text

    print("WYNIKI:")
    print(f"  Entropia H                          = {H:.6f} bit/znak")
    print(f"  Entropia maksymalna log2({len(stats)})        = {H_max:.6f} bit/znak")
    print(f"  Redundancja 1 - H/Hmax              = {(1 - H / H_max) * 100:.4f} %")
    print(f"  Średnia długość kodu Huffmana L     = {L:.6f} bit/znak")
    print(f"  Różnica L - H                       = {L - H:.6f} bit/znak")
    print(f"  Efektywność kodu H/L                = {H / L * 100:.4f} %")
    print(f"  Warunek H <= L < H + 1              = {H <= L < H + 1}")
    print(f"  Kod o stałej długości               = {fixed_len} bit/znak")
    print(f"  Rozmiar tekstu kodem stałej dł.     = {total * fixed_len} bitów")
    print(f"  Rozmiar tekstu kodem Huffmana       = {len(encoded)} bitów")
    print(f"  Teoretyczne minimum (H * N)         = {H * total:.0f} bitów")
    print(f"  Oszczędność względem kodu stałego   = {(1 - len(encoded) / (total * fixed_len)) * 100:.2f} %")
    print(f"  Dekodowanie odtwarza tekst          = {decoded_ok}\n")
    return stats, codes, H, L


def save_csv(path, stats, codes):
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("znak;licznosc;udzial_procent;prawdopodobienstwo;kod_huffmana;dlugosc_kodu\n")
        for ch, n, p in stats:
            name = "spacja" if ch == " " else ch
            f.write(f"{name};{n};{p * 100:.4f};{p:.6f};{codes[ch]};{len(codes[ch])}\n")


def plot_letters(stats, path):
    """Wykres słupkowy udziału procentowego liter."""
    letters = [ch for ch, _, _ in stats]
    shares = [p * 100 for _, _, p in stats]
    fig, ax = plt.subplots(figsize=(11, 4.2))
    bars = ax.bar(letters, shares, color="#2a6fdb")
    for b, s in zip(bars, shares):
        ax.text(b.get_x() + b.get_width() / 2, s + 0.15, f"{s:.1f}", ha="center", fontsize=7)
    ax.set_ylabel("Udział w korpusie [%]")
    ax.set_title("Udział liter serbskiego alfabetu w korpusie (bez spacji)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_code_lengths(stats, codes, path):
    """Porównanie długości kodu Huffmana z 'idealną' długością -log2 p dla każdej litery."""
    letters = [ch for ch, _, _ in stats]
    ideal = [-math.log2(p) for _, _, p in stats]
    real = [len(codes[ch]) for ch in letters]
    x = range(len(letters))
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.bar([i - 0.2 for i in x], ideal, width=0.4, color="#9ecae1", label="−log₂ p (długość idealna, z entropii)")
    ax.bar([i + 0.2 for i in x], real, width=0.4, color="#08519c", label="długość kodu Huffmana")
    ax.set_xticks(list(x))
    ax.set_xticklabels(letters)
    ax.set_ylabel("Liczba bitów")
    ax.set_title("Długość kodu Huffmana a długość idealna dla każdej litery")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    report_to(os.path.join(OUTPUT_DIR, "raport.txt"))

    # 1. Weryfikacja korpusu
    with open(CLEAN_FILE, encoding="utf-8") as f:
        corpus = f.read()
    foreign = verify_corpus(corpus)
    print("=" * 84)
    print("WERYFIKACJA KORPUSU")
    print("=" * 84)
    print(f"Długość korpusu: {len(corpus)} znaków")
    if foreign:
        print(f"UWAGA - znaki spoza alfabetu: {dict(foreign.most_common())}")
    else:
        print("Korpus zawiera wyłącznie litery serbskiego alfabetu i spacje - OK.")
    print(f"Występuje {len(set(corpus) - {' '})} z 30 liter alfabetu: {' '.join(SERBIAN_ALPHABET)}\n")

    # 2. Same litery (bez spacji) - wariant główny
    letters_only = corpus.replace(" ", "")
    stats_l, codes_l, H_l, L_l = analyze(letters_only, "ANALIZA 1: SAME LITERY (bez spacji)")
    save_csv(os.path.join(OUTPUT_DIR, "statystyka_litery.csv"), stats_l, codes_l)
    plot_letters(stats_l, os.path.join(OUTPUT_DIR, "udzial_liter.png"))
    plot_code_lengths(stats_l, codes_l, os.path.join(OUTPUT_DIR, "dlugosci_kodow.png"))

    # 3. Litery + spacja (spacja jako 31. symbol)
    stats_s, codes_s, H_s, L_s = analyze(corpus, "ANALIZA 2: LITERY + SPACJA")
    save_csv(os.path.join(OUTPUT_DIR, "statystyka_litery_spacja.csv"), stats_s, codes_s)

    # 4. Podsumowanie
    print("=" * 84)
    print("PODSUMOWANIE")
    print("=" * 84)
    print(f"{'Wariant':<18} | {'H [bit]':>9} | {'L Huffman [bit]':>15} | {'L - H':>8} | {'H/L [%]':>8}")
    print("-" * 70)
    print(f"{'Same litery':<18} | {H_l:>9.5f} | {L_l:>15.5f} | {L_l - H_l:>8.5f} | {H_l / L_l * 100:>8.3f}")
    print(f"{'Litery + spacja':<18} | {H_s:>9.5f} | {L_s:>15.5f} | {L_s - H_s:>8.5f} | {H_s / L_s * 100:>8.3f}")
    print("\nWniosek: średnia długość kodu Huffmana jest tylko nieznacznie większa od entropii")
    print("(H <= L < H + 1), więc kod Huffmana jest prawie optymalny. Różnica wynika z tego,")
    print("że kod musi mieć całkowitą liczbę bitów, a -log2 p zwykle nie jest liczbą całkowitą.")
    print(f"\nWyniki zapisano w folderze {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
