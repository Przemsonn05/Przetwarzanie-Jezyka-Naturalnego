"""
Generuje sprawozdanie PDF (sprawozdanie/sprawozdanie.pdf) z wyników lab01-lab04.
Wszystkie liczby, tabele i wykresy są wczytywane z plików w folderach dane/ i wyniki/,
więc po ponownym uruchomieniu laboratoriów wystarczy ponownie uruchomić ten skrypt.
"""
import csv
import datetime
import json
import math
import os
import re
from collections import Counter

import matplotlib
import numpy as np
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from slownik import GLOSSARY

AUTHOR = ""  # wpisz imię i nazwisko, np. AUTHOR = "Jan Kowalski"
OUTPUT = os.path.join("sprawozdanie", "sprawozdanie.pdf")
R3 = os.path.join("wyniki", "lab03")
R4 = os.path.join("wyniki", "lab04")

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
GRID = colors.HexColor("#b8c4d0")

S = {
    "title": ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=22, leading=28,
                            alignment=TA_CENTER, textColor=ACCENT, spaceAfter=10),
    "subtitle": ParagraphStyle("subtitle", fontName="DejaVu", fontSize=13, leading=18,
                               alignment=TA_CENTER, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=16, leading=21, textColor=ACCENT,
                         spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=12, leading=16, textColor=ACCENT,
                         spaceBefore=10, spaceAfter=5),
    "body": ParagraphStyle("body", fontName="DejaVu", fontSize=9.5, leading=13.5, alignment=TA_JUSTIFY,
                           spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName="DejaVu", fontSize=9.5, leading=13.5, leftIndent=14,
                             bulletIndent=4, spaceAfter=2),
    "caption": ParagraphStyle("caption", fontName="DejaVu-Oblique", fontSize=8.5, leading=11,
                              alignment=TA_CENTER, textColor=colors.HexColor("#444444"), spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName="DejaVu", fontSize=7.5, leading=9.5),
    "code": ParagraphStyle("code", fontName="DejaVuMono", fontSize=7.5, leading=10, leftIndent=8,
                           backColor=colors.HexColor("#f5f5f5"), borderPadding=4, spaceAfter=8),
}

story = []


def p(text, style="body"):
    story.append(Paragraph(text, S[style]))


def bullets(items):
    for it in items:
        story.append(Paragraph(it, S["bullet"], bulletText="•"))


def table(rows, widths, font_size=7.5, header_rows=1, align_right_from=None, zebra=True):
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
    if zebra:
        for i in range(header_rows, len(rows)):
            if (i - header_rows) % 2:
                style.append(("BACKGROUND", (0, i), (-1, i), LIGHT))
    t.setStyle(TableStyle(style))
    # krótkie tabele nie są dzielone między strony
    story.append(KeepTogether([t]) if len(rows) <= 30 else t)
    story.append(Spacer(1, 6))


def figure(path, width_cm, caption):
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    width = width_cm * cm
    story.append(KeepTogether([Image(path, width=width, height=width * h / w),
                               Paragraph(caption, S["caption"])]))


def read_csv(path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def gloss(word):
    g = GLOSSARY.get(word)
    return f"{word} <font color='#666666'>({g})</font>" if g else word


def fmt(x, nd=2):
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


def num(x):
    return f"{x:,}".replace(",", " ")


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(colors.HexColor("#777777"))
    if doc.page > 1:
        canvas.drawString(2 * cm, 1.2 * cm, "Przetwarzanie języka naturalnego – sprawozdanie (język serbski)")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"strona {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Strona tytułowa
# ---------------------------------------------------------------------------
def title_page():
    story.append(Spacer(1, 5 * cm))
    p("Przetwarzanie języka naturalnego", "title")
    p("Sprawozdanie z laboratoriów 1–4", "subtitle")
    p("Analiza korpusu języka serbskiego: entropia i kodowanie Huffmana, prawo Zipfa, "
      "graf sąsiedztwa wyrazów, sieć Kohonena", "subtitle")
    story.append(Spacer(1, 3 * cm))
    author = AUTHOR or "...................................................."
    rows = [["Autor", author],
            ["Język korpusu", "serbski (cyrylica, 30 liter)"],
            ["Źródło danych", "serbska Wikipedia (sr.wikipedia.org), API MediaWiki"],
            ["Język programowania", "Python 3 (numpy, scipy, matplotlib, networkx, stanza, reportlab)"],
            ["Data", datetime.date.today().strftime("%d.%m.%Y")]]
    t = Table([[Paragraph(f"<b>{a}</b>", S["body"]), Paragraph(b, S["body"])] for a, b in rows],
              colWidths=[4.5 * cm, 10.5 * cm], hAlign="CENTER")
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, GRID),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(t)
    story.append(PageBreak())


