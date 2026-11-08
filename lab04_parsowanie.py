"""
LAB 4, krok 1 - analiza składniowa korpusu (biblioteka stanza, model języka serbskiego).

Po co? Żeby wybrać czasowniki PRZECHODNIE i ich dopełnienia, musimy wiedzieć dla każdego
wyrazu w zdaniu:
  - jaką jest częścią mowy (rzeczownik NOUN, czasownik VERB, ...),
  - jaka jest jego forma podstawowa - lemat (np. цркву -> црква, подигао -> подићи),
  - od którego wyrazu zależy i w jakiej relacji (np. "obj" = dopełnienie czasownika).

Model stanza dla serbskiego był uczony na tekstach pisanych ŁACINKĄ, dlatego:
  cyrylica -> łacinka (1:1, np. љ->lj, њ->nj, џ->dž)  ->  analiza  ->  wynik z powrotem na cyrylicę.

Parsowane są dwa korpusy:
  dane/surowy_serbski.txt   -> dane/korpus_sparsowany.tsv.gz            (korpus z lab 1)
  dane/surowy_semantyka.txt -> dane/korpus_sparsowany_semantyka.tsv.gz  (korpus dodatkowy,
                               lab04_pobieranie.py - potrzebny do 1000 rzeczowników)
Format: jeden wiersz na wyraz:
    nr_zdania, nr_wyrazu, forma, lemat, część_mowy (UPOS), nr_wyrazu_nadrzędnego, relacja

Tekst dzielony jest na porcje ok. 20 tys. znaków, przetwarzane równolegle w kilku procesach.
Każda porcja trafia do osobnego pliku w folderze roboczym, więc przerwane parsowanie po
ponownym uruchomieniu wznawia się od brakujących porcji. Na koniec porcje są łączone w jeden
plik .tsv.gz, a folder roboczy usuwany. Parsowanie korpusu dodatkowego trwa kilka godzin na CPU.
Gotowe pliki są w repozytorium i nie są nadpisywane (chyba że z opcją --od-nowa).
"""
import gzip
import os
import re
import sys
import time

from multiprocessing import Pool

from wspolne import PARSED_FILE, RAW_FILE, SEM_PARSED_FILE, SEM_RAW_FILE, SERBIAN_ALPHABET, setup_console

CHUNK_SIZE = 20_000  # przybliżona liczba znaków w jednej porcji
WORKERS = max(1, min(4, (os.cpu_count() or 2) // 3))  # procesy równoległe
CORPORA = [(RAW_FILE, PARSED_FILE), (SEM_RAW_FILE, SEM_PARSED_FILE)]

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


_nlp = None


def _init_worker(threads):
    """Każdy proces ładuje własną kopię modelu stanza."""
    global _nlp
    import torch
    import stanza

    torch.set_num_threads(threads)
    _nlp = stanza.Pipeline("sr", processors="tokenize,pos,lemma,depparse", verbose=False)


def _parse_chunk(job):
    """Parsuje jedną porcję i zapisuje ją do pliku (numery zdań lokalne w porcji)."""
    index, text, out_path = job
    doc = _nlp(to_latin(text))
    rows = []
    for sid, sentence in enumerate(doc.sentences):
        for w in sentence.words:
            rows.append(f"{sid}\t{w.id}\t{to_cyrillic(w.text)}\t{to_cyrillic(w.lemma or w.text)}"
                        f"\t{w.upos}\t{w.head}\t{w.deprel}\n")
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.writelines(rows)
    os.replace(tmp, out_path)  # plik pojawia się dopiero po zapisaniu całej porcji
    return index


def parse_corpus(raw_file, parsed_file):
    if "--od-nowa" in sys.argv and os.path.exists(parsed_file):
        os.remove(parsed_file)
    if os.path.exists(parsed_file):
        print(f"Korpus jest już sparsowany: {parsed_file} (opcja --od-nowa wymusza ponowne parsowanie)")
        return
    if not os.path.exists(raw_file):
        print(f"Brak pliku {raw_file} - pomijam")
        return

    with open(raw_file, encoding="utf-8") as f:
        raw = f.read()
    # Usuwamy nagłówki sekcji Wikipedii ("== Историја ==") - to nie są zdania
    raw = re.sub(r"^=+.*?=+\s*$", "", raw, flags=re.MULTILINE)
    chunks = split_chunks(raw, CHUNK_SIZE)

    work_dir = parsed_file.replace(".tsv.gz", "_porcje")
    os.makedirs(work_dir, exist_ok=True)
    paths = [os.path.join(work_dir, f"{i:05d}.tsv") for i in range(len(chunks))]
    jobs = [(i, chunks[i], paths[i]) for i in range(len(chunks)) if not os.path.exists(paths[i])]
    print(f"{raw_file}: porcji {len(chunks)}, do przetworzenia {len(jobs)} ({WORKERS} procesy)", flush=True)

    import stanza  # pobranie modelu (jednorazowo, ok. 400 MB)
    stanza.download("sr", processors="tokenize,pos,lemma,depparse", verbose=False)

    start = time.time()
    if jobs:
        threads = max(1, (os.cpu_count() or 2) // WORKERS)
        with Pool(WORKERS, initializer=_init_worker, initargs=(threads,)) as pool:
            for done, _ in enumerate(pool.imap_unordered(_parse_chunk, jobs), 1):
                elapsed = time.time() - start
                left = elapsed / done * (len(jobs) - done)
                print(f"  porcja {done}/{len(jobs)}  czas: {elapsed / 60:.1f} min  "
                      f"pozostało ok. {left / 60:.1f} min", flush=True)

    # łączenie porcji w jeden plik z globalną numeracją zdań
    sentence_id = 0
    with gzip.open(parsed_file + ".tmp", "wt", encoding="utf-8") as out:
        for path in paths:
            last = None
            with open(path, encoding="utf-8") as f:
                for line in f:
                    sid, rest = line.split("\t", 1)
                    if sid != last:
                        if last is not None:
                            sentence_id += 1
                        last = sid
                    out.write(f"{sentence_id}\t{rest}")
            if last is not None:
                sentence_id += 1
    os.replace(parsed_file + ".tmp", parsed_file)
    for path in paths:
        os.remove(path)
    os.rmdir(work_dir)
    print(f"Zakończono: {sentence_id} zdań -> {parsed_file}")


def main():
    setup_console()
    for raw_file, parsed_file in CORPORA:
        parse_corpus(raw_file, parsed_file)


if __name__ == "__main__":
    main()
