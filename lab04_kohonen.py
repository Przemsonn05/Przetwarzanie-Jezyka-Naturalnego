"""
LAB 4 (analiza semantyczna) - klasyfikator semantyczny rzeczowników oparty na sieci Kohonena.

Idea (hipoteza dystrybucyjna): znaczenie rzeczownika poznajemy po czasownikach, których jest
dopełnieniem. "Jeść chleb / ser / mięso", "pić wodę / kawę / wino", "grać mecz / rolę":
rzeczowniki z jednego pola semantycznego łączą się z tymi samymi czasownikami, więc mają
podobne wektory, a sieć Kohonena powinna sama (bez nauczyciela) umieścić je w tym samym
albo sąsiednim neuronie.

Kroki:
  1. Z korpusu sparsowanego (lab04_parsowanie.py) bierzemy frazy VO - pary czasownik ->
     dopełnienie bliższe (relacja 'obj', np. "попио воду" -> obj(попити, вода)).
  2. Wybieramy 100 czasowników przechodnich (najczęściej mających dopełnienie rzeczownikowe)
     i 1000 rzeczowników najczęściej występujących jako ich dopełnienie.
  3. Każdy rzeczownik = wektor o 100 składowych: składowa j = liczba wystąpień frazy VO
     (j-ty czasownik + ten rzeczownik). 1000 wektorów = zbiór treningowy.
  4. Uczymy sieć Kohonena z 50 neuronami (siatka 5 x 10).
  5. Analizujemy klastry: które rzeczowniki trafiły do każdego neuronu, czy tworzą jednorodne
     pole semantyczne, ile pól powstało, które neurony niczego się nie nauczyły (martwe).

Wyniki: wyniki/lab04/ (raport.txt, CSV, wykresy PNG, podsumowanie.json).
"""
import csv
import gzip
import json
import os
import textwrap
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")  # wykresy zapisujemy do plików, bez otwierania okien
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np

from wspolne import PARSED_FILE, SEM_PARSED_FILE, SERBIAN_ALPHABET, report_to, results_dir

OUTPUT_DIR = results_dir("lab04")
N_VERBS = 100
N_NOUNS = 1000
SOM_ROWS, SOM_COLS = 5, 10          # 50 neuronów
EPOCHS = 40                          # liczba przejść przez cały zbiór treningowy
SEED = 42
EXCLUDED_VERBS = {"бити", "хтети", "моћи", "морати", "требати", "јесам"}  # posiłkowe / modalne
MIN_TRANSITIVITY = 0.2   # min. odsetek wystąpień czasownika z dopełnieniem (odrzuca błędy parsera)
ALPHABET = set(SERBIAN_ALPHABET)
OUTLINE = [pe.withStroke(linewidth=2, foreground="white")]
PARSED_FILES = [PARSED_FILE, SEM_PARSED_FILE]

