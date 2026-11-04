"""
Lab 4, krok 1: analiza składniowa korpusu (stanza, model serbski 'sr').

Model stanza dla serbskiego był trenowany na łacince (korpus SETimes.SR),
dlatego tekst jest najpierw transliterowany z cyrylicy na łacinkę, a lematy
i formy wyrazów są po analizie przepisywane z powrotem na cyrylicę.

Wynik: dane/korpus_sparsowany.tsv.gz - jeden wiersz na wyraz:
    zdanie, nr, forma, lemat, czesc_mowy (UPOS), nadrzednik (nr), relacja (deprel)

Parsowanie trwa ok. godziny na CPU, dlatego wynik jest zapisywany porcjami,
a przerwany skrypt można uruchomić ponownie - wznowi pracę od ostatniej porcji.
"""
import gzip
import os
import re
import sys
import time

import stanza

from lab01 import SERBIAN_ALPHABET

sys.stdout.reconfigure(encoding="utf-8")

INPUT_FILE = "surowy_serbski.txt"
OUTPUT_DIR = "dane"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "korpus_sparsowany.tsv.gz")
PROGRESS_FILE = os.path.join(OUTPUT_DIR, "korpus_sparsowany.postep")
CHUNK_SIZE = 20_000  # liczba znaków w jednej porcji

LATIN = ["a", "b", "v", "g", "d", "đ", "e", "ž", "z", "i", "j", "k", "l", "lj", "m",
         "n", "nj", "o", "p", "r", "s", "t", "ć", "u", "f", "h", "c", "č", "dž", "š"]
CYR_TO_LAT = dict(zip(SERBIAN_ALPHABET, LATIN))
CYR_TO_LAT.update({c.upper(): l.capitalize() for c, l in zip(SERBIAN_ALPHABET, LATIN)})
# Przy transliteracji odwrotnej najpierw dwuznaki (lj, nj, dž), potem pojedyncze litery
LAT_TO_CYR = sorted(((l, c) for c, l in zip(SERBIAN_ALPHABET, LATIN)), key=lambda x: -len(x[0]))
LAT_PATTERN = re.compile("|".join(re.escape(l) for l, _ in LAT_TO_CYR))
LAT_MAP = dict(LAT_TO_CYR)


def to_latin(text):
    return "".join(CYR_TO_LAT.get(ch, ch) for ch in text)


def to_cyrillic(text):
    return LAT_PATTERN.sub(lambda m: LAT_MAP[m.group(0)], text.lower())


def split_chunks(text, size):
    """Dzieli tekst na porcje ok. `size` znaków, tnąc tylko na granicach akapitów."""
    chunks, current = [], []
    length = 0
    for paragraph in text.split("\n"):
        current.append(paragraph)
        length += len(paragraph) + 1
        if length >= size:
            chunks.append("\n".join(current))
            current, length = [], 0
    if current:
        chunks.append("\n".join(current))
    return chunks


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(INPUT_FILE, encoding="utf-8") as f:
        raw = f.read()

    # Usuwamy nagłówki sekcji Wikipedii ("== Историја ==") - to nie są zdania
    raw = re.sub(r"^=+.*?=+\s*$", "", raw, flags=re.MULTILINE)
    chunks = split_chunks(raw, CHUNK_SIZE)

    done = 0
    if os.path.exists(PROGRESS_FILE) and os.path.exists(OUTPUT_FILE):
        done = int(open(PROGRESS_FILE).read().strip() or 0)
    elif os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    if done >= len(chunks):
        print(f"Korpus jest już sparsowany: {OUTPUT_FILE}")
        return

    print(f"Porcji do przetworzenia: {len(chunks) - done} z {len(chunks)}")
    nlp = stanza.Pipeline("sr", processors="tokenize,pos,lemma,depparse", verbose=False)

    sentence_id = 0
    if done:
        with gzip.open(OUTPUT_FILE, "rt", encoding="utf-8") as f:
            for line in f:
                pass
            sentence_id = int(line.split("\t")[0]) + 1

    start = time.time()
    for i in range(done, len(chunks)):
        doc = nlp(to_latin(chunks[i]))
        rows = []
        for sentence in doc.sentences:
            for w in sentence.words:
                rows.append(f"{sentence_id}\t{w.id}\t{to_cyrillic(w.text)}\t{to_cyrillic(w.lemma or w.text)}"
                            f"\t{w.upos}\t{w.head}\t{w.deprel}\n")
            sentence_id += 1
        with gzip.open(OUTPUT_FILE, "at", encoding="utf-8") as f:
            f.writelines(rows)
        with open(PROGRESS_FILE, "w") as f:
            f.write(str(i + 1))

        elapsed = time.time() - start
        left = elapsed / (i + 1 - done) * (len(chunks) - i - 1)
        print(f"Porcja {i + 1}/{len(chunks)}  zdań: {sentence_id}  "
              f"czas: {elapsed / 60:.1f} min  pozostało ok. {left / 60:.1f} min", flush=True)

    print(f"Zakończono. Wynik zapisany w {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
