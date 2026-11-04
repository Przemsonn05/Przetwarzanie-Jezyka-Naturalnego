"""
Generuje sprawozdanie PDF (sprawozdanie/sprawozdanie.pdf) z wyników laboratoriów 1-4.

Wszystkie liczby, tabele i wykresy są wczytywane z plików w folderach dane/ i wyniki/,
więc po ponownym uruchomieniu laboratoriów wystarczy ponownie uruchomić ten skrypt.
Rysunki pomocnicze (schemat programu, zasada działania sieci Kohonena) są rysowane tutaj
i zapisywane w sprawozdanie/rysunki/.
"""
import csv
import datetime
import json
import math
import os
import re
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from lab02_entropia_huffman import entropy, huffman_codes, letter_statistics
from slownik import GLOSSARY
from sprawdz_wyniki import run_checks
from wspolne import ARTICLES_FILE, CLEAN_FILE, PARSED_FILE, RAW_FILE, RESULTS_DIR, SERBIAN_ALPHABET

AUTHOR = "Przemysław Kondrat"
OUTPUT = os.path.join("sprawozdanie", "sprawozdanie.pdf")
FIG_DIR = os.path.join("sprawozdanie", "rysunki")
R1, R2, R3, R4 = (os.path.join(RESULTS_DIR, f"lab0{i}") for i in range(1, 5))

# ---------------------------------------------------------------------------
# Czcionki (DejaVu Sans z matplotlib - obsługuje polskie znaki i cyrylicę)
# ---------------------------------------------------------------------------
FONT_DIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
for name, file in (("DejaVu", "DejaVuSans.ttf"), ("DejaVu-Bold", "DejaVuSans-Bold.ttf"),
                   ("DejaVu-Oblique", "DejaVuSans-Oblique.ttf"), ("DejaVuMono", "DejaVuSansMono.ttf")):
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, file)))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                              italic="DejaVu-Oblique", boldItalic="DejaVu-Bold")

ACCENT = colors.HexColor("#1f4e79")
LIGHT = colors.HexColor("#eef3f8")
BOX = colors.HexColor("#fff6e0")
BOX_EDGE = colors.HexColor("#e0a800")
GRID = colors.HexColor("#b8c4d0")

S = {
    "title": ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=22, leading=28,
                            alignment=TA_CENTER, textColor=ACCENT, spaceAfter=10),
    "subtitle": ParagraphStyle("subtitle", fontName="DejaVu", fontSize=13, leading=18,
                               alignment=TA_CENTER, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=16, leading=21, textColor=ACCENT,
                         spaceBefore=6, spaceAfter=8, keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=12, leading=16, textColor=ACCENT,
                         spaceBefore=10, spaceAfter=5, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="DejaVu-Bold", fontSize=10, leading=14, spaceBefore=6, spaceAfter=3,
                         keepWithNext=1),
    "body": ParagraphStyle("body", fontName="DejaVu", fontSize=9.5, leading=13.5, alignment=TA_JUSTIFY,
                           spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName="DejaVu", fontSize=9.5, leading=13.5, leftIndent=14,
                             bulletIndent=4, spaceAfter=2),
    "caption": ParagraphStyle("caption", fontName="DejaVu-Oblique", fontSize=8.5, leading=11,
                              alignment=TA_CENTER, textColor=colors.HexColor("#444444"), spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName="DejaVu", fontSize=7.5, leading=9.5),
    "box": ParagraphStyle("box", fontName="DejaVu", fontSize=9.2, leading=13, alignment=TA_JUSTIFY),
    "code": ParagraphStyle("code", fontName="DejaVuMono", fontSize=7.5, leading=10, leftIndent=8,
                           backColor=colors.HexColor("#f5f5f5"), borderPadding=4, spaceAfter=8),
    "formula": ParagraphStyle("formula", fontName="DejaVu", fontSize=10.5, leading=15,
                              alignment=TA_CENTER, spaceBefore=2, spaceAfter=6),
}

story = []
pending_headings = []  # nagłówki czekające na pierwszy element, z którym trafią na tę samą stronę
counters = {"fig": 0, "tab": 0}


# ---------------------------------------------------------------------------
# Pomocnicze funkcje do budowania dokumentu
# ---------------------------------------------------------------------------
def add(*flowables, keep=False):
    """Dodaje elementy do dokumentu; nagłówek nigdy nie zostaje sam na dole strony."""
    items = list(flowables)
    if pending_headings:
        items = pending_headings + items
        pending_headings.clear()
        keep = True
    if keep:
        story.append(KeepTogether(items))
    else:
        story.extend(items)


def p(text, style="body"):
    para = Paragraph(text, S[style])
    if style in ("h1", "h2", "h3"):
        pending_headings.append(para)
    else:
        add(para)


def bullets(items):
    for it in items:
        add(Paragraph(it, S["bullet"], bulletText="•"))


def steps(items):
    for i, it in enumerate(items, 1):
        add(Paragraph(it, S["bullet"], bulletText=f"{i}."))


def box(title, text):
    """Ramka z wyjaśnieniem 'w prostych słowach'."""
    content = [Paragraph(f"<b>{title}</b>", S["box"]), Spacer(1, 2), Paragraph(text, S["box"])]
    t = Table([[content]], colWidths=[17 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BOX),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, BOX_EDGE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    add(t, keep=True)
    story.append(Spacer(1, 6))


def table(rows, widths, caption=None, font_size=7.5, header_rows=1):
    cell = ParagraphStyle("c", parent=S["cell"], fontSize=font_size, leading=font_size + 2)
    head = ParagraphStyle("h", parent=cell, fontName="DejaVu-Bold", textColor=colors.white)
    data = [[Paragraph(str(c), head if i < header_rows else cell) for c in row]
            for i, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=header_rows, hAlign="CENTER")
    style = [("BACKGROUND", (0, 0), (-1, header_rows - 1), ACCENT),
             ("GRID", (0, 0), (-1, -1), 0.4, GRID),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    for i in range(header_rows, len(rows)):
        if (i - header_rows) % 2:
            style.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(style))
    parts = [t]
    if caption:
        counters["tab"] += 1
        parts.append(Paragraph(f"Tabela {counters['tab']}. {caption}", S["caption"]))
    # KeepTogether przenosi krótką tabelę w całości na następną stronę; tabelę dłuższą
    # niż strona dzieli normalnie, a nagłówek rozdziału zostaje z jej początkiem
    add(*parts, keep=True)
    story.append(Spacer(1, 4))


def figure(path, width_cm, caption):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    width = width_cm * cm
    counters["fig"] += 1
    add(Image(path, width=width, height=width * h / w),
        Paragraph(f"Rys. {counters['fig']}. {caption}", S["caption"]), keep=True)


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def gloss(word):
    """Serbski wyraz z polskim tłumaczeniem w nawiasie (jeśli jest w słowniku)."""
    g = GLOSSARY.get(word)
    return f"{word} <font color='#666666'>({g})</font>" if g else word


def fmt(x, nd=2):
    """Liczba w polskim zapisie: spacja tysięcy, przecinek dziesiętny."""
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


def num(x):
    return f"{x:,}".replace(",", " ")


def mono(text):
    return f"<font face='DejaVuMono'>{text}</font>"


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(colors.HexColor("#777777"))
    if doc.page > 1:
        canvas.drawString(2 * cm, 1.2 * cm, "Przetwarzanie języka naturalnego – sprawozdanie (język serbski)")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"strona {doc.page}")
    canvas.restoreState()


class ReportDoc(SimpleDocTemplate):
    """Dokument, który zbiera nagłówki h1/h2 do spisu treści."""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ("h1", "h2"):
            level = 0 if flowable.style.name == "h1" else 1
            self.notify("TOCEntry", (level, flowable.getPlainText(), self.page))


