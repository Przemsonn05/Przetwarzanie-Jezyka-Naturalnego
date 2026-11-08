"""
LAB 5 (analiza syntaktyczna) - generator zdań prostych typu SVO dla języka serbskiego.

Zdanie: PODMIOT - ORZECZENIE - (DOPEŁNIENIE BLIŻSZE)
  podmiot     : fraza rzeczownikowa albo zaimek osobowy (mianownik),
  orzeczenie  : czasownik przechodni, nieprzechodni albo zwrotny (z "se"),
  dopełnienie : fraza rzeczownikowa albo zaimek osobowy (biernik) - tylko przy przechodnich.
Fraza rzeczownikowa = [określnik] [przymiotnik] rzeczownik, gdzie określnik to zaimek
wskazujący (ovaj/taj/onaj), dzierżawczy (moj, tvoj, njegov, ..., zwrotny svoj), nieokreślony
(jedan, neki) albo upowszechniający (svaki). Serbski nie ma rodzajników - ich rolę pełnią
"jedan" (≈ nieokreślony) i "taj" (≈ określony).

Uwzględnione kategorie orzeczenia (wszystkie istniejące w serbskim):
  czasy trybu oznajmującego: prezent, perfekat, aorist, imperfekat, pluskvamperfekat,
                             futur I, futur II
  tryby: oznajmujący, rozkazujący (imperativ; 3. os. i 1. os. lp. przez "neka"),
         przypuszczający (potencijal I - teraźniejszy, potencijal II - przeszły)
  typ zdania: oznajmujące / pytające ("da li"), polaryzacja: twierdzące / przeczące
  strona: czynna / bierna (biti + imiesłów bierny, wykonawca: "od strane" + dopełniacz)

Gramatyka, o którą dba generator:
  - odmiana przez przypadki (M., B., D.), liczby i rodzaje, biernik = dopełniacz dla
    rzeczowników męskich żywotnych (vidim psa, ale vidim grad),
  - zgoda podmiotu z orzeczeniem w osobie, liczbie i rodzaju (čitao / čitala / čitalo / čitali...),
  - enklityki na drugim miejscu w zdaniu w kolejności: li - posiłkowe - biernik - se - je
    (Ja sam ga video. On se smejao. Da li si je ti video?),
  - zaimek dzierżawczy zwrotny svoj, gdy posiadaczem jest podmiot (Ja čitam svoju knjigu),
  - imperfekat tylko od czasowników niedokonanych, strona bierna tylko od przechodnich,
  - przeczenie trybu rozkazującego: "ne" + imperatyw (niedokonane), "nemoj" + bezokolicznik
    (dokonane),
  - ograniczenia semantyczne (pas jede meso, ale nie knjiga jede psa).

Uruchomienie:
  python lab05_generator_svo.py               # raport + 200 losowych zdań -> wyniki/lab05/
  python lab05_generator_svo.py -n 20         # 20 losowych zdań na ekran
  python lab05_generator_svo.py -n 20 --seed 5 --lacinka
"""
import argparse
import csv
import os
import random
import re

from leksykon_svo import (ADJECTIVES, DETERMINERS, NOUNS, POSSESSIVE_OF, PRONOUNS,
                          REFLEXIVE_POSSESSIVE, VERBS)
from wspolne import report_to, results_dir, setup_console

TENSES = ["prezent", "perfekat", "aorist", "imperfekat", "pluskvamperfekat", "futur I", "futur II"]
CONDITIONALS = ["potencijal I", "potencijal II"]
MOODS = ["oznajmujący", "rozkazujący", "przypuszczający"]
TYPES = ["oznajmujące", "pytające"]
POLARITIES = ["twierdzące", "przeczące"]
VOICES = ["czynna", "bierna"]
CASES = {"nom": 0, "gen": 1, "acc": 2}