# ---------------------------------------------------------------------------
# Interpretacja klastrów (wynik ręcznej analizy zawartości neuronów dla SEED = 42).
# Każde pole opisane jest kilkoma rzeczownikami-"kotwicami": etykieta zostaje przypisana
# neuronowi tylko wtedy, gdy większość kotwic rzeczywiście w nim leży - po zmianie danych
# lub parametrów nieaktualna interpretacja nie zostanie więc przypisana błędnie.
# (etykieta pola, jednorodne?, kotwice)
# ---------------------------------------------------------------------------
FIELD_LABELS = [
    ("przedmioty noszone: broń, oznaki, rękawice", False, ["опрема", "оружје", "застава", "рукавица", "штит"]),
    ("pomoc, wsparcie, ochrona", True, ["подршка", "заштита", "помоћ", "услуга", "отпор"]),
    ("etapy dziejów: rozkwit i upadek", True, ["пораз", "пад", "процват", "врхунац", "успон"]),
    ("skutki negatywne: choroby, szkody, straty", True, ["болест", "губитак", "загађење", "депресија"]),
    ("skutki negatywne: choroby, szkody, straty", True, ["оштећење", "поремећај", "смрт", "бол", "повреда"]),
    ("procesy i zmiany", True, ["развој", "кретање", "стварање", "смањење", "формирање"]),
    ("czynności i działania", True, ["примена", "рад", "коришћење", "истраживање", "увођење"]),
    ("działania wykonywane: ataki, reformy, służba", True, ["инвазија", "напад", "притисак", "реформа", "служба"]),
    ("wojna, polityka, walka (prowadzić)", True, ["рат", "политика", "борба", "војска", "преговор"]),
    ("teorie i systemy pojęć", True, ["језик", "теорија", "концепт", "принцип", "стратегија"]),
    ("władza, odpowiedzialność, propozycje", True, ["власт", "одговорност", "предлог", "вођство", "обавеза"]),
    ("decyzje i akty prawne", True, ["одлука", "закон", "декларација", "резолуција", "акт"]),
    ("osiągnięcia: gole, sukcesy", True, ["гол", "успех", "погодак"]),
    ("cechy i przejawy zachowania", True, ["варијација", "сличност", "симптом", "понашање"]),
    ("mieszany: przyroda i różne obiekty", False, ["животиња", "аспект", "море", "долина"]),
    ("mieszany: działalność i wydarzenia", False, ["догађај", "делатност", "путовање", "каријера"]),
    ("wydarzenia organizowane: gry, wystawy, referenda", True, ["игра", "такмичење", "изложба", "референдум", "протест"]),
    ("metody, techniki, narzędzia", True, ["метод", "техника", "мотор", "технологија"]),
    ("systemy, programy, modele", True, ["систем", "програм", "верзија", "модел"]),
    ("teksty i dzieła", True, ["књига", "писмо", "извештај", "роман", "опера"]),
    ("trofea i zawody sportowe", True, ["титула", "медаља", "првенство", "турнир", "лига"]),
    ("wielkości, które rosną i maleją", True, ["способност", "брзина", "ризик", "температура", "отпорност"]),
    ("jednostki miary i liczebność", True, ["становник", "тона", "долар", "хектар", "метар"]),
    ("mieszany: ludzie, instytucje, normy", False, ["човек", "стандард", "институција", "питање"]),
    ("porozumienia i związki", True, ["контакт", "унија", "споразум", "сарадња"]),
    ("państwa i instytucje zakładane", True, ["царство", "колонија", "школа", "република", "друштво"]),
    ("materiały i substancje wytwarzane", True, ["материјал", "ресурс", "супстанац", "гас", "барут"]),
    ("mieszany: rodzaje i sposoby", False, ["врста", "начин", "тип", "пример"]),
    ("mieszany: dźwięki, obrazy, ślady", False, ["звук", "слика", "траг", "сигнал"]),
    ("miejsca i pozycje zajmowane", True, ["место", "позиција", "регион", "тврђава"]),
    ("role i terytoria zdobywane", True, ["улога", "територија", "моћ", "положај"]),
    ("właściwości i cechy", True, ["снага", "својство", "особина", "капацитет"]),
    ("właściwości i cechy", True, ["вредност", "однос", "карактеристика", "садржај"]),
    ("mieszany: wielkości i kategorie", False, ["величина", "категорија", "предмет", "фактор"]),
    ("mieszany: różnice i podziały", False, ["разлика", "линија", "избор", "целина"]),
    ("grupy społeczne i organizacje", True, ["група", "држава", "влада", "заједница", "организација"]),
    ("substancje i składniki chemiczne", True, ["киселина", "бакар", "кисеоник", "протеина", "шећер"]),
    ("substancje i składniki chemiczne", False, ["количина", "вода", "елемент", "информација", "податак"]),
    ("korzyści i cechy nadawane", True, ["предност", "боја", "резултат", "укус", "допринос"]),
    ("nazwy i formy otrzymywane", True, ["име", "облик", "значење", "изглед", "форма"]),
    ("prawa i status zdobywane", True, ["право", "статус", "контрола", "независност", "популарност"]),
    ("mieszany: znaczenie i kompetencje", False, ["значај", "зуб", "овлашћење", "пречник"]),
    ("mieszany: narządy i cechy", False, ["мембрана", "око", "смисао", "жица"]),
    ("części składowe całości", True, ["компонент", "половина", "стуб", "остатак"]),
    ("obszar i ludność", True, ["површина", "већина", "подручје", "популација", "становништво"]),
    ("struktury tworzone", True, ["структура", "мрежа", "слој", "једињење", "јединица"]),
]