# ---------------------------------------------------------------------------
# Rysunki pomocnicze
# ---------------------------------------------------------------------------
def draw_pipeline(path):
    """Schemat: skąd biorą się dane i który skrypt co robi."""
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 4.6)
    ax.axis("off")

    def node(x, y, w, h, text, color):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=color, ec="#333333", lw=1))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8.5)

    def arrow(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.3, color="#333333"))

    node(0.1, 1.9, 1.6, 0.8, "Wikipedia\n(sr.wikipedia.org)", "#e8e8e8")
    node(2.2, 1.9, 1.8, 0.8, "lab01.py\npobranie + czyszczenie", "#cfe2f3")
    node(4.5, 3.2, 2.0, 0.8, "dane/oczyszczony_\nserbski.txt (korpus)", "#fff2cc")
    node(4.5, 0.6, 2.0, 0.8, "dane/surowy_\nserbski.txt (z interpunkcją)", "#fff2cc")
    node(7.1, 3.7, 1.9, 0.7, "lab02.py\nlitery, entropia, Huffman", "#cfe2f3")
    node(7.1, 2.75, 1.9, 0.7, "lab03.py\n90%, Zipf, graf", "#cfe2f3")
    node(7.1, 0.6, 1.9, 0.8, "lab04_parsowanie.py\nanaliza składniowa", "#cfe2f3")
    node(9.3, 0.6, 1.6, 0.8, "lab04_kohonen.py\nsieć Kohonena", "#cfe2f3")
    node(9.3, 2.2, 1.6, 1.1, "generuj_\nsprawozdanie.py\n→ PDF", "#d9ead3")
    arrow(1.7, 2.3, 2.2, 2.3)
    arrow(4.0, 2.5, 4.5, 3.5)
    arrow(4.0, 2.1, 4.5, 1.0)
    arrow(6.5, 3.7, 7.1, 4.0)
    arrow(6.5, 3.5, 7.1, 3.1)
    arrow(6.5, 1.0, 7.1, 1.0)
    arrow(9.0, 1.0, 9.3, 1.0)
    arrow(9.0, 4.0, 9.6, 3.3)
    arrow(9.0, 3.1, 9.3, 2.9)
    arrow(10.1, 1.4, 10.1, 2.2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def draw_som_idea(path, noun, components):
    """Ilustracja jednego kroku uczenia sieci Kohonena; `components` = [(czasownik, wartość), ...]."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    verbs = [v for v, _ in components] + ["…", "(razem 100 składowych)"]
    vals = [fmt(x, 2) if x else "0" for _, x in components] + ["…", ""]
    ax.text(5, 9.4, f"wektor rzeczownika {noun} ({GLOSSARY.get(noun, '')})", ha="center",
            fontsize=10, weight="bold")
    for i, (v, x) in enumerate(zip(verbs, vals)):
        y = 8.2 - i * 1.25
        ax.add_patch(FancyBboxPatch((1.5, y - 0.4), 4.2, 0.8, boxstyle="round,pad=0.03",
                                    fc="#fff2cc" if x not in ("0", "", "…") else "#f3f3f3", ec="#999999"))
        ax.text(1.8, y, v, va="center", fontsize=9)
        ax.text(5.4, y, x, va="center", ha="right", fontsize=9)
    ax.annotate("", xy=(9.8, 5.0), xytext=(6.2, 5.0), arrowprops=dict(arrowstyle="->", lw=2))
    ax.text(8.0, 5.4, "szukamy\nnajbardziej\npodobnego\nneuronu", ha="center", fontsize=8.5)

    ax = axes[1]
    n, bmu, sigma = 10, (6, 3), 1.6
    yy, xx = np.mgrid[0:n, 0:n]
    h = np.exp(-((yy - bmu[0]) ** 2 + (xx - bmu[1]) ** 2) / (2 * sigma ** 2))
    ax.imshow(h, cmap="Oranges", vmin=0, vmax=1.15)
    for i in range(n + 1):
        ax.axhline(i - 0.5, color="white", lw=1)
        ax.axvline(i - 0.5, color="white", lw=1)
    ax.add_patch(plt.Rectangle((bmu[1] - 0.5, bmu[0] - 0.5), 1, 1, fill=False, ec="#b2182b", lw=2.5))
    ax.annotate("neuron zwycięski (BMU):\nzmienia się najmocniej", xy=(bmu[1], bmu[0]), xytext=(6.3, 8.9),
                fontsize=8.5, arrowprops=dict(arrowstyle="->", color="#b2182b"), color="#b2182b")
    ax.text(5.6, 1.2, "sąsiedzi też się uczą,\ntym słabiej, im dalej\nod zwycięzcy", fontsize=8.5)
    ax.set_title("mapa 10 × 10 neuronów (kolor = siła zmiany wag)", fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Strona tytułowa, spis treści, wprowadzenie
# ---------------------------------------------------------------------------
def title_page():
    story.append(Spacer(1, 4.5 * cm))
    p("Przetwarzanie języka naturalnego", "title")
    p("Sprawozdanie z laboratoriów 1–4", "subtitle")
    p("Analiza korpusu języka serbskiego: statystyka liter, entropia i kodowanie Huffmana, "
      "prawo Zipfa, graf sąsiedztwa wyrazów, sieć Kohonena", "subtitle")
    story.append(Spacer(1, 3 * cm))
    rows = [["Autor", AUTHOR or "...................................................."],
            ["Język korpusu", "serbski (cyrylica, 30 liter)"],
            ["Źródło danych", "serbska Wikipedia (sr.wikipedia.org), API MediaWiki"],
            ["Język programowania", "Python 3 (numpy, scipy, matplotlib, networkx, stanza, reportlab)"],
            ["Data", datetime.date.today().strftime("%d.%m.%Y")]]
    t = Table([[Paragraph(f"<b>{a}</b>", S["body"]), Paragraph(b, S["body"])] for a, b in rows],
              colWidths=[4.5 * cm, 10.5 * cm], hAlign="CENTER")
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t)
    story.append(PageBreak())


def contents():
    p("Spis treści", "h1x")
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("toc0", fontName="DejaVu-Bold", fontSize=10.5, leading=16, leftIndent=0),
        ParagraphStyle("toc1", fontName="DejaVu", fontSize=9.5, leading=13, leftIndent=16),
    ]
    story.append(toc)
    story.append(PageBreak())


def introduction():
    articles = [a for a in open(ARTICLES_FILE, encoding="utf-8").read().split("\n") if a]
    p("Wprowadzenie", "h1")
    p("Celem laboratoriów było przeanalizowanie dużego tekstu w wybranym języku metodami "
      "przetwarzania języka naturalnego: od statystyki pojedynczych liter, przez statystykę "
      "wyrazów i ich sąsiedztwa, aż po sieć neuronową Kohonena, która grupuje rzeczowniki "
      "według czasowników, z którymi się łączą.")
    p("<b>Wybrany język: serbski.</b> Serbski zapisuje się m.in. cyrylicą, która ma dokładnie "
      "30 liter, a każda litera odpowiada jednej głosce (zasada „piši kao što govoriš” – pisz tak, "
      "jak mówisz). Dzięki temu łatwo sprawdzić, że w korpusie zostały wyłącznie litery alfabetu. "
      "Bogata odmiana wyrazów przez przypadki jest z kolei ciekawa przy badaniu prawa Zipfa "
      "i wymaga analizy składniowej w laboratorium 4.")
    p(f"<b>Dane:</b> {len(articles)} artykułów z serbskiej Wikipedii (ok. 1 mln znaków), "
      "głównie o historii i geografii Serbii i regionu.")
    p("Struktura programu", "h2")
    p("Każde laboratorium to osobny skrypt w Pythonie. Wspólne ustawienia (alfabet, ścieżki "
      f"do plików) są w {mono('wspolne.py')}, a {mono('uruchom_wszystko.py')} uruchamia "
      f"wszystkie etapy po kolei. Skrypt {mono('sprawdz_wyniki.py')} niezależnie przelicza "
      "wyniki i potwierdza ich poprawność (rozdział 5). Kod i wyniki są w repozytorium "
      "GitHub; opis uruchomienia jest w pliku README.md.")
    draw_pipeline(os.path.join(FIG_DIR, "schemat.png"))
    figure(os.path.join(FIG_DIR, "schemat.png"), 16.5, "Schemat działania programu – przepływ danych między skryptami.")

    p("Słowniczek pojęć", "h2")
    rows = [["Pojęcie", "Wyjaśnienie"],
            ["korpus", "duży zbiór tekstu przygotowany do analizy; u nas: same wyrazy z liter serbskiego alfabetu"],
            ["token / typ", "token to każde wystąpienie wyrazu w tekście, typ to różny wyraz "
                            "(w zdaniu „и ја и ти” są 4 tokeny i 3 typy)"],
            ["lemat", "forma podstawowa wyrazu, np. цркву, цркве, црквом → црква (cerkiew)"],
            ["prawdopodobieństwo p", "udział litery w tekście: p = liczba wystąpień / liczba wszystkich liter"],
            ["entropia H", "średnia liczba bitów na znak, poniżej której nie da się zakodować tekstu "
                           "(miara „nieprzewidywalności” tekstu)"],
            ["kod Huffmana", "kod, w którym częste znaki dostają krótkie ciągi bitów, a rzadkie długie; "
                             "najkrótszy możliwy kod przypisujący każdemu znakowi stały ciąg bitów"],
            ["kod prefiksowy", "żaden kod nie jest początkiem innego, więc tekst da się odczytać bez separatorów"],
            ["prawo Zipfa", "częstość wyrazu jest odwrotnie proporcjonalna do jego miejsca w rankingu: "
                            "2. wyraz występuje ok. 2 razy rzadziej niż 1., 3. ok. 3 razy rzadziej itd."],
            ["hapax legomenon", "wyraz, który występuje w tekście tylko raz"],
            ["graf, węzeł, krawędź", "węzły to wyrazy, krawędź łączy dwa wyrazy stojące w tekście obok siebie"],
            ["stopień węzła", "liczba krawędzi wychodzących z węzła, czyli liczba różnych sąsiadów wyrazu"],
            ["rdzeń grafu", "100 węzłów o największej liczbie sąsiadów"],
            ["czasownik przechodni", "czasownik, który łączy się z dopełnieniem w bierniku: "
                                     "„podjąć <i>decyzję</i>”, „zdobyć <i>miasto</i>”"],
            ["kolokacja", "częste połączenie wyrazów, u nas: czasownik + jego dopełnienie"],
            ["wektor cech", "opis obiektu listą liczb; u nas rzeczownik = 100 liczb (po jednej na czasownik)"],
            ["sieć Kohonena (SOM)", "sieć neuronowa ucząca się bez nauczyciela, która układa podobne "
                                    "obiekty blisko siebie na dwuwymiarowej mapie"],
            ["neuron zwycięski (BMU)", "neuron sieci najbardziej podobny do danego wektora wejściowego"]]
    table(rows, [4 * cm, 13 * cm], "Najważniejsze pojęcia używane w sprawozdaniu.", font_size=7.8)


# ---------------------------------------------------------------------------
# Lab 1
# ---------------------------------------------------------------------------
def lab1():
    story.append(PageBreak())
    raw = open(RAW_FILE, encoding="utf-8").read()
    clean = open(CLEAN_FILE, encoding="utf-8").read()
    articles = [a for a in open(ARTICLES_FILE, encoding="utf-8").read().split("\n") if a]
    words = clean.split()

    p("1. Laboratorium 1 – wybór języka i przygotowanie korpusu", "h1")
    p("<b>Zadanie:</b> wybrać język, pobrać duży tekst w tym języku i zostawić z niego sam korpus "
      "wyrazów: bez znaków specjalnych, interpunkcji, liczb i znaków spoza alfabetu.")
    box("W prostych słowach",
        "Komputer ma liczyć litery i wyrazy, więc tekst musi być „czysty”. Gdyby zostały w nim "
        "kropki, cyfry albo angielskie słowa, zafałszowałyby statystyki: kropka liczyłaby się jako "
        "litera, a „1389” jako wyraz. Dlatego zostawiamy tylko 30 małych liter serbskiej cyrylicy "
        "oddzielonych pojedynczymi spacjami.")

    p("1.1. Jak to zrobiliśmy", "h2")
    steps([
        f"<b>Pobranie tekstu.</b> Skrypt {mono('lab01.py')} pobiera artykuły z serbskiej Wikipedii "
        "przez oficjalne API (sam tekst, bez kodu strony), aż zbierze ok. 1 000 000 znaków. "
        "Pomija artykuły krótsze niż 5000 znaków (szablonowe zalążki) i duplikaty, a między "
        "zapytaniami czeka 1,5 s, żeby nie obciążać serwera.",
        "<b>Zamiana na małe litery</b> – „Србија” i „србија” to ten sam wyraz.",
        "<b>Usunięcie znaków spoza alfabetu</b> – każdy znak, który nie jest jedną z 30 liter "
        f"({mono(SERBIAN_ALPHABET)}), zamieniamy na spację. Jedno wyrażenie regularne "
        f"{mono('[^абв…ш]')} usuwa naraz cyfry, interpunkcję, symbole, łacinkę i grekę.",
        "<b>Zwinięcie spacji</b> – kilka spacji lub nowych linii z rzędu zamieniamy na jedną spację.",
        "<b>Kontrola</b> – skrypt liczy, ile znaków każdego rodzaju usunął, i sprawdza, "
        "czy w wyniku zostały tylko litery i spacje.",
    ])
    p(f"Pobrane artykuły ({len(articles)}): {', '.join(articles)}.")

    p("1.2. Wynik czyszczenia", "h2")
    removed = read_csv(os.path.join(R1, "usuniete_znaki.csv"))
    groups, examples = Counter(), defaultdict(list)
    for r in removed:
        groups[r["grupa"]] += int(r["liczba"])
        if r["znak"] not in (" ",) and len(examples[r["grupa"]]) < 12:
            examples[r["grupa"]].append(r["znak"].replace("\\n", "↵").replace("\\u202f", "␣"))
    rows = [["Grupa usuniętych znaków", "Liczba", "Przykłady (od najczęstszych)"]]
    for g, n in groups.most_common():
        rows.append([g, num(n), " ".join(examples[g]).replace("&", "&amp;").replace("<", "&lt;")])
    table(rows, [6 * cm, 2 * cm, 9 * cm], "Znaki usunięte z tekstu surowego. Białe znaki nie znikają: "
          "zamieniane są na pojedynczą spację oddzielającą wyrazy.")
    uppercase = sum(1 for ch in raw if ch.isupper() and ch.lower() in SERBIAN_ALPHABET)
    table([["Wielkość", "Wartość"],
           ["Liczba znaków tekstu surowego", num(len(raw))],
           ["Liczba znaków po oczyszczeniu", num(len(clean))],
           ["Wielkie litery zamienione na małe", num(uppercase)],
           ["Liczba wyrazów (tokenów)", num(len(words))],
           ["Liczba różnych wyrazów (typów)", num(len(set(words)))],
           ["Różne znaki w korpusie", f"{len(set(clean))} (30 liter + spacja)"]],
          [8 * cm, 5 * cm], "Korpus przed i po oczyszczeniu.")
    candidates = [m.group(0).strip() for m in re.finditer(r"[^.\n]{120,260}\.", raw)
                  if re.search(r"\d", m.group(0)) and re.search(r"[,()–-]", m.group(0))]
    frag = candidates[0] if candidates else raw[:260]
    p("Przykład – zdanie z tekstu surowego i to samo zdanie po oczyszczeniu:")
    add(Paragraph(frag, S["code"]))
    add(Paragraph(re.sub(r"\s+", " ", re.sub(f"[^{SERBIAN_ALPHABET}]", " ", frag.lower())).strip(),
                           S["code"]))
    p("<b>Wniosek:</b> w korpusie zostały wyłącznie wyrazy złożone z liter serbskiego alfabetu. "
      "Potwierdza to zarówno kontrola w lab01.py, jak i niezależne testy z rozdziału 5. "
      "Korpus zapisano w dane/oczyszczony_serbski.txt, a tekst surowy w dane/surowy_serbski.txt "
      "(potrzebny w lab 4, bo do analizy składniowej niezbędne są granice zdań).")


# ---------------------------------------------------------------------------
# Lab 2
# ---------------------------------------------------------------------------
def lab2():
    story.append(PageBreak())
    p("2. Laboratorium 2 – statystyka liter, entropia i kodowanie Huffmana", "h1")
    p("<b>Zadanie:</b> upewnić się, że został sam korpus; w tabeli podać udział procentowy "
      "każdej litery (prawdopodobieństwa); policzyć entropię tekstu; wyznaczyć ciągi kodowe "
      "Huffmana i porównać je z entropią.")
    box("W prostych słowach",
        "Komputer zapisuje każdą literę jako ciąg zer i jedynek (bitów). Gdyby każda z 30 liter "
        "miała kod tej samej długości, potrzebowalibyśmy 5 bitów na literę (2<super>5</super> = 32 ≥ 30). "
        "Litery nie są jednak równie częste: „а” pojawia się ponad 600 razy częściej niż „џ”. "
        "<b>Kod Huffmana</b> wykorzystuje to i daje częstym literom krótkie kody, a rzadkim długie, "
        "więc średnio wychodzi mniej bitów. <b>Entropia</b> mówi, ile bitów na literę wystarczy "
        "w najlepszym możliwym przypadku. Porównujemy więc, jak blisko tego ideału jest Huffman.")

    p("2.1. Jak to zrobiliśmy", "h2")
    steps([
        f"Skrypt {mono('lab02_entropia_huffman.py')} wczytuje korpus i jeszcze raz sprawdza, że nie "
        "ma w nim żadnego znaku spoza alfabetu i spacji. Wynik: brak obcych znaków, występują "
        "wszystkie 30 liter.",
        "Liczy wystąpienia każdej litery (słownik <i>Counter</i>) i dzieli przez liczbę wszystkich "
        "liter. Tak powstaje prawdopodobieństwo p każdej litery.",
        "Liczy entropię ze wzoru Shannona.",
        "Buduje kod Huffmana algorytmem z kolejką priorytetową (opis i przykład w p. 2.3).",
        "Koduje cały korpus, dekoduje go z powrotem i sprawdza, czy wyszedł identyczny tekst.",
        "Wszystko liczy w dwóch wariantach: same litery (30 symboli) oraz litery + spacja (31 symboli).",
    ])

    rows_l = read_csv(os.path.join(R2, "statystyka_litery.csv"))
    results = {}
    for key, fname in (("litery", "statystyka_litery.csv"), ("spacja", "statystyka_litery_spacja.csv")):
        rows = read_csv(os.path.join(R2, fname))
        n = sum(int(r["licznosc"]) for r in rows)
        probs = [int(r["licznosc"]) / n for r in rows]
        H = -sum(q * math.log2(q) for q in probs)
        L = sum(q * len(r["kod_huffmana"]) for q, r in zip(probs, rows))
        results[key] = (n, H, L, len(rows))
    n, H, L, k = results["litery"]

    p("2.2. Udział liter – prawdopodobieństwa", "h2")
    p(f"Korpus bez spacji zawiera {num(n)} liter. Tabela podaje dla każdej litery liczbę "
      "wystąpień, udział procentowy i prawdopodobieństwo p, a także „idealną” długość kodu "
      "−log<sub>2</sub> p i faktyczny kod Huffmana (omówione w p. 2.3–2.4).")
    data = [["Lp", "Litera", "Liczność", "Udział [%]", "p", "−log₂ p", "Kod Huffmana", "Dł. kodu"]]
    for i, r in enumerate(rows_l, 1):
        q = int(r["licznosc"]) / n
        data.append([i, f"<b>{r['znak']}</b>", num(int(r["licznosc"])), fmt(q * 100, 3), fmt(q, 5),
                     fmt(-math.log2(q), 3), mono(r["kod_huffmana"]), len(r["kod_huffmana"])])
    data.append(["", "<b>Suma</b>", num(n), "100,000", "1,00000", "", "", ""])
    table(data, [1 * cm, 1.4 * cm, 2 * cm, 2 * cm, 1.9 * cm, 1.7 * cm, 3.2 * cm, 1.4 * cm],
          "Udział liter w korpusie (bez spacji) i ich kody Huffmana.")
    figure(os.path.join(R2, "udzial_liter.png"), 16.5, "Udział procentowy liter w korpusie.")
    p("Rozkład jest bardzo nierównomierny: cztery samogłoski а, и, о, е to razem ok. 40% liter, "
      "a najrzadsze litery (ђ, ф, џ) mają poniżej 0,3% każda. Te różnice wykorzystuje kod Huffmana.")

    p("2.3. Entropia i kod Huffmana – jak działają (na małym przykładzie)", "h2")
    p("<b>Entropia</b> (C. Shannon, 1948) to średnia liczba bitów potrzebna na jeden znak:")
    p("H = − Σ p<sub>i</sub> · log<sub>2</sub> p<sub>i</sub>", "formula")
    p("Składnik −log<sub>2</sub> p<sub>i</sub> to „idealna” długość kodu znaku i: im rzadszy znak, "
      "tym więcej niesie informacji i tym dłuższy może być jego kod. Entropia jest średnią z tych "
      "długości, ważoną częstością znaków.")
    p("<b>Algorytm Huffmana</b> (D. Huffman, 1952): (1) każdy znak to osobny węzeł z wagą równą "
      "liczbie wystąpień; (2) bierzemy dwa węzły o najmniejszych wagach i łączymy je w nowy węzeł "
      "o sumie wag; (3) powtarzamy, aż zostanie jeden węzeł (korzeń drzewa). Kod znaku to droga "
      "od korzenia do znaku: krok w lewo = 0, w prawo = 1. Częste znaki są łączone na końcu, "
      "więc leżą blisko korzenia i mają krótkie kody.")
    word = "абракадабра"
    ex_stats, ex_n = letter_statistics(word)
    ex_steps = []
    ex_codes = huffman_codes(ex_stats, ex_steps)
    ex_H = entropy(ex_stats)
    ex_L = sum(q * len(ex_codes[ch]) for ch, _, q in ex_stats)
    p(f"Przykład dla słowa <b>„{word}”</b> ({ex_n} liter): "
      + ", ".join(f"{ch} × {c}" for ch, c, _ in ex_stats) + ".")
    rows = [["Krok", "Łączymy węzeł", "waga", "z węzłem", "waga", "Nowy węzeł (suma)"]]
    for i, (a, wa, b, wb, s) in enumerate(ex_steps, 1):
        rows.append([i, "{" + ", ".join(a) + "}", wa, "{" + ", ".join(b) + "}", wb, s])
    table(rows, [1.2 * cm, 3.5 * cm, 1.4 * cm, 3.5 * cm, 1.4 * cm, 3.5 * cm],
          f"Kolejne kroki algorytmu Huffmana dla słowa „{word}”.")
    rows = [["Litera", "Liczność", "p", "−log₂ p (ideał)", "Kod Huffmana", "Długość"]]
    for ch, c, q in ex_stats:
        rows.append([f"<b>{ch}</b>", c, fmt(q, 3), fmt(-math.log2(q), 3), mono(ex_codes[ch]), len(ex_codes[ch])])
    table(rows, [2 * cm, 2 * cm, 2 * cm, 3 * cm, 3 * cm, 2 * cm], f"Kody Huffmana dla słowa „{word}”.")
    fixed = math.ceil(math.log2(len(ex_stats)))
    p(f"Dla tego słowa entropia wynosi H = {fmt(ex_H, 3)} bit/znak, a średnia długość kodu "
      f"Huffmana L = {fmt(ex_L, 3)} bit/znak. Kod o stałej długości potrzebowałby {fixed} bitów "
      f"na znak ({ex_n * fixed} bitów na całe słowo), a Huffman potrzebuje "
      f"{sum(len(ex_codes[ch]) for ch in word)} bitów.")

    p("2.4. Wyniki dla całego korpusu", "h2")
    data = [["Wariant", "n", "H [bit]", "H<sub>max</sub> = log₂ n", "Redund.",
             "L Huffmana [bit]", "L − H", "H / L", "Kod stały"]]
    for key, label in (("litery", "same litery"), ("spacja", "litery + spacja")):
        n_, H_, L_, k_ = results[key]
        hmax = math.log2(k_)
        data.append([label, k_, fmt(H_, 4), fmt(hmax, 4), f"{fmt((1 - H_ / hmax) * 100)}%",
                     fmt(L_, 4), fmt(L_ - H_, 4), f"{fmt(H_ / L_ * 100)}%", f"{math.ceil(hmax)} bit"])
    table(data, [2.6 * cm, 0.9 * cm, 1.6 * cm, 2.3 * cm, 1.7 * cm, 2.6 * cm, 1.5 * cm, 1.7 * cm, 1.6 * cm],
          "Entropia a średnia długość kodu Huffmana. H<sub>max</sub> – entropia, gdyby wszystkie "
          "znaki były równie częste; redundancja = 1 − H/H<sub>max</sub>.")
    figure(os.path.join(R2, "dlugosci_kodow.png"), 16.5,
           "Długość kodu Huffmana każdej litery w porównaniu z długością idealną −log₂ p.")
    p("<b>Wnioski.</b>", "h3")
    bullets([
        f"Średnia długość kodu Huffmana ({fmt(L, 4)} bit) jest tylko o {fmt(L - H, 4)} bitu większa "
        f"od entropii ({fmt(H, 4)} bit). Efektywność kodu wynosi {fmt(H / L * 100)}%, a warunek "
        "H ≤ L &lt; H + 1 z twierdzenia Shannona o kodowaniu jest spełniony.",
        "Różnica L − H bierze się stąd, że kod musi mieć całkowitą liczbę bitów, a −log<sub>2</sub> p "
        "zwykle nie jest liczbą całkowitą. Na wykresie słupki Huffmana są raz trochę wyższe, "
        "raz trochę niższe od ideału.",
        f"Względem kodu o stałej długości (5 bitów) Huffman skraca zapis tekstu o "
        f"{fmt((1 - L / 5) * 100, 1)}%.",
        f"Redundancja języka na poziomie pojedynczych liter wynosi ok. "
        f"{fmt((1 - H / math.log2(k)) * 100, 1)}%: tyle „zbędnej” informacji wynika "
        "z nierównej częstości liter.",
        "Kod jest poprawny: zakodowany i zdekodowany korpus jest identyczny z oryginałem.",
    ])


# ---------------------------------------------------------------------------
# Lab 3
# ---------------------------------------------------------------------------
def lab3():
    story.append(PageBreak())
    p("3. Laboratorium 3 – pokrycie tekstu, prawo Zipfa, graf sąsiedztwa", "h1")
    p("<b>Zadanie:</b> znaleźć wyrazy, które pokrywają 90% tekstu; sprawdzić prawo Zipfa; "
      "zbudować graf wyrazów sąsiadujących, zliczyć krawędzie wychodzące z każdego węzła "
      "i wyznaczyć rdzeń, czyli 100 wyrazów o największej liczbie sąsiadów.")
    zipf = read_csv(os.path.join(R3, "zipf.csv"))
    freqs = np.array([int(r["licznosc"]) for r in zipf], dtype=float)
    total, types = int(freqs.sum()), len(freqs)
    cum = np.cumsum(freqs) / total
    k90 = int(np.searchsorted(cum, 0.9) + 1)
    hapax = int(np.sum(freqs == 1))

    p("3.1. Wyrazy pokrywające 90% tekstu", "h2")
    box("W prostych słowach",
        "Ustawiamy wyrazy od najczęstszego i dodajemy ich udziały w tekście: „и” to 4,8% tekstu, "
        "„и” + „је” to już 8,8%, i tak dalej. Szukamy momentu, w którym suma przekroczy 90%. "
        "Liczba wyrazów do tego miejsca mówi, ile słów trzeba znać, żeby rozumieć 90% słów "
        "w tekście.")
    p(f"Korpus zawiera {num(total)} wyrazów (tokenów) i {num(types)} różnych wyrazów (typów). "
      f"<b>Do pokrycia 90% tekstu potrzeba {num(k90)} najczęstszych wyrazów</b>, czyli "
      f"{fmt(k90 / types * 100)}% słownika. Aż {num(hapax)} wyrazów ({fmt(hapax / types * 100, 1)}%) "
      "występuje tylko raz.")
    data = [["Pokrycie tekstu", "Liczba najczęstszych wyrazów", "Udział w słowniku"]]
    for lvl in (0.25, 0.5, 0.75, 0.8, 0.9, 0.95, 0.99):
        k = int(np.searchsorted(cum, lvl - 1e-12) + 1)
        data.append([f"<b>{int(lvl * 100)}%</b>" if lvl == 0.9 else f"{int(lvl * 100)}%", num(k),
                     f"{fmt(k / types * 100)}%"])
    table(data, [4 * cm, 5 * cm, 4 * cm], "Liczba najczęstszych wyrazów potrzebna do pokrycia danej części tekstu.")
    top = read_csv(os.path.join(R3, "wyrazy_pokrycie_90.csv"))[:20]
    data = [["Ranga", "Wyraz", "Liczność", "Udział [%]", "Skum. [%]"] * 2]
    for i in range(10):
        a, b = top[i], top[i + 10]
        data.append([a["ranga"], gloss(a["wyraz"]), a["licznosc"], a["udzial_procent"].replace(".", ","),
                     a["pokrycie_skumulowane_procent"].replace(".", ","),
                     b["ranga"], gloss(b["wyraz"]), b["licznosc"], b["udzial_procent"].replace(".", ","),
                     b["pokrycie_skumulowane_procent"].replace(".", ",")])
    table(data, [0.9 * cm, 2.9 * cm, 1.2 * cm, 1.3 * cm, 1.4 * cm] * 2,
          f"20 najczęstszych wyrazów (z polskim znaczeniem). Pełna lista {num(k90)} wyrazów: "
          "wyniki/lab03/wyrazy_pokrycie_90.csv.", font_size=6.8)
    figure(os.path.join(R3, "pokrycie_tekstu.png"), 12.5, "Pokrycie tekstu przez najczęstsze wyrazy.")
    p("<b>Wniosek:</b> krzywa rośnie bardzo szybko na początku: zaledwie 19 wyrazów (głównie "
      "spójniki i przyimki) pokrywa 25% tekstu, a 455 wyrazów – połowę. Potem rośnie powoli, "
      "bo pozostała część tekstu składa się z rzadkich wyrazów, m.in. różnych form "
      "odmiany tego samego słowa i nazw własnych.")

    p("3.2. Prawo Zipfa", "h2")
    ranks = np.arange(1, types + 1)
    slope, c = np.polyfit(np.log10(ranks), np.log10(freqs), 1)
    pred = c + slope * np.log10(ranks)
    r2 = 1 - np.sum((np.log10(freqs) - pred) ** 2) / np.sum((np.log10(freqs) - np.log10(freqs).mean()) ** 2)
    m = freqs >= 2
    s2 = -np.polyfit(np.log10(ranks[m]), np.log10(freqs[m]), 1)[0]
    s = -slope
    box("W prostych słowach",
        "George Zipf zauważył, że w każdym dużym tekście drugi najczęstszy wyraz występuje mniej "
        "więcej 2 razy rzadziej niż pierwszy, trzeci 3 razy rzadziej itd. Wzorem: f(r) ≈ C / r, "
        "gdzie r to miejsce w rankingu, a f to częstość. Na wykresie w skali logarytmicznej "
        "(log-log) taka zależność jest linią prostą o nachyleniu −1.")
    p("Ogólniej: f(r) = C / r<super>s</super>. Po zlogarytmowaniu log f = log C − s · log r, "
      "więc s i C wyznaczyliśmy regresją liniową (metodą najmniejszych kwadratów, "
      f"{mono('numpy.polyfit')}) na punktach (log r, log f).")
    table([["Dopasowanie", "Wykładnik s", "C", "R²"],
           [f"wszystkie wyrazy ({num(types)})", f"<b>{fmt(s, 4)}</b>", fmt(10 ** c, 1), fmt(r2, 4)],
           [f"bez hapaksów, f ≥ 2 ({num(int(m.sum()))})", fmt(s2, 4), "", ""]],
          [6 * cm, 3 * cm, 3 * cm, 2.5 * cm], "Parametry prawa Zipfa dla korpusu (R² – jakość dopasowania, 1 = idealne).")
    data = [["Ranga r", "Wyraz", "f(r)", "r · f(r)", "f z prawa Zipfa (f₁ / r)"]]
    for rk in (1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000):
        r = zipf[rk - 1]
        data.append([rk, gloss(r["wyraz"]), r["licznosc"], num(int(r["ranga_razy_licznosc"])),
                     fmt(freqs[0] / rk, 1)])
    table(data, [2 * cm, 5 * cm, 2 * cm, 2.5 * cm, 4 * cm],
          "Sprawdzenie prawa Zipfa dla wybranych rang: iloczyn r · f(r) powinien być w przybliżeniu stały.")
    figure(os.path.join(R3, "prawo_zipfa.png"), 16.5,
           "Prawo Zipfa: częstość w funkcji rangi w skali log-log (po lewej) i iloczyn r · f(r) (po prawej).")
    p(f"<b>Wniosek:</b> punkty układają się niemal na prostej (R² = {fmt(r2, 3)}), a wykładnik "
      f"s = {fmt(s, 2)} jest bardzo bliski 1, więc <b>korpus spełnia prawo Zipfa</b>. Odchylenia "
      "widać dla kilku pierwszych rang (bardzo częste słowa funkcyjne и, у, је) i w ogonie, gdzie "
      "tysiące wyrazów mają tę samą małą częstość (poziome „schodki”). Lekkie spłaszczenie (s &lt; 1) "
      "wynika z odmiany wyrazów w serbskim: србија, србије, србији, србију liczone są osobno. "
      "Ciekawostka: na 10 razy mniejszym korpusie (100 tys. znaków) wyszło s = 0,68. Prawo Zipfa "
      "dobrze widać dopiero na dużym tekście.")

    p("3.3. Graf wyrazów sąsiadujących i jego rdzeń", "h2")
    words = open(CLEAN_FILE, encoding="utf-8").read().split()
    directed = {e for e in zip(words, words[1:]) if e[0] != e[1]}
    undirected = {tuple(sorted(e)) for e in directed}
    deg = read_csv(os.path.join(R3, "stopnie_wezlow.csv"))
    degrees = np.array([int(r["liczba_sasiadow"]) for r in deg])
    box("W prostych słowach",
        "Każdy wyraz to punkt (węzeł). Jeśli dwa wyrazy choć raz stoją w tekście obok siebie, "
        "łączymy je kreską (krawędzią). Dla fragmentu „кнез лазар је подигао цркву” powstają "
        "krawędzie кнез–лазар, лазар–је, је–подигао, подигао–цркву. Wyraz, z którego wychodzi "
        "najwięcej krawędzi, sąsiaduje z największą liczbą różnych wyrazów, więc jest „centralny” "
        "dla języka. 100 takich wyrazów to rdzeń grafu.")
    p("Krawędzie zliczyliśmy na dwa sposoby. <b>Krawędzie wychodzące</b> z wyrazu w to różne "
      "wyrazy występujące bezpośrednio po nim; <b>wchodzące</b> to wyrazy występujące "
      "bezpośrednio przed nim. Liczba wszystkich różnych sąsiadów to liczba krawędzi "
      "wychodzących z węzła w grafie nieskierowanym; według niej wyznaczyliśmy rdzeń. "
      f"Graf zbudowano w {mono('lab03_wyrazy_zipf_graf.py')} (słowniki zbiorów sąsiadów, "
      "zapis do formatu GEXF biblioteką networkx).")
    table([["Wielkość", "Wartość"],
           ["Liczba węzłów (różnych wyrazów)", num(len(deg))],
           ["Liczba krawędzi skierowanych (a → b)", num(len(directed))],
           ["Liczba krawędzi nieskierowanych (a — b)", num(len(undirected))],
           ["Średnia / mediana liczby sąsiadów", f"{fmt(degrees.mean())} / {int(np.median(degrees))}"],
           ["Maksymalna liczba sąsiadów", f"{num(int(degrees.max()))} ({gloss(deg[0]['wyraz'])})"]],
          [8 * cm, 5 * cm], "Podstawowe parametry grafu sąsiedztwa.")
    core = read_csv(os.path.join(R3, "rdzen_100.csv"))
    data = [["Lp", "Wyraz", "Sąs.", "Wych.", "Wch.", "Częst."] * 2]
    for i in range(50):
        a, b = core[i], core[i + 50]
        data.append([a["lp"], gloss(a["wyraz"]), a["liczba_sasiadow"], a["krawedzie_wychodzace"],
                     a["krawedzie_wchodzace"], a["licznosc"],
                     b["lp"], gloss(b["wyraz"]), b["liczba_sasiadow"], b["krawedzie_wychodzace"],
                     b["krawedzie_wchodzace"], b["licznosc"]])
    table(data, [0.8 * cm, 3.5 * cm, 1 * cm, 1 * cm, 1 * cm, 1.1 * cm] * 2,
          "Rdzeń grafu – 100 wyrazów o największej liczbie sąsiadów (Sąs. – różni sąsiedzi, "
          "Wych./Wch. – krawędzie wychodzące/wchodzące, Częst. – liczba wystąpień).", font_size=6.3)
    core_words = [r["wyraz"] for r in core]
    top100 = {r["wyraz"] for r in zipf[:100]}
    by_out = {r["wyraz"] for r in sorted(deg, key=lambda r: -int(r["krawedzie_wychodzace"]))[:100]}
    cover = sum(int(r["licznosc"]) for r in core) / total
    figure(os.path.join(R3, "rdzen_grafu.png"), 14.5,
           "Podgraf rdzenia: wielkość węzła odpowiada liczbie sąsiadów w całym grafie, "
           "grubość krawędzi – liczbie wystąpień pary.")
    figure(os.path.join(R3, "rozklad_stopni.png"), 10,
           "Rozkład liczby sąsiadów (skala log-log): bardzo wiele wyrazów ma 1–2 sąsiadów, nieliczne – tysiące.")
    p("<b>Wnioski.</b>", "h3")
    bullets([
        "Rdzeń tworzą głównie <b>słowa funkcyjne</b>: spójniki (и, а, али), przyimki (у, на, од, са, за), "
        "formy czasownika бити (је, су) i zaimki. Łączą się one z niemal każdym wyrazem, "
        "dlatego mają tysiące sąsiadów.",
        f"Wyrazy rdzenia to {fmt(cover * 100, 1)}% wszystkich wyrazów tekstu, a {len(set(core_words) & top100)} "
        "ze 100 z nich należy też do 100 najczęstszych wyrazów: im częstszy wyraz, tym więcej ma sąsiadów.",
        f"Ranking według samych krawędzi wychodzących (skierowanych) daje rdzeń wspólny z powyższym "
        f"w {len(by_out & set(core_words))} wyrazach na 100, więc wybór sposobu liczenia krawędzi "
        "niewiele zmienia.",
        "Rozkład liczby sąsiadów jest potęgowy (prosta w skali log-log): mediana to 2 sąsiadów, "
        "a maksimum to kilka tysięcy. Taki graf nazywa się <b>bezskalowym</b>: kilka węzłów-hubów "
        "łączy całą sieć, podobnie jak w sieciach społecznych czy w internecie.",
    ])


# ---------------------------------------------------------------------------
# Lab 4
# ---------------------------------------------------------------------------
def lab4():
    story.append(PageBreak())
    summ = json.load(open(os.path.join(R4, "podsumowanie.json"), encoding="utf-8"))
    A = summ["warianty"]["A"]
    som = summ["som"]

    p("4. Laboratorium 4 – sieć Kohonena: rzeczowniki w przestrzeni czasowników przechodnich", "h1")
    p("<b>Zadanie:</b> wybrać 50 rzeczowników i 100 czasowników przechodnich. Dla każdego "
      "rzeczownika wygenerować wektor o 100 składowych (kolokacje z czasownikami) – to zbiór "
      "treningowy. Nauczyć na nim sieć Kohonena i przedstawić rzeczowniki w 100-wymiarowej "
      "przestrzeni czasowników. Zbadać, jak wynik zależy od wyboru czasowników, np. biorąc "
      "100 najczęstszych czasowników korpusu.")
    box("W prostych słowach",
        "Rzeczownik można poznać po tym, z jakimi czasownikami się łączy. „Decyzję” i „ustawę” "
        "się <i>podejmuje/uchwala</i> (донети), „wojnę” i „walkę” się <i>prowadzi</i> (водити), "
        "a „miasto” i „medal” się <i>zdobywa</i> (освојити). Zapisujemy więc dla każdego rzeczownika "
        "100 liczb: ile razy był dopełnieniem każdego ze 100 czasowników. Te 100 liczb to punkt "
        "w przestrzeni 100-wymiarowej, której osiami są czasowniki. Człowiek nie zobaczy 100 wymiarów, "
        "więc sieć Kohonena „spłaszcza” tę przestrzeń do mapy 10 × 10, tak żeby rzeczowniki "
        "o podobnych wektorach leżały obok siebie.")

    p("4.1. Analiza składniowa korpusu", "h2")
    p("Żeby wiedzieć, które czasowniki są przechodnie i który rzeczownik jest dopełnieniem którego "
      "czasownika, potrzebna jest analiza gramatyczna zdań. Użyto biblioteki <b>stanza</b> "
      "(Stanford NLP) z modelem języka serbskiego (treebank UD Serbian-SET, standard Universal "
      f"Dependencies). Skrypt {mono('lab04_parsowanie.py')}:")
    steps([
        "wczytuje tekst surowy z lab 1 (z interpunkcją, bo potrzebne są granice zdań),",
        "zamienia cyrylicę na łacinkę, bo model był uczony na serbskiej łacince "
        "(odpowiedniość liter jest 1:1, np. љ → lj, њ → nj, џ → dž),",
        "dla każdego wyrazu ustala część mowy, lemat (formę podstawową) i wyraz nadrzędny wraz "
        "z relacją, np. <i>obj</i> = dopełnienie bliższe,",
        "przepisuje wynik z powrotem na cyrylicę i zapisuje go do dane/korpus_sparsowany.tsv.gz.",
    ])
    p(f"Wynik: {num(summ['zdania'])} zdań, {num(summ['tokeny'])} tokenów (razem z interpunkcją), "
      f"{num(summ['rozne_czasowniki'])} różnych czasowników i {num(summ['rozne_rzeczowniki'])} różnych "
      f"rzeczowników, <b>{num(summ['relacje_obj'])} par czasownik → dopełnienie rzeczownikowe</b>. "
      "Przykład: w zdaniu „Кнез Лазар је подигао цркву и водио војску” parser znajduje pary "
      "obj(подићи, црква) i obj(водити, војска). Dzięki lematyzacji formy цркву, цркве, "
      "црквом liczą się jako jeden rzeczownik црква.")

    p("4.2. Wybór 100 czasowników przechodnich i 50 rzeczowników", "h2")
    steps([
        "Dla każdego czasownika liczymy, ile razy ma w korpusie dopełnienie rzeczownikowe. "
        "Liczymy też dopełnienia współrzędne: w „подигао цркву и кућу” oba rzeczowniki są "
        "dopełnieniami.",
        "Czasownik uznajemy za <b>przechodni</b>, jeśli dopełnienie ma w co najmniej 20% wystąpień. "
        "Odrzuca to błędy parsera, np. постати (stać się; „постао је краљ” – „został królem”), "
        "постојати (istnieć) i вратити (najczęściej zwrotne вратити се – wrócić).",
        "Pomijamy czasowniki posiłkowe i modalne (бити, хтети, моћи, морати, требати).",
        "Bierzemy <b>100 czasowników</b> o największej liczbie dopełnień, a potem <b>50 rzeczowników</b>, "
        "które najczęściej są dopełnieniem tych czasowników. Dzięki temu każdy wektor ma dane.",
    ])
    verbs = read_csv(os.path.join(R4, "czasowniki_przechodnie.csv"))
    data = [["Lp", "Czasownik", "Dop.", "Wyst.", "Lp", "Czasownik", "Dop.", "Wyst."]]
    for i in range(50):
        a, b = verbs[i], verbs[i + 50]
        data.append([a["lp"], gloss(a["czasownik"]), a["dopelnienia_rzeczownikowe"], a["wystapienia"],
                     b["lp"], gloss(b["czasownik"]), b["dopelnienia_rzeczownikowe"], b["wystapienia"]])
    table(data, [0.8 * cm, 5.2 * cm, 1.1 * cm, 1.2 * cm] * 2,
          "100 wybranych czasowników przechodnich (Dop. – liczba dopełnień rzeczownikowych, "
          "Wyst. – liczba wystąpień czasownika).", font_size=6.5)
    nouns = read_csv(os.path.join(R4, "rzeczowniki.csv"))
    data = [["Lp", "Rzeczownik", "Jako dop.", "Wyst."] * 2]
    for i in range(25):
        a, b = nouns[i], nouns[i + 25]
        data.append([a["lp"], gloss(a["rzeczownik"]), a["liczba_jako_dopelnienie"], a["wystapienia"],
                     b["lp"], gloss(b["rzeczownik"]), b["liczba_jako_dopelnienie"], b["wystapienia"]])
    table(data, [0.8 * cm, 5 * cm, 1.4 * cm, 1.2 * cm] * 2,
          "50 wybranych rzeczowników (Jako dop. – ile razy były dopełnieniem wybranych czasowników).",
          font_size=6.8)

    p("4.3. Zbiór treningowy – wektory o 100 składowych", "h2")
    train = read_csv(os.path.join(R4, "wariant_A_zbior_treningowy.csv"))
    example = next(r for r in train if r["rzeczownik"] == "одлука")
    nz = sorted(((k, int(v)) for k, v in example.items() if k != "rzeczownik" and int(v) > 0), key=lambda x: -x[1])
    p("Każdy rzeczownik zamieniamy na wektor x = (x<sub>1</sub>, …, x<sub>100</sub>), gdzie "
      "x<sub>j</sub> to liczba wystąpień rzeczownika jako dopełnienia j-tego czasownika. Przykład – "
      f"wektor rzeczownika <b>одлука</b> (decyzja) ma {len(nz)} niezerowe składowe: "
      + ", ".join(f"{gloss(k)} = {v}" for k, v in nz) + "; pozostałe składowe to zera.")
    p(f"Cała macierz 50 × 100 zawiera {num(A['suma_kolokacji'])} kolokacji; niezerowych jest "
      f"{num(A['niezerowe'])} pól ({fmt(A['gestosc'] * 100, 1)}%), bo każdy rzeczownik łączy się "
      "tylko z kilkoma czasownikami. Przed uczeniem wektory przygotowano w dwóch krokach:")
    bullets([
        "<b>log(1 + x)</b> – zmniejsza wpływ bardzo częstych par (np. одлука + донети = 21), "
        "żeby jedna para nie zdominowała wektora,",
        "<b>normalizacja do długości 1</b> – porównujemy „profil” czasowników, a nie to, jak często "
        "rzeczownik w ogóle występuje (rzadki i częsty rzeczownik z tym samym profilem są podobne).",
    ])
    figure(os.path.join(R4, "wariant_A_macierz.png"), 17,
           "Zbiór treningowy: 50 rzeczowników (wiersze) × 100 czasowników (kolumny); "
           "ciemniejszy kolor = więcej kolokacji.")

    p("4.4. Sieć Kohonena – jak działa i jak ją nauczyliśmy", "h2")
    box("W prostych słowach",
        "Sieć Kohonena to siatka 10 × 10 „szufladek” (neuronów). Każda szufladka ma własny wektor "
        "100 liczb, czyli wzorcowy profil czasowników. Uczenie polega na powtarzaniu jednego kroku: "
        "losujemy rzeczownik, szukamy szufladki najbardziej do niego podobnej (zwycięzcy) "
        "i przesuwamy jej wektor trochę w stronę tego rzeczownika. Sąsiednie szufladki też się "
        "przesuwają, ale słabiej. Po tysiącach powtórzeń sąsiednie szufladki mają podobne profile, "
        "więc podobne rzeczowniki trafiają w pobliskie miejsca mapy. Przypomina to układanie "
        "książek na półkach tak, żeby podobne tematy stały obok siebie.")
    # prawdziwy wektor rzeczownika одлука po przekształceniu log(1+x) i normalizacji
    raw_vec = np.array([float(v) for k, v in example.items() if k != "rzeczownik"])
    vec = np.log1p(raw_vec) / np.linalg.norm(np.log1p(raw_vec))
    names = [k for k in example if k != "rzeczownik"]
    shown = [(names[j], vec[j]) for j in np.argsort(-vec)[:3]] + [("водити", vec[names.index("водити")])]
    draw_som_idea(os.path.join(FIG_DIR, "kohonen_zasada.png"), "одлука", shown)
    figure(os.path.join(FIG_DIR, "kohonen_zasada.png"), 16.5,
           "Jeden krok uczenia sieci Kohonena: wektor rzeczownika (po lewej) przyciąga neuron "
           "zwycięski i, słabiej, jego sąsiadów (po prawej).")
    p(f"Sieć zaimplementowano samodzielnie w numpy (klasa {mono('KohonenSOM')} w "
      f"{mono('lab04_kohonen.py')}). Parametry i algorytm:")
    bullets([
        f"siatka {som['wiersze']} × {som['kolumny']} = {som['wiersze'] * som['kolumny']} neuronów; "
        "każdy neuron ma wektor wag w ∈ R<super>100</super>,",
        "inicjalizacja wag na płaszczyźnie dwóch głównych kierunków zmienności danych (PCA), "
        "dzięki czemu wynik jest powtarzalny,",
        f"{num(som['iteracje'])} kroków; w każdym losujemy wektor x i znajdujemy neuron zwycięski "
        "(BMU) – o najmniejszej odległości euklidesowej ‖x − w‖,",
        "aktualizacja wag: w ← w + η(t) · h(t) · (x − w), gdzie h = exp(−d² / 2σ(t)²) to "
        "„siła sąsiedztwa”, a d to odległość neuronu od zwycięzcy na siatce,",
        f"współczynnik uczenia η maleje z 0,5 do 0,01, a promień sąsiedztwa σ z {som['wiersze'] // 2} "
        "do 0,5: najpierw mapa układa się z grubsza, potem dopracowuje szczegóły,",
        "ocena mapy: <b>błąd kwantyzacji</b> (średnia odległość wektora od jego BMU – im mniejszy, "
        "tym lepiej neurony odwzorowują dane) i <b>błąd topograficzny</b> (odsetek wektorów, "
        "których dwa najlepsze neurony nie sąsiadują – 0% oznacza zachowane sąsiedztwo).",
    ])
    figure(os.path.join(R4, "uczenie.png"), 11.5, "Spadek błędu kwantyzacji w trakcie uczenia (trzy warianty z p. 4.7).")

    p("4.5. Wynik – mapa rzeczowników", "h2")
    p("Na mapie każdy rzeczownik (czerwony) stoi w swoim neuronie zwycięskim. Pod nim, na "
      "niebiesko, podpisano czasownik, który ma w danym neuronie największą wagę. Tło to "
      "<b>U-macierz</b>: jasne pola oznaczają, że neuron jest podobny do sąsiadów (wnętrze "
      "skupienia), a ciemne, że się od nich różni (granica między skupieniami).")
    figure(os.path.join(R4, "wariant_A_mapa.png"), 17,
           f"Mapa Kohonena – wariant A (błąd kwantyzacji {fmt(A['blad_kwantyzacji'], 3)}, "
           f"błąd topograficzny {fmt(A['blad_topograficzny'] * 100, 1)}%).")
    groups = "; ".join(", ".join(gloss(w) for w in g) for g in A["grupy"])
    p(f"Rzeczowniki, które trafiły do tego samego neuronu, mają najbardziej podobne wektory: {groups}.")
    p(INTERPRETATION_A)

    p("4.6. Gdzie są czasowniki w przestrzeni 100D", "h2")
    p("Każda oś 100-wymiarowej przestrzeni to jeden czasownik. Dla każdej osi można narysować "
      "<b>płaszczyznę składowej</b>, czyli wartość tej jednej wagi we wszystkich 100 neuronach. Jasny "
      "obszar to rejon mapy „należący” do danego czasownika: leżą tam rzeczowniki, które się z nim "
      "łączą. Rysunek pokazuje 16 czasowników o największej liczbie kolokacji.")
    figure(os.path.join(R4, "wariant_A_plaszczyzny.png"), 16.5,
           "Płaszczyzny składowych – położenie wybranych czasowników (osi przestrzeni 100D) na mapie.")
    p("Widać, że czasowniki zajmują <b>różne, zwarte obszary</b> mapy: имати – górne wiersze, "
      "заузимати i обухватати – prawy górny róg, добити i носити – lewą kolumnę, водити i донети – "
      "dół mapy. Mapa jest więc dwuwymiarowym „rzutem” przestrzeni czasowników, w którym "
      "sąsiedztwo zostało zachowane.")
    train_x = np.log1p(np.array([[float(v) for k, v in r.items() if k != "rzeczownik"] for r in train]))
    train_x /= np.linalg.norm(train_x, axis=1, keepdims=True)
    sv = np.linalg.svd(train_x - train_x.mean(axis=0), compute_uv=False) ** 2
    expl = sv[:2].sum() / sv.sum()
    figure(os.path.join(R4, "wariant_A_pca.png"), 13,
           "Dla porównania: zwykły rzut liniowy PCA tych samych wektorów 100D na płaszczyznę. "
           "Strzałki to kierunki osi najważniejszych czasowników.")
    p(f"Dla porównania pokazano rzut PCA. Dwie najważniejsze osie zachowują tylko {fmt(expl * 100, 1)}% "
      "informacji (wariancji), a pierwsza oś to w praktyce jeden czasownik – имати. Rzut liniowy "
      "gubi więc większość struktury, a część punktów się nakłada. Sieć Kohonena jest nieliniowa: "
      "korzysta ze wszystkich 100 wymiarów i układa rzeczowniki po całej mapie, zachowując sąsiedztwo.")

    p("4.7. Czy wynik zależy od wyboru czasowników?", "h2")
    p("Ten sam zbiór 50 rzeczowników nauczono w trzech wariantach, przy identycznych parametrach sieci:")
    bullets([f"<b>Wariant {k}</b> – {summ['warianty'][k]['opis']}." for k in "ABC"])
    p(f"Warianty A i B mają {summ['wspolne_czasowniki_AB']} wspólnych czasowników na 100. "
      "W wariancie B są też częste czasowniki nieprzechodnie (налазити се, постати, доћи, живети, "
      "ићи, умрети), które prawie nie mają dopełnień rzeczownikowych.")
    data = [["Wariant", "Suma kolokacji", "Wypełnienie macierzy", "Rzeczowniki z zerowym wektorem",
             "Błąd kwantyzacji", "Błąd topograficzny", "Zajęte neurony"]]
    for k in "ABC":
        v = summ["warianty"][k]
        data.append([k, num(v["suma_kolokacji"]), f"{fmt(v['gestosc'] * 100, 1)}%",
                     ", ".join(v["puste_rzeczowniki"]) or "0", fmt(v["blad_kwantyzacji"], 3),
                     f"{fmt(v['blad_topograficzny'] * 100, 1)}%", v["zajete_neurony"]])
    table(data, [1.5 * cm, 2.1 * cm, 2.4 * cm, 3.4 * cm, 2.3 * cm, 2.4 * cm, 2 * cm], "Porównanie wariantów.")
    data = [["Porównanie map", "Korelacja odległości (Spearman)", "Wspólni sąsiedzi (5 najbliższych)"]]
    for key, v in summ["porownanie"].items():
        data.append([key.replace("-", " – "), fmt(v["spearman"], 3), f"{fmt(v['wspolni_sasiedzi'] * 100, 1)}%"])
    table(data, [3.5 * cm, 6 * cm, 6 * cm],
          "Podobieństwo map. Korelacja 1 oznacza identyczny układ wzajemnych odległości rzeczowników na "
          "mapie, 0 – brak związku.")
    figure(os.path.join(R4, "wariant_B_mapa.png"), 13.5, "Mapa Kohonena – wariant B (100 najczęstszych czasowników).")
    figure(os.path.join(R4, "wariant_C_mapa.png"), 13.5, "Mapa Kohonena – wariant C (kolokacje w oknie ±5 wyrazów).")
    p(INTERPRETATION_ABC)


# ---------------------------------------------------------------------------
# Weryfikacja, podsumowanie, bibliografia
# ---------------------------------------------------------------------------
def verification():
    story.append(PageBreak())
    p("5. Sprawdzenie poprawności wyników", "h1")
    p(f"Skrypt {mono('sprawdz_wyniki.py')} nie korzysta z kodu laboratoriów: każdą wartość liczy "
      "od nowa, najprostszą możliwą metodą, i porównuje ją z plikami wynikowymi. Poniżej "
      "wynik jego działania.")
    checks = run_checks()
    rows = [["Lab", "Co sprawdzamy", "Wynik"]]
    for lab, name, ok, info in checks:
        rows.append([lab, name + (f" <font color='#666666'>({info})</font>" if info else ""),
                     "<font color='#1a7f37'><b>OK</b></font>" if ok else "<font color='#c00000'><b>BŁĄD</b></font>"])
    table(rows, [1 * cm, 14.3 * cm, 1.5 * cm], f"Wyniki testów: zaliczone {sum(c[2] for c in checks)} "
          f"z {len(checks)}.", font_size=7)


def conclusion():
    story.append(PageBreak())
    p("6. Podsumowanie", "h1")
    n2 = read_csv(os.path.join(R2, "statystyka_litery.csv"))
    tot = sum(int(r["licznosc"]) for r in n2)
    H = -sum(int(r["licznosc"]) / tot * math.log2(int(r["licznosc"]) / tot) for r in n2)
    L = sum(int(r["licznosc"]) / tot * len(r["kod_huffmana"]) for r in n2)
    zipf = read_csv(os.path.join(R3, "zipf.csv"))
    f = np.array([int(r["licznosc"]) for r in zipf], float)
    s = -np.polyfit(np.log10(np.arange(1, len(f) + 1)), np.log10(f), 1)[0]
    k90 = len(read_csv(os.path.join(R3, "wyrazy_pokrycie_90.csv")))
    summ = json.load(open(os.path.join(R4, "podsumowanie.json"), encoding="utf-8"))
    words = open(CLEAN_FILE, encoding="utf-8").read().split()

    p("Realizacja wymagań", "h2")
    rows = [["Wymaganie", "Jak zrealizowano", "Wynik", "Rozdz."],
            ["Wybrać język, zostawić sam korpus", "pobranie z Wikipedii, zostawienie tylko 30 liter cyrylicy",
             f"{num(len(words))} wyrazów, 0 obcych znaków", "1"],
            ["Usunąć znaki specjalne, interpunkcję, liczby, znaki spoza alfabetu",
             "wyrażenie regularne [^абв…ш] → spacja; raport usuniętych znaków; testy", "tylko litery i spacje", "1, 2, 5"],
            ["Tabela udziału procentowego liter (prawdopodobieństwa)", "Counter + p = n / N",
             "tabela 30 liter", "2.2"],
            ["Entropia tekstu", "H = −Σ p log₂ p", f"H = {fmt(H, 4)} bit/znak", "2.4"],
            ["Ciągi kodowe Huffmana i porównanie z entropią", "algorytm Huffmana (heapq)",
             f"L = {fmt(L, 4)} bit, H/L = {fmt(H / L * 100, 1)}%", "2.3–2.4"],
            ["Wyrazy pokrywające 90% tekstu", "sortowanie i sumowanie udziałów",
             f"{num(k90)} wyrazów", "3.1"],
            ["Prawo Zipfa", "regresja w skali log-log", f"s = {fmt(s, 3)}", "3.2"],
            ["Graf wyrazów sąsiadujących, krawędzie wychodzące", "zbiory sąsiadów, networkx",
             "krawędzie wych./wch./sąsiedzi", "3.3"],
            ["Rdzeń: 100 wyrazów o największej liczbie sąsiadów", "ranking stopni węzłów",
             "tabela 100 wyrazów + rysunek", "3.3"],
            ["50 rzeczowników i 100 czasowników przechodnich", "analiza składniowa (stanza), relacja obj",
             "tabele czasowników i rzeczowników", "4.1–4.2"],
            ["Wektor o 100 składowych – zbiór treningowy", "kolokacje czasownik–dopełnienie",
             "macierz 50 × 100", "4.3"],
            ["Sieć Kohonena", "własna implementacja SOM 10 × 10",
             f"błąd topograficzny {fmt(summ['warianty']['A']['blad_topograficzny'] * 100, 0)}%", "4.4–4.5"],
            ["Przedstawienie w przestrzeni 100D czasowników", "mapa z czasownikami dominującymi, "
             "płaszczyzny składowych, PCA", "rysunki map", "4.5–4.6"],
            ["Wpływ wyboru czasowników, 100 najczęstszych czasowników", "warianty A, B, C",
             f"korelacja A–B = {fmt(summ['porownanie']['A-B']['spearman'], 2)}", "4.7"],
            ["Sprawozdanie PDF, kod na GitHub", "generuj_sprawozdanie.py, repozytorium git",
             "ten dokument + README", "–"]]
    table(rows, [5 * cm, 5.6 * cm, 4.6 * cm, 1.6 * cm], "Lista wymagań z laboratoriów i miejsce ich realizacji.",
          font_size=7.2)

    p("Najważniejsze wnioski", "h2")
    bullets([
        f"<b>Litery:</b> rozkład liter jest nierównomierny, dlatego kod Huffmana ({fmt(L, 2)} bit/znak) jest "
        f"o {fmt((1 - L / 5) * 100, 0)}% krótszy od kodu 5-bitowego i tylko o {fmt(L - H, 3)} bitu "
        f"dłuższy od teoretycznego minimum, czyli entropii ({fmt(H, 2)} bit/znak).",
        f"<b>Wyrazy:</b> kilkaset najczęstszych wyrazów pokrywa połowę tekstu, ale do 90% potrzeba już "
        f"{num(k90)} wyrazów, bo serbski ma bogatą odmianę. Częstości wyrazów spełniają prawo Zipfa "
        f"(s = {fmt(s, 2)}).",
        "<b>Graf:</b> sieć sąsiedztwa wyrazów jest bezskalowa, a jej rdzeń tworzą słowa funkcyjne.",
        "<b>Sieć Kohonena:</b> ucząc się bez nauczyciela, pogrupowała rzeczowniki w sensowne obszary "
        "(posiadanie, przestrzeń, nadawanie nazw i tytułów, działania polityczne i wojskowe). Wynik "
        "zależy od wyboru czasowników i od definicji kolokacji. Najlepszą mapę daje wariant "
        "z czasownikami faktycznie przechodnimi i kolokacjami wyznaczonymi składniowo.",
    ])
    p("Uruchomienie programu", "h2")
    p(f"{mono('pip install -r requirements.txt')}, a następnie {mono('python uruchom_wszystko.py')} "
      "(lub kolejno lab01.py → lab02… → lab03… → lab04_parsowanie.py → lab04_kohonen.py → "
      "sprawdz_wyniki.py → generuj_sprawozdanie.py). Pobrany korpus i wynik analizy składniowej są "
      "w repozytorium, więc pełne przeliczenie trwa kilka minut.")

    p("Bibliografia", "h2")
    bullets([
        "C. E. Shannon, <i>A Mathematical Theory of Communication</i>, Bell System Technical Journal 27, 1948.",
        "D. A. Huffman, <i>A Method for the Construction of Minimum-Redundancy Codes</i>, "
        "Proceedings of the IRE 40(9), 1952.",
        "G. K. Zipf, <i>Human Behavior and the Principle of Least Effort</i>, Addison-Wesley, 1949.",
        "T. Kohonen, <i>Self-Organized Formation of Topologically Correct Feature Maps</i>, "
        "Biological Cybernetics 43, 1982.",
        "P. Qi, Y. Zhang, Y. Zhang, J. Bolton, C. D. Manning, <i>Stanza: A Python Natural Language "
        "Processing Toolkit for Many Human Languages</i>, ACL 2020 (System Demonstrations).",
        "Universal Dependencies – treebank UD_Serbian-SET, https://universaldependencies.org",
        "MediaWiki API (rozszerzenie TextExtracts), https://www.mediawiki.org/wiki/API:Main_page",
    ])


# Opis wyników lab 4 (dla ziarna losowania SEED = 42 w lab04_kohonen.py)
INTERPRETATION_A = (
    "<b>Interpretacja mapy.</b> Sieć sama, bez żadnych etykiet, podzieliła rzeczowniki na obszary "
    "wyznaczone przez czasowniki, z którymi się łączą:"
    "<br/>• <b>górne wiersze</b> – rejon czasownika <i>имати</i> (mieć): статус, традиција, "
    "становник, утицај, улога, право, подршка, успех („mieć status, tradycję, mieszkańców, wpływ, "
    "rolę, prawo, poparcie, sukces”);"
    "<br/>• <b>prawy górny róg</b> – rzeczowniki przestrzenne z czasownikami <i>заузимати</i> "
    "(zajmować) i <i>обухватати</i> (obejmować): место, положај, површина, део, територија, "
    "подручје, област;"
    "<br/>• <b>lewa kolumna</b> – rzeczy, które się otrzymuje, nadaje lub nosi (<i>добити, дати, "
    "носити, издати, пружити</i>): аутономија, име, назив, титула, повеља, помоћ, отпор;"
    "<br/>• <b>dolny wiersz</b> – działania polityczne i wojskowe: независност и република "
    "(<i>прогласити</i> – ogłosić), одлука и закон (<i>донети</i> – podjąć, uchwalić), мир "
    "(<i>склопити</i> – zawrzeć), преговор, борба, рат, политика, војска (<i>водити</i> – prowadzić);"
    "<br/>• <b>środek dołu mapy</b> – пораз (<i>претрпети</i> – ponieść), победа (<i>однети</i> – "
    "odnieść), власт (<i>преузети</i> – przejąć)."
    "<br/>Ciekawy przypadek to град (miasto) i медаља (medal) leżące obok siebie. Łączy je "
    "czasownik <i>освојити</i>, który znaczy zarówno „zdobyć miasto”, jak i „zdobyć medal”. Mapa "
    "grupuje więc rzeczowniki według zachowania składniowego (wspólnych czasowników), a nie według "
    "samego znaczenia. Błąd topograficzny wynosi 0%: rzeczowniki podobne w przestrzeni 100D leżą "
    "na mapie obok siebie."
)
INTERPRETATION_ABC = (
    "<b>Wnioski z porównania.</b> Wynik wyraźnie zależy od wyboru czasowników:"
    "<br/>• <b>A i B</b> mają wspólną połowę czasowników, w tym te o największej liczbie kolokacji "
    "(имати, донети, водити, прогласити, освојити). Dlatego ogólny układ mapy jest podobny "
    "(korelacja odległości ok. 0,7), ale pokrywa się tylko ok. połowa najbliższych sąsiadów. "
    "Czasowniki nieprzechodnie z wariantu B nie wnoszą informacji o dopełnieniu, a rzeczowniki "
    "пораз i отпор mają w B zerowe wektory, bo ich jedyne czasowniki (претрпети, пружити) nie "
    "należą do 100 najczęstszych. Trafiają więc do jednego neuronu z braku danych, a nie "
    "z podobieństwa."
    "<br/>• <b>C</b> (okno ±5 wyrazów zamiast relacji składniowej) daje gęstszą, ale bardziej "
    "zaszumioną macierz. Okno łapie też podmioty i wyrazy niezwiązane z czasownikiem: np. град "
    "dostaje 22 kolokacje z <i>имати</i> ze zdań typu „град има … становника” (miasto ma … "
    "mieszkańców), w których jest podmiotem, a nie dopełnieniem. Mapa C najmniej przypomina "
    "pozostałe, choć najsilniejsze pary (одлука–закон, рат–борба, територија–површина) nadal "
    "leżą obok siebie."
    "<br/>Najbardziej wiarygodna jest więc mapa A, w której wymiarami są czasowniki faktycznie "
    "przechodnie, a kolokacje pochodzą z relacji czasownik–dopełnienie."
)

S["h1x"] = ParagraphStyle("h1x", parent=S["h1"])  # nagłówek spisu treści (nie trafia do spisu)


def build():
    os.makedirs(FIG_DIR, exist_ok=True)
    doc = ReportDoc(OUTPUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                    topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                    title="Przetwarzanie języka naturalnego – sprawozdanie",
                    author=AUTHOR or "student", subject="Laboratoria 1–4: korpus języka serbskiego")
    title_page()
    contents()
    introduction()
    lab1()
    lab2()
    lab3()
    lab4()
    verification()
    conclusion()
    doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Zapisano {OUTPUT}")


if __name__ == "__main__":
    build()