# ---------------------------------------------------------------------------
# Lab 1
# ---------------------------------------------------------------------------
def lab1():
    raw = open("surowy_serbski.txt", encoding="utf-8").read()
    clean = open("oczyszczony_serbski.txt", encoding="utf-8").read()
    articles = [a for a in open(os.path.join("dane", "artykuly.txt"), encoding="utf-8").read().split("\n") if a]
    words = clean.split()

    p("1. Laboratorium 1 – wybór języka i pozyskanie korpusu", "h1")
    p("<b>Cel:</b> wybrać język, pobrać duży tekst w tym języku i zostawić z niego sam korpus wyrazów.")
    p("Wybrano <b>język serbski</b> zapisany cyrylicą. Tekst pobrano z serbskiej Wikipedii przez API "
      "MediaWiki (<font face='DejaVuMono'>action=query&amp;prop=extracts&amp;explaintext=1</font>). "
      "Skrypt <font face='DejaVuMono'>lab01.py</font> pobiera kolejne artykuły z listy, aż zbierze co "
      "najmniej 1 000 000 znaków. Pomija artykuły krótsze niż 5000 znaków (szablonowe zalążki) "
      "i duplikaty. Między zapytaniami robi 1,5-sekundową przerwę i przedstawia się nagłówkiem "
      "User-Agent, zgodnie z zasadami API Wikipedii.")
    p(f"Pobrano {len(articles)} artykułów: {', '.join(articles)}.")
    p("Czyszczenie (<font face='DejaVuMono'>clean_text</font>): tekst zamieniany jest na małe litery, "
      "a każdy znak spoza 30-literowego alfabetu serbskiego "
      "(<font face='DejaVuMono'>абвгдђежзијклљмнњопрстћуфхцчџш</font>) zastępowany spacją. "
      "Usuwane są więc interpunkcja, cyfry, znaki specjalne, indeksy typu „²”, wyrazy w łacince "
      "i w alfabecie greckim. Na końcu wielokrotne białe znaki są zwijane do jednej spacji.")
    # przykładowy fragment z liczbami i interpunkcją
    candidates = [m.group(0).strip() for m in re.finditer(r"[^.\n]{120,260}\.", raw)
                  if re.search(r"\d", m.group(0)) and re.search(r"[,()–-]", m.group(0))]
    frag = candidates[0] if candidates else raw[:260]
    p("Przykład – fragment surowy i po oczyszczeniu:", "body")
    story.append(Paragraph(frag, S["code"]))
    story.append(Paragraph(re.sub(r"\s+", " ", re.sub(r"[^абвгдђежзијклљмнњопрстћуфхцчџш]", " ",
                                                         frag.lower())).strip(), S["code"]))
    table([["Wielkość", "Wartość"],
           ["Liczba znaków tekstu surowego", num(len(raw))],
           ["Liczba znaków po oczyszczeniu", num(len(clean))],
           ["Liczba wyrazów (tokenów)", num(len(words))],
           ["Liczba różnych wyrazów", num(len(set(words)))],
           ["Liczba różnych znaków w korpusie", f"{len(set(clean))} (30 liter + spacja)"]],
          [8 * cm, 5 * cm])
    p("Wynik zapisano w pliku <font face='DejaVuMono'>oczyszczony_serbski.txt</font>, "
      "a tekst surowy w <font face='DejaVuMono'>surowy_serbski.txt</font>. Tekstu surowego "
      "potrzebuje laboratorium 4, bo do analizy składniowej niezbędne są granice zdań.")


# ---------------------------------------------------------------------------
# Lab 2
# ---------------------------------------------------------------------------
def lab2():
    story.append(PageBreak())
    p("2. Laboratorium 2 – statystyka liter, entropia i kodowanie Huffmana", "h1")
    p("<b>Cel:</b> upewnić się, że został sam korpus, policzyć udział procentowy (prawdopodobieństwo) "
      "każdej litery, entropię tekstu i kody Huffmana, a następnie porównać średnią długość kodu "
      "z entropią.")
    p("Skrypt <font face='DejaVuMono'>lab02_entropia_huffman.py</font> wczytuje korpus i jeszcze raz "
      "go czyści. Potem sprawdza, czy zostały w nim wyłącznie litery alfabetu serbskiego i spacje. "
      "Weryfikacja wypadła pomyślnie: korpus nie zawiera żadnych innych znaków, a występują w nim "
      "wszystkie 30 liter.")

    results = {}
    for key, fname in (("litery", "statystyka_litery.csv"), ("spacja", "statystyka_litery_spacja.csv")):
        rows = read_csv(os.path.join("wyniki", fname))
        n = sum(int(r["licznosc"]) for r in rows)
        probs = [int(r["licznosc"]) / n for r in rows]
        H = -sum(q * math.log2(q) for q in probs)
        L = sum(q * len(r["kod_huffmana"]) for q, r in zip(probs, rows))
        results[key] = (rows, n, H, L, len(rows))

    rows, n, H, L, k = results["litery"]
    p("2.1. Prawdopodobieństwa liter i kody Huffmana", "h2")
    p(f"Tabela 1 pokazuje statystykę {k} liter w korpusie bez spacji ({num(n)} liter). "
      "Prawdopodobieństwo litery to p = n / N. Kody Huffmana zbudowano algorytmem zachłannym: "
      "dwa węzły o najmniejszych wagach są wielokrotnie łączone przy użyciu kolejki priorytetowej "
      "<font face='DejaVuMono'>heapq</font>.")
    data = [["Lp", "Litera", "Liczność", "Udział [%]", "p", "−log₂ p", "Kod Huffmana", "Dł."]]
    for i, r in enumerate(rows, 1):
        q = int(r["licznosc"]) / n
        data.append([i, r["znak"], num(int(r["licznosc"])), fmt(q * 100, 3), fmt(q, 5),
                     fmt(-math.log2(q), 3), f"<font face='DejaVuMono'>{r['kod_huffmana']}</font>",
                     len(r["kod_huffmana"])])
    data.append(["", "<b>Suma</b>", num(n), "100,000", "1,00000", "", "", ""])
    table(data, [1 * cm, 1.4 * cm, 2 * cm, 2 * cm, 1.9 * cm, 1.7 * cm, 3.2 * cm, 1 * cm])
    p("Tabela 1. Udział liter w korpusie (bez spacji) i kody Huffmana.", "caption")

    p("2.2. Entropia i porównanie z kodem Huffmana", "h2")
    p("Entropia Shannona H = −Σ p<sub>i</sub> log<sub>2</sub> p<sub>i</sub> to dolna granica średniej "
      "liczby bitów na znak dla dowolnego kodu bezprefiksowego. Średnia długość kodu Huffmana to "
      "L = Σ p<sub>i</sub> · l<sub>i</sub>. Policzono dwa warianty: same litery oraz litery "
      "ze spacją jako 31. symbolem.")
    data = [["Wariant", "n", "H [bit]", "H<sub>max</sub> = log₂ n", "Redund.",
             "L Huffmana [bit]", "L − H", "H / L", "Kod stały"]]
    for key, label in (("litery", "same litery"), ("spacja", "litery + spacja")):
        _, n_, H_, L_, k_ = results[key]
        hmax = math.log2(k_)
        data.append([label, k_, fmt(H_, 4), fmt(hmax, 4), f"{fmt((1 - H_ / hmax) * 100)} %",
                     fmt(L_, 4), fmt(L_ - H_, 4), f"{fmt(H_ / L_ * 100)} %", f"{math.ceil(hmax)} bit"])
    table(data, [2.6 * cm, 0.9 * cm, 1.6 * cm, 2.3 * cm, 1.7 * cm, 2.6 * cm, 1.5 * cm, 1.7 * cm, 1.6 * cm])
    p("Tabela 2. Entropia a średnia długość kodu Huffmana.", "caption")
    hl = results["litery"]
    saving = (1 - hl[3] / 5) * 100
    p("<b>Wnioski.</b>", "body")
    bullets([
        f"Średnia długość kodu Huffmana ({fmt(hl[3], 4)} bit) jest tylko o {fmt(hl[3] - hl[2], 4)} bitu "
        f"większa od entropii ({fmt(hl[2], 4)} bit). Spełniony jest warunek H ≤ L &lt; H + 1, "
        f"a efektywność kodu wynosi {fmt(hl[2] / hl[3] * 100)}%.",
        "Różnica L − H bierze się z tego, że długości słów kodowych muszą być liczbami całkowitymi, "
        "a prawdopodobieństwa liter nie są potęgami 1/2.",
        f"W porównaniu z kodem o stałej długości (5 bitów na 30 liter) kod Huffmana skraca zapis "
        f"tekstu o ok. {fmt(saving, 1)}%.",
        "Najczęstsze litery (а, и, о, е) dostają kody 3–4-bitowe, a najrzadsze (ђ, ф, џ) kody "
        "8–9-bitowe.",
        "Kod sprawdzono, kodując i dekodując cały korpus: dekodowanie odtworzyło tekst bez zmian.",
    ])