# ---------------------------------------------------------------------------
# Wczytanie korpusu sparsowanego i frazy VO
# ---------------------------------------------------------------------------
def is_word(s):
    return len(s) > 1 and set(s) <= ALPHABET


def read_sentences(path):
    """Zdania jako listy krotek (id, lemat, upos, head, deprel)."""
    current, current_id = [], None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            sid, wid, form, lemma, upos, head, deprel = line.rstrip("\n").split("\t")
            if sid != current_id and current:
                yield current
                current = []
            current_id = sid
            current.append((int(wid), lemma, upos, int(head), deprel))
    if current:
        yield current


def extract_relations(paths):
    """
    obj_pairs - Counter[(czasownik, rzeczownik)]: frazy VO z relacji obj, z rozwinięciem
                dopełnień współrzędnych ("kupio hleb i mleko" -> hleb, mleko)
    verb_freq - liczba wystąpień czasowników, verb_objs - liczba ich dopełnień (dowolnych)
    """
    obj_pairs, verb_freq, verb_objs = Counter(), Counter(), Counter()
    stats = Counter()
    for path in paths:
        if not os.path.exists(path):
            print(f"[!] Brak pliku {path} - pomijam")
            continue
        for sent in read_sentences(path):
            stats["zdania"] += 1
            stats["tokeny"] += len(sent)
            by_id = {w[0]: w for w in sent}
            for w in sent:
                if w[2] == "VERB" and is_word(w[1]):
                    verb_freq[w[1]] += 1
            for w in sent:
                if w[4] != "obj":
                    continue
                head = by_id.get(w[3])
                if not head or head[2] != "VERB" or not is_word(head[1]):
                    continue
                verb_objs[head[1]] += 1
                objects = [w] + [c for c in sent if c[4] == "conj" and c[3] == w[0]]
                for o in objects:
                    if o[2] == "NOUN" and is_word(o[1]):
                        obj_pairs[(head[1], o[1])] += 1
    return obj_pairs, verb_freq, verb_objs, stats


# ---------------------------------------------------------------------------
# Sieć Kohonena (implementacja własna, numpy)
# ---------------------------------------------------------------------------
class KohonenSOM:
    def __init__(self, rows, cols, dim, seed=SEED):
        self.rows, self.cols, self.dim = rows, cols, dim
        self.rng = np.random.default_rng(seed)
        self.grid = np.array([(r, c) for r in range(rows) for c in range(cols)], dtype=float)
        # klasyczna inicjalizacja: małe losowe wagi
        self.weights = self.rng.uniform(0, 0.1, size=(rows * cols, dim))

    def bmu(self, x):
        return int(np.argmin(np.linalg.norm(self.weights - x, axis=1)))

    def train(self, data, epochs, lr0=0.5, lr_end=0.01, sigma0=None, sigma_end=0.5):
        """Algorytm Kohonena (uczenie on-line, sąsiedztwo gaussowskie malejące w czasie)."""
        sigma0 = sigma0 or max(self.rows, self.cols) / 2
        total = epochs * len(data)
        history, t = [], 0
        for epoch in range(epochs):
            for idx in self.rng.permutation(len(data)):
                frac = t / total
                lr = lr0 * (lr_end / lr0) ** frac
                sigma = sigma0 * (sigma_end / sigma0) ** frac
                x = data[idx]
                b = self.bmu(x)
                d2 = np.sum((self.grid - self.grid[b]) ** 2, axis=1)
                h = np.exp(-d2 / (2 * sigma ** 2))
                self.weights += lr * h[:, None] * (x - self.weights)
                t += 1
            history.append((epoch + 1, self.quantization_error(data)))
        return history

    def distances(self, data):
        return np.linalg.norm(data[:, None, :] - self.weights[None, :, :], axis=2)

    def quantization_error(self, data):
        return float(np.mean(np.min(self.distances(data), axis=1)))

    def topographic_error(self, data):
        """Odsetek próbek, dla których 1. i 2. najlepszy neuron nie sąsiadują na siatce."""
        order = np.argsort(self.distances(data), axis=1)[:, :2]
        far = np.max(np.abs(self.grid[order[:, 0]] - self.grid[order[:, 1]]), axis=1) > 1
        return float(np.mean(far))

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
    """
    Przygotowanie wektorów przed uczeniem (same liczby fraz VO są w zbior_treningowy.csv):
      1. log(1 + liczba) - tłumi bardzo częste frazy,
      2. waga IDF czasownika = log(liczba rzeczowników / liczba rzeczowników z tym czasownikiem) -
         czasowniki łączące się prawie ze wszystkim (имати 'mieć', представљати 'stanowić')
         niewiele mówią o znaczeniu, więc dostają mniejszą wagę niż np. освојити 'zdobyć',
      3. długość wektora = 1 - o podobieństwie decyduje PROFIL czasowników, a nie to,
         jak często rzeczownik występuje.
    """
    df = np.maximum((counts > 0).sum(axis=0), 1)
    x = np.log1p(counts) * np.log(len(counts) / df)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


