"""
Leksykon generatora zdań SVO języka serbskiego (lab05_generator_svo.py).

Wyrazy zapisane są ŁACINKĄ (serbska łacinka jest jednoznacznie przepisywalna na cyrylicę,
a w łacince łatwiej kontrolować odmianę); generator wypisuje zdania cyrylicą i łacinką.
Używamy wymowy ekawskiej (standard w Serbii: mleko, devojka, videti).

Klasy semantyczne (ograniczenia selekcyjne - żeby zdania miały sens, np. "pas jede meso",
a nie "knjiga jede psa"):
    H - ludzie            A - zwierzęta         F - jedzenie          D - napoje
    O - przedmioty        C - ubrania           V - pojazdy           B - budynki i miejsca
    T - teksty, dzieła    M - muzyka (utwory)   I - instrumenty       P - rośliny
    N - pieniądze         K - części ciała
"""

# ---------------------------------------------------------------------------
# RZECZOWNIKI: 6 form = M. lp., D. lp., B. lp., M. lm., D. lm., B. lm.
# (mianownik - podmiot, biernik - dopełnienie bliższe, dopełniacz - wykonawca w stronie
# biernej "od strane + D.")
# ---------------------------------------------------------------------------
NOUNS = []


def _add(forms, gender, animate, classes, gloss, mass=False):
    NOUNS.append({"lemma": forms[0], "forms": tuple(forms), "gender": gender, "animate": animate,
                  "classes": classes, "gloss": gloss, "mass": mass})


def M(nom, gen, npl, gpl, classes, gloss, apl=None, mass=False):
    """Rodzaj męski. Żywotne (ludzie, zwierzęta) mają biernik l. poj. = dopełniacz."""
    animate = bool(set(classes) & set("HA"))
    _add([nom, gen, gen if animate else nom, npl, gpl, apl or npl[:-1] + "e"], "m", animate,
         classes, gloss, mass)


def Fa(nom, classes, gloss, gpl=None, mass=False):
    """Rodzaj żeński zakończony na -a (žena, žene, ženu, žene, žena, žene)."""
    s = nom[:-1]
    _add([nom, s + "e", s + "u", s + "e", gpl or nom, s + "e"], "f", bool(set(classes) & set("HA")),
         classes, gloss, mass)


def Fi(nom, classes, gloss):
    """Rodzaj żeński zakończony na spółgłoskę (stvar, stvari, stvar, stvari, stvari, stvari)."""
    _add([nom, nom + "i", nom, nom + "i", nom + "i", nom + "i"], "f", False, classes, gloss)


def N(nom, classes, gloss, gpl=None, mass=False):
    """Rodzaj nijaki (selo, sela, selo, sela, sela, sela)."""
    s = nom[:-1]
    _add([nom, s + "a", nom, s + "a", gpl or s + "a", s + "a"], "n", False, classes, gloss, mass)