# ---------------------------------------------------------------------------
# Transliteracja łacinka -> cyrylica
# ---------------------------------------------------------------------------
_LAT = ["lj", "nj", "dž", "a", "b", "v", "g", "d", "đ", "e", "ž", "z", "i", "j", "k", "l", "m",
        "n", "o", "p", "r", "s", "t", "ć", "u", "f", "h", "c", "č", "š"]
_CYR = ["љ", "њ", "џ", "а", "б", "в", "г", "д", "ђ", "е", "ж", "з", "и", "ј", "к", "л", "м",
        "н", "о", "п", "р", "с", "т", "ћ", "у", "ф", "х", "ц", "ч", "ш"]
_L2C = dict(zip(_LAT, _CYR))
_L2C.update({l.capitalize(): c.upper() for l, c in zip(_LAT, _CYR)})
_L2C.update({l.upper(): c.upper() for l, c in zip(_LAT, _CYR)})
_PATTERN = re.compile("|".join(sorted(map(re.escape, _L2C), key=len, reverse=True)))


def cyr(text):
    """Srbija -> Србија (dwuznaki lj, nj, dž -> љ, њ, џ)."""
    return _PATTERN.sub(lambda m: _L2C[m.group(0)], text)


# ---------------------------------------------------------------------------
# Odmiana przymiotników i zaimków przymiotnych
# ---------------------------------------------------------------------------
SOFT_ENDINGS = ("č", "ć", "š", "ž", "đ", "j")  # j obejmuje też lj, nj


def decline_adj(stem, nom_m, case, gender, number, animate, gen_m=None):
    """Odmiana przymiotnikowa (nowi, nova, novo; novog; novu; novi, nove, nova; novih)."""
    soft = stem.endswith(SOFT_ENDINGS)
    gen_sg = gen_m or stem + ("eg" if soft else "og")
    if number == "sg":
        if gender == "m":
            return {"nom": nom_m, "acc": gen_sg if animate else nom_m, "gen": gen_sg}[case]
        if gender == "n":
            return gen_sg if case == "gen" else stem + ("e" if soft else "o")
        return stem + {"nom": "a", "acc": "u", "gen": "e"}[case]
    if case == "gen":
        return stem + "ih"
    if gender == "m":
        return stem + ("i" if case == "nom" else "e")
    return stem + ("e" if gender == "f" else "a")


def agree(stem, masc_sg, gender, number):
    """Formy imiesłowów zgodne z podmiotem: čitao/čitala/čitalo/čitali/čitale/čitala."""
    if number == "sg":
        return {"m": masc_sg, "f": stem + "a", "n": stem + "o"}[gender]
    return stem + {"m": "i", "f": "e", "n": "a"}[gender]


# ---------------------------------------------------------------------------
# Odmiana czasownika
# ---------------------------------------------------------------------------
PERSON_INDEX = {("1", "sg"): 0, ("2", "sg"): 1, ("3", "sg"): 2, ("1", "pl"): 3, ("2", "pl"): 4, ("3", "pl"): 5}

BITI_PRES = ["sam", "si", "je", "smo", "ste", "su"]            # enklityczne
BITI_NEG = ["nisam", "nisi", "nije", "nismo", "niste", "nisu"]
HTETI = ["ću", "ćeš", "će", "ćemo", "ćete", "će"]              # enklityczne
HTETI_NEG = ["neću", "nećeš", "neće", "nećemo", "nećete", "neće"]
BITI_COND = ["bih", "bi", "bi", "bismo", "biste", "bi"]         # enklityczne (potencijal)
BITI_AOR = ["bih", "bi", "bi", "bismo", "biste", "biše"]
BITI_IMPF = ["bejah", "beše", "beše", "bejasmo", "bejaste", "behu"]
BITI_PF = ["budem", "budeš", "bude", "budemo", "budete", "budu"]