# ---------------------------------------------------------------------------
# Lab 3
# ---------------------------------------------------------------------------
def lab3():
    story.append(PageBreak())
    p("3. Laboratorium 3 – pokrycie tekstu, prawo Zipfa, graf sąsiedztwa", "h1")
    zipf = read_csv(os.path.join(R3, "zipf.csv"))
    freqs = np.array([int(r["licznosc"]) for r in zipf], dtype=float)
    total, types = int(freqs.sum()), len(freqs)
    cum = np.cumsum(freqs) / total

    p("3.1. Wyrazy pokrywające 90% tekstu", "h2")
    k90 = int(np.searchsorted(cum, 0.9) + 1)
    hapax = int(np.sum(freqs == 1))
    p(f"Korpus zawiera {num(total)} wyrazów (tokenów) i {num(types)} różnych wyrazów (typów). "
      f"Wyrazy posortowano malejąco według liczności i sumowano ich udziały, aż łączny udział "
      f"osiągnął 90%. <b>Do pokrycia 90% tekstu potrzeba {num(k90)} najczęstszych wyrazów</b>, "
      f"czyli {fmt(k90 / types * 100)}% słownika. Aż {num(hapax)} wyrazów "
      f"({fmt(hapax / types * 100, 1)}%) występuje tylko raz (tzw. hapax legomena).")
    data = [["Pokrycie tekstu", "Liczba wyrazów", "Udział w słowniku"]]
    for lvl in (0.25, 0.5, 0.75, 0.8, 0.9, 0.95, 0.99):
        k = int(np.searchsorted(cum, lvl - 1e-12) + 1)
        data.append([f"{int(lvl * 100)}%", num(k), f"{fmt(k / types * 100)}%"])
    table(data, [4 * cm, 4 * cm, 4 * cm])
    p("Tabela 3. Liczba najczęstszych wyrazów potrzebna do pokrycia danej części tekstu.", "caption")
    top = read_csv(os.path.join(R3, "wyrazy_pokrycie_90.csv"))[:20]
    data = [["Ranga", "Wyraz", "Liczność", "Udział [%]", "Pokrycie skum. [%]"] * 2]
    for i in range(10):
        a, b = top[i], top[i + 10]
        data.append([a["ranga"], gloss(a["wyraz"]), a["licznosc"], a["udzial_procent"].replace(".", ","),
                     a["pokrycie_skumulowane_procent"].replace(".", ","),
                     b["ranga"], gloss(b["wyraz"]), b["licznosc"], b["udzial_procent"].replace(".", ","),
                     b["pokrycie_skumulowane_procent"].replace(".", ",")])
    table(data, [0.9 * cm, 2.9 * cm, 1.2 * cm, 1.3 * cm, 1.7 * cm] * 2, font_size=6.8)
    p("Tabela 4. 20 najczęstszych wyrazów korpusu. Pełna lista "
      f"{num(k90)} wyrazów jest w pliku wyniki/lab03/wyrazy_pokrycie_90.csv.", "caption")
    figure(os.path.join(R3, "pokrycie_tekstu.png"), 13, "Rys. 1. Pokrycie tekstu przez najczęstsze wyrazy.")

    p("3.2. Prawo Zipfa", "h2")
    ranks = np.arange(1, types + 1)
    s, c = np.polyfit(np.log10(ranks), np.log10(freqs), 1)
    pred = c + s * np.log10(ranks)
    r2 = 1 - np.sum((np.log10(freqs) - pred) ** 2) / np.sum((np.log10(freqs) - np.log10(freqs).mean()) ** 2)
    m = freqs >= 2
    s2 = np.polyfit(np.log10(ranks[m]), np.log10(freqs[m]), 1)[0]
    p("Prawo Zipfa mówi, że częstość wyrazu jest odwrotnie proporcjonalna do jego rangi: "
      "f(r) ≈ C / r<super>s</super>, gdzie s ≈ 1. Wtedy iloczyn r · f(r) jest w przybliżeniu stały. "
      "Parametry wyznaczono regresją liniową w skali log-log: "
      "log f = log C − s · log r.")
    table([["Dopasowanie", "Wykładnik s", "C", "R²"],
           [f"wszystkie wyrazy ({num(types)})", fmt(-s, 4), fmt(10 ** c, 1), fmt(r2, 4)],
           [f"bez hapaksów, f ≥ 2 ({num(int(m.sum()))})", fmt(-s2, 4), "", ""]],
          [6 * cm, 3 * cm, 3 * cm, 2.5 * cm])
    p("Tabela 5. Parametry prawa Zipfa dla korpusu.", "caption")
    data = [["Ranga r", "Wyraz", "f(r)", "r · f(r)"]]
    for rk in (1, 2, 3, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000):
        r = zipf[rk - 1]
        data.append([rk, gloss(r["wyraz"]), r["licznosc"], num(int(r["ranga_razy_licznosc"]))])
    table(data, [2 * cm, 5.5 * cm, 2 * cm, 2.5 * cm])
    p("Tabela 6. Iloczyn rangi i częstości dla wybranych rang.", "caption")
    figure(os.path.join(R3, "prawo_zipfa.png"), 16.5,
           "Rys. 2. Prawo Zipfa: częstość w funkcji rangi (log-log) oraz iloczyn r · f(r).")
    p(f"<b>Wniosek.</b> W skali log-log punkty układają się niemal na prostej (R² = {fmt(r2, 3)}), "
      f"a wykładnik s = {fmt(-s, 2)} jest bliski klasycznej wartości 1, więc korpus spełnia prawo Zipfa. "
      "Odchylenia widać dla kilku pierwszych rang (słowa funkcyjne и, у, је) oraz w ogonie, "
      "gdzie wiele wyrazów ma tę samą małą częstość (schodki na wykresie). Lekkie spłaszczenie "
      "rozkładu (s &lt; 1) wynika z odmiany wyrazów w serbskim: formy србија, србије, србији, "
      "србију liczone są osobno. Przy dziesięciokrotnie mniejszym korpusie (100 tys. znaków) "
      "wykładnik wynosił tylko 0,68, co pokazuje, że prawo Zipfa ujawnia się wyraźnie dopiero "
      "na dużych tekstach.")

    p("3.3. Graf wyrazów sąsiadujących i jego rdzeń", "h2")
    words = open("oczyszczony_serbski.txt", encoding="utf-8").read().split()
    edges = {tuple(sorted(e)) for e in zip(words, words[1:]) if e[0] != e[1]}
    directed = {e for e in zip(words, words[1:]) if e[0] != e[1]}
    deg = read_csv(os.path.join(R3, "stopnie_wezlow.csv"))
    degrees = np.array([int(r["liczba_sasiadow"]) for r in deg])
    p("Graf zbudowano tak: węzłem jest wyraz, a krawędź łączy dwa wyrazy, które choć raz stoją "
      "w tekście bezpośrednio obok siebie. Dla każdego węzła zliczono krawędzie wychodzące "
      "(różne wyrazy występujące bezpośrednio po nim), wchodzące (różne wyrazy występujące "
      "bezpośrednio przed nim) oraz liczbę wszystkich różnych sąsiadów. <b>Rdzeń</b> grafu to "
      "100 wyrazów o największej liczbie sąsiadów.")
    table([["Wielkość", "Wartość"],
           ["Liczba węzłów (różnych wyrazów)", num(len(deg))],
           ["Liczba krawędzi skierowanych (a → b)", num(len(directed))],
           ["Liczba krawędzi nieskierowanych (a — b)", num(len(edges))],
           ["Średnia / mediana liczby sąsiadów", f"{fmt(degrees.mean())} / {int(np.median(degrees))}"],
           ["Maksymalna liczba sąsiadów", f"{num(int(degrees.max()))} ({deg[0]['wyraz']})"]],
          [8 * cm, 5 * cm])
    core = read_csv(os.path.join(R3, "rdzen_100.csv"))
    data = [["Lp", "Wyraz", "Sąs.", "Wych.", "Wch.", "Częst."] * 2]
    for i in range(50):
        a, b = core[i], core[i + 50]
        data.append([a["lp"], gloss(a["wyraz"]), a["liczba_sasiadow"], a["krawedzie_wychodzace"],
                     a["krawedzie_wchodzace"], a["licznosc"],
                     b["lp"], gloss(b["wyraz"]), b["liczba_sasiadow"], b["krawedzie_wychodzace"],
                     b["krawedzie_wchodzace"], b["licznosc"]])
    table(data, [0.8 * cm, 3.5 * cm, 1 * cm, 1 * cm, 1 * cm, 1.1 * cm] * 2, font_size=6.3)
    p("Tabela 7. Rdzeń grafu – 100 wyrazów o największej liczbie sąsiadów "
      "(Sąs. – różni sąsiedzi, Wych./Wch. – krawędzie wychodzące/wchodzące, Częst. – liczność).",
      "caption")
    core_words = {r["wyraz"] for r in core}
    top100 = {r["wyraz"] for r in zipf[:100]}
    cover = sum(int(r["licznosc"]) for r in core) / total
    figure(os.path.join(R3, "rdzen_grafu.png"), 15,
           "Rys. 3. Podgraf rdzenia (wielkość węzła ~ liczba sąsiadów w całym grafie).")
    figure(os.path.join(R3, "rozklad_stopni.png"), 10.5,
           "Rys. 4. Rozkład liczby sąsiadów w grafie (skala log-log).")
    p("<b>Wnioski.</b>", "body")
    bullets([
        f"Wyrazy rdzenia stanowią {fmt(cover * 100, 1)}% wszystkich wyrazów tekstu, "
        f"a {len(core_words & top100)} ze 100 z nich należy też do 100 najczęstszych wyrazów.",
        "Rdzeń tworzą głównie słowa funkcyjne: spójniki (и, а, али), przyimki (у, на, од, са, за) "
        "i formy czasownika бити (је, су). Łączą się one z bardzo wieloma różnymi wyrazami.",
        "Rozkład liczby sąsiadów jest silnie skośny i w skali log-log zbliżony do potęgowego. "
        "Mediana to tylko 2 sąsiadów, a maksimum przekracza 6000. Graf ma więc strukturę "
        "„bezskalową” z kilkoma silnie połączonymi hubami.",
        "Ranking według samych krawędzi wychodzących daje rdzeń pokrywający się z powyższym "
        "w ok. 83%. Obie miary są podane w tabeli.",
    ])