# ludzie
M("čovek", "čoveka", "ljudi", "ljudi", "H", "człowiek")
M("prijatelj", "prijatelja", "prijatelji", "prijatelja", "H", "przyjaciel")
M("učitelj", "učitelja", "učitelji", "učitelja", "H", "nauczyciel")
M("student", "studenta", "studenti", "studenata", "H", "student")
M("lekar", "lekara", "lekari", "lekara", "H", "lekarz")
M("vojnik", "vojnika", "vojnici", "vojnika", "H", "żołnierz", apl="vojnike")
M("kralj", "kralja", "kraljevi", "kraljeva", "H", "król")
M("sused", "suseda", "susedi", "suseda", "H", "sąsiad")
M("dečak", "dečaka", "dečaci", "dečaka", "H", "chłopiec", apl="dečake")
M("lovac", "lovca", "lovci", "lovaca", "H", "myśliwy")
M("pisac", "pisca", "pisci", "pisaca", "H", "pisarz")
M("pevač", "pevača", "pevači", "pevača", "H", "piosenkarz")
M("radnik", "radnika", "radnici", "radnika", "H", "robotnik", apl="radnike")
M("seljak", "seljaka", "seljaci", "seljaka", "H", "chłop, rolnik", apl="seljake")
M("kuvar", "kuvara", "kuvari", "kuvara", "H", "kucharz")
M("vozač", "vozača", "vozači", "vozača", "H", "kierowca")
M("ribar", "ribara", "ribari", "ribara", "H", "rybak")
M("gost", "gosta", "gosti", "gostiju", "H", "gość")
M("lopov", "lopova", "lopovi", "lopova", "H", "złodziej")
M("policajac", "policajca", "policajci", "policajaca", "H", "policjant")
M("novinar", "novinara", "novinari", "novinara", "H", "dziennikarz")
M("sin", "sina", "sinovi", "sinova", "H", "syn")
M("otac", "oca", "očevi", "očeva", "H", "ojciec")
Fa("žena", "H", "kobieta")
Fa("devojka", "H", "dziewczyna", gpl="devojaka")
Fa("majka", "H", "matka", gpl="majki")
Fa("sestra", "H", "siostra", gpl="sestara")
Fa("učiteljica", "H", "nauczycielka")
# zwierzęta
M("pas", "psa", "psi", "pasa", "A", "pies")
M("konj", "konja", "konji", "konja", "A", "koń")
M("vuk", "vuka", "vukovi", "vukova", "A", "wilk")
M("medved", "medveda", "medvedi", "medveda", "A", "niedźwiedź")
M("orao", "orla", "orlovi", "orlova", "A", "orzeł")
M("lav", "lava", "lavovi", "lavova", "A", "lew")
M("zec", "zeca", "zečevi", "zečeva", "A", "zając")
Fa("mačka", "A", "kot", gpl="mačaka")
Fa("krava", "A", "krowa")
Fa("ptica", "A", "ptak")
Fa("riba", "AF", "ryba")
# jedzenie
M("hleb", "hleba", "hlebovi", "hlebova", "F", "chleb")
M("sir", "sira", "sirevi", "sireva", "F", "ser")
M("kolač", "kolača", "kolači", "kolača", "F", "ciasto")
M("krompir", "krompira", "krompiri", "krompira", "FP", "ziemniak")
Fa("jabuka", "FP", "jabłko")
N("jaje", "F", "jajko")
N("meso", "F", "mięso", mass=True)
N("jelo", "F", "potrawa")
N("voće", "F", "owoce", mass=True)
N("povrće", "F", "warzywa", mass=True)
# napoje
Fa("kafa", "D", "kawa", mass=True)
Fa("voda", "D", "woda", mass=True)
N("vino", "D", "wino")
N("mleko", "D", "mleko", mass=True)
M("čaj", "čaja", "čajevi", "čajeva", "D", "herbata")
N("pivo", "D", "piwo")
# przedmioty
M("nož", "noža", "noževi", "noževa", "O", "nóż")
M("sto", "stola", "stolovi", "stolova", "O", "stół")
M("telefon", "telefona", "telefoni", "telefona", "O", "telefon")
M("računar", "računara", "računari", "računara", "O", "komputer")
M("ključ", "ključa", "ključevi", "ključeva", "O", "klucz")
M("papir", "papira", "papiri", "papira", "O", "papier")
M("kamen", "kamena", "kamenovi", "kamenova", "O", "kamień", mass=True)
M("poklon", "poklona", "pokloni", "poklona", "O", "prezent")
M("prozor", "prozora", "prozori", "prozora", "O", "okno")
Fa("torba", "O", "torba", gpl="torbi")
Fa("olovka", "O", "ołówek", gpl="olovaka")
Fa("čaša", "O", "szklanka")
Fa("lopta", "O", "piłka", gpl="lopti")
Fa("gitara", "OI", "gitara")
N("ogledalo", "O", "lustro")
Fi("stvar", "O", "rzecz")
Fi("kost", "OK", "kość")
# ubrania
M("kaput", "kaputa", "kaputi", "kaputa", "C", "płaszcz")
M("šešir", "šešira", "šeširi", "šešira", "C", "kapelusz")
Fa("haljina", "C", "sukienka")
Fa("cipela", "C", "but")
# pojazdy
M("automobil", "automobila", "automobili", "automobila", "V", "samochód")
M("voz", "voza", "vozovi", "vozova", "V", "pociąg")
M("brod", "broda", "brodovi", "brodova", "V", "statek")
M("bicikl", "bicikla", "bicikli", "bicikala", "V", "rower")
# budynki i miejsca
M("grad", "grada", "gradovi", "gradova", "B", "miasto")
M("most", "mosta", "mostovi", "mostova", "B", "most")
M("zid", "zida", "zidovi", "zidova", "B", "mur")
M("dvorac", "dvorca", "dvorci", "dvoraca", "B", "zamek")
Fa("kuća", "B", "dom")
Fa("škola", "B", "szkoła")
Fa("crkva", "B", "cerkiew", gpl="crkava")
Fa("zgrada", "B", "budynek")
Fa("ulica", "B", "ulica")
N("selo", "B", "wieś")
N("pozorište", "B", "teatr")
N("jezero", "B", "jezioro")
# teksty i dzieła
Fa("knjiga", "T", "książka")
N("pismo", "T", "list", gpl="pisama")
M("zakon", "zakona", "zakoni", "zakona", "T", "ustawa")
M("ugovor", "ugovora", "ugovori", "ugovora", "T", "umowa")
M("film", "filma", "filmovi", "filmova", "T", "film")
Fa("pesma", "TM", "piosenka, wiersz", gpl="pesama")
Fa("slika", "TO", "obraz")
Fa("karta", "T", "bilet, mapa", gpl="karata")
Fi("vest", "T", "wiadomość")
Fi("reč", "T", "słowo")
# inne
M("cvet", "cveta", "cvetovi", "cvetova", "P", "kwiat")
M("novac", "novca", "novci", "novaca", "N", "pieniądze", mass=True)
M("zub", "zuba", "zubi", "zuba", "K", "ząb")
N("srce", "K", "serce", gpl="srca")