class Verb:
    def __init__(self, entry):
        self.__dict__.update(entry)
        self.stem = self.inf[:-2]   # temat bezokolicznika: čita-ti, nosi-ti, vide-ti
        self.pres_stem = self.p1[:-1]  # temat czasu teraźniejszego: čita-m, piše-m, nosi-m

    @property
    def transitive(self):
        return self.typ == "tr"

    @property
    def reflexive(self):
        return self.typ == "refl"

    def present(self, i):
        return self.p3 if i == 5 else self.pres_stem + ["m", "š", "", "mo", "te"][i]

    def aorist(self, i):
        s1, s23 = getattr(self, "aor", (self.stem, self.stem))
        return s23 if i in (1, 2) else s1 + ["h", "", "", "smo", "ste", "še"][i]

    def imperfect(self, i):
        if self.asp != "impf":
            return None  # imperfekt tworzą tylko czasowniki niedokonane
        stem = getattr(self, "impf", None)
        if stem is None:
            if self.inf.endswith("ati"):
                stem = self.stem                       # čita-h
            elif self.p1.endswith("im") and self.pres_stem[:-1].endswith(SOFT_ENDINGS):
                stem = self.pres_stem[:-1] + "a"       # traži-m -> traža-h, uči-m -> uča-h
            elif self.p1.endswith("im"):
                stem = self.pres_stem + "ja"           # nosi-ja-h
            elif self.pres_stem.endswith("je"):
                stem = self.pres_stem[:-1] + "a"       # pija-h
            else:
                stem = self.pres_stem[:-1] + "ija"     # (inne tematy na -e-)
        return stem + ["h", "še", "še", "smo", "ste", "hu"][i]

    def l_participle(self, gender, number):
        msg, lstem = getattr(self, "lp", (self.stem + "o", self.stem + "l"))
        return agree(lstem, msg, gender, number)

    def passive_participle(self, gender, number):
        return agree(self.pp, self.pp, gender, number)

    def imperative(self, i):
        """2. os. lp. (čitaj, piši, nosi), 1. os. lm. (čitajmo), 2. os. lm. (čitajte)."""
        base = getattr(self, "imp", None)
        if base is None:
            if self.p3.endswith("ju") and self.p3[-3] in "aeiou":
                base = self.p3[:-2] + "j"    # čitaju -> čitaj, piju -> pij, kupuju -> kupuj
            else:
                base = self.p3[:-1] + "i"    # pišu -> piši, nose -> nosi
        return {1: base, 3: base + "mo", 4: base + "te"}[i]


# ---------------------------------------------------------------------------
# Frazy: rzeczownikowa i zaimek osobowy
# ---------------------------------------------------------------------------
class NounPhrase:
    """[określnik] [przymiotnik] rzeczownik - odmieniane przez przypadki."""
    person = "3"

    def __init__(self, noun, number="sg", adj=None, det=None):
        self.noun, self.number, self.adj, self.det = noun, number, adj, det
        self.gender = noun["gender"]
        self.classes = noun["classes"]

    def form(self, case, owner=None):
        """owner = (osoba, liczba) podmiotu - zamienia moj/tvoj/naš/vaš na zwrotne svoj."""
        n, an = self.number, self.noun["animate"]
        words = []
        if self.det:
            nom_m, stem, gen_m = self.det[:3]
            if owner and POSSESSIVE_OF.get(owner) == nom_m:
                nom_m, stem, gen_m = REFLEXIVE_POSSESSIVE
            words.append(decline_adj(stem, nom_m, case, self.gender, n, an, gen_m))
        if self.adj:
            words.append(decline_adj(self.adj[:-1], self.adj, case, self.gender, n, an))
        words.append(self.noun["forms"][CASES[case] + (3 if n == "pl" else 0)])
        return " ".join(words)

    def describe(self):
        parts = [self.det[0] if self.det else None, self.adj, self.noun["lemma"]]
        return "FR(" + " + ".join(p for p in parts if p) + f", {self.number})"


