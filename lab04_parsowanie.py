"""
LAB 4, krok 1 - analiza składniowa korpusu (biblioteka stanza, model języka serbskiego).

Po co? Żeby wybrać czasowniki PRZECHODNIE i ich dopełnienia, musimy wiedzieć dla każdego
wyrazu w zdaniu:
  - jaką jest częścią mowy (rzeczownik NOUN, czasownik VERB, ...),
  - jaka jest jego forma podstawowa - lemat (np. цркву -> црква, подигао -> подићи),
  - od którego wyrazu zależy i w jakiej relacji (np. "obj" = dopełnienie czasownika).

Model stanza dla serbskiego był uczony na tekstach pisanych ŁACINKĄ, dlatego:
  cyrylica -> łacinka (1:1, np. љ->lj, њ->nj, џ->dž)  ->  analiza  ->  wynik z powrotem na cyrylicę.

Wynik: dane/korpus_sparsowany.tsv.gz - jeden wiersz na wyraz:
    nr_zdania, nr_wyrazu, forma, lemat, część_mowy (UPOS), nr_wyrazu_nadrzędnego, relacja

Parsowanie trwa ok. 30-90 minut na CPU, dlatego wynik zapisywany jest porcjami; przerwany
skrypt po ponownym uruchomieniu wznawia pracę. Gotowy plik jest w repozytorium, więc
skrypt go nie nadpisuje (chyba że uruchomimy go z opcją --od-nowa).
"""
import gzip
import os
import re
import sys
import time

from wspolne import PARSED_FILE, RAW_FILE, SERBIAN_ALPHABET, setup_console

PROGRESS_FILE = PARSED_FILE.replace(".tsv.gz", ".postep")  # ile porcji już przetworzono
CHUNK_SIZE = 20_000  # przybliżona liczba znaków w jednej porcji

# Transliteracja: serbskie litery cyrylicy i ich odpowiedniki w łacince (ta sama kolejność)
LATIN = ["a", "b", "v", "g", "d", "đ", "e", "ž", "z", "i", "j", "k", "l", "lj", "m",
         "n", "nj", "o", "p", "r", "s", "t", "ć", "u", "f", "h", "c", "č", "dž", "š"]
CYR_TO_LAT = dict(zip(SERBIAN_ALPHABET, LATIN))
CYR_TO_LAT.update({c.upper(): l.capitalize() for c, l in zip(SERBIAN_ALPHABET, LATIN)})
# Przy zamianie odwrotnej najpierw sprawdzamy dwuznaki (lj, nj, dž), potem pojedyncze litery
LAT_TO_CYR = sorted(((l, c) for c, l in zip(SERBIAN_ALPHABET, LATIN)), key=lambda x: -len(x[0]))
LAT_PATTERN = re.compile("|".join(re.escape(l) for l, _ in LAT_TO_CYR))
LAT_MAP = dict(LAT_TO_CYR)


def to_latin(text):
    """Србија -> Srbija"""
    return "".join(CYR_TO_LAT.get(ch, ch) for ch in text)


def to_cyrillic(text):
    """Srbija -> србија (małymi literami)"""
    return LAT_PATTERN.sub(lambda m: LAT_MAP[m.group(0)], text.lower())


def split_chunks(text, size):
    """Dzieli tekst na porcje ok. `size` znaków, tnąc tylko na granicach akapitów."""
    chunks, current, length = [], [], 0
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
    setup_console()

    if "--od-nowa" in sys.argv:
        for path in (PARSED_FILE, PROGRESS_FILE):
            if os.path.exists(path):
                os.remove(path)
    if os.path.exists(PARSED_FILE) and not os.path.exists(PROGRESS_FILE):
        print(f"Korpus jest już sparsowany: {PARSED_FILE} (opcja --od-nowa wymusza ponowne parsowanie)")
        return

    with open(RAW_FILE, encoding="utf-8") as f:
        raw = f.read()
    # Usuwamy nagłówki sekcji Wikipedii ("== Историја ==") - to nie są zdania
    raw = re.sub(r"^=+.*?=+\s*$", "", raw, flags=re.MULTILINE)
    chunks = split_chunks(raw, CHUNK_SIZE)

    done, sentence_id = 0, 0
    if os.path.exists(PROGRESS_FILE):  # wznowienie przerwanego parsowania
        done = int(open(PROGRESS_FILE).read().strip() or 0)
        with gzip.open(PARSED_FILE, "rt", encoding="utf-8") as f:
            for line in f:
                pass
            sentence_id = int(line.split("\t")[0]) + 1

    import stanza  # ładujemy dopiero tutaj - import jest wolny
    stanza.download("sr", processors="tokenize,pos,lemma,depparse", verbose=False)
    nlp = stanza.Pipeline("sr", processors="tokenize,pos,lemma,depparse", verbose=False)
    print(f"Porcji do przetworzenia: {len(chunks) - done} z {len(chunks)}")

    start = time.time()
    for i in range(done, len(chunks)):
        doc = nlp(to_latin(chunks[i]))
        rows = []
        for sentence in doc.sentences:
            for w in sentence.words:
                rows.append(f"{sentence_id}\t{w.id}\t{to_cyrillic(w.text)}\t{to_cyrillic(w.lemma or w.text)}"
                            f"\t{w.upos}\t{w.head}\t{w.deprel}\n")
            sentence_id += 1
        with gzip.open(PARSED_FILE, "at", encoding="utf-8") as f:
            f.writelines(rows)
        with open(PROGRESS_FILE, "w") as f:
            f.write(str(i + 1))

        elapsed = time.time() - start
        left = elapsed / (i + 1 - done) * (len(chunks) - i - 1)
        print(f"Porcja {i + 1}/{len(chunks)}  zdań: {sentence_id}  "
              f"czas: {elapsed / 60:.1f} min  pozostało ok. {left / 60:.1f} min", flush=True)

    os.remove(PROGRESS_FILE)  # brak pliku postępu = parsowanie zakończone
    print(f"Zakończono. Wynik zapisany w {PARSED_FILE}")


if __name__ == "__main__":
    main()