# ---------------------------------------------------------------------------
# Wykresy
# ---------------------------------------------------------------------------
def plot_map(som, clusters, verbs, labels, path, per_cell=5):
    """Mapa neuronów rysowana pionowo (siatka 5 x 10 obrócona: wiersz sieci = kolumna rysunku),
    żeby zmieściła się czytelnie na stronie A4."""
    u = som.u_matrix().T
    fig, ax = plt.subplots(figsize=(13, 22))
    im = ax.imshow(u, cmap="Greys", origin="upper", vmin=u.min() - 0.6 * (u.max() - u.min()),
                   vmax=u.max() + 0.8 * (u.max() - u.min()))  # jasne tło - czytelne podpisy
    plt.colorbar(im, ax=ax, fraction=0.03, pad=0.01, label="U-macierz (odległość do sąsiednich neuronów)")
    for k in range(som.rows * som.cols):
        r, c = divmod(k, som.cols)
        x, y = r, c  # obrót siatki
        members = clusters[k]
        top_verb = verbs[int(np.argmax(som.weights[k]))]
        if not members:
            ax.add_patch(plt.Rectangle((x - 0.5, y - 0.5), 1, 1, fill=False, hatch="///", ec="#c00000", lw=0))
            ax.text(x, y, f"#{k}\nmartwy", ha="center", va="center", fontsize=13, color="#c00000",
                    fontweight="bold", path_effects=OUTLINE)
            continue
        ax.text(x, y - 0.40, f"#{k}  ({len(members)})  {top_verb}", ha="center", va="center", fontsize=11,
                fontweight="bold", color="#0b4f9c", path_effects=OUTLINE)
        words = [n for n, _ in members[:per_cell]]
        ax.text(x, y - 0.02, "\n".join(words), ha="center", va="center", fontsize=10.5,
                color="#b2182b", linespacing=1.1, path_effects=OUTLINE)
        if labels.get(k):
            text = labels[k][0].replace("mieszany: ", "mieszany:\n") if not labels[k][1] else labels[k][0]
            ax.text(x, y + 0.40, "\n".join(textwrap.wrap(text, 26))[:60], ha="center", va="center",
                    fontsize=8.5, color="#1a7f37" if labels[k][1] else "#7a5c00", style="italic",
                    linespacing=1.0, path_effects=OUTLINE)
    ax.set_xticks(range(som.rows))
    ax.set_yticks(range(som.cols))
    ax.set_xlabel("wiersz siatki sieci")
    ax.set_ylabel("kolumna siatki sieci")
    ax.set_title(f"Sieć Kohonena {som.rows} × {som.cols}: #neuron (liczba rzeczowników) i czasownik o największej "
                 "wadze;\nczerwony – najczęstsze rzeczowniki; zielony – pole semantyczne, brązowy – klaster mieszany",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=100)
    plt.close(fig)