class Pronoun:
    def __init__(self, person, number, gender):
        self.person, self.number, self.gender = person, number, gender
        self.nom, self.acc_clitic, self.acc_full, self.gen = PRONOUNS[(person, number, gender)]
        self.classes = "H" if person in "12" else "HAFDOCVBTMIPNK"

    def form(self, case, owner=None):
        return {"nom": self.nom, "acc": self.acc_full, "gen": self.gen}[case]

    def describe(self):
        return f"zaimek({self.nom}, {self.person}. os. {self.number}, rodz. {self.gender})"


# ---------------------------------------------------------------------------
# Enklityki (klityki) - zawsze na drugim miejscu w zdaniu
# ---------------------------------------------------------------------------
CLITIC_RANK = {"aux": 1, "acc": 3, "se": 4, "je": 5}


def clitic_cluster(clitics):
    """clitics: lista (typ, forma). Ustala kolejność aux < acc < se < je oraz:
       - 'se je' -> 'se' (on se smejao), - biernik 'je' przed posiłkowym 'je' -> 'ju'."""
    kinds = {k for k, _ in clitics}
    out = []
    for kind, form in sorted(clitics, key=lambda c: CLITIC_RANK[c[0]]):
        if kind == "je" and "se" in kinds:
            continue
        if kind == "acc" and form == "je" and "je" in kinds:
            form = "ju"
        out.append(form)
    return out


def aux_clitic(form):
    """Posiłkowe 'je' (3. os. lp. od biti) zajmuje ostatnie miejsce w grupie enklityk."""
    return ("je", form) if form == "je" else ("aux", form)


# ---------------------------------------------------------------------------
# Budowa zdania
# ---------------------------------------------------------------------------
def realize(subj, verb, obj, tense, mood="oznajmujący", stype="oznajmujące",
            polarity="twierdzące", voice="czynna", clitic_object=True):
    """
    Zwraca zdanie (łacinką) albo None, jeśli taka kombinacja nie istnieje w serbskim.
    tense: dla oznajmującego - jeden z TENSES, dla przypuszczającego - z CONDITIONALS,
           dla rozkazującego - "imperativ".
    """
    neg = polarity == "przeczące"
    question = stype == "pytające"

    if voice == "bierna":
        if not verb.transitive or not verb.pp:
            return None
        return _realize_passive(subj, verb, obj, tense, mood, question, neg)
    if verb.transitive and obj is None or not verb.transitive and obj is not None:
        return None

    i = PERSON_INDEX[(subj.person, subj.number)]
    g, num = subj.gender, subj.number
    owner = (subj.person, subj.number)
    clitics, rest = [], []
    if verb.reflexive:
        clitics.append(("se", "se"))

    # dopełnienie: zaimek -> enklityka biernika (ga, je, ih...), fraza -> po czasowniku
    obj_words = []
    if obj is not None:
        if isinstance(obj, Pronoun) and clitic_object:
            clitics.append(("acc", obj.acc_clitic))
        else:
            obj_words = [obj.form("acc", owner)]

    lp = verb.l_participle(g, num)
    first = None  # element przed enklitykami ("Da li", "Neka", "Ako") - domyślnie podmiot

    if mood == "oznajmujący":
        if tense == "prezent":
            rest = (["ne"] if neg else []) + [verb.present(i)]
        elif tense == "perfekat":
            if neg:
                rest = [BITI_NEG[i], lp]
            else:
                clitics.append(aux_clitic(BITI_PRES[i]))
                rest = [lp]
        elif tense == "aorist":
            rest = (["ne"] if neg else []) + [verb.aorist(i)]
        elif tense == "imperfekat":
            form = verb.imperfect(i)
            if form is None:
                return None
            rest = (["ne"] if neg else []) + [form]
        elif tense == "pluskvamperfekat":
            bio = agree("bil", "bio", g, num)
            if neg:
                rest = [BITI_NEG[i], bio, lp]
            else:
                clitics.append(aux_clitic(BITI_PRES[i]))
                rest = [bio, lp]
        elif tense == "futur I":
            if neg:
                rest = [HTETI_NEG[i], verb.inf]
            else:
                clitics.append(("aux", HTETI[i]))
                rest = [verb.inf]
        elif tense == "futur II":
            # futur II występuje tylko w zdaniach warunkowych/czasowych: "Ako budem čitao..."
            if question:
                return None
            first = "ako"
            rest = (["ne"] if neg else []) + [BITI_PF[i], lp]
        else:
            return None
    elif mood == "przypuszczający":
        if tense not in CONDITIONALS:
            return None
        extra = [agree("bil", "bio", g, num)] if tense == "potencijal II" else []
        if neg:
            rest = ["ne", BITI_COND[i]] + extra + [lp]
        else:
            clitics.append(("aux", BITI_COND[i]))
            rest = extra + [lp]
    elif mood == "rozkazujący":
        if question or tense != "imperativ":
            return None
        if i in (1, 3, 4):   # ti, mi, vi - imperatyw syntetyczny
            if neg and verb.asp == "pf":
                rest = [{1: "nemoj", 3: "nemojmo", 4: "nemojte"}[i], verb.inf]
            else:
                rest = (["ne"] if neg else []) + [verb.imperative(i)]
        else:                # ja, on, ona, oni, fraza rzeczownikowa: "Neka on čita"
            first = "neka"
            rest = (["ne"] if neg else []) + [verb.present(i)]
    else:
        return None

    subject = subj.form("nom")
    if question:
        first = "da li"
    if first is None:
        words = [subject] + clitic_cluster(clitics) + rest + obj_words
    else:
        words = [first] + clitic_cluster(clitics) + [subject] + rest + obj_words
    end = "?" if question else ("!" if mood == "rozkazujący" else ("…" if tense == "futur II" else "."))
    return finish(words, end)