# ---------------------------------------------------------------------------
# CZASOWNIKI
#   inf - bezokolicznik, p1 - 1. os. l. poj. czasu teraźniejszego, p3 - 3. os. l. mn.,
#   asp - aspekt (impf - niedokonany, pf - dokonany),
#   typ - 'tr' przechodni, 'intr' nieprzechodni, 'refl' zwrotny (z "se"),
#   pp  - imiesłów bierny (trpni pridev) - tylko przechodnie, potrzebny do strony biernej,
#   subj / obj - dozwolone klasy semantyczne podmiotu i dopełnienia.
# Formy regularne (aoryst, imperfekt, imiesłów na -l, tryb rozkazujący) generator tworzy
# sam z bezokolicznika i czasu teraźniejszego; nieregularne są podane jawnie:
#   aor=(temat 1. os./lm., forma 2./3. os. lp.), lp=(imiesłów m. lp., temat na -l),
#   impf=temat imperfektu, imp=tryb rozkazujący 2. os. lp.
# ---------------------------------------------------------------------------
VERBS = []


def V(inf, p1, p3, asp, typ, pp, subj, obj, gloss, **irregular):
    VERBS.append({"inf": inf, "p1": p1, "p3": p3, "asp": asp, "typ": typ, "pp": pp,
                  "subj": subj, "obj": obj, "gloss": gloss, **irregular})


ANY = "HAFDOCVBTMIPNK"
THING = "AFDOCVBTMIPNK"

# --- przechodnie ---
V("čitati", "čitam", "čitaju", "impf", "tr", "čitan", "H", "T", "czytać")
V("pročitati", "pročitam", "pročitaju", "pf", "tr", "pročitan", "H", "T", "przeczytać")
V("pisati", "pišem", "pišu", "impf", "tr", "pisan", "H", "TM", "pisać")
V("napisati", "napišem", "napišu", "pf", "tr", "napisan", "H", "TM", "napisać")
V("videti", "vidim", "vide", "impf", "tr", "viđen", "HA", ANY, "widzieć", impf="viđa")
V("gledati", "gledam", "gledaju", "impf", "tr", "gledan", "HA", ANY, "oglądać, patrzeć na")
V("voleti", "volim", "vole", "impf", "tr", "voljen", "HA", ANY, "kochać, lubić", impf="volja")
V("mrzeti", "mrzim", "mrze", "impf", "tr", "mržen", "H", ANY, "nienawidzić", impf="mrža")
V("jesti", "jedem", "jedu", "impf", "tr", "jeden", "HA", "F", "jeść",
  aor=("jedo", "jede"), lp=("jeo", "jel"), impf="jeđa")
V("pojesti", "pojedem", "pojedu", "pf", "tr", "pojeden", "HA", "F", "zjeść",
  aor=("pojedo", "pojede"), lp=("pojeo", "pojel"))
