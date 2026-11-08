"""
Generuje sprawozdanie PDF (sprawozdanie/sprawozdanie.pdf) z wyników laboratoriów 1-5.

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
from wspolne import (ARTICLES_FILE, CLEAN_FILE, PARSED_FILE, RAW_FILE, RESULTS_DIR, SEM_ARTICLES_FILE,
                     SERBIAN_ALPHABET)

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
    node(2.2, 0.15, 1.8, 0.8, "lab04_pobieranie.py\nkorpus semantyczny", "#cfe2f3")
    node(0.1, 3.4, 1.9, 0.9, "leksykon_svo.py →\nlab05_generator_\nsvo.py (zdania SVO)", "#cfe2f3")
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
    arrow(1.7, 2.1, 2.4, 0.95)
    arrow(4.0, 0.55, 7.1, 0.75)
    arrow(2.0, 3.85, 9.3, 3.0)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def draw_som_idea(path, noun, components, rows=5, cols=10):
    """Ilustracja jednego kroku uczenia sieci Kohonena; `components` = [(czasownik, wartość), ...]."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1, 1.25]})
    ax = axes[0]
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    verbs = [v for v, _ in components] + ["…", "(razem 100 składowych)"]
    vals = [fmt(x, 2) if x else "0" for _, x in components] + ["…", ""]
    ax.text(5, 9.4, f"wektor rzeczownika {noun}" + (f" ({GLOSSARY[noun]})" if noun in GLOSSARY else ""), ha="center",
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
    bmu, sigma = (rows // 2, cols // 3), 1.6
    yy, xx = np.mgrid[0:rows, 0:cols]
    h = np.exp(-((yy - bmu[0]) ** 2 + (xx - bmu[1]) ** 2) / (2 * sigma ** 2))
    ax.imshow(h, cmap="Oranges", vmin=0, vmax=1.15)
    for i in range(rows + 1):
        ax.axhline(i - 0.5, color="white", lw=1)
    for i in range(cols + 1):
        ax.axvline(i - 0.5, color="white", lw=1)
    ax.add_patch(plt.Rectangle((bmu[1] - 0.5, bmu[0] - 0.5), 1, 1, fill=False, ec="#b2182b", lw=2.5))
    ax.annotate("neuron zwycięski (BMU):\nzmienia się najmocniej", xy=(bmu[1], bmu[0]), xytext=(cols * 0.55, rows - 0.7),
                fontsize=8.5, arrowprops=dict(arrowstyle="->", color="#b2182b"), color="#b2182b")
    ax.text(cols * 0.58, 0.6, "sąsiedzi też się uczą,\ntym słabiej, im dalej\nod zwycięzcy", fontsize=8.5)
    ax.set_title(f"mapa {rows} × {cols} = {rows * cols} neuronów (kolor = siła zmiany wag)", fontsize=10)
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
    p("Sprawozdanie z laboratoriów 1–5", "subtitle")
    p("Język serbski: analiza statystyczna (entropia, Huffman, prawo Zipfa, pokrycie 90% tekstu, "
      "rdzeń języka), analiza syntaktyczna (generator zdań SVO) i analiza semantyczna "
      "(klasyfikator rzeczowników – sieć Kohonena)", "subtitle")
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
    p("Celem laboratoriów było przeanalizowanie wybranego języka naturalnego na trzech poziomach:")
    bullets([
        "<b>analiza statystyczna</b> (rozdziały 1–3): korpus ponad 100 000 wyrazów, statystyka liter, "
        "entropia i kod Huffmana, prawo Zipfa, lista wyrazów pokrywających 90% tekstu, rdzeń języka "
        "(100 wyrazów o największej liczbie sąsiadów),",
        "<b>analiza semantyczna</b> (rozdział 4): klasyfikator semantyczny 1000 rzeczowników – sieć "
        "Kohonena z 50 neuronami ucząca się na frazach czasownik–dopełnienie,",
        "<b>analiza syntaktyczna</b> (rozdział 5): generator zdań prostych SVO we wszystkich czasach, "
        "trybach i stronach.",
    ])
    p("<b>Wybrany język: serbski.</b> Serbski zapisuje się m.in. cyrylicą, która ma dokładnie "
      "30 liter, a każda litera odpowiada jednej głosce (zasada „piši kao što govoriš” – pisz tak, "
      "jak mówisz). Dzięki temu łatwo sprawdzić, że w korpusie zostały wyłącznie litery alfabetu. "
      "Bogata odmiana wyrazów przez przypadki jest z kolei ciekawa przy badaniu prawa Zipfa "
      "i wymaga analizy składniowej w laboratorium 4.")
    p(f"<b>Dane:</b> korpus podstawowy – {len(articles)} artykułów z serbskiej Wikipedii (ok. 1 mln "
      "znaków), głównie o historii i geografii Serbii i regionu; do analizy semantycznej dodatkowo "
      "ok. 8 mln znaków z artykułów o różnej tematyce (rozdział 4.1).")
    p("Struktura programu", "h2")
    p("Każde laboratorium to osobny skrypt w Pythonie. Wspólne ustawienia (alfabet, ścieżki "
      f"do plików) są w {mono('wspolne.py')}, a {mono('uruchom_wszystko.py')} uruchamia "
      f"wszystkie etapy po kolei. Skrypt {mono('sprawdz_wyniki.py')} niezależnie przelicza "
      "wyniki i potwierdza ich poprawność (rozdział 6). Kod i wyniki są w repozytorium "
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
            ["fraza VO", "połączenie czasownika z jego dopełnieniem bliższym, np. попити воду (wypić wodę)"],
            ["pole semantyczne", "grupa wyrazów o wspólnym zakresie znaczeniowym, np. jedzenie, pojazdy, budynki"],
            ["neuron martwy", "neuron sieci Kohonena, który po uczeniu nie jest zwycięzcą dla żadnego wektora"],
            ["zdanie SVO", "zdanie o szyku podmiot (S) – orzeczenie (V) – dopełnienie (O)"],
            ["enklityka", "krótki wyraz bez akcentu (сам, је, га, се, ће), który w serbskim stoi na drugim "
                          "miejscu w zdaniu"],
            ["wektor cech", "opis obiektu listą liczb; u nas rzeczownik = 100 liczb (po jednej na czasownik)"],
            ["sieć Kohonena (SOM)", "sieć neuronowa ucząca się bez nauczyciela, która układa podobne "
                                    "obiekty w tych samych lub sąsiednich neuronach"],
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
    som = summ["som"]
    n_neurons = som["wiersze"] * som["kolumny"]
    verbs = read_csv(os.path.join(R4, "czasowniki_przechodnie.csv"))
    nouns = read_csv(os.path.join(R4, "rzeczowniki.csv"))
    neurons = read_csv(os.path.join(R4, "neurony.csv"))
    sem_articles = [a for a in open(SEM_ARTICLES_FILE, encoding="utf-8").read().split("\n") if a] \
        if os.path.exists(SEM_ARTICLES_FILE) else []

    p("4. Laboratorium 4 – analiza semantyczna: klasyfikator rzeczowników oparty na sieci Kohonena", "h1")
    p(f"<b>Zadanie:</b> opracować klasyfikator semantyczny rzeczowników oparty na sieci Kohonena. "
      "Przeanalizować co najmniej 1000 rzeczowników na podstawie ich powiązań ze 100 czasownikami "
      "przechodnimi: każdy rzeczownik to wektor o 100 składowych, z których każda zawiera liczbę "
      "wystąpień frazy VO (czasownik + jego dopełnienie bliższe). Sieć ma mieć 50 neuronów. "
      "Oczekuje się, że sieć spontanicznie wytworzy klastry rzeczowników ze wspólnego pola "
      "semantycznego. Należy sprawdzić, czy klastry są logicznie uzasadnione i jednorodne, ile pól "
      "semantycznych powstało i czy są neurony, które niczego się nie nauczyły.")
    box("W prostych słowach",
        "Rzeczownik można poznać po tym, z jakimi czasownikami się łączy. „Chleb”, „mięso” i „ser” "
        "się <i>je</i>, „wodę”, „kawę” i „wino” się <i>pije</i>, a „mecz” i „rolę” się <i>gra</i>. "
        "Zapisujemy więc dla każdego rzeczownika 100 liczb: ile razy był dopełnieniem każdego ze 100 "
        "czasowników. Rzeczowniki z jednego pola znaczeniowego mają podobne listy liczb. Sieć "
        "Kohonena to 50 „szufladek”, które – bez żadnej podpowiedzi – uczą się zbierać podobne "
        "rzeczowniki do jednej szufladki, a podobne szufladki układać obok siebie.")

    p("4.1. Korpus do analizy semantycznej", "h2")
    p("Korpus z laboratorium 1 (ok. 150 tys. wyrazów, głównie historia i geografia Serbii) dawał tylko "
      "ok. 900 rzeczowników będących dopełnieniem 100 czasowników przechodnich, w dodatku większość "
      "z jednym wystąpieniem – za mało na 1000 wektorów i zbyt jednorodnie tematycznie, żeby powstały "
      f"różne pola znaczeniowe. Dlatego skrypt {mono('lab04_pobieranie.py')} pobrał z serbskiej "
      f"Wikipedii dodatkowe {num(len(sem_articles))} artykułów (ok. 8 mln znaków) z różnych dziedzin: "
      "jedzenie i napoje, zwierzęta, rośliny, ubrania, budynki, transport, muzyka i sztuka, medycyna, "
      "sport, nauka i technika, gospodarka i polityka, wojsko, przyroda, rodzina. Do analizy użyto "
      "obu korpusów razem.")
    if sem_articles:
        domains = Counter(a.split("\t")[0] for a in sem_articles)
        table([["Dziedzina", "Artykułów", "Przykłady"]]
              + [[d, c, ", ".join(a.split("\t")[1] for a in sem_articles if a.startswith(d + "\t"))[:150] + "…"]
                 for d, c in domains.most_common()],
              [3.6 * cm, 1.8 * cm, 11.4 * cm], "Dziedziny artykułów korpusu dodatkowego.", font_size=6.8)

    p("4.2. Analiza składniowa i frazy VO", "h2")
    p("Żeby wiedzieć, który rzeczownik jest dopełnieniem którego czasownika, potrzebna jest analiza "
      "gramatyczna zdań. Użyto biblioteki <b>stanza</b> (Stanford NLP) z modelem języka serbskiego "
      f"(treebank UD Serbian-SET, standard Universal Dependencies). Skrypt {mono('lab04_parsowanie.py')}:")
    steps([
        "wczytuje tekst surowy (z interpunkcją, bo potrzebne są granice zdań) i dzieli go na porcje, "
        "przetwarzane równolegle w kilku procesach,",
        "zamienia cyrylicę na łacinkę, bo model był uczony na serbskiej łacince "
        "(odpowiedniość liter jest 1:1, np. љ → lj, њ → nj, џ → dž),",
        "dla każdego wyrazu ustala część mowy, lemat (formę podstawową) i wyraz nadrzędny wraz "
        "z relacją, np. <i>obj</i> = dopełnienie bliższe,",
        "przepisuje wynik z powrotem na cyrylicę i zapisuje go do plików .tsv.gz w folderze dane/.",
    ])
    p(f"Wynik: {num(summ['zdania'])} zdań, {num(summ['tokeny'])} tokenów i "
      f"<b>{num(summ['frazy_vo'])} fraz VO</b> (czasownik → dopełnienie rzeczownikowe). Przykład: "
      "w zdaniu „Кнез Лазар је подигао цркву и водио војску” parser znajduje frazy "
      "VO(подићи, црква) i VO(водити, војска). Dzięki lematyzacji formy цркву, цркве, црквом "
      "liczą się jako jeden rzeczownik црква. Liczone są też dopełnienia współrzędne: "
      "w „купио хлеб и млеко” dopełnieniami są oba rzeczowniki.")

    p("4.3. Wybór 100 czasowników przechodnich i 1000 rzeczowników", "h2")
    steps([
        "Dla każdego czasownika liczymy, ile razy ma dopełnienie rzeczownikowe.",
        "Czasownik uznajemy za <b>przechodni</b>, jeśli dopełnienie ma w co najmniej 20% wystąpień "
        "(odrzuca to błędy parsera, np. постати – stać się: „постао је краљ”).",
        "Pomijamy czasowniki posiłkowe i modalne (бити, хтети, моћи, морати, требати).",
        "Bierzemy <b>100 czasowników</b> o największej liczbie fraz VO, a potem <b>1000 rzeczowników</b>, "
        "które najczęściej są dopełnieniem tych czasowników.",
    ])
    data = [["Lp", "Czasownik", "VO", "Lp", "Czasownik", "VO"]]
    for i in range(50):
        a, b = verbs[i], verbs[i + 50]
        data.append([a["lp"], gloss(a["czasownik"]), a["frazy_vo"], b["lp"], gloss(b["czasownik"]), b["frazy_vo"]])
    table(data, [0.8 * cm, 6.3 * cm, 1.2 * cm] * 2,
          "100 wybranych czasowników przechodnich (VO – liczba fraz czasownik–dopełnienie rzeczownikowe).",
          font_size=6.5)
    vo = [int(n["liczba_fraz_vo"]) for n in nouns]
    dv = [int(n["liczba_roznych_czasownikow"]) for n in nouns]
    p(f"Wybrane rzeczowniki mają od {min(vo)} do {max(vo)} fraz VO (mediana {int(np.median(vo))}) "
      f"i łączą się średnio z {fmt(np.mean(dv), 1)} różnymi czasownikami. Najczęstsze: "
      + ", ".join(f"{n['rzeczownik']} ({n['liczba_fraz_vo']})" for n in nouns[:30])
      + f". Pełna lista {len(nouns)} rzeczowników jest w {mono('wyniki/lab04/rzeczowniki.csv')}.")

    p("4.4. Zbiór treningowy – wektory o 100 składowych", "h2")
    train = read_csv(os.path.join(R4, "zbior_treningowy.csv"))
    example = max(train[:60], key=lambda r: sum(1 for k, v in r.items() if k != "rzeczownik" and int(v) > 0))
    nz = sorted(((k, int(v)) for k, v in example.items() if k != "rzeczownik" and int(v) > 0), key=lambda x: -x[1])
    p("Każdy rzeczownik zamieniamy na wektor x = (x<sub>1</sub>, …, x<sub>100</sub>), gdzie "
      "x<sub>j</sub> to liczba wystąpień frazy VO złożonej z j-tego czasownika i tego rzeczownika. "
      f"Przykład – wektor rzeczownika <b>{example['rzeczownik']}</b> ma {len(nz)} niezerowych składowych, "
      "największe: " + ", ".join(f"{k} = {v}" for k, v in nz[:10]) + "; pozostałe składowe to zera. "
      f"Cały zbiór treningowy to macierz {len(train)} × 100 ({mono('wyniki/lab04/zbior_treningowy.csv')}). "
      "Przed uczeniem wektory przygotowano w dwóch krokach:")
    bullets([
        "<b>log(1 + x)</b> – zmniejsza wpływ bardzo częstych fraz, żeby jedna fraza nie zdominowała wektora,",
        "<b>waga IDF czasownika</b> = log(1000 / liczba rzeczowników łączących się z tym czasownikiem) – "
        "czasowniki łączące się prawie ze wszystkim (имати – mieć, представљати – stanowić, садржати – "
        "zawierać) niewiele mówią o znaczeniu rzeczownika, więc dostają mniejszą wagę niż czasowniki "
        "wybiórcze (освојити – zdobyć, изазвати – wywołać). Bez tej wagi połowa neuronów była zdominowana "
        "przez имати i zawierała przypadkowe mieszaniny rzeczowników,",
        "<b>normalizacja do długości 1</b> – porównujemy „profil” czasowników, a nie to, jak często "
        "rzeczownik w ogóle występuje (rzadki i częsty rzeczownik z tym samym profilem są podobne).",
    ])

    p("4.5. Sieć Kohonena – budowa i uczenie", "h2")
    # prawdziwy wektor wejściowy sieci: log(1 + x) · IDF, znormalizowany
    allc = np.array([[float(v) for k, v in r.items() if k != "rzeczownik"] for r in train])
    idf = np.log(len(allc) / np.maximum((allc > 0).sum(axis=0), 1))
    raw_vec = np.array([float(v) for k, v in example.items() if k != "rzeczownik"])
    vec = np.log1p(raw_vec) * idf
    vec /= np.linalg.norm(vec)
    names = [k for k in example if k != "rzeczownik"]
    draw_som_idea(os.path.join(FIG_DIR, "kohonen_zasada.png"), example["rzeczownik"],
                  [(names[j], vec[j]) for j in np.argsort(-vec)[:4]], som["wiersze"], som["kolumny"])
    figure(os.path.join(FIG_DIR, "kohonen_zasada.png"), 16.5,
           "Jeden krok uczenia sieci Kohonena: wektor rzeczownika (po lewej) przyciąga neuron "
           "zwycięski i, słabiej, jego sąsiadów (po prawej).")
    p(f"Sieć zaimplementowano samodzielnie w numpy (klasa {mono('KohonenSOM')} w "
      f"{mono('lab04_kohonen.py')}). Parametry i algorytm:")
    bullets([
        f"<b>{n_neurons} neuronów</b> ułożonych w siatkę {som['wiersze']} × {som['kolumny']}; każdy neuron "
        "ma wektor wag w ∈ R<super>100</super>,",
        "inicjalizacja: małe losowe wagi (rozkład jednostajny 0–0,1, stałe ziarno – wynik powtarzalny),",
        f"{som['epoki']} epok; w każdej epoce wszystkie {len(train)} wektorów w losowej kolejności. Dla "
        "wektora x szukamy neuronu zwycięskiego (BMU) – o najmniejszej odległości ‖x − w‖,",
        "aktualizacja wag: w ← w + η(t) · h(t) · (x − w), gdzie h = exp(−d² / 2σ(t)²) to "
        "„siła sąsiedztwa”, a d to odległość neuronu od zwycięzcy na siatce,",
        f"współczynnik uczenia η maleje z 0,5 do 0,01, a promień sąsiedztwa σ z {max(som['wiersze'], som['kolumny']) // 2} "
        "do 0,5: najpierw mapa układa się z grubsza, potem dopracowuje szczegóły,",
        "ocena: błąd kwantyzacji (średnia odległość wektora od jego BMU) i błąd topograficzny "
        "(odsetek wektorów, których dwa najlepsze neurony nie sąsiadują na siatce).",
    ])
    figure(os.path.join(R4, "uczenie.png"), 11, "Spadek błędu kwantyzacji w trakcie uczenia.")
    p(f"Po uczeniu: błąd kwantyzacji {fmt(summ['blad_kwantyzacji'], 3)}, błąd topograficzny "
      f"{fmt(summ['blad_topograficzny'] * 100, 1)}%.")

    p("4.6. Wynik – klastry rzeczowników", "h2")
    p("Na mapie (rys. niżej) każdy kwadrat to jeden neuron: numer i liczba rzeczowników, na "
      "niebiesko czasownik o największej wadze, na czerwono najczęstsze rzeczowniki, które do niego "
      "trafiły, na zielono pole semantyczne (nasza interpretacja). Tło to U-macierz: jasne pola – "
      "neuron podobny do sąsiadów, ciemne – granica między skupieniami.")
    figure(os.path.join(R4, "mapa_kohonena.png"), 14, "Mapa Kohonena – 1000 rzeczowników na 50 neuronach "
           "(siatka 5 × 10 narysowana pionowo; w każdym neuronie 5 najczęstszych rzeczowników).")
    figure(os.path.join(R4, "liczebnosc_klastrow.png"), 14, "Liczba rzeczowników w każdym neuronie.")
    rows = [["#", "N", "Spójn.", "Dominujące czasowniki", "Pole semantyczne", "Rzeczowniki (najczęstsze)"]]
    for n in neurons:
        members = n["rzeczowniki"].split(", ") if n["rzeczowniki"] else []
        label = n["pole_semantyczne"] + (" <i>(niejednorodny)</i>" if n["jednorodny"] == "nie" else "")
        rows.append([n["neuron"], n["liczba_rzeczownikow"],
                     "" if n["spojnosc"] == "nan" else n["spojnosc"].replace(".", ","),
                     n["dominujace_czasowniki"], label or ("<b>neuron martwy</b>" if not members else "–"),
                     ", ".join(members[:12]) + (" …" if len(members) > 12 else "")])
    table(rows, [0.6 * cm, 0.8 * cm, 1 * cm, 4 * cm, 3.4 * cm, 7 * cm],
          "Zawartość wszystkich 50 neuronów (N – liczba rzeczowników, Spójn. – średnie podobieństwo "
          "kosinusowe rzeczowników w klastrze; pełne listy: wyniki/lab04/neurony.csv).", font_size=6)

    p("4.7. Analiza klastrów", "h2")
    dead = summ["martwe_neurony"]
    labels = summ["pola"]
    hom = sum(1 for v in labels.values() if v["jednorodny"])
    coh = list(summ["spojnosc"].values())
    p(f"<b>Neurony martwe.</b> {len(dead)} z {n_neurons} neuronów nie wygrało dla żadnego rzeczownika"
      + (f" (#{', #'.join(map(str, dead))})" if dead else "") + ". "
      + KOHONEN_DEAD_COMMENT)
    p(f"<b>Spójność.</b> Średnie podobieństwo kosinusowe dwóch rzeczowników z tego samego klastra "
      f"wynosi {fmt(np.mean(coh), 2)}, a dwóch dowolnych rzeczowników – {fmt(summ['podobienstwo_srednie'], 2)}. "
      "Klastry skupiają więc rzeczowniki o wyraźnie podobnych profilach czasowników.")
    mixed = [k for k, v in labels.items() if not v["jednorodny"]]
    no_field = [n["neuron"] for n in neurons if n["rzeczowniki"] and not n["pole_semantyczne"]]
    p(f"<b>Pola semantyczne.</b> Zawartość każdego neuronu oceniliśmy ręcznie (tabela {counters['tab']}). "
      f"<b>{hom} klastrów jest jednorodnych</b> – ich rzeczowniki należą do wspólnego pola semantycznego; "
      f"{len(mixed)} klastrów jest mieszanych (da się wskazać dominujący motyw, ale rzeczowniki pochodzą z "
      f"różnych pól), a {len(no_field)} małe neurony (#{', #'.join(no_field)}) nie mają żadnego wspólnego "
      f"pola. Klastry jednorodne tworzą <b>{summ['liczba_pol']} różne pola semantyczne</b> – niektóre pola "
      "zajmują dwa sąsiednie neurony:")
    by_field = defaultdict(list)
    for k, v in labels.items():
        if v["jednorodny"]:
            by_field[v["pole"]].append(int(k))
    rows = [["Pole semantyczne", "Neurony", "Przykładowe rzeczowniki"]]
    clusters = summ["klastry"]
    for field, ks in sorted(by_field.items(), key=lambda x: min(x[1])):
        ex = [w for k in sorted(ks) for w in clusters[str(k)][:6]]
        rows.append([field, ", ".join(f"#{k}" for k in sorted(ks)), ", ".join(ex[:12])])
    table(rows, [4.6 * cm, 1.8 * cm, 10.4 * cm], f"Pola semantyczne ({summ['liczba_pol']}) utworzone "
          "przez klastry jednorodne.", font_size=6.8)
    rows = [["Klaster mieszany", "Neuron", "Przykładowe rzeczowniki"]]
    for k in sorted(map(int, mixed)):
        rows.append([labels[str(k)]["pole"].replace("mieszany: ", ""), f"#{k}", ", ".join(clusters[str(k)][:10])])
    table(rows, [4.6 * cm, 1.8 * cm, 10.4 * cm], "Klastry niejednorodne (dominujący motyw i przykłady).",
          font_size=6.8)
    p(KOHONEN_INTERPRETATION)


# ---------------------------------------------------------------------------
# Lab 5 - generator zdań SVO
# ---------------------------------------------------------------------------
def lab5():
    import lab05_generator_svo as g
    import leksykon_svo as lx

    story.append(PageBreak())
    verbs = [g.Verb(v) for v in lx.VERBS]
    vtype = Counter(v.typ for v in verbs)
    p("5. Laboratorium 5 – analiza syntaktyczna: generator zdań SVO", "h1")
    p("<b>Zadanie:</b> opracować generator zdań prostych typu SVO (podmiot – orzeczenie – dopełnienie "
      "bliższe). Podmiotem jest fraza rzeczownikowa lub zaimek osobowy, orzeczeniem czasownik "
      "nieprzechodni, przechodni lub zwrotny we wszystkich możliwych w danym języku czasach, trybach "
      "(oznajmujący, pytający, przeczący, rozkazujący, przypuszczający) i stronach (czynna, bierna), "
      "a dopełnieniem fraza rzeczownikowa lub zaimek osobowy. Fraza rzeczownikowa to rzeczownik, "
      "opcjonalnie poprzedzony przymiotnikiem i rodzajnikiem lub zaimkiem. Leksykon: co najmniej "
      "100 rzeczowników, 100 czasowników i 100 przymiotników.")
    box("W prostych słowach",
        "Generator składa zdanie z klocków: losuje czasownik, do niego pasujący podmiot i (jeśli "
        "czasownik jest przechodni) dopełnienie, a potem losuje czas, tryb i stronę. Najtrudniejsza "
        "jest odmiana: serbski ma 7 przypadków, 3 rodzaje, zgodę przymiotnika i imiesłowu z rzeczownikiem "
        "oraz „enklityki” – krótkie słówka (сам, је, га, се, ће…), które muszą stać na drugim miejscu "
        "w zdaniu w ściśle określonej kolejności. Generator zna te reguły, więc „Ја сам га видео” "
        "(Widziałem go) powstaje poprawnie, a nie jako „Ја видео сам њега”.")

    p("5.1. Leksykon", "h2")
    p(f"Leksykon jest w pliku {mono('leksykon_svo.py')}, a generator w {mono('lab05_generator_svo.py')}. "
      "Wyrazy zapisano łacinką (w niej łatwiej kontrolować odmianę), a zdania są wypisywane cyrylicą "
      "i łacinką (transliteracja jest jednoznaczna). Użyto wymowy ekawskiej (standard w Serbii).")
    det_kinds = Counter(d[4] for d in lx.DETERMINERS)
    table([["Część leksykonu", "Liczba", "Szczegóły"],
           ["rzeczowniki", len(lx.NOUNS), f"m: {sum(n['gender'] == 'm' for n in lx.NOUNS)}, "
            f"ż: {sum(n['gender'] == 'f' for n in lx.NOUNS)}, n: {sum(n['gender'] == 'n' for n in lx.NOUNS)}; "
            "dla każdego 6 form: mianownik, dopełniacz, biernik × l. poj./mn.; żywotność; klasa znaczeniowa"],
           ["czasowniki", len(verbs), f"przechodnie {vtype['tr']}, nieprzechodnie {vtype['intr']}, zwrotne "
            f"{vtype['refl']}; niedokonane {sum(v.asp == 'impf' for v in verbs)}, dokonane "
            f"{sum(v.asp == 'pf' for v in verbs)}; przechodnie z imiesłowem biernym"],
           ["przymiotniki", len(lx.ADJECTIVES), "forma określona, z listą klas rzeczowników, do których pasują"],
           ["określniki", len(lx.DETERMINERS) + 1,
            ", ".join(f"{k}: {c}" for k, c in det_kinds.items()) + "; zwrotny dzierżawczy свој"],
           ["zaimki osobowe", 10, "ја, ти, он, она, оно, ми, ви, они, оне, она (M., B. enklityczny, B. pełny, D.)"]],
          [3.2 * cm, 1.6 * cm, 12 * cm], "Zawartość leksykonu generatora.")
    p("Serbski <b>nie ma rodzajników</b>. Ich funkcję pełnią zaimki: <i>један</i> (jeden, pewien) "
      "działa jak rodzajnik nieokreślony, a <i>тај</i> (ten) jak określony. Dlatego jako „element "
      "dodatkowy” frazy rzeczownikowej generator używa zaimków wskazujących (овај, тај, онај), "
      "dzierżawczych (мој, твој, његов, њен, наш, ваш, њихов, свој), nieokreślonych (један, неки) "
      "i upowszechniającego (сваки).")
    rows = [["Rzeczownik", "Znaczenie", "Rodz.", "Kl."] * 3]
    for i in range(0, len(lx.NOUNS), 3):
        row = []
        for n in lx.NOUNS[i:i + 3]:
            row += [g.cyr(n["lemma"]), n["gloss"], n["gender"] + ("*" if n["animate"] else ""), n["classes"]]
        rows.append(row + [""] * (12 - len(row)))
    table(rows, [1.9 * cm, 2.3 * cm, 0.8 * cm, 0.8 * cm] * 3,
          "Rzeczowniki (* – żywotne; klasy: H ludzie, A zwierzęta, F jedzenie, D napoje, O przedmioty, "
          "C ubrania, V pojazdy, B budynki/miejsca, T teksty/dzieła, M utwory muzyczne, I instrumenty, "
          "P rośliny, N pieniądze, K części ciała).", font_size=6.2)
    rows = [["Czasownik", "Znaczenie", "Typ", "Asp."] * 2]
    half = (len(verbs) + 1) // 2
    for i in range(half):
        row = []
        for v in (verbs[i], verbs[i + half] if i + half < len(verbs) else None):
            row += ([g.cyr(v.inf + (" se" if v.reflexive else "")), v.gloss, v.typ, v.asp] if v else [""] * 4)
        rows.append(row)
    table(rows, [2.6 * cm, 3.6 * cm, 0.9 * cm, 1.1 * cm] * 2,
          "Czasowniki (tr – przechodni, intr – nieprzechodni, refl – zwrotny; impf – niedokonany, "
          "pf – dokonany).", font_size=6.2)
    rows = [["Przymiotnik", "Znaczenie"] * 4]
    q = (len(lx.ADJECTIVES) + 3) // 4
    for i in range(q):
        row = []
        for k in range(4):
            j = i + k * q
            row += [g.cyr(lx.ADJECTIVES[j][0]), lx.ADJECTIVES[j][1]] if j < len(lx.ADJECTIVES) else ["", ""]
        rows.append(row)
    table(rows, [2 * cm, 2.25 * cm] * 4, "Przymiotniki (forma określona, rodzaj męski).", font_size=6.2)

    p("5.2. Fraza rzeczownikowa i jej odmiana", "h2")
    p("Fraza rzeczownikowa ma postać [określnik] [przymiotnik] rzeczownik. Wszystkie trzy elementy "
      "zgadzają się w rodzaju, liczbie i przypadku. Podmiot stoi w mianowniku, dopełnienie bliższe "
      "w bierniku, a wykonawca czynności w stronie biernej w dopełniaczu (<i>од стране</i> + D.). "
      "Rzeczowniki męskie <b>żywotne</b> mają w bierniku l. poj. formę dopełniacza (видим пса – "
      "widzę psa), a nieżywotne – formę mianownika (видим град – widzę miasto). Gdy posiadaczem "
      "dopełnienia jest podmiot, zaimek dzierżawczy zmienia się na zwrotny <i>свој</i> (Ја читам "
      "<i>своју</i> књигу – Czytam swoją książkę).")
    noun = {n["lemma"]: n for n in lx.NOUNS}
    det = {d[0]: d for d in lx.DETERMINERS}
    rows = [["Fraza", "Mianownik (podmiot)", "Biernik (dopełnienie)", "Dopełniacz (wykonawca)"]]
    for lemma, num_, adj, d in (("pas", "sg", "veliki", "naš"), ("grad", "sg", "stari", "ovaj"),
                                ("knjiga", "sg", "novi", "moj"), ("pismo", "pl", "dugi", "taj"),
                                ("devojka", "pl", "mladi", "neki")):
        np_ = g.NounPhrase(noun[lemma], num_, adj, det[d])
        rows.append([f"{d} + {adj} + {lemma} ({'l. mn.' if num_ == 'pl' else 'l. poj.'})"]
                    + [g.cyr(np_.form(c)) for c in ("nom", "acc", "gen")])
    table(rows, [5 * cm, 3.9 * cm, 3.9 * cm, 3.9 * cm], "Przykłady odmiany frazy rzeczownikowej.")

    p("5.3. Orzeczenie: czasy, tryby i strony", "h2")
    p("Serbski ma siedem czasów trybu oznajmującego, dwa czasy trybu przypuszczającego (potencijal) "
      "i tryb rozkazujący. Każdą formę można postawić w zdaniu oznajmującym lub pytającym "
      "(<i>да ли</i> …?) oraz twierdzącym lub przeczącym. Pięć „trybów” z polecenia "
      "realizujemy więc jako trzy tryby gramatyczne × typ zdania × polaryzację, co daje także "
      "kombinacje (np. pytanie przeczące w potencjale).")
    example = [
        ("prezent", "czas teraźniejszy", "forma osobowa", "Ја читам књигу."),
        ("perfekat", "przeszły złożony", "сам/си/је… + imiesłów na -l", "Ја сам читао књигу."),
        ("aorist", "przeszły dokonany (literacki)", "forma syntetyczna", "Ја прочитах књигу."),
        ("imperfekat", "przeszły niedokonany (literacki), tylko czas. niedokonane", "forma syntetyczna",
         "Ја читах књигу."),
        ("pluskvamperfekat", "zaprzeszły", "сам био + imiesłów na -l", "Ја сам био читао књигу."),
        ("futur I", "przyszły", "ћу/ћеш… + bezokolicznik", "Ја ћу читати књигу."),
        ("futur II", "przyszły uprzedni (tylko w zdaniach warunkowych/czasowych)", "будем + imiesłów",
         "Ако ја будем читао књигу…"),
        ("potencijal I", "tryb przypuszczający", "бих/би… + imiesłów", "Ја бих читао књигу."),
        ("potencijal II", "tryb przypuszczający przeszły", "бих био + imiesłów", "Ја бих био читао књигу."),
        ("imperativ", "tryb rozkazujący (ti, mi, vi)", "forma syntetyczna; przeczenie: не / немој + bezok.",
         "Ти читај књигу! Немој прочитати!"),
        ("imperativ z неka", "rozkaz dla 1. os. lp. i 3. os.", "нека + prezent", "Нека он чита књигу!"),
        ("strona bierna", "wszystkie czasy oprócz zaprzeszłego", "бити + imiesłów bierny (+ од стране D.)",
         "Књига је прочитана од стране мог брата."),
    ]
    table([["Forma", "Znaczenie", "Budowa", "Przykład"]] + [list(r) for r in example],
          [2.6 * cm, 4.6 * cm, 4.6 * cm, 5 * cm], "Formy orzeczenia obsługiwane przez generator.", font_size=7)
    p("Formy regularne generator tworzy sam z bezokolicznika i 1. os. lp. czasu teraźniejszego "
      "(np. aoryst: читати → читах, чита, читасмо, читасте, читаше; imperatyw: читају → читај, "
      "пишу → пиши). Formy nieregularne (np. јести → једох, јео; доћи → дођох, дошао; пећи → пеци) "
      "są zapisane w leksykonie. Imiesłowy zgadzają się z podmiotem w rodzaju i liczbie: читао "
      "(on), читала (ona), читало (ono), читали (oni), читале (one), читала (ona – l. mn. nijaka). "
      "Kombinacje niemożliwe w serbskim są odrzucane: imperfekt czasowników dokonanych, strona "
      "bierna czasowników nieprzechodnich i zwrotnych, pytanie w trybie rozkazującym, futur II "
      "w zdaniu pytającym.")

    p("5.4. Szyk zdania i enklityki", "h2")
    p("Podstawowy szyk to SVO, ale serbskie enklityki (słowa bez akcentu) muszą stać na "
      "<b>drugim miejscu</b> w zdaniu – po pierwszej frazie (podmiocie albo <i>да ли</i>, <i>нека</i>, "
      "<i>ако</i>). Generator ustawia je w kolejności: <i>li</i> – czasownik posiłkowy (сам, си, смо, "
      "сте, су, бих, ћу…) – zaimek w bierniku (ме, те, га, је, нас, вас, их) – <i>се</i> – <i>је</i>. "
      "Dodatkowo: posiłkowe је znika po се (Он се смејао), a zaimek је przed posiłkowym је "
      "zmienia się w ју (Он ју је видео). Dopełnienie-zaimek ma formę enklityczną, więc w tym "
      "przypadku szyk staje się SOV – tak jak wymaga gramatyka.")
    rows = [["Zdanie", "Tłumaczenie"],
            ["Ја сам га видео.", "Widziałem go."], ["Он ју је видео.", "On ją widział."],
            ["Да ли си ти видела тог пса?", "Czy (ty) widziałaś tego psa?"],
            ["Ми се нисмо смејали.", "Nie śmialiśmy się."], ["Нека га он чита!", "Niech on go czyta!"],
            ["Ви бисте се били смејали.", "Bylibyście się śmiali."]]
    table(rows, [8 * cm, 8 * cm], "Przykłady szyku enklityk.")

    p("5.5. Ograniczenia znaczeniowe", "h2")
    p("Zdania mają być nie tylko poprawne gramatycznie, ale też sensowne. Każdy rzeczownik ma klasę "
      "znaczeniową, a każdy czasownik listę klas dozwolonych dla podmiotu i dopełnienia (np. јести: "
      "podmiot H/A – człowiek lub zwierzę, dopełnienie F – jedzenie; возити: dopełnienie V – pojazd). "
      "Podobnie przymiotniki mają listę klas, do których pasują (зелени цвет tak, зелена вест nie). "
      "Zaimki 1. i 2. osoby mogą być tylko ludźmi.")

    p("5.6. Wyniki", "h2")
    pairs = [(g.Pronoun("1", "sg", "m"), verbs[[v.inf for v in verbs].index("pročitati")],
              g.NounPhrase(noun["knjiga"], "sg", "novi", det["moj"]))]
    s, v, o = pairs[0]
    rows = [["Strona", "Tryb", "Czas", "Typ", "Polaryz.", "Zdanie"]]
    for voice, mood, tense, st, pol, text in g.all_forms(s, v, o):
        rows.append([voice, mood, tense, st, pol, g.cyr(text)])
    table(rows, [1.3 * cm, 2.1 * cm, 2.7 * cm, 1.8 * cm, 1.6 * cm, 7.3 * cm],
          f"Wszystkie {len(rows) - 1} formy dla jednej trójki: ја + прочитати + (мој + нови + књига) "
          "(strona bierna: „Moja nowa książka została przeczytana”).", font_size=6.4)
    combos = read_csv(os.path.join(RESULTS_DIR, "lab05", "losowe_zdania.csv"))
    rows = [["Lp", "Zdanie", "Cechy"]]
    for r in combos[:40]:
        rows.append([r["lp"], r["zdanie_cyrylica"],
                     f"{r['strona']}, {r['tryb']}, {r['czas']}, {r['typ_zdania']}, {r['polaryzacja']}"])
    table(rows, [0.8 * cm, 9.2 * cm, 6.8 * cm], "Pierwsze 40 z 200 losowych zdań (pełna lista: "
          "wyniki/lab05/losowe_zdania.csv).", font_size=6.6)
    p(f"Pełne wyniki są w folderze {mono('wyniki/lab05/')}: raport.txt (leksykon, pełne odmiany "
      "czterech trójek SVO – z czasownikiem przechodnim dokonanym i niedokonanym, nieprzechodnim "
      "i zwrotnym – oraz 200 losowych zdań), tabele CSV leksykonu i zdań. Generator można też "
      f"uruchomić interaktywnie: {mono('python lab05_generator_svo.py -n 20 --lacinka')}. "
      "Poprawność sprawdza 16 zdań wzorcowych zweryfikowanych ręcznie (rozdział 6).")


# ---------------------------------------------------------------------------
# Weryfikacja, podsumowanie, bibliografia
# ---------------------------------------------------------------------------
def verification():
    story.append(PageBreak())
    p("6. Sprawdzenie poprawności wyników", "h1")
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
    p("7. Podsumowanie", "h1")
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
    import leksykon_svo as lx
    core = read_csv(os.path.join(R3, "rdzen_100.csv"))

    p("Realizacja wymagań", "h2")
    rows = [["Wymaganie", "Jak zrealizowano", "Wynik", "Rozdz."],
            ["<b>1. Analiza statystyczna</b>", "", "", ""],
            ["Korpus min. 100 000 wyrazów", "Wikipedia, zostawienie tylko 30 liter cyrylicy",
             f"{num(len(words))} wyrazów", "1"],
            ["Prawo Zipfa", "regresja w skali log-log", f"s = {fmt(s, 3)}", "3.2"],
            ["Wyrazy potrzebne do rozumienia 90% tekstu", "sortowanie i sumowanie udziałów",
             f"{num(k90)} wyrazów (lista CSV)", "3.1"],
            ["Rdzeń języka: 100 wyrazów o najwięcej sąsiadach", "graf sąsiedztwa, ranking stopni węzłów",
             f"100 wyrazów, od {core[0]['wyraz']} do {core[-1]['wyraz']}", "3.3"],
            ["(dodatkowo) entropia i kod Huffmana", "H = −Σ p log₂ p, algorytm Huffmana",
             f"H = {fmt(H, 3)}, L = {fmt(L, 3)} bit/znak", "2"],
            ["<b>2. Analiza syntaktyczna</b>", "", "", ""],
            ["Generator zdań SVO; podmiot i dopełnienie: fraza rzeczownikowa lub zaimek",
             "lab05_generator_svo.py, odmiana przez przypadki, enklityki", "losowe zdania + pełne odmiany", "5"],
            ["Czasowniki nieprzechodnie, przechodnie, zwrotne",
             "typ czasownika w leksykonie", f"{sum(v['typ'] == 'tr' for v in lx.VERBS)} / "
             f"{sum(v['typ'] == 'intr' for v in lx.VERBS)} / {sum(v['typ'] == 'refl' for v in lx.VERBS)}", "5.1"],
            ["Wszystkie czasy, tryby (oznajmujący, pytający, przeczący, rozkazujący, przypuszczający), strony",
             "7 czasów + 2 potencjały + imperatyw; pytanie, przeczenie; strona czynna i bierna",
             "do 60 form na trójkę SVO", "5.3"],
            ["Min. 100 rzeczowników, 100 czasowników, 100 przymiotników", "leksykon_svo.py",
             f"{len(lx.NOUNS)} / {len(lx.VERBS)} / {len(lx.ADJECTIVES)}", "5.1"],
            ["Fraza rzecz.: [rodzajnik/zaimek] [przymiotnik] rzeczownik",
             "zaimki wskazujące, dzierżawcze (z svoj), nieokreślone (jedan ≈ rodzajnik)",
             f"{len(lx.DETERMINERS) + 1} określników", "5.2"],
            ["<b>3. Analiza semantyczna</b>", "", "", ""],
            ["Min. 1000 rzeczowników, 100 czasowników przechodnich",
             "analiza składniowa (stanza), korpus dodatkowy",
             f"{len(summ['rzeczowniki'])} rzeczowników, {len(summ['czasowniki'])} czasowników", "4.1–4.3"],
            ["Wektory 100 składowych = liczby fraz VO", "relacja obj z parsera", "macierz 1000 × 100", "4.4"],
            ["Sieć Kohonena z 50 neuronami", f"własna implementacja SOM {summ['som']['wiersze']} × "
             f"{summ['som']['kolumny']}", f"błąd topogr. {fmt(summ['blad_topograficzny'] * 100, 1)}%", "4.5"],
            ["Analiza klastrów: pola semantyczne, ich liczba, neurony martwe",
             "ręczna analiza zawartości neuronów, spójność klastrów",
             f"pola semantyczne: {summ['liczba_pol']}, neurony martwe: {len(summ['martwe_neurony'])}", "4.6–4.7"],
            ["Sprawozdanie PDF, kod w repozytorium", "generuj_sprawozdanie.py, git", "ten dokument + README", "–"]]
    table(rows, [5.4 * cm, 5.4 * cm, 4.4 * cm, 1.6 * cm], "Lista wymagań i miejsce ich realizacji.",
          font_size=7.2)

    p("Najważniejsze wnioski", "h2")
    bullets([
        f"<b>Statystyka:</b> rozkład liter jest nierównomierny, dlatego kod Huffmana ({fmt(L, 2)} bit/znak) "
        f"jest tylko o {fmt(L - H, 3)} bitu dłuższy od entropii ({fmt(H, 2)} bit/znak). Częstości wyrazów "
        f"spełniają prawo Zipfa (s = {fmt(s, 2)}). Do zrozumienia 90% tekstu potrzeba aż {num(k90)} "
        "wyrazów, bo serbski ma bogatą odmianę. Rdzeń języka tworzą słowa funkcyjne (spójniki, "
        "przyimki, czasownik бити).",
        "<b>Semantyka:</b> " + KOHONEN_CONCLUSION,
        "<b>Składnia:</b> generator tworzy poprawne zdania we wszystkich 7 czasach, 3 trybach, "
        "w zdaniach pytających i przeczących oraz w stronie czynnej i biernej. Najważniejsze dla "
        "poprawności okazały się: zgoda imiesłowów z podmiotem, biernik rzeczowników żywotnych "
        "i reguły szyku enklityk.",
    ])
    p("Uruchomienie programu", "h2")
    p(f"{mono('pip install -r requirements.txt')}, a następnie {mono('python uruchom_wszystko.py')} "
      "(lub kolejno lab01.py → lab02… → lab03… → lab04_pobieranie.py → lab04_parsowanie.py → "
      "lab04_kohonen.py → lab05_generator_svo.py → sprawdz_wyniki.py → generuj_sprawozdanie.py). "
      "Pobrane korpusy i wyniki analizy składniowej są w repozytorium, więc pełne przeliczenie "
      "trwa kilka minut.")

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


# Opis wyników lab 4 (interpretacja zawartości klastrów dla ziarna SEED = 42 w lab04_kohonen.py)
KOHONEN_DEAD_COMMENT = (
    "Wszystkie neurony się czegoś nauczyły. Wynika to z proporcji danych do rozmiaru sieci: na jeden "
    "neuron przypada średnio 20 rzeczowników, a szerokie sąsiedztwo na początku uczenia rozciąga całą "
    "siatkę na obszar zajmowany przez dane, zanim neurony się wyspecjalizują. Najmniejsze klastry "
    "(3–7 rzeczowników) leżą na granicach dużych skupień i zbierają rzeczowniki o nietypowych "
    "profilach – to neurony, które nauczyły się „niewiele”: nie reprezentują żadnego pola znaczeniowego.")
KOHONEN_INTERPRETATION = (
    "<b>Ocena klastrów.</b> Sieć rzeczywiście spontanicznie wytworzyła klastry, w których rzeczowniki "
    "należą do wspólnego pola semantycznego. Najbardziej jednorodne są klastry wyznaczone przez "
    "czasowniki o wąskim zakresie dopełnień:"
    "<br/>• <b>trofea i zawody sportowe</b> (освојити – zdobyć): титула, медаља, првенство, турнир, лига, "
    "куп, бод, поен;"
    "<br/>• <b>substancje i składniki chemiczne</b> (садржати – zawierać): киселина, бакар, кисеоник, "
    "протеин, шећер, маст, литијум;"
    "<br/>• <b>skutki negatywne</b> – dwa sąsiednie neurony (изазвати, узроковати – wywołać, "
    "spowodować): болест, смрт, бол, повреда, оштећење, депресија, загађење;"
    "<br/>• <b>decyzje i akty prawne</b> (донети, усвојити – podjąć, uchwalić): одлука, закон, "
    "декларација, резолуција, акт;"
    "<br/>• <b>działania wojenne i polityczne</b> (извршити – dokonać, водити – prowadzić): инвазија, "
    "напад, реформа; рат, политика, борба, преговор;"
    "<br/>• <b>państwa i instytucje</b> (основати – założyć): царство, колонија, република, школа, "
    "друштво, болница; obok nich <b>grupy i organizacje</b> (формирати – utworzyć): група, влада, "
    "заједница, организација;"
    "<br/>• <b>prawa i status</b> (стећи – zdobyć, uzyskać): право, статус, контрола, независност; "
    "<b>nazwy</b> (добити – otrzymać): име, облик, значење, изглед."
    "<br/><b>Topologia.</b> Pokrewne pola leżą obok siebie: dwa neurony skutków negatywnych sąsiadują "
    "z procesami i zmianami, pola „prawa i status” i „nazwy otrzymywane” są w sąsiednich neuronach "
    "dolnego wiersza, a „państwa i instytucje” stykają się z „grupami i organizacjami”."
    "<br/><b>Ograniczenia.</b> 11 klastrów uznaliśmy za niejednorodne. Są to głównie neurony "
    "czasowników o bardzo ogólnym znaczeniu (укључивати – obejmować, чинити – stanowić, давати – dawać, "
    "немати – nie mieć), które przyjmują dopełnienia z dowolnego pola. Rzeczowniki konkretne "
    "(zwierzęta, jedzenie, ubrania) rzadko występują w encyklopedycznym tekście jako dopełnienie "
    "i mają tylko kilka fraz VO, dlatego nie utworzyły osobnych klastrów, tylko trafiły do klastrów "
    "mieszanych. Sieć grupuje więc rzeczowniki według <i>zachowania składniowego</i>: tam, gdzie "
    "czasownik jest wybiórczy, daje to jednorodne pole znaczeniowe; tam, gdzie jest ogólny – mieszankę."
)
KOHONEN_CONCLUSION = (
    "sieć Kohonena z 50 neuronami, ucząc się bez nauczyciela na wektorach fraz VO 1000 rzeczowników, "
    "wytworzyła 35 jednorodnych klastrów tworzących 33 pola semantyczne (m.in. sport, substancje "
    "chemiczne, choroby i szkody, akty prawne, wojna, instytucje, prawa i status). 11 klastrów jest "
    "mieszanych (czasowniki ogólne), a żaden neuron nie jest martwy. Kluczowe okazało się ważenie IDF, "
    "które osłabia czasowniki łączące się ze wszystkim (имати)."
)

S["h1x"] = ParagraphStyle("h1x", parent=S["h1"])  # nagłówek spisu treści (nie trafia do spisu)


def build():
    os.makedirs(FIG_DIR, exist_ok=True)
    doc = ReportDoc(OUTPUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                    topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                    title="Przetwarzanie języka naturalnego – sprawozdanie",
                    author=AUTHOR or "student", subject="Laboratoria 1–5: język serbski")
    title_page()
    contents()
    introduction()
    lab1()
    lab2()
    lab3()
    lab4()
    lab5()
    verification()
    conclusion()
    doc.multiBuild(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Zapisano {OUTPUT}")


if __name__ == "__main__":
    build()