# ---------------------------------------------------------------------------
# Lab 4
# ---------------------------------------------------------------------------
def lab4():
    story.append(PageBreak())
    summ = json.load(open(os.path.join(R4, "podsumowanie.json"), encoding="utf-8"))
    A, B, C = (summ["warianty"][k] for k in "ABC")
    som = summ["som"]

    p("4. Laboratorium 4 – sieć Kohonena dla rzeczowników i czasowników przechodnich", "h1")
    p("<b>Cel:</b> wybrać 50 rzeczowników i 100 czasowników przechodnich. Każdy rzeczownik "
      "opisać wektorem o 100 składowych, w którym składowa i to liczba kolokacji rzeczownika "
      "z i-tym czasownikiem. Te 50 wektorów tworzy zbiór treningowy dla sieci Kohonena. "
      "Mapa sieci pokazuje, jak rzeczowniki układają się w 100-wymiarowej przestrzeni "
      "czasowników. Na koniec sprawdzono, jak wynik zależy od wyboru czasowników.")

    p("4.1. Analiza składniowa korpusu", "h2")
    p("Żeby wiedzieć, który rzeczownik jest dopełnieniem którego czasownika i które czasowniki są "
      "przechodnie, potrzebna jest analiza morfologiczna i składniowa. Użyto biblioteki "
      "<b>stanza</b> (Stanford NLP) z modelem dla języka serbskiego (treebank SETimes.SR, "
      "standard Universal Dependencies). Skrypt <font face='DejaVuMono'>lab04_parsowanie.py</font>:")
    bullets([
        "wczytuje tekst surowy z lab 1 (z interpunkcją, bo potrzebne są granice zdań) "
        "i usuwa z niego nagłówki sekcji Wikipedii,",
        "transliteruje cyrylicę na łacinkę, bo model był trenowany na serbskiej łacince. "
        "Alfabety serbskie odpowiadają sobie 1:1, np. љ → lj, њ → nj, џ → dž, ћ → ć,",
        "wykonuje tokenizację, znakowanie częściami mowy (UPOS), lematyzację i parsowanie "
        "zależnościowe,",
        "przepisuje lematy z powrotem na cyrylicę i zapisuje wynik do "
        "<font face='DejaVuMono'>dane/korpus_sparsowany.tsv.gz</font>.",
    ])
    p(f"Wynik: {num(summ['zdania'])} zdań, {num(summ['tokeny'])} tokenów (razem ze znakami interpunkcji), "
      f"{num(summ['rozne_czasowniki'])} różnych lematów czasowników, "
      f"{num(summ['rozne_rzeczowniki'])} różnych lematów rzeczowników oraz "
      f"<b>{num(summ['relacje_obj'])} relacji czasownik → dopełnienie rzeczownikowe</b> "
      "(relacja <font face='DejaVuMono'>obj</font>). Przykład analizy zdania "
      "„Кнез Лазар је подигао цркву и водио војску”: "
      "obj(подићи, црква), obj(водити, војска).")

    p("4.2. Wybór czasowników przechodnich i rzeczowników", "h2")
    p("Czasownik przechodni to taki, który łączy się z dopełnieniem bliższym w bierniku "
      "(relacja <font face='DejaVuMono'>obj</font>). Wybrano <b>100 czasowników, które najczęściej "
      "występują w korpusie z dopełnieniem rzeczownikowym</b>. Pominięto czasowniki posiłkowe "
      "i modalne (бити, хтети, моћи). Dopełnienia współrzędne też są liczone: w zdaniu "
      "„подигао цркву и кућу” oba rzeczowniki są dopełnieniami czasownika. Następnie wybrano "
      "<b>50 rzeczowników, które najczęściej są dopełnieniem tych czasowników</b>. Dzięki temu "
      "każdy rzeczownik ma niezerowy wektor cech.")
    verbs = read_csv(os.path.join(R4, "czasowniki_przechodnie.csv"))
    data = [["Lp", "Czasownik", "Dop.", "Wyst.", "Lp", "Czasownik", "Dop.", "Wyst."]]
    for i in range(50):
        a, b = verbs[i], verbs[i + 50]
        data.append([a["lp"], gloss(a["czasownik"]), a["dopelnienia_rzeczownikowe"], a["wystapienia"],
                     b["lp"], gloss(b["czasownik"]), b["dopelnienia_rzeczownikowe"], b["wystapienia"]])
    table(data, [0.8 * cm, 5.2 * cm, 1.1 * cm, 1.2 * cm] * 2, font_size=6.5)
    p("Tabela 8. 100 wybranych czasowników przechodnich (Dop. – liczba dopełnień rzeczownikowych, "
      "Wyst. – liczba wystąpień czasownika w korpusie).", "caption")
    nouns = read_csv(os.path.join(R4, "rzeczowniki.csv"))
    data = [["Lp", "Rzeczownik", "Jako dop.", "Wyst."] * 2]
    for i in range(25):
        a, b = nouns[i], nouns[i + 25]
        data.append([a["lp"], gloss(a["rzeczownik"]), a["liczba_jako_dopelnienie"], a["wystapienia"],
                     b["lp"], gloss(b["rzeczownik"]), b["liczba_jako_dopelnienie"], b["wystapienia"]])
    table(data, [0.8 * cm, 5 * cm, 1.4 * cm, 1.2 * cm] * 2, font_size=6.8)
    p("Tabela 9. 50 wybranych rzeczowników (Jako dop. – ile razy były dopełnieniem wybranych "
      "czasowników).", "caption")

    p("4.3. Zbiór treningowy – wektory 100-wymiarowe", "h2")
    p(f"Dla każdego z 50 rzeczowników zbudowano wektor x ∈ R<super>100</super>, w którym x<sub>j</sub> "
      f"to liczba wystąpień rzeczownika jako dopełnienia j-tego czasownika. Macierz 50 × 100 zawiera "
      f"łącznie {num(A['suma_kolokacji'])} kolokacji; niezerowych jest {num(A['niezerowe'])} składowych "
      f"({fmt(A['gestosc'] * 100, 1)}%). Przed uczeniem liczności przekształcono funkcją log(1 + x), "
      "żeby kilka bardzo częstych par nie zdominowało wektora, a następnie każdy wektor "
      "znormalizowano do długości 1. Odległość euklidesowa między wektorami odpowiada wtedy "
      "podobieństwu kosinusowemu, a porównywane są proporcje czasowników, a nie częstość "
      "rzeczownika.")
    figure(os.path.join(R4, "wariant_A_macierz.png"), 17,
           "Rys. 5. Zbiór treningowy (wariant A): 50 rzeczowników × 100 czasowników, skala log(1 + n).")

    p("4.4. Sieć Kohonena", "h2")
    p(f"Sieć Kohonena (samoorganizująca się mapa, SOM) zaimplementowano samodzielnie w numpy "
      f"(klasa <font face='DejaVuMono'>KohonenSOM</font>). Ma {som['wiersze']} × {som['kolumny']} = "
      f"{som['wiersze'] * som['kolumny']} neuronów ułożonych w prostokątną siatkę. Każdy neuron ma "
      "wektor wag w tej samej 100-wymiarowej przestrzeni co dane. Algorytm uczenia:")
    bullets([
        "inicjalizacja wag na płaszczyźnie dwóch pierwszych składowych głównych (PCA) danych,",
        f"{num(som['iteracje'])} iteracji: losujemy wektor x i znajdujemy neuron zwycięski (BMU), "
        "czyli najbliższy w sensie odległości euklidesowej,",
        "aktualizacja wag: w ← w + η(t) · h(t) · (x − w), gdzie h = exp(−d² / 2σ(t)²) jest "
        "gaussowską funkcją sąsiedztwa na siatce,",
        f"współczynnik uczenia η maleje wykładniczo z 0,5 do 0,01, a promień sąsiedztwa σ "
        f"z {som['wiersze'] // 2} do 0,5,",
        "jakość mapy: błąd kwantyzacji (średnia odległość wektora od wag jego BMU) i błąd "
        "topograficzny (odsetek wektorów, których dwa najlepsze neurony nie sąsiadują ze sobą).",
    ])
    figure(os.path.join(R4, "uczenie.png"), 12, "Rys. 6. Spadek błędu kwantyzacji w trakcie uczenia.")

    p("4.5. Wynik – mapa rzeczowników w przestrzeni czasowników przechodnich", "h2")
    p("Na mapie (Rys. 7) każdy rzeczownik umieszczono w jego neuronie zwycięskim. Tło to "
      "U-macierz: ciemne pola oznaczają duże odległości między sąsiednimi neuronami, czyli granice "
      "skupień. W każdym neuronie podpisano też czasownik, którego składowa ma w nim największą wagę. "
      "W ten sposób widać, które wymiary 100-wymiarowej przestrzeni dominują w danym rejonie mapy.")
    figure(os.path.join(R4, "wariant_A_mapa.png"), 17,
           f"Rys. 7. Mapa Kohonena – wariant A (błąd kwantyzacji {fmt(A['blad_kwantyzacji'], 3)}, "
           f"błąd topograficzny {fmt(A['blad_topograficzny'] * 100, 1)}%).")
    groups = "; ".join(", ".join(gloss(w) for w in g) for g in A["grupy"])
    p(f"Rzeczowniki, które trafiły do tego samego neuronu, mają najbardziej podobne wektory "
      f"kolokacji: {groups}.")
    p(INTERPRETATION_A)
    figure(os.path.join(R4, "wariant_A_plaszczyzny.png"), 17,
           "Rys. 8. Płaszczyzny składowych: rozkład wag neuronów dla 16 czasowników o największej "
           "liczbie kolokacji. Jasny obszar to rejon mapy, w którym leżą rzeczowniki łączące się "
           "z danym czasownikiem.")
    figure(os.path.join(R4, "wariant_A_pca.png"), 14,
           "Rys. 9. Dla porównania: rzut liniowy PCA tych samych wektorów 100D na płaszczyznę. "
           "Strzałki pokazują kierunki osi najważniejszych czasowników.")
    train = read_csv(os.path.join(R4, "wariant_A_zbior_treningowy.csv"))
    x = np.log1p(np.array([[float(v) for k, v in r.items() if k != "rzeczownik"] for r in train]))
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    sv = np.linalg.svd(x - x.mean(axis=0), compute_uv=False) ** 2
    expl = sv[:2].sum() / sv.sum()
    p(f"Porównanie z PCA (Rys. 9) pokazuje przewagę sieci Kohonena. Dwie pierwsze składowe główne "
      f"wyjaśniają łącznie tylko {fmt(expl * 100, 1)}% wariancji, a PC1 to w praktyce oś czasownika "
      "<i>имати</i>. Rzut liniowy gubi więc większość informacji ze 100 wymiarów i część "
      "punktów nakłada się na siebie. Sieć Kohonena jest nieliniowa: korzysta z całej "
      "przestrzeni 100D, rozkłada rzeczowniki po siatce i zachowuje ich sąsiedztwo.")

    p("4.6. Wpływ wyboru czasowników na wynik", "h2")
    p("Wynik zależy od tego, które czasowniki są wymiarami przestrzeni. Ten sam zbiór 50 "
      "rzeczowników nauczono więc w trzech wariantach, przy identycznych parametrach sieci:")
    bullets([f"<b>Wariant {k}</b> – {summ['warianty'][k]['opis']}." for k in "ABC"])
    p(f"Warianty A i B mają {summ['wspolne_czasowniki_AB']} wspólnych czasowników na 100. "
      "W wariancie B są też częste czasowniki nieprzechodnie lub zwrotne (np. налазити се, "
      "постати), które prawie nie mają dopełnień rzeczownikowych.")
    data = [["Wariant", "Suma kolokacji", "Gęstość macierzy", "Rzeczowniki z zerowym wektorem",
             "Błąd kwantyzacji", "Błąd topograficzny", "Zajęte neurony"]]
    for k in "ABC":
        v = summ["warianty"][k]
        data.append([k, num(v["suma_kolokacji"]), f"{fmt(v['gestosc'] * 100, 1)}%",
                     len(v["puste_rzeczowniki"]), fmt(v["blad_kwantyzacji"], 3),
                     f"{fmt(v['blad_topograficzny'] * 100, 1)}%", v["zajete_neurony"]])
    table(data, [1.6 * cm, 2.2 * cm, 2.2 * cm, 3.2 * cm, 2.3 * cm, 2.4 * cm, 2 * cm])
    p("Tabela 10. Porównanie wariantów.", "caption")
    data = [["Porównanie", "Korelacja Spearmana odległości na mapie", "Wspólni sąsiedzi (5 najbliższych)"]]
    for key, v in summ["porownanie"].items():
        data.append([key.replace("-", " – "), fmt(v["spearman"], 3), f"{fmt(v['wspolni_sasiedzi'] * 100, 1)}%"])
    table(data, [3 * cm, 6 * cm, 6 * cm])
    p("Tabela 11. Podobieństwo map uzyskanych w różnych wariantach. Korelacja 1 oznacza identyczny "
      "układ wzajemnych odległości rzeczowników.", "caption")
    figure(os.path.join(R4, "wariant_B_mapa.png"), 14, "Rys. 10. Mapa Kohonena – wariant B.")
    figure(os.path.join(R4, "wariant_C_mapa.png"), 14, "Rys. 11. Mapa Kohonena – wariant C.")
    p(INTERPRETATION_ABC)


