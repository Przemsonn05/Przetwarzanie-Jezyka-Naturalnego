import heapq
import math
import os
import sys
from collections import Counter

from lab01 import SERBIAN_ALPHABET, clean_text

# Konsola Windows domyślnie nie obsługuje cyrylicy
sys.stdout.reconfigure(encoding="utf-8")

INPUT_FILE = "oczyszczony_serbski.txt"
OUTPUT_DIR = "wyniki"


def load_and_verify_corpus(filename):
    """
    Wczytuje korpus, ponownie go czyści i sprawdza, czy zostały w nim
    wyłącznie litery serbskiego alfabetu i spacje.
    """
    with open(filename, encoding="utf-8") as f:
        text = f.read()

    foreign = Counter(ch for ch in text if ch not in SERBIAN_ALPHABET and ch != " ")
    cleaned = clean_text(text)
    remaining = set(cleaned) - set(SERBIAN_ALPHABET) - {" "}

    return text, cleaned, foreign, remaining


def letter_statistics(text):
    """Zwraca listę (znak, liczność, prawdopodobieństwo) posortowaną malejąco."""
    counts = Counter(text)
    total = sum(counts.values())
    stats = [(ch, n, n / total) for ch, n in counts.items()]
    stats.sort(key=lambda x: (-x[1], x[0]))
    return stats, total


def entropy(stats):
    """Entropia Shannona H = -sum(p * log2 p) [bit/znak]."""
    return -sum(p * math.log2(p) for _, _, p in stats if p > 0)


def huffman_codes(stats):
    """
    Buduje drzewo Huffmana i zwraca słownik {znak: ciąg kodowy}.
    Węzły na kopcu: (waga, licznik_do_rozstrzygania_remisów, {znak: kod}).
    """
    heap = [(n, i, {ch: ""}) for i, (ch, n, _) in enumerate(stats)]
    heapq.heapify(heap)
    counter = len(heap)

    if len(heap) == 1:
        return {ch: "0" for ch in heap[0][2]}

    while len(heap) > 1:
        w1, _, left = heapq.heappop(heap)
        w2, _, right = heapq.heappop(heap)
        merged = {ch: "0" + code for ch, code in left.items()}
        merged.update({ch: "1" + code for ch, code in right.items()})
        heapq.heappush(heap, (w1 + w2, counter, merged))
        counter += 1

    return heap[0][2]


def huffman_decode(bits, codes):
    reverse = {code: ch for ch, code in codes.items()}
    out, buf = [], ""
    for b in bits:
        buf += b
        if buf in reverse:
            out.append(reverse[buf])
            buf = ""
    return "".join(out)


def show(ch):
    return "␣ (spacja)" if ch == " " else ch


def analyze(text, title, report):
    """Pełna analiza: tabela prawdopodobieństw, entropia, Huffman, porównanie."""
    stats, total = letter_statistics(text)
    H = entropy(stats)
    codes = huffman_codes(stats)
    L = sum(p * len(codes[ch]) for ch, _, p in stats)
    fixed_len = math.ceil(math.log2(len(stats)))
    H_max = math.log2(len(stats))

    lines = []
    lines.append("=" * 84)
    lines.append(title)
    lines.append("=" * 84)
    lines.append(f"Liczba znaków w korpusie: {total}")
    lines.append(f"Liczba różnych symboli:   {len(stats)}")
    lines.append("")
    header = f"{'Lp':>3} | {'Znak':<11} | {'Liczność':>8} | {'Udział [%]':>10} | {'p':>8} | {'-log2 p':>8} | {'Kod Huffmana':<14} | {'Dł.':>3}"
    lines.append(header)
    lines.append("-" * len(header))
    for i, (ch, n, p) in enumerate(stats, 1):
        lines.append(
            f"{i:>3} | {show(ch):<11} | {n:>8} | {p * 100:>10.4f} | {p:>8.5f} | "
            f"{-math.log2(p):>8.4f} | {codes[ch]:<14} | {len(codes[ch]):>3}"
        )
    lines.append("-" * len(header))
    lines.append(f"    | {'SUMA':<11} | {total:>8} | {100:>10.4f} | {1:>8.5f} |")
    lines.append("")

    # Kodowanie całego tekstu i weryfikacja
    encoded = "".join(codes[ch] for ch in text)
    decoded_ok = huffman_decode(encoded, codes) == text

    lines.append("WYNIKI:")
    lines.append(f"  Entropia H                         = {H:.6f} bit/znak")
    lines.append(f"  Entropia maksymalna log2({len(stats)})       = {H_max:.6f} bit/znak")
    lines.append(f"  Redundancja 1 - H/Hmax             = {(1 - H / H_max) * 100:.4f} %")
    lines.append(f"  Średnia długość kodu Huffmana L    = {L:.6f} bit/znak")
    lines.append(f"  Różnica L - H                      = {L - H:.6f} bit/znak")
    lines.append(f"  Efektywność kodu H/L               = {H / L * 100:.4f} %")
    lines.append(f"  Warunek H <= L < H + 1             = {H <= L < H + 1}")
    lines.append(f"  Kod o stałej długości              = {fixed_len} bit/znak")
    lines.append("")
    lines.append(f"  Rozmiar tekstu kodem stałej dł.    = {total * fixed_len} bitów")
    lines.append(f"  Rozmiar tekstu kodem Huffmana      = {len(encoded)} bitów")
    lines.append(f"  Teoretyczne minimum (H * N)        = {H * total:.0f} bitów")
    lines.append(f"  Kompresja względem kodu stałego    = {(1 - len(encoded) / (total * fixed_len)) * 100:.2f} %")
    lines.append(f"  Dekodowanie odtwarza tekst         = {decoded_ok}")
    lines.append("")

    output = "\n".join(lines)
    print(output)
    report.append(output)
    return stats, codes, H, L