V("piti", "pijem", "piju", "impf", "tr", "pijen", "HA", "D", "pić")
V("popiti", "popijem", "popiju", "pf", "tr", "popijen", "HA", "D", "wypić")
V("probati", "probam", "probaju", "pf", "tr", "proban", "H", "FD", "spróbować")
V("kupiti", "kupim", "kupe", "pf", "tr", "kupljen", "H", "AFDOCVBTIPK", "kupić")
V("kupovati", "kupujem", "kupuju", "impf", "tr", "kupovan", "H", "AFDOCVBTIP", "kupować")
V("prodati", "prodam", "prodaju", "pf", "tr", "prodat", "H", "AFDOCVBTIP", "sprzedać", aor=("prodado", "prodade"))
V("nositi", "nosim", "nose", "impf", "tr", "nošen", "HA", "AFDOCIPN", "nosić")
V("doneti", "donesem", "donesu", "pf", "tr", "donet", "HA", "FDOCTIPN", "przynieść", aor=("doneso", "donese"))
V("odneti", "odnesem", "odnesu", "pf", "tr", "odnet", "HA", "FDOCTIPN", "odnieść, zabrać", aor=("odneso", "odnese"))
V("izgubiti", "izgubim", "izgube", "pf", "tr", "izgubljen", "HA", "OCTINK", "zgubić")
V("naći", "nađem", "nađu", "pf", "tr", "nađen", "HA", ANY, "znaleźć", aor=("nađo", "nađe"), lp=("našao", "našl"))
V("tražiti", "tražim", "traže", "impf", "tr", "tražen", "HA", ANY, "szukać")
V("otvoriti", "otvorim", "otvore", "pf", "tr", "otvoren", "H", "OTB", "otworzyć")
V("zatvoriti", "zatvorim", "zatvore", "pf", "tr", "zatvoren", "H", "OTB", "zamknąć")
V("graditi", "gradim", "grade", "impf", "tr", "građen", "H", "BV", "budować", impf="građa")
V("sagraditi", "sagradim", "sagrade", "pf", "tr", "sagrađen", "H", "BV", "zbudować")
V("uništiti", "uništim", "unište", "pf", "tr", "uništen", "HA", THING, "zniszczyć")
V("prati", "perem", "peru", "impf", "tr", "pran", "H", "OCVFK", "myć, prać", impf="perija")
V("oprati", "operem", "operu", "pf", "tr", "opran", "H", "OCVFK", "umyć, wyprać")
V("kuvati", "kuvam", "kuvaju", "impf", "tr", "kuvan", "H", "FD", "gotować")
V("skuvati", "skuvam", "skuvaju", "pf", "tr", "skuvan", "H", "FD", "ugotować")
V("peći", "pečem", "peku", "impf", "tr", "pečen", "H", "F", "piec",
  aor=("peko", "peče"), lp=("pekao", "pekl"), impf="pecija", imp="peci")
V("seći", "sečem", "seku", "impf", "tr", "sečen", "H", "FOP", "kroić, ciąć",
  aor=("seko", "seče"), lp=("sekao", "sekl"), impf="secija", imp="seci")
V("hraniti", "hranim", "hrane", "impf", "tr", "hranjen", "H", "HA", "karmić")
V("loviti", "lovim", "love", "impf", "tr", "lovljen", "HA", "A", "łowić, polować na")
V("uhvatiti", "uhvatim", "uhvate", "pf", "tr", "uhvaćen", "HA", "HAO", "złapać")
V("ubiti", "ubijem", "ubiju", "pf", "tr", "ubijen", "HA", "HA", "zabić")
V("voziti", "vozim", "voze", "impf", "tr", "vožen", "H", "V", "prowadzić (pojazd)")
V("popraviti", "popravim", "poprave", "pf", "tr", "popravljen", "H", "OCVBIK", "naprawić")
V("slomiti", "slomim", "slome", "pf", "tr", "slomljen", "HA", "OIK", "złamać")
V("baciti", "bacim", "bace", "pf", "tr", "bačen", "H", "FOCTIN", "rzucić, wyrzucić")
V("dobiti", "dobijem", "dobiju", "pf", "tr", "dobijen", "H", "AFDOCVTIPN", "dostać")
V("dati", "dam", "daju", "pf", "tr", "dat", "H", "AFDOCTIPN", "dać", aor=("dado", "dade"))
V("poslati", "pošaljem", "pošalju", "pf", "tr", "poslat", "H", "OTN", "wysłać")
V("primiti", "primim", "prime", "pf", "tr", "primljen", "H", "HOTN", "otrzymać, przyjąć")
V("slušati", "slušam", "slušaju", "impf", "tr", "slušan", "HA", "HTM", "słuchać")
V("učiti", "učim", "uče", "impf", "tr", "učen", "H", "TM", "uczyć się (czegoś)")
V("naučiti", "naučim", "nauče", "pf", "tr", "naučen", "H", "TM", "nauczyć się")
V("crtati", "crtam", "crtaju", "impf", "tr", "crtan", "H", ANY, "rysować")
V("pevati", "pevam", "pevaju", "impf", "tr", "pevan", "H", "M", "śpiewać")
V("svirati", "sviram", "sviraju", "impf", "tr", "sviran", "H", "MI", "grać (na instrumencie)")
V("pozvati", "pozovem", "pozovu", "pf", "tr", "pozvan", "H", "H", "zaprosić, zawołać")
V("pozdraviti", "pozdravim", "pozdrave", "pf", "tr", "pozdravljen", "H", "H", "pozdrowić")
V("posetiti", "posetim", "posete", "pf", "tr", "posećen", "H", "HB", "odwiedzić")
V("čekati", "čekam", "čekaju", "impf", "tr", "čekan", "HA", "HAV", "czekać na")
V("braniti", "branim", "brane", "impf", "tr", "branjen", "HA", "HAB", "bronić")
V("napasti", "napadnem", "napadnu", "pf", "tr", "napadnut", "HA", "HAB", "zaatakować",
  aor=("napado", "napade"), lp=("napao", "napal"))