def plot_sizes(clusters, path):
    sizes = [len(clusters[k]) for k in sorted(clusters)]
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(range(len(sizes)), sizes, color=["#c00000" if s == 0 else "#1f6fb4" for s in sizes])
    ax.set_xlabel("Numer neuronu")
    ax.set_ylabel("Liczba rzeczowników")
    ax.set_title("Liczebność klastrów (czerwone – neurony, które niczego się nie nauczyły)")
    ax.set_xticks(range(0, len(sizes), 5))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def plot_learning(history, path):
    e, qe = zip(*history)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(e, qe, marker="o", ms=3)
    ax.set_xlabel("Epoka")
    ax.set_ylabel("Błąd kwantyzacji")
    ax.set_title("Przebieg uczenia sieci Kohonena")
    ax.grid(alpha=0.3)
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


def assign_labels(clusters):
    """Przypisuje neuronom etykiety pól semantycznych z FIELD_LABELS (gdy kotwice się zgadzają)."""
    where = {n: k for k, members in clusters.items() for n, _ in members}
    labels = {}
    for label, homogeneous, anchors in FIELD_LABELS:
        votes = Counter(where.get(a) for a in anchors if a in where)
        if votes:
            k, hits = votes.most_common(1)[0]
            if hits * 2 > len(anchors) and k not in labels:
                labels[k] = (label, homogeneous)
    return labels