def _realize_passive(subj, verb, obj, tense, mood, question, neg):
    """Strona bierna: dopełnienie staje się podmiotem, wykonawca: 'od strane' + dopełniacz."""
    new_subj = obj
    i = PERSON_INDEX[(new_subj.person, new_subj.number)]
    g, num = new_subj.gender, new_subj.number
    pp = verb.passive_participle(g, num)
    bio = agree("bil", "bio", g, num)
    clitics, first = [], None
    if mood == "oznajmujący":
        if tense == "prezent":
            if neg:
                rest = [BITI_NEG[i], pp]
            else:
                clitics.append(aux_clitic(BITI_PRES[i]))
                rest = [pp]
        elif tense == "perfekat":
            if neg:
                rest = [BITI_NEG[i], bio, pp]
            else:
                clitics.append(aux_clitic(BITI_PRES[i]))
                rest = [bio, pp]
        elif tense == "aorist":
            rest = (["ne"] if neg else []) + [BITI_AOR[i], pp]
        elif tense == "imperfekat":
            rest = (["ne"] if neg else []) + [BITI_IMPF[i], pp]
        elif tense == "futur I":
            if neg:
                rest = [HTETI_NEG[i], "biti", pp]
            else:
                clitics.append(("aux", HTETI[i]))
                rest = ["biti", pp]
        elif tense == "futur II":
            if question:
                return None
            first = "ako"
            rest = (["ne"] if neg else []) + [BITI_PF[i], pp]
        else:
            return None  # pluskvamperfekat bierny praktycznie nie istnieje
    elif mood == "przypuszczający":
        if tense != "potencijal I":
            return None  # potencijal II bierny praktycznie nie istnieje
        if neg:
            rest = ["ne", BITI_COND[i], bio, pp]
        else:
            clitics.append(("aux", BITI_COND[i]))
            rest = [bio, pp]
    elif mood == "rozkazujący":
        if question or tense != "imperativ":
            return None
        if i in (1, 3, 4):
            rest = (["ne"] if neg else []) + [{1: "budi", 3: "budimo", 4: "budite"}[i], pp]
        else:
            first = "neka"
            rest = (["ne"] if neg else []) + [BITI_PF[i], pp]
    else:
        return None

    agent = ["od strane", subj.form("gen")] if isinstance(subj, NounPhrase) else []
    subject = new_subj.form("nom")
    if question:
        first = "da li"
    if first is None:
        words = [subject] + clitic_cluster(clitics) + rest + agent
    else:
        words = [first] + clitic_cluster(clitics) + [subject] + rest + agent
    end = "?" if question else ("!" if mood == "rozkazujący" else ("…" if tense == "futur II" else "."))
    return finish(words, end)