V("pobediti", "pobedim", "pobede", "pf", "tr", "pobeđen", "H", "H", "pokonać")
V("obući", "obučem", "obuku", "pf", "tr", "obučen", "H", "C", "włożyć (ubranie)",
  aor=("obuko", "obuče"), lp=("obukao", "obukl"), imp="obuci")
V("skinuti", "skinem", "skinu", "pf", "tr", "skinut", "H", "C", "zdjąć")
V("ostaviti", "ostavim", "ostave", "pf", "tr", "ostavljen", "HA", ANY, "zostawić")
V("čuvati", "čuvam", "čuvaju", "impf", "tr", "čuvan", "HA", ANY, "pilnować, przechowywać")
V("posaditi", "posadim", "posade", "pf", "tr", "posađen", "H", "P", "posadzić")
V("brati", "berem", "beru", "impf", "tr", "bran", "H", "P", "zrywać, zbierać", impf="berija")
V("platiti", "platim", "plate", "pf", "tr", "plaćen", "H", "FDOCTV", "zapłacić za")
V("zaraditi", "zaradim", "zarade", "pf", "tr", "zarađen", "H", "N", "zarobić")
V("brojati", "brojim", "broje", "impf", "tr", "brojan", "H", "HAONK", "liczyć", imp="broj")
V("pokazati", "pokažem", "pokažu", "pf", "tr", "pokazan", "H", ANY, "pokazać")
V("potpisati", "potpišem", "potpišu", "pf", "tr", "potpisan", "H", "T", "podpisać")
V("snimiti", "snimim", "snime", "pf", "tr", "snimljen", "H", "HATM", "nagrać, sfilmować")
V("znati", "znam", "znaju", "impf", "tr", "znan", "H", "HT", "znać")
V("zaboraviti", "zaboravim", "zaborave", "pf", "tr", "zaboravljen", "H", ANY, "zapomnieć")
V("ljubiti", "ljubim", "ljube", "impf", "tr", "ljubljen", "H", "HA", "całować")
V("lečiti", "lečim", "leče", "impf", "tr", "lečen", "H", "HAK", "leczyć")
V("pozajmiti", "pozajmim", "pozajme", "pf", "tr", "pozajmljen", "H", "OCVTIN", "pożyczyć")
V("očistiti", "očistim", "očiste", "pf", "tr", "očišćen", "H", "OCVBK", "wyczyścić")
V("zapaliti", "zapalim", "zapale", "pf", "tr", "zapaljen", "H", "OBV", "zapalić, podpalić")