# ---------------------------------------------------------------------------
# Podsumowanie
# ---------------------------------------------------------------------------
def conclusion():
    story.append(PageBreak())
    p("5. Podsumowanie", "h1")
    p(SUMMARY)
    p("Struktura programu (repozytorium)", "h2")
    data = [["Plik", "Zawartość"],
            ["lab01.py", "pobranie artykułów z serbskiej Wikipedii i oczyszczenie korpusu"],
            ["lab02_entropia_huffman.py", "statystyka liter, entropia, kodowanie Huffmana"],
            ["lab03_wyrazy_zipf_graf.py", "pokrycie 90% tekstu, prawo Zipfa, graf sąsiedztwa i rdzeń"],
            ["lab04_parsowanie.py", "analiza składniowa korpusu (stanza, transliteracja cyrylica ↔ łacinka)"],
            ["lab04_kohonen.py", "wybór czasowników i rzeczowników, zbiór treningowy, sieć Kohonena"],
            ["generuj_sprawozdanie.py, slownik.py", "generowanie tego sprawozdania"],
            ["dane/, wyniki/", "korpus sparsowany oraz wszystkie tabele CSV, raporty i wykresy"]]
    table(data, [5.5 * cm, 11 * cm], font_size=7.5)
    p("Kolejność uruchamiania: <font face='DejaVuMono'>pip install -r requirements.txt</font>, a potem "
      "lab01.py → lab02_entropia_huffman.py → lab03_wyrazy_zipf_graf.py → lab04_parsowanie.py → "
      "lab04_kohonen.py → generuj_sprawozdanie.py.")