def finish(words, end):
    text = " ".join(w for w in words if w)
    return text[0].upper() + text[1:] + end


# ---------------------------------------------------------------------------
# Losowanie składników
# ---------------------------------------------------------------------------
class Generator:
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.verbs = [Verb(v) for v in VERBS]
    def noun_phrase(self, classes):
        candidates = [n for n in NOUNS if set(n["classes"]) & set(classes)]
        noun = self.rng.choice(candidates)
        det = self.rng.choice(DETERMINERS) if self.rng.random() < 0.55 else None
        singular_only = noun["mass"] or (det and det[3])
        number = "pl" if not singular_only and self.rng.random() < 0.3 else "sg"
        fitting = [a for a, _, c in ADJECTIVES if set(c) & set(noun["classes"])]
        adj = self.rng.choice(fitting) if fitting and self.rng.random() < 0.6 else None
        return NounPhrase(noun, number, adj, det)

    def pronoun(self, classes, exclude=None):
        options = [k for k in PRONOUNS if ("H" in classes or k[0] == "3") and k[:2] != exclude]
        return Pronoun(*self.rng.choice(options))

    def phrase(self, classes, pronoun_prob, exclude=None):
        if self.rng.random() < pronoun_prob:
            return self.pronoun(classes, exclude)
        return self.noun_phrase(classes)

    def random_features(self, verb):
        voice = "bierna" if verb.transitive and self.rng.random() < 0.25 else "czynna"
        mood = self.rng.choices(MOODS, weights=[0.7, 0.15, 0.15])[0]
        tense = {"oznajmujący": self.rng.choice(TENSES), "przypuszczający": self.rng.choice(CONDITIONALS),
                 "rozkazujący": "imperativ"}[mood]
        stype = "pytające" if mood != "rozkazujący" and self.rng.random() < 0.3 else "oznajmujące"
        polarity = "przeczące" if self.rng.random() < 0.3 else "twierdzące"
        return dict(tense=tense, mood=mood, stype=stype, polarity=polarity, voice=voice)

    def sentence(self):
        """Losowe poprawne zdanie: (tekst łacinką, opis składników i cech)."""
        while True:
            verb = self.rng.choice(self.verbs)
            feats = self.random_features(verb)
            # w trybie rozkazującym podmiotem jest zwykle zaimek 2. os. (ti, vi) lub 1. os. lm. (mi)
            p_pron = 0.8 if feats["mood"] == "rozkazujący" else 0.35
            subj = self.phrase(verb.subj, p_pron)
            obj = None
            if verb.transitive:
                obj = self.phrase(verb.obj, 0.2, exclude=(subj.person, subj.number)
                                  if isinstance(subj, Pronoun) else None)
            text = realize(subj, verb, obj, **feats)
            if text:
                return text, subj, verb, obj, feats


# ---------------------------------------------------------------------------
# Raport
# ---------------------------------------------------------------------------
def all_forms(subj, verb, obj):
    """Wszystkie kombinacje czasu, trybu, typu zdania, polaryzacji i strony dla jednej trójki SVO."""
    rows = []
    for voice in VOICES:
        for mood in MOODS:
            tenses = {"oznajmujący": TENSES, "przypuszczający": CONDITIONALS, "rozkazujący": ["imperativ"]}[mood]
            for tense in tenses:
                for stype in TYPES:
                    for polarity in POLARITIES:
                        text = realize(subj, verb, obj, tense, mood, stype, polarity, voice)
                        if text:
                            rows.append((voice, mood, tense, stype, polarity, text))
    return rows