# --- nieprzechodnie ---
V("spavati", "spavam", "spavaju", "impf", "intr", None, "HA", "", "spać")
V("trčati", "trčim", "trče", "impf", "intr", None, "HA", "", "biec, biegać")
V("hodati", "hodam", "hodaju", "impf", "intr", None, "HA", "", "chodzić")
V("sedeti", "sedim", "sede", "impf", "intr", None, "HA", "", "siedzieć", impf="seđa")
V("stajati", "stojim", "stoje", "impf", "intr", None, "HAOVB", "", "stać", imp="stoj")
V("ležati", "ležim", "leže", "impf", "intr", None, "HAO", "", "leżeć")
V("plakati", "plačem", "plaču", "impf", "intr", None, "H", "", "płakać")
V("plivati", "plivam", "plivaju", "impf", "intr", None, "HA", "", "pływać")
V("leteti", "letim", "lete", "impf", "intr", None, "A", "", "latać, lecieć", impf="leća")
V("raditi", "radim", "rade", "impf", "intr", None, "H", "", "pracować")
V("živeti", "živim", "žive", "impf", "intr", None, "HA", "", "żyć, mieszkać", impf="življa")
V("putovati", "putujem", "putuju", "impf", "intr", None, "H", "", "podróżować")
V("lajati", "lajem", "laju", "impf", "intr", None, "A", "", "szczekać")
V("ćutati", "ćutim", "ćute", "impf", "intr", None, "H", "", "milczeć")
V("kasniti", "kasnim", "kasne", "impf", "intr", None, "HV", "", "spóźniać się")
V("umreti", "umrem", "umru", "pf", "intr", None, "HA", "", "umrzeć", lp=("umro", "umrl"))
V("doći", "dođem", "dođu", "pf", "intr", None, "HAV", "", "przyjść, przyjechać",
  aor=("dođo", "dođe"), lp=("došao", "došl"))
V("otići", "odem", "odu", "pf", "intr", None, "HAV", "", "odejść, odjechać",
  aor=("otido", "otide"), lp=("otišao", "otišl"), imp="otidi")
V("ići", "idem", "idu", "impf", "intr", None, "HAV", "", "iść, jechać",
  aor=("iđo", "iđe"), lp=("išao", "išl"), impf="iđa")
V("pasti", "padnem", "padnu", "pf", "intr", None, "HAO", "", "upaść", aor=("pado", "pade"), lp=("pao", "pal"))
V("skočiti", "skočim", "skoče", "pf", "intr", None, "HA", "", "skoczyć")
V("pobeći", "pobegnem", "pobegnu", "pf", "intr", None, "HA", "", "uciec",
  aor=("pobego", "pobeže"), lp=("pobegao", "pobegl"))
V("zaspati", "zaspim", "zaspe", "pf", "intr", None, "HA", "", "zasnąć")
V("cvetati", "cvetam", "cvetaju", "impf", "intr", None, "P", "", "kwitnąć")

# --- zwrotne (z zaimkiem "se") ---
V("smejati", "smejem", "smeju", "impf", "refl", None, "H", "", "śmiać się")
V("nasmejati", "nasmejem", "nasmeju", "pf", "refl", None, "H", "", "zaśmiać się")
V("radovati", "radujem", "raduju", "impf", "refl", None, "HA", "", "cieszyć się")
V("bojati", "bojim", "boje", "impf", "refl", None, "HA", "", "bać się", imp="boj")
V("umivati", "umivam", "umivaju", "impf", "refl", None, "H", "", "myć się")
V("umiti", "umijem", "umiju", "pf", "refl", None, "H", "", "umyć się")
V("oblačiti", "oblačim", "oblače", "impf", "refl", None, "H", "", "ubierać się")
V("šetati", "šetam", "šetaju", "impf", "refl", None, "HA", "", "spacerować")
V("igrati", "igram", "igraju", "impf", "refl", None, "HA", "", "bawić się")
V("vratiti", "vratim", "vrate", "pf", "refl", None, "HAV", "", "wrócić")
V("probuditi", "probudim", "probude", "pf", "refl", None, "HA", "", "obudzić się")
V("kupati", "kupam", "kupaju", "impf", "refl", None, "HA", "", "kąpać się")
V("odmarati", "odmaram", "odmaraju", "impf", "refl", None, "HA", "", "odpoczywać")
V("odmoriti", "odmorim", "odmore", "pf", "refl", None, "HA", "", "odpocząć")
V("nadati", "nadam", "nadaju", "impf", "refl", None, "H", "", "mieć nadzieję")
V("svađati", "svađam", "svađaju", "impf", "refl", None, "H", "", "kłócić się")
V("popeti", "popnem", "popnu", "pf", "refl", None, "HA", "", "wspiąć się")
V("zaljubiti", "zaljubim", "zaljube", "pf", "refl", None, "H", "", "zakochać się")
V("osmehnuti", "osmehnem", "osmehnu", "pf", "refl", None, "H", "", "uśmiechnąć się")