def main():
    report_to(os.path.join(OUTPUT_DIR, "raport.txt"))
    if not os.path.exists(PARSED_FILE):
        raise SystemExit(f"Brak pliku {PARSED_FILE} - najpierw uruchom lab04_parsowanie.py")

    section("ANALIZA KORPUSU")
    obj_pairs, verb_freq, verb_objs, stats = extract_relations(PARSED_FILES)
    print(f"Pliki: {', '.join(p for p in PARSED_FILES if os.path.exists(p))}")
    print(f"Zdania: {stats['zdania']}, tokeny: {stats['tokeny']}")
    print(f"Różne czasowniki: {len(verb_freq)}")
    print(f"Frazy VO (czasownik -> dopełnienie rzeczownikowe): {sum(obj_pairs.values())}, "
          f"różnych par: {len(obj_pairs)}")

    # 100 czasowników przechodnich: najwięcej dopełnień rzeczownikowych, przy czym dopełnienie
    # musi wystąpić w co najmniej MIN_TRANSITIVITY wystąpień czasownika
    per_verb = Counter()
    for (v, n), c in obj_pairs.items():
        per_verb[v] += c
    ok = lambda v: v not in EXCLUDED_VERBS and verb_objs[v] >= MIN_TRANSITIVITY * verb_freq[v]
    rejected = [v for v, _ in per_verb.most_common(N_VERBS) if not ok(v)]
    verbs = [v for v, _ in per_verb.most_common() if ok(v)][:N_VERBS]
    print("Odrzucone (posiłkowe/modalne lub dopełnienie w < 20% wystąpień): "
          + ", ".join(f"{v} ({verb_objs[v] / max(1, verb_freq[v]):.0%})" for v in rejected))

    noun_obj = Counter()
    for (v, n), c in obj_pairs.items():
        if v in verbs:
            noun_obj[n] += c
    nouns = [n for n, _ in noun_obj.most_common(N_NOUNS)]

    section(f"WYBRANE CZASOWNIKI PRZECHODNIE ({len(verbs)})")
    rows = []
    for i, v in enumerate(verbs, 1):
        ratio = min(1.0, verb_objs[v] / verb_freq[v]) if verb_freq[v] else 0
        rows.append([i, v, per_verb[v], verb_objs[v], verb_freq[v], f"{ratio:.3f}"])
    print(f"{'Lp':>3} | {'czasownik':<16} | {'frazy VO':>8} | {'wystąpienia':>11} | {'przechodniość':>13}")
    for r in rows:
        print(f"{r[0]:>3} | {r[1]:<16} | {r[2]:>8} | {r[4]:>11} | {r[5]:>13}")
    write_csv(os.path.join(OUTPUT_DIR, "czasowniki_przechodnie.csv"),
              ["lp", "czasownik", "frazy_vo", "dopelnienia_wszystkie", "wystapienia",
               "wspolczynnik_przechodniosci"], rows)

    section(f"WYBRANE RZECZOWNIKI ({len(nouns)})")
    counts = build_matrix(nouns, verbs, obj_pairs)
    nnz = (counts > 0).sum(axis=1)
    print(f"Liczba fraz VO na rzeczownik: od {int(counts.sum(1).min())} do {int(counts.sum(1).max())}, "
          f"mediana {int(np.median(counts.sum(1)))}")
    print(f"Liczba różnych czasowników na rzeczownik: mediana {int(np.median(nnz))}, "
          f"średnio {nnz.mean():.1f}")
    print(f"Wypełnienie macierzy 1000 × 100: {np.count_nonzero(counts) / counts.size:.1%} niezerowych składowych")
    print("Pierwsze 40: " + ", ".join(f"{n} ({noun_obj[n]})" for n in nouns[:40]))
    write_csv(os.path.join(OUTPUT_DIR, "rzeczowniki.csv"),
              ["lp", "rzeczownik", "liczba_fraz_vo", "liczba_roznych_czasownikow"],
              [[i, n, int(counts[i - 1].sum()), int(nnz[i - 1])] for i, n in enumerate(nouns, 1)])
    write_csv(os.path.join(OUTPUT_DIR, "zbior_treningowy.csv"), ["rzeczownik"] + verbs,
              [[n] + [int(c) for c in row] for n, row in zip(nouns, counts)])

    section(f"SIEĆ KOHONENA ({SOM_ROWS * SOM_COLS} neuronów, siatka {SOM_ROWS} × {SOM_COLS})")
    data = normalize(counts)
    som = KohonenSOM(SOM_ROWS, SOM_COLS, len(verbs))
    history = som.train(data, EPOCHS)
    qe, te = som.quantization_error(data), som.topographic_error(data)
    print(f"Uczenie: {EPOCHS} epok × {len(data)} wektorów = {EPOCHS * len(data)} kroków, "
          f"współczynnik uczenia 0,5 → 0,01, promień sąsiedztwa {max(SOM_ROWS, SOM_COLS) / 2} → 0,5")
    print(f"Błąd kwantyzacji: {qe:.4f}, błąd topograficzny: {te:.2%}")

    dist = som.distances(data)
    winners = np.argmin(dist, axis=1)
    clusters = {k: [] for k in range(SOM_ROWS * SOM_COLS)}
    for i, k in enumerate(winners):
        clusters[k].append((nouns[i], int(counts[i].sum())))
    for k in clusters:
        clusters[k].sort(key=lambda x: -x[1])
    dead = [k for k, m in clusters.items() if not m]
    labels = assign_labels(clusters)

    # spójność klastra: średnie podobieństwo kosinusowe rzeczowników do siebie nawzajem
    sim = data @ data.T
    cohesion = {}
    for k, members in clusters.items():
        idx = [i for i in range(len(nouns)) if winners[i] == k]
        if len(idx) > 1:
            block = sim[np.ix_(idx, idx)]
            cohesion[k] = float((block.sum() - len(idx)) / (len(idx) * (len(idx) - 1)))
    inter = float((sim.sum() - len(nouns)) / (len(nouns) * (len(nouns) - 1)))

    section("ZAWARTOŚĆ NEURONÓW (KLASTRÓW)")
    neuron_rows = []
    for k in range(SOM_ROWS * SOM_COLS):
        r, c = divmod(k, SOM_COLS)
        members = clusters[k]
        top = np.argsort(-som.weights[k])[:4]
        top_verbs = ", ".join(f"{verbs[j]} ({som.weights[k, j]:.2f})" for j in top)
        label, homog = labels.get(k, ("", ""))
        print(f"\nNeuron #{k} (wiersz {r}, kolumna {c}): {len(members)} rzeczowników"
              + (f", spójność {cohesion[k]:.2f}" if k in cohesion else ""))
        print(f"  czasowniki o największych wagach: {top_verbs}")
        if label:
            print(f"  pole semantyczne: {label}" + ("" if homog else " (klaster niejednorodny)"))
        if members:
            print("  " + ", ".join(n for n, _ in members[:40]) + (" ..." if len(members) > 40 else ""))
        else:
            print("  NEURON MARTWY - nie wygrał dla żadnego rzeczownika")
        neuron_rows.append([k, r, c, len(members), f"{cohesion.get(k, float('nan')):.3f}",
                            ", ".join(verbs[j] for j in top), label,
                            "" if not label else ("tak" if homog else "nie"),
                            ", ".join(n for n, _ in members)])
    write_csv(os.path.join(OUTPUT_DIR, "neurony.csv"),
              ["neuron", "wiersz", "kolumna", "liczba_rzeczownikow", "spojnosc", "dominujace_czasowniki",
               "pole_semantyczne", "jednorodny", "rzeczowniki"], neuron_rows)
    write_csv(os.path.join(OUTPUT_DIR, "wagi_neuronow.csv"), ["neuron"] + verbs,
              [[k] + [f"{w:.6f}" for w in som.weights[k]] for k in range(SOM_ROWS * SOM_COLS)])
    write_csv(os.path.join(OUTPUT_DIR, "przypisanie_rzeczownikow.csv"),
              ["rzeczownik", "neuron", "wiersz", "kolumna", "odleglosc_od_wag", "liczba_fraz_vo",
               "najczestsze_czasowniki"],
              [[n, int(winners[i]), *divmod(int(winners[i]), SOM_COLS), f"{dist[i, winners[i]]:.4f}",
                int(counts[i].sum()), ", ".join(f"{verbs[j]}({int(counts[i, j])})"
                                                for j in np.argsort(-counts[i])[:4] if counts[i, j] > 0)]
               for i, n in enumerate(nouns)])

    section("PODSUMOWANIE ANALIZY KLASTRÓW")
    sizes = sorted((len(m) for m in clusters.values()), reverse=True)
    print(f"Neurony aktywne: {50 - len(dead)} / 50, martwe (nie nauczyły się niczego): {len(dead)}"
          + (f" -> {', '.join('#' + str(k) for k in dead)}" if dead else ""))
    print(f"Liczebność klastrów: największy {sizes[0]}, najmniejszy niepusty "
          f"{min(s for s in sizes if s)}, mediana {int(np.median([s for s in sizes if s]))}")
    print(f"Średnia spójność klastrów: {np.mean(list(cohesion.values())):.3f} "
          f"(średnie podobieństwo dowolnych dwóch rzeczowników: {inter:.3f})")
    fields = sorted({lab for lab, h in labels.values() if h})  # pola = etykiety klastrów jednorodnych
    if labels:
        hom = sum(1 for _, h in labels.values() if h)
        print(f"Neurony z rozpoznanym polem semantycznym: {len(labels)}, w tym jednorodnych: {hom}")
        print(f"Liczba różnych pól semantycznych (z klastrów jednorodnych): {len(fields)}")
        print(f"Neurony bez rozpoznanego pola: {', '.join('#' + str(k) for k in clusters if k not in labels and clusters[k])}")
        for f in fields:
            ks = [k for k, (lab, _) in labels.items() if lab == f]
            print(f"  - {f}: neurony {', '.join('#' + str(k) for k in sorted(ks))}")

    plot_map(som, clusters, verbs, labels, os.path.join(OUTPUT_DIR, "mapa_kohonena.png"))
    plot_sizes(clusters, os.path.join(OUTPUT_DIR, "liczebnosc_klastrow.png"))
    plot_learning(history, os.path.join(OUTPUT_DIR, "uczenie.png"))

    summary = {
        "zdania": stats["zdania"], "tokeny": stats["tokeny"], "frazy_vo": sum(obj_pairs.values()),
        "czasowniki": verbs, "rzeczowniki": nouns,
        "som": {"wiersze": SOM_ROWS, "kolumny": SOM_COLS, "epoki": EPOCHS, "ziarno": SEED},
        "blad_kwantyzacji": qe, "blad_topograficzny": te, "martwe_neurony": dead,
        "spojnosc": cohesion, "podobienstwo_srednie": inter,
        "klastry": {str(k): [n for n, _ in m] for k, m in clusters.items()},
        "pola": {str(k): {"pole": lab, "jednorodny": h} for k, (lab, h) in labels.items()},
        "liczba_pol": len(fields),
    }
    with open(os.path.join(OUTPUT_DIR, "podsumowanie.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=1)

    print(f"\nZapisano wyniki w folderze '{OUTPUT_DIR}':")
    for name in sorted(os.listdir(OUTPUT_DIR)):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