def label(f):
    return f"{f['voice']}, {f['mood']}, {f['tense']}, {f['stype']}, {f['polarity']}"


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)


def section(title):
    print("\n" + "=" * 90 + "\n" + title + "\n" + "=" * 90)


def report(n_sentences=200, seed=2024):
    out = results_dir("lab05")
    report_to(os.path.join(out, "raport.txt"))
    gen = Generator(seed)

    section("LEKSYKON")
    by_type = {t: [v for v in gen.verbs if v.typ == t] for t in ("tr", "intr", "refl")}
    print(f"Rzeczowniki:  {len(NOUNS)}  (m: {sum(n['gender'] == 'm' for n in NOUNS)}, "
          f"ż: {sum(n['gender'] == 'f' for n in NOUNS)}, n: {sum(n['gender'] == 'n' for n in NOUNS)})")
    print(f"Czasowniki:   {len(VERBS)}  (przechodnie: {len(by_type['tr'])}, nieprzechodnie: "
          f"{len(by_type['intr'])}, zwrotne: {len(by_type['refl'])}; "
          f"niedokonane: {sum(v.asp == 'impf' for v in gen.verbs)}, dokonane: {sum(v.asp == 'pf' for v in gen.verbs)})")
    print(f"Przymiotniki: {len(ADJECTIVES)}")
    print(f"Określniki:   {len(DETERMINERS)} + zwrotny dzierżawczy svoj "
          f"({', '.join(d[0] for d in DETERMINERS)})")
    print(f"Zaimki osobowe: {', '.join(sorted({p[0] for p in PRONOUNS.values()}))}")

    write_csv(os.path.join(out, "rzeczowniki.csv"),
              ["lemat_cyrylica", "lemat_lacinka", "rodzaj", "zywotny", "klasy", "znaczenie",
               "M_lp", "D_lp", "B_lp", "M_lm", "D_lm", "B_lm"],
              [[cyr(n["lemma"]), n["lemma"], n["gender"], int(n["animate"]), n["classes"], n["gloss"]]
               + [cyr(f) for f in n["forms"]] for n in NOUNS])
    write_csv(os.path.join(out, "czasowniki.csv"),
              ["bezokolicznik_cyrylica", "bezokolicznik_lacinka", "typ", "aspekt", "znaczenie",
               "prezent_1lp", "prezent_3lm", "aoryst_1lp", "imperfekt_1lp", "imieslow_l", "imieslow_bierny",
               "imperatyw_2lp", "klasy_podmiotu", "klasy_dopelnienia"],
              [[cyr(v.inf + (" se" if v.reflexive else "")), v.inf + (" se" if v.reflexive else ""),
                v.typ, v.asp, v.gloss, cyr(v.present(0)), cyr(v.present(5)), cyr(v.aorist(0)),
                cyr(v.imperfect(0) or "—"), cyr(v.l_participle("m", "sg")), cyr(v.pp or "—"),
                cyr(v.imperative(1)), v.subj, v.obj or "—"] for v in gen.verbs])
    write_csv(os.path.join(out, "przymiotniki.csv"),
              ["cyrylica", "lacinka", "znaczenie", "klasy_rzeczownikow", "Ż_lp", "N_lp", "D_m_lp"],
              [[cyr(a), a, g, c, cyr(a[:-1] + "a"), cyr(decline_adj(a[:-1], a, "nom", "n", "sg", False)),
                cyr(decline_adj(a[:-1], a, "gen", "m", "sg", False))] for a, g, c in ADJECTIVES])

    section("PEŁNA ODMIANA - PRZYKŁADY")
    noun = {n["lemma"]: n for n in NOUNS}
    det = {d[0]: d for d in DETERMINERS}
    verb = {v.inf: v for v in gen.verbs}
    examples = [
        ("czasownik przechodni dokonany, podmiot - zaimek, dopełnienie - fraza z zaimkiem dzierżawczym",
         Pronoun("1", "sg", "m"), verb["pročitati"], NounPhrase(noun["knjiga"], "sg", "novi", det["moj"])),
        ("czasownik przechodni niedokonany, podmiot - fraza rzeczownikowa, dopełnienie - zaimek",
         NounPhrase(noun["pas"], "sg", "veliki", det["naš"]), verb["čuvati"], Pronoun("3", "sg", "f")),
        ("czasownik nieprzechodni, podmiot - fraza rzeczownikowa w liczbie mnogiej",
         NounPhrase(noun["devojka"], "pl", "mladi", det["ovaj"]), verb["trčati"], None),
        ("czasownik zwrotny, podmiot - zaimek",
         Pronoun("2", "pl", "f"), verb["smejati"], None),
    ]
    all_rows = []
    for title, s, v, o in examples:
        rows = all_forms(s, v, o)
        print(f"\n--- {title}: {s.describe()} + {v.inf}{' se' if v.reflexive else ''}"
              f"{' + ' + o.describe() if o else ''}  ({len(rows)} form)")
        for voice, mood, tense, stype, pol, text in rows:
            print(f"  {voice:<7} {mood:<16} {tense:<17} {stype:<12} {pol:<11} {cyr(text)}   ({text})")
            all_rows.append([v.inf, voice, mood, tense, stype, pol, cyr(text), text])
    write_csv(os.path.join(out, "pelna_odmiana.csv"),
              ["czasownik", "strona", "tryb", "czas", "typ_zdania", "polaryzacja", "zdanie_cyrylica",
               "zdanie_lacinka"], all_rows)

    section(f"LOSOWE ZDANIA ({n_sentences}, ziarno {seed})")
    rows = []
    for k in range(1, n_sentences + 1):
        text, s, v, o, f = gen.sentence()
        print(f"{k:>3}. {cyr(text)}\n     {text}\n     [{label(f)}]")
        rows.append([k, cyr(text), text, f["voice"], f["mood"], f["tense"], f["stype"], f["polarity"],
                     v.inf, v.typ, s.describe(), o.describe() if o else ""])
    write_csv(os.path.join(out, "losowe_zdania.csv"),
              ["lp", "zdanie_cyrylica", "zdanie_lacinka", "strona", "tryb", "czas", "typ_zdania",
               "polaryzacja", "czasownik", "typ_czasownika", "podmiot", "dopelnienie"], rows)

    section("PODSUMOWANIE")
    combos = sum(1 for v in gen.verbs for voice in VOICES for mood in MOODS
                 for tense in {"oznajmujący": TENSES, "przypuszczający": CONDITIONALS,
                               "rozkazujący": ["imperativ"]}[mood]
                 for st in TYPES for pol in POLARITIES
                 if realize(Pronoun("3", "sg", "m"), v, Pronoun("3", "sg", "f") if v.transitive else None,
                            tense, mood, st, pol, voice))
    print(f"Liczba poprawnych kombinacji (czasownik × strona × tryb × czas × typ × polaryzacja): {combos}")
    print(f"Pliki w '{out}': raport.txt, rzeczowniki.csv, czasowniki.csv, przymiotniki.csv, "
          "pelna_odmiana.csv, losowe_zdania.csv")


def main():
    parser = argparse.ArgumentParser(description="Generator zdań SVO języka serbskiego")
    parser.add_argument("-n", type=int, help="wypisz tylko N losowych zdań (bez zapisywania raportu)")
    parser.add_argument("--seed", type=int, default=None, help="ziarno generatora losowego")
    parser.add_argument("--lacinka", action="store_true", help="pokaż też zapis łacinką")
    args = parser.parse_args()
    if args.n is None:
        report()
        return
    setup_console()
    gen = Generator(args.seed)
    for k in range(1, args.n + 1):
        text, s, v, o, f = gen.sentence()
        print(f"{k:>3}. {cyr(text)}" + (f"  ({text})" if args.lacinka else "") + f"   [{label(f)}]")


if __name__ == "__main__":
    main()