# ---------------------------------------------------------------------------
# PRZYMIOTNIKI (forma określona, rodzaj męski, mianownik l. poj.), znaczenie, klasy rzeczowników,
# z którymi przymiotnik może się łączyć (zielony kwiat - tak, zielona wiadomość - nie)
# ---------------------------------------------------------------------------
ADJECTIVES = [
    ("novi", "nowy", "OCVBTMI"), ("stari", "stary", "HAOCVBTMI"), ("mladi", "młody", "HAP"), ("veliki", "duży", "HAFOCVBTIPKN"), ("mali", "mały", "HAFOCVBTIPKN"),
    ("lepi", "ładny", "HAOCVBTMIPK"), ("ružni", "brzydki", "HAOCVBTIPK"), ("dobri", "dobry", "HAFDOCVBTMIK"), ("loši", "zły, kiepski", "HAFDOCVBTMIK"),
    ("brzi", "szybki", "HAV"), ("spori", "wolny", "HAV"), ("visoki", "wysoki", "HAB"), ("niski", "niski", "HAB"),
    ("debeli", "gruby", "HAOT"), ("tanki", "cienki", "HAOCT"), ("crveni", "czerwony", "AFOCVBIP"), ("plavi", "niebieski", "AOCVBIP"),
    ("zeleni", "zielony", "AFOCVBIP"), ("žuti", "żółty", "AFOCVBIP"), ("crni", "czarny", "AFOCVBIP"), ("beli", "biały", "AFDOCVBIP"), ("sivi", "szary", "AOCVB"),
    ("smeđi", "brązowy", "AOCVIP"), ("topli", "ciepły", "FDOCB"), ("hladni", "zimny", "FDOB"), ("vrući", "gorący", "FD"),
    ("slatki", "słodki", "FD"), ("kiseli", "kwaśny", "FD"), ("slani", "słony", "F"), ("gorki", "gorzki", "FD"),
    ("ukusni", "smaczny", "FD"), ("sveži", "świeży", "FDP"), ("skupi", "drogi", "FDOCVBTI"), ("jeftini", "tani", "FDOCVBTI"),
    ("bogati", "bogaty", "H"), ("siromašni", "biedny", "H"), ("srećni", "szczęśliwy", "HA"), ("tužni", "smutny", "HAMT"),
    ("pametni", "mądry", "HA"), ("glupi", "głupi", "HA"), ("hrabri", "odważny", "H"), ("umorni", "zmęczony", "HA"),
    ("gladni", "głodny", "HA"), ("žedni", "spragniony", "HA"), ("zdravi", "zdrowy", "HAFK"), ("bolesni", "chory", "HAK"),
    ("jaki", "silny", "HAD"), ("slabi", "słaby", "HAD"), ("ljubazni", "uprzejmy", "H"), ("ljuti", "zły, gniewny", "HAF"),
    ("veseli", "wesoły", "HAM"), ("mirni", "spokojny", "HAB"), ("glasni", "głośny", "HAM"), ("tihi", "cichy", "HAMB"),
    ("čisti", "czysty", "OCVBDK"), ("prljavi", "brudny", "HAOCVBKN"), ("suvi", "suchy", "FOCP"), ("mokri", "mokry", "HAOC"),
    ("teški", "ciężki", "OTI"), ("laki", "lekki", "OTIN"), ("dugi", "długi", "OCTMB"), ("kratki", "krótki", "OCTM"),
    ("široki", "szeroki", "OCB"), ("uski", "wąski", "OCB"), ("duboki", "głęboki", "B"), ("plitki", "płytki", "B"),
    ("okrugli", "okrągły", "OF"), ("oštri", "ostry", "O"), ("meki", "miękki", "OCF"), ("tvrdi", "twardy", "OF"),
    ("prazni", "pusty", "OB"), ("puni", "pełny", "OB"), ("poznati", "znany", "HTMB"), ("nepoznati", "nieznany", "HTMB"),
    ("važni", "ważny", "HT"), ("zanimljivi", "ciekawy", "HTM"), ("dosadni", "nudny", "HTM"), ("opasni", "niebezpieczny", "HAV"),
    ("sigurni", "bezpieczny", "BV"), ("divlji", "dziki", "AP"), ("domaći", "domowy", "AFD"), ("strani", "obcy", "HTN"),
    ("drveni", "drewniany", "OBI"), ("kameni", "kamienny", "B"), ("zlatni", "złoty", "O"), ("srebrni", "srebrny", "O"),
    ("stakleni", "szklany", "O"), ("vuneni", "wełniany", "C"), ("kožni", "skórzany", "OC"), ("gvozdeni", "żelazny", "O"),
    ("moderni", "nowoczesny", "OCVBTM"), ("drevni", "starożytny", "BT"), ("savremeni", "współczesny", "TMB"),
    ("glavni", "główny", "HBT"), ("ogromni", "ogromny", "AOVB"), ("mračni", "ciemny", "B"), ("svetli", "jasny", "BC"),
    ("sjajni", "lśniący, świetny", "HOCTM"), ("čudni", "dziwny", "HATM"), ("obični", "zwykły", "HAOFT"), ("posebni", "szczególny", "HOT"),
    ("ozbiljni", "poważny", "HT"), ("vredni", "pracowity, cenny", "HOT"), ("lokalni", "lokalny", "HTFB"), ("retki", "rzadki", "APOT"),
]