def save_csv(path, stats, codes):
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("znak;licznosc;udzial_procent;prawdopodobienstwo;kod_huffmana;dlugosc_kodu\n")
        for ch, n, p in stats:
            name = "spacja" if ch == " " else ch
            f.write(f"{name};{n};{p * 100:.4f};{p:.6f};{codes[ch]};{len(codes[ch])}\n")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report = []

    # 1. Weryfikacja korpusu
    original, corpus, foreign, remaining = load_and_verify_corpus(INPUT_FILE)
    lines = ["=" * 84, "WERYFIKACJA KORPUSU", "=" * 84]
    lines.append(f"Długość pliku wejściowego:   {len(original)} znaków")
    if foreign:
        lines.append(f"Znalezione znaki spoza alfabetu serbskiego ({sum(foreign.values())} wystąpień):")
        lines.append("  " + ", ".join(f"'{ch}'×{n}" for ch, n in foreign.most_common()))
    else:
        lines.append("Brak znaków spoza alfabetu serbskiego.")
    lines.append(f"Długość po ponownym czyszczeniu: {len(corpus)} znaków")
    lines.append(f"Po czyszczeniu zostały tylko litery alfabetu i spacje: {not remaining}")
    lines.append(f"Alfabet ({len(SERBIAN_ALPHABET)} liter): {' '.join(SERBIAN_ALPHABET)}")
    lines.append("")
    print("\n".join(lines))
    report.append("\n".join(lines))

    corpus_path = os.path.join(OUTPUT_DIR, "korpus_oczyszczony.txt")
    with open(corpus_path, "w", encoding="utf-8") as f:
        f.write(corpus)

    # 2. Analiza samych liter (bez spacji)
    letters_only = corpus.replace(" ", "")
    stats_l, codes_l, H_l, L_l = analyze(letters_only, "ANALIZA 1: SAME LITERY (bez spacji)", report)
    save_csv(os.path.join(OUTPUT_DIR, "statystyka_litery.csv"), stats_l, codes_l)

    # 3. Analiza liter ze spacją (spacja jako 31. symbol)
    stats_s, codes_s, H_s, L_s = analyze(corpus, "ANALIZA 2: LITERY + SPACJA", report)
    save_csv(os.path.join(OUTPUT_DIR, "statystyka_litery_spacja.csv"), stats_s, codes_s)

    # 4. Podsumowanie
    summary = [
        "=" * 84,
        "PODSUMOWANIE",
        "=" * 84,
        f"{'Wariant':<22} | {'H [bit]':>9} | {'L Huffman [bit]':>15} | {'L - H':>8} | {'H/L [%]':>8}",
        "-" * 74,
        f"{'Same litery':<22} | {H_l:>9.5f} | {L_l:>15.5f} | {L_l - H_l:>8.5f} | {H_l / L_l * 100:>8.3f}",
        f"{'Litery + spacja':<22} | {H_s:>9.5f} | {L_s:>15.5f} | {L_s - H_s:>8.5f} | {H_s / L_s * 100:>8.3f}",
        "",
        "Wniosek: średnia długość kodu Huffmana jest tylko nieznacznie większa od entropii",
        "(H <= L < H + 1), więc kod Huffmana jest bliski optymalnemu. Różnica wynika z tego,",
        "że długości słów kodowych muszą być całkowite, a prawdopodobieństwa liter nie są",
        "potęgami 1/2.",
    ]
    print("\n".join(summary))
    report.append("\n".join(summary))

    with open(os.path.join(OUTPUT_DIR, "raport.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(report))

    print(f"\nZapisano wyniki w folderze '{OUTPUT_DIR}/': raport.txt, "
          "statystyka_litery.csv, statystyka_litery_spacja.csv, korpus_oczyszczony.txt")


if __name__ == "__main__":
    main()