# Teksty interpretacji (opis wyników lab04 dla ziarna losowania SEED = 42)
INTERPRETATION_A = (
    "<b>Interpretacja mapy.</b> Sieć bez nadzoru podzieliła rzeczowniki na obszary wyznaczone "
    "przez czasowniki, z którymi się łączą:"
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
    "(<i>склопити</i> – zawrzeć), преговор, борба, рат, политика, војска (<i>водити</i> – "
    "prowadzić);"
    "<br/>• <b>środek dołu mapy</b> – пораз (<i>претрпети</i> – ponieść), победа (<i>однети</i> – "
    "odnieść), власт (<i>преузети</i> – przejąć)."
    "<br/>Ciekawym przypadkiem są град (miasto) i медаља (medal) leżące obok siebie. Łączy je "
    "czasownik <i>освојити</i>, który znaczy zarówno „zdobyć miasto”, jak i „zdobyć medal”. "
    "Mapa grupuje więc rzeczowniki według zachowania składniowego (wspólnych czasowników), "
    "a nie według samego znaczenia. Błąd topograficzny wynosi 0%: rzeczowniki podobne "
    "w przestrzeni 100D leżą na mapie obok siebie."
)
INTERPRETATION_ABC = (
    "<b>Wnioski z porównania.</b> Wynik wyraźnie zależy od wyboru czasowników:"
    "<br/>• <b>A i B</b> mają wspólną połowę czasowników, w tym te o największej liczbie "
    "kolokacji (имати, донети, водити, прогласити, освојити). Dlatego ogólny układ mapy jest "
    "podobny (korelacja odległości ok. 0,7), ale tylko około połowy najbliższych sąsiadów się "
    "pokrywa. W wariancie B znalazło się wiele czasowników nieprzechodnich (доћи, живети, ићи, "
    "умрети...), które nie wnoszą informacji o dopełnieniu. Rzeczowniki пораз i отпор "
    "mają w B zerowe wektory, bo ich jedyne czasowniki (претрпети, пружити) nie należą do "
    "100 najczęstszych. Trafiają więc do jednego neuronu nie z podobieństwa, lecz z braku danych."
    "<br/>• <b>C</b> (okno ±5 wyrazów zamiast relacji składniowej) daje gęstszą macierz, "
    "ale bardziej zaszumioną. W oknie łapane są też podmioty i wyrazy niezwiązane z czasownikiem: "
    "np. град dostaje 22 kolokacje z <i>имати</i> ze zdań typu „град има … становника” "
    "(miasto ma … mieszkańców), w których jest podmiotem, a nie dopełnieniem. Mapa C najmniej "
    "przypomina pozostałe, choć najsilniejsze pary (одлука–закон, рат–борба, "
    "територија–површина) nadal leżą obok siebie."
    "<br/>Najbardziej wiarygodna jest więc mapa A, w której wymiarami są czasowniki faktycznie "
    "przechodnie, a kolokacje pochodzą z relacji czasownik–dopełnienie."
)
SUMMARY = (
    "W ramach czterech laboratoriów zbudowano i przeanalizowano korpus języka serbskiego "
    "(ok. 1 mln znaków z 20 artykułów Wikipedii). Najważniejsze wyniki:"
    "<br/>• <b>Lab 1:</b> po oczyszczeniu w korpusie zostały wyłącznie wyrazy z 30 liter "
    "serbskiej cyrylicy (149 tys. wyrazów, 25,6 tys. różnych)."
    "<br/>• <b>Lab 2:</b> entropia liter wynosi ok. 4,30 bit/znak, a kod Huffmana osiąga "
    "średnio 4,34 bit/znak (efektywność 99,2%, H ≤ L &lt; H + 1). Względem kodu 5-bitowego "
    "to oszczędność ok. 13%."
    "<br/>• <b>Lab 3:</b> 90% tekstu pokrywa ok. 11 tys. najczęstszych wyrazów (43,5% słownika). "
    "Korpus spełnia prawo Zipfa z wykładnikiem s ≈ 0,96. Rdzeń grafu sąsiedztwa tworzą "
    "słowa funkcyjne (и, у, је, на, су...)."
    "<br/>• <b>Lab 4:</b> analiza składniowa pozwoliła wybrać 100 czasowników przechodnich "
    "i 50 rzeczowników będących ich dopełnieniami. Sieć Kohonena nauczona na 100-wymiarowych "
    "wektorach kolokacji pogrupowała rzeczowniki w czytelne obszary semantyczno-składniowe, "
    "np. posiadanie, przestrzeń, nadawanie nazw i tytułów, działania polityczne i wojskowe. "
    "Porównanie trzech wariantów pokazało, że mapa w dużym stopniu zależy od tego, jakie "
    "czasowniki są wymiarami przestrzeni i jak definiujemy kolokację."
)


def build():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title="Przetwarzanie języka naturalnego – sprawozdanie",
                            author=AUTHOR or "student", subject="Lab 1–4: korpus serbski")
    title_page()
    lab1()
    lab2()
    lab3()
    lab4()
    conclusion()
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Zapisano {OUTPUT}")


if __name__ == "__main__":
    build()