# ---------------------------------------------------------------------------
# ZAIMKI I OKREŚLNIKI FRAZY RZECZOWNIKOWEJ
# Serbski NIE ma rodzajników. Ich funkcję pełnią: "jedan" (jeden - jak rodzajnik nieokreślony),
# "neki" (jakiś) oraz zaimki wskazujące "taj/ovaj/onaj" (jak rodzajnik określony).
#   (forma m. lp., temat, dopełniacz m. lp. jeśli nieregularny, tylko l. poj.?, rodzaj, opis)
# ---------------------------------------------------------------------------
DETERMINERS = [
    ("ovaj", "ov", None, False, "wskazujący", "ten (blisko mówiącego)"),
    ("taj", "t", None, False, "wskazujący", "ten (blisko słuchacza)"),
    ("onaj", "on", None, False, "wskazujący", "tamten"),
    ("moj", "moj", "mog", False, "dzierżawczy", "mój"),
    ("tvoj", "tvoj", "tvog", False, "dzierżawczy", "twój"),
    ("njegov", "njegov", None, False, "dzierżawczy", "jego"),
    ("njen", "njen", None, False, "dzierżawczy", "jej"),
    ("naš", "naš", None, False, "dzierżawczy", "nasz"),
    ("vaš", "vaš", None, False, "dzierżawczy", "wasz"),
    ("njihov", "njihov", None, False, "dzierżawczy", "ich"),
    ("jedan", "jedn", None, True, "nieokreślony", "jeden, pewien (≈ rodzajnik nieokreślony)"),
    ("neki", "nek", None, False, "nieokreślony", "jakiś, pewien"),
    ("svaki", "svak", None, True, "upowszechniający", "każdy"),
]
# zaimek dzierżawczy zwrotny - zastępuje moj/tvoj/naš/vaš, gdy posiadaczem jest podmiot
REFLEXIVE_POSSESSIVE = ("svoj", "svoj", "svog")
POSSESSIVE_OF = {("1", "sg"): "moj", ("2", "sg"): "tvoj", ("1", "pl"): "naš", ("2", "pl"): "vaš"}

# Zaimki osobowe: (osoba, liczba, rodzaj) -> mianownik, biernik (forma enklityczna), biernik pełny,
# dopełniacz
PRONOUNS = {
    ("1", "sg", "m"): ("ja", "me", "mene", "mene"), ("1", "sg", "f"): ("ja", "me", "mene", "mene"),
    ("2", "sg", "m"): ("ti", "te", "tebe", "tebe"), ("2", "sg", "f"): ("ti", "te", "tebe", "tebe"),
    ("3", "sg", "m"): ("on", "ga", "njega", "njega"), ("3", "sg", "f"): ("ona", "je", "nju", "nje"),
    ("3", "sg", "n"): ("ono", "ga", "njega", "njega"),
    ("1", "pl", "m"): ("mi", "nas", "nas", "nas"), ("1", "pl", "f"): ("mi", "nas", "nas", "nas"),
    ("2", "pl", "m"): ("vi", "vas", "vas", "vas"), ("2", "pl", "f"): ("vi", "vas", "vas", "vas"),
    ("3", "pl", "m"): ("oni", "ih", "njih", "njih"), ("3", "pl", "f"): ("one", "ih", "njih", "njih"),
    ("3", "pl", "n"): ("ona", "ih", "njih", "njih"),
}
