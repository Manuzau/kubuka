"""
Generate UML Use Case Diagram and DFD Context Diagram for KUBUKA TFC.
Run with: python generate_diagrams.py
Output: media/diagrams/diagrama_casos_uso.png
         media/diagrams/diagrama_contexto.png
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD    = "C:/Windows/Fonts/arialbd.ttf"
OUT_DIR      = "media/diagrams"
os.makedirs(OUT_DIR, exist_ok=True)


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def text_size(draw, text, font):
    bb = draw.textbbox((0, 0), text, font=font)
    return bb[2] - bb[0], bb[3] - bb[1]


def ellipse(draw, cx, cy, rx, ry, outline, width=2, fill=None):
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                 outline=outline, width=width, fill=fill)


def rect(draw, x1, y1, x2, y2, outline, width=2, fill=None):
    draw.rectangle([x1, y1, x2, y2], outline=outline, width=width, fill=fill)


def draw_multiline_centered(draw, cx, cy, lines, font, fill, line_gap=4):
    fh = text_size(draw, "Ag", font)[1]
    total_h = len(lines) * fh + (len(lines) - 1) * line_gap
    y0 = cy - total_h / 2
    for i, line in enumerate(lines):
        w = text_size(draw, line, font)[0]
        draw.text((cx - w / 2, y0 + i * (fh + line_gap)), line, font=font, fill=fill)


def stick_figure(draw, cx, cy, label_lines, font, color="#1E293B"):
    head_r = 14
    ellipse(draw, cx, cy, head_r, head_r, outline=color, width=2)
    body_top = cy + head_r
    body_bot = cy + head_r + 32
    draw.line([(cx, body_top), (cx, body_bot)], fill=color, width=2)
    arm_y = cy + head_r + 14
    draw.line([(cx - 20, arm_y + 8), (cx + 20, arm_y + 8)], fill=color, width=2)
    draw.line([(cx, body_bot), (cx - 18, body_bot + 24)], fill=color, width=2)
    draw.line([(cx, body_bot), (cx + 18, body_bot + 24)], fill=color, width=2)
    fh = text_size(draw, "Ag", font)[1]
    total_h = len(label_lines) * fh + (len(label_lines) - 1) * 3
    ty = body_bot + 28
    for line in label_lines:
        w = text_size(draw, line, font)[0]
        draw.text((cx - w // 2, ty), line, font=font, fill=color)
        ty += fh + 3


def arrow_line(draw, x1, y1, x2, y2, color="#475569", width=2, dashed=False):
    if dashed:
        total = math.hypot(x2 - x1, y2 - y1)
        if total < 1:
            return
        dash_len, gap_len = 10, 6
        dx, dy = (x2 - x1) / total, (y2 - y1) / total
        dist = 0
        drawing = True
        while dist < total - 4:
            seg = min(dash_len if drawing else gap_len, total - dist)
            if drawing:
                px1 = x1 + dx * dist
                py1 = y1 + dy * dist
                px2 = x1 + dx * (dist + seg)
                py2 = y1 + dy * (dist + seg)
                draw.line([(px1, py1), (px2, py2)], fill=color, width=width)
            dist += seg
            drawing = not drawing
    else:
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    angle = math.atan2(y2 - y1, x2 - x1)
    asize = 10
    for da in [0.4, -0.4]:
        ax = x2 - asize * math.cos(angle - da)
        ay = y2 - asize * math.sin(angle - da)
        draw.line([(x2, y2), (ax, ay)], fill=color, width=width)


def draw_use_case(draw, cx, cy, lines, font, border="#3B82F6", fill="#EFF6FF", width=2):
    rx, ry = 92, 30
    ellipse(draw, cx, cy, rx, ry, outline=border, width=width, fill=fill)
    fh = text_size(draw, "Ag", font)[1]
    total_h = len(lines) * fh + (len(lines) - 1) * 2
    ty = cy - total_h // 2
    for line in lines:
        lw = text_size(draw, line, font)[0]
        draw.text((cx - lw // 2, ty), line, font=font, fill="#0F172A")
        ty += fh + 2


# ---------------------------------------------------------------------------
# USE CASE DIAGRAM
# ---------------------------------------------------------------------------

def make_use_case_diagram():
    W, H = 1680, 1200
    img = Image.new("RGB", (W, H), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    f8  = load_font(FONT_REGULAR, 12)
    f9  = load_font(FONT_REGULAR, 13)
    f10 = load_font(FONT_REGULAR, 14)
    f11 = load_font(FONT_BOLD,    14)
    f13 = load_font(FONT_BOLD,    17)
    f16 = load_font(FONT_BOLD,    22)

    # Title
    title = "Diagrama de Casos de Uso — KUBUKA"
    tw, _ = text_size(draw, title, f16)
    draw.text(((W - tw) // 2, 14), title, font=f16, fill="#1E293B")

    # System boundary
    SX1, SY1, SX2, SY2 = 210, 58, 1450, 1160
    rect(draw, SX1, SY1, SX2, SY2, outline="#7C3AED", width=3)
    sys_label = "KUBUKA — Sistema de Pré-Selecção Inteligente de Candidatos"
    slw, _ = text_size(draw, sys_label, f11)
    draw.text(((SX1 + SX2) // 2 - slw // 2, SY1 + 7), sys_label, font=f11, fill="#7C3AED")

    # --- Actors ---
    CAND_X, CAND_Y = 90,  480
    REC_X,  REC_Y  = 1590, 380
    ADM_X,  ADM_Y  = 1590, 750
    IA_X,   IA_Y   = 1590, 1010

    stick_figure(draw, CAND_X, CAND_Y, ["Candidato"],        f10, "#0F172A")
    stick_figure(draw, REC_X,  REC_Y,  ["Recrutador"],       f10, "#0F172A")
    stick_figure(draw, ADM_X,  ADM_Y,  ["Administrador"],    f10, "#6D28D9")
    stick_figure(draw, IA_X,   IA_Y,   ["Motor de IA",
                                         "(n8n+Ollama)"],    f9,  "#64748B")

    # Generalização Administrador → Recrutador (hollow triangle at Recrutador end)
    ax0, ay0 = ADM_X, ADM_Y - 14
    ax1, ay1 = REC_X, REC_Y + 104
    draw.line([(ax0, ay0), (ax1, ay1)], fill="#6D28D9", width=2)
    draw.polygon([(ax1, ay1 - 14), (ax1 - 9, ay1 + 2), (ax1 + 9, ay1 + 2)],
                 outline="#6D28D9", fill="#FAFAFA")

    # --- Use Case positions ---
    # Candidato column x=470
    CX = 470
    uc_cand = [
        (CX, 110,  ["Registar Conta"]),
        (CX, 193,  ["Autenticar-se", "no Sistema"]),
        (CX, 283,  ["Submeter /", "Actualizar CV"]),
        (CX, 370,  ["Consultar", "Feedback do CV"]),
        (CX, 455,  ["Consultar Vagas", "Disponíveis"]),
        (CX, 540,  ["Candidatar-se", "a Vaga"]),
        (CX, 628,  ["Acompanhar", "Candidaturas"]),
        (CX, 718,  ["Retirar", "Candidatura"]),
        (CX, 808,  ["Indicar", "Indisponibilidade"]),
    ]

    # IA column x=840 (centre)
    AX = 840
    uc_ai = [
        (AX, 283, ["Analisar", "Currículo"]),
        (AX, 540, ["Calcular Score", "de Compatibilidade"]),
    ]

    # Recrutador column x=1150
    RX = 1150
    uc_rec = [
        (RX, 110,  ["Criar Vaga"]),
        (RX, 193,  ["Editar /", "Desactivar Vaga"]),
        (RX, 283,  ["Consultar Candidatos", "por Vaga"]),
        (RX, 370,  ["Filtrar", "Candidatos"]),
        (RX, 455,  ["Pré-seleccionar", "Candidato"]),
        (RX, 540,  ["Rejeitar", "Candidato"]),
        (RX, 628,  ["Agendar", "Entrevista"]),
        (RX, 718,  ["Registar Notas", "Internas"]),
        (RX, 808,  ["Exportar", "Candidaturas CSV"]),
        (RX, 900,  ["Consultar", "Analytics"]),
    ]

    # Admin-exclusive UCs (purple) — x=1350
    AX2 = 1350
    uc_adm = [
        (AX2, 990,  ["Aprovar", "Recrutadores"]),
        (AX2, 1090, ["Consultar Registo", "de Auditoria"]),
    ]

    # Draw use cases
    for (cx, cy, lines) in uc_cand:
        draw_use_case(draw, cx, cy, lines, f9, border="#3B82F6", fill="#EFF6FF")
    for (cx, cy, lines) in uc_rec:
        draw_use_case(draw, cx, cy, lines, f9, border="#10B981", fill="#F0FDF4")
    for (cx, cy, lines) in uc_ai:
        draw_use_case(draw, cx, cy, lines, f9, border="#0284C7", fill="#E0F2FE")
    for (cx, cy, lines) in uc_adm:
        draw_use_case(draw, cx, cy, lines, f9, border="#7C3AED", fill="#FAF5FF")

    # --- Association lines ---
    def assoc(x1, y1, x2, y2):
        draw.line([(x1, y1), (x2, y2)], fill="#94A3B8", width=1)

    # Candidato (right side of figure ≈ x+20) to left edge of each UC (cx-92)
    for (cx, cy, _) in uc_cand:
        assoc(CAND_X + 20, CAND_Y, cx - 92, cy)

    # Recrutador to recruiter UCs
    for (cx, cy, _) in uc_rec:
        assoc(REC_X - 20, REC_Y, cx + 92, cy)

    # Administrador to admin UCs
    for (cx, cy, _) in uc_adm:
        assoc(ADM_X - 20, ADM_Y, cx + 92, cy)

    # Motor de IA to AI UCs
    for (cx, cy, _) in uc_ai:
        assoc(IA_X - 20, IA_Y, cx + 92, cy)

    # --- «include» arrows ---
    def include_arrow(x1, y1, x2, y2):
        arrow_line(draw, x1, y1, x2, y2, color="#0284C7", width=1, dashed=True)
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        lbl = "«include»"
        lw, lh = text_size(draw, lbl, f8)
        draw.rectangle([mx - lw//2 - 1, my - lh - 4, mx + lw//2 + 1, my], fill="#FAFAFA")
        draw.text((mx - lw//2, my - lh - 2), lbl, font=f8, fill="#0284C7")

    def extend_arrow(x1, y1, x2, y2, label="«extend»"):
        arrow_line(draw, x1, y1, x2, y2, color="#6D28D9", width=1, dashed=True)
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2
        lw, lh = text_size(draw, label, f8)
        draw.rectangle([mx - lw//2 - 1, my, mx + lw//2 + 1, my + lh + 4], fill="#FAFAFA")
        draw.text((mx - lw//2, my + 2), label, font=f8, fill="#6D28D9")

    # Submeter CV --include--> Analisar Currículo
    include_arrow(CX + 92, 283, AX - 92, 283)
    # Candidatar-se --include--> Calcular Score
    include_arrow(CX + 92, 540, AX - 92, 540)

    # Retirar Candidatura --extend--> Acompanhar Candidaturas
    # Route via offset to left so label doesn't overlap ellipses
    extend_arrow(CX - 110, 718 - 20, CX - 110, 628 + 20, "«extend»")
    draw.line([(CX - 92, 718), (CX - 110, 718 - 20)], fill="#94A3B8", width=1)
    draw.line([(CX - 92, 628), (CX - 110, 628 + 20)], fill="#94A3B8", width=1)
    # Indicar Indisponibilidade --extend--> Acompanhar Candidaturas
    extend_arrow(CX - 140, 808 - 20, CX - 140, 628 + 20, "«extend»")
    draw.line([(CX - 92, 808), (CX - 140, 808 - 20)], fill="#94A3B8", width=1)
    draw.line([(CX - 92, 628), (CX - 140, 628 + 20)], fill="#94A3B8", width=1)

    # --- Legend ---
    LX, LY = SX1 + 10, SY2 - 235
    rect(draw, LX, LY, LX + 270, SY2 - 10, outline="#94A3B8", width=1, fill="#F1F5F9")
    draw.text((LX + 8, LY + 6), "Legenda", font=f11, fill="#1E293B")

    items = [
        ("#3B82F6", "#EFF6FF", "Caso de uso do Candidato"),
        ("#10B981", "#F0FDF4", "Caso de uso do Recrutador"),
        ("#0284C7", "#E0F2FE", "Caso de uso do Motor de IA"),
        ("#7C3AED", "#FAF5FF", "Caso de uso do Administrador"),
    ]
    for i, (border, fill, lbl) in enumerate(items):
        y = LY + 30 + i * 22
        ellipse(draw, LX + 20, y + 7, 14, 7, outline=border, width=2, fill=fill)
        draw.text((LX + 40, y), lbl, font=f8, fill="#1E293B")

    y = LY + 30 + len(items) * 22 + 4
    draw.line([(LX + 8, y + 7), (LX + 36, y + 7)], fill="#94A3B8", width=1)
    draw.text((LX + 40, y), "Associação (actor ↔ caso de uso)", font=f8, fill="#1E293B")
    y += 22
    arrow_line(draw, LX + 8, y + 7, LX + 36, y + 7, color="#0284C7", width=1, dashed=True)
    draw.text((LX + 40, y), "«include»", font=f8, fill="#0284C7")
    y += 22
    arrow_line(draw, LX + 8, y + 7, LX + 36, y + 7, color="#6D28D9", width=1, dashed=True)
    draw.text((LX + 40, y), "«extend»", font=f8, fill="#6D28D9")
    y += 22
    draw.line([(LX + 8, y + 7), (LX + 30, y + 7)], fill="#6D28D9", width=2)
    draw.polygon([(LX + 30, y + 3), (LX + 22, y + 11), (LX + 22, y + 3)],
                 outline="#6D28D9", fill="#F1F5F9")
    draw.text((LX + 40, y), "Generalização", font=f8, fill="#1E293B")

    out = os.path.join(OUT_DIR, "diagrama_casos_uso.png")
    img.save(out, dpi=(150, 150))
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# CONTEXT DIAGRAM (DFD Level 0)
# ---------------------------------------------------------------------------

def make_context_diagram():
    W, H = 1200, 900
    img = Image.new("RGB", (W, H), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    f9  = load_font(FONT_REGULAR, 14)
    f10 = load_font(FONT_REGULAR, 15)
    f11 = load_font(FONT_BOLD,    16)
    f14 = load_font(FONT_BOLD,    21)
    f16 = load_font(FONT_BOLD,    23)

    # Title
    title = "Diagrama de Contexto (DFD Nível 0) — KUBUKA"
    tw, _ = text_size(draw, title, f16)
    draw.text(((W - tw) // 2, 14), title, font=f16, fill="#1E293B")

    # Central system ellipse
    CX, CY = W // 2, H // 2 + 30
    SRX, SRY = 158, 72
    ellipse(draw, CX, CY, SRX, SRY, outline="#7C3AED", width=4, fill="#EDE9FE")
    draw_multiline_centered(draw, CX, CY - 14, ["KUBUKA"], f14, "#4C1D95")
    draw_multiline_centered(draw, CX, CY + 14, ["Sistema de Pré-Selecção", "Inteligente de Candidatos"], f9, "#6D28D9", line_gap=3)

    # External entities: (cx, cy, lines, text_color, fill, border)
    EW, EH = 210, 85
    entities = {
        "cand": (175,  175,  ["Candidato"],               "#0F172A", "#EFF6FF", "#3B82F6"),
        "rec":  (1025, 175,  ["Recrutador"],              "#0F172A", "#F0FDF4", "#10B981"),
        "adm":  (175,  725,  ["Administrador"],           "#4C1D95", "#FAF5FF", "#7C3AED"),
        "ia":   (1025, 725,  ["Motor de IA",
                               "(n8n + Ollama)"],         "#0F172A", "#E0F2FE", "#0284C7"),
    }

    def draw_double_rect(ex, ey, lines, tcol, fill, border):
        x1, y1 = ex - EW//2, ey - EH//2
        x2, y2 = ex + EW//2, ey + EH//2
        rect(draw, x1, y1, x2, y2, outline=border, width=3, fill=fill)
        rect(draw, x1+5, y1+5, x2-5, y2-5, outline=border, width=1)
        fh = text_size(draw, "Ag", f11)[1]
        total = len(lines) * fh + (len(lines)-1)*3
        ty = ey - total//2
        for line in lines:
            lw = text_size(draw, line, f11)[0]
            draw.text((ex - lw//2, ty), line, font=f11, fill=tcol)
            ty += fh + 3

    coords = {}
    for key, (ex, ey, lines, tcol, fill, border) in entities.items():
        draw_double_rect(ex, ey, lines, tcol, fill, border)
        coords[key] = (ex, ey)

    def ellipse_edge(tx, ty):
        angle = math.atan2(ty - CY, tx - CX)
        ex = CX + SRX * math.cos(angle)
        ey = CY + SRY * math.sin(angle)
        return int(ex), int(ey)

    def rect_edge(ex, ey):
        dx, dy = CX - ex, CY - ey
        hw, hh = EW // 2, EH // 2
        if abs(dx) * hh > abs(dy) * hw:
            sx = int(math.copysign(hw, dx))
            sy = int(dy * hw / abs(dx)) if dx != 0 else 0
        else:
            sy = int(math.copysign(hh, dy))
            sx = int(dx * hh / abs(dy)) if dy != 0 else 0
        return ex + sx, ey + sy

    def flow(entity_key, label_out, label_in):
        ex, ey = coords[entity_key]
        rx, ry = rect_edge(ex, ey)
        ex2, ey2 = ellipse_edge(ex, ey)

        dx, dy = ex2 - rx, ey2 - ry
        dist = math.hypot(dx, dy) or 1
        # perpendicular offset — larger separation so labels don't overlap
        sep = 18
        px, py = int(-dy / dist * sep), int(dx / dist * sep)

        COL_OUT = "#1D4ED8"
        COL_IN  = "#0369A1"

        # normalised perpendicular unit vector (same direction as px,py)
        pnorm = math.hypot(px, py) or 1
        unx, uny = px / pnorm, py / pnorm

        # outbound: entity → system
        o1x, o1y = rx + px, ry + py
        o2x, o2y = ex2 + px, ey2 + py
        arrow_line(draw, o1x, o1y, o2x, o2y, color="#0F172A", width=2)
        # label at midpoint, pushed further in the +perp direction
        mlx = int((o1x+o2x)//2 + unx*22)
        mly = int((o1y+o2y)//2 + uny*22)
        lw, lh = text_size(draw, label_out, f9)
        draw.rectangle([mlx-lw//2-3, mly-lh-4, mlx+lw//2+3, mly+4], fill="#FAFAFA")
        draw.text((mlx-lw//2, mly-lh//2-2), label_out, font=f9, fill=COL_OUT)

        # inbound: system → entity
        i1x, i1y = ex2 - px, ey2 - py
        i2x, i2y = rx - px, ry - py
        arrow_line(draw, i1x, i1y, i2x, i2y, color="#0F172A", width=2)
        # label at midpoint, pushed in the -perp direction
        mlx2 = int((i1x+i2x)//2 - unx*22)
        mly2 = int((i1y+i2y)//2 - uny*22)
        lw2, lh2 = text_size(draw, label_in, f9)
        draw.rectangle([mlx2-lw2//2-3, mly2-lh2//2-4, mlx2+lw2//2+3, mly2+lh2//2+4], fill="#FAFAFA")
        draw.text((mlx2-lw2//2, mly2-lh2//2), label_in, font=f9, fill=COL_IN)

    flow("cand",
         "Dados de CV / Candidatura",
         "Feedback de CV / Estado da Candidatura")
    flow("rec",
         "Dados de Vaga / Acções de Recrutador",
         "Lista de Candidatos / Scores / Relatórios")
    flow("adm",
         "Comandos de Gestão do Sistema",
         "Registos de Auditoria / Relatórios Admin")
    flow("ia",
         "Texto CV / Dados da Candidatura",
         "Score de Compatibilidade / Análise de CV")

    # Legend
    LX, LY = 10, H - 115
    rect(draw, LX, LY, 380, H - 10, outline="#94A3B8", width=1, fill="#F1F5F9")
    draw.text((LX + 8, LY + 5), "Legenda", font=f11, fill="#1E293B")
    arrow_line(draw, LX+10, LY+32, LX+40, LY+32, color="#0F172A", width=2)
    draw.text((LX+48, LY+24), "Fluxo de dados: Entidade → Sistema", font=f9, fill="#1D4ED8")
    arrow_line(draw, LX+10, LY+56, LX+40, LY+56, color="#0F172A", width=2)
    draw.text((LX+48, LY+48), "Fluxo de dados: Sistema → Entidade", font=f9, fill="#0369A1")
    draw.text((LX+8,  LY+74), "Entidades externas: rectângulo de dupla borda", font=f9, fill="#475569")
    draw.text((LX+8,  LY+93), "Processo central: elipse", font=f9, fill="#475569")

    out = os.path.join(OUT_DIR, "diagrama_contexto.png")
    img.save(out, dpi=(150, 150))
    print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# CLASS DIAGRAM (UML)
# ---------------------------------------------------------------------------

def measure_uml_class(draw, attrs, methods, font_title, font_body):
    line_h = text_size(draw, "Ag", font_body)[1] + 8
    title_h = text_size(draw, "Ag", font_title)[1] + 18
    attrs_h = max(len(attrs), 1) * line_h + 10
    methods_h = (len(methods) * line_h + 10) if methods else 0
    return title_h + attrs_h + methods_h, line_h, title_h, attrs_h, methods_h


def draw_uml_class(draw, cx, cy, w, name, attrs, methods, font_title, font_body,
                    border="#7C3AED", header_fill="#EDE9FE"):
    total_h, line_h, title_h, attrs_h, methods_h = measure_uml_class(
        draw, attrs, methods, font_title, font_body)
    x, y = int(cx - w / 2), int(cy - total_h / 2)

    rect(draw, x, y, x + w, y + total_h, outline=border, width=2, fill="white")
    rect(draw, x, y, x + w, y + title_h, outline=border, width=2, fill=header_fill)
    tw, th = text_size(draw, name, font_title)
    draw.text((x + (w - tw) // 2, y + (title_h - th) // 2), name, font=font_title, fill="#4C1D95")

    ay = y + title_h
    for i, a in enumerate(attrs):
        draw.text((x + 10, ay + 5 + i * line_h), a, font=font_body, fill="#1E293B")

    if methods:
        my = ay + attrs_h
        draw.line([(x, my), (x + w, my)], fill=border, width=1)
        for i, m in enumerate(methods):
            draw.text((x + 10, my + 5 + i * line_h), m, font=font_body, fill="#0F172A")

    return {"x": x, "y": y, "w": w, "h": total_h, "cx": x + w / 2, "cy": y + total_h / 2}


def rect_edge_pt(box, tx, ty):
    cx, cy = box["cx"], box["cy"]
    dx, dy = tx - cx, ty - cy
    hw, hh = box["w"] / 2, box["h"] / 2
    if dx == 0 and dy == 0:
        return cx, cy
    if abs(dx) * hh > abs(dy) * hw:
        sx = hw if dx > 0 else -hw
        sy = dy * hw / abs(dx) if dx != 0 else 0
    else:
        sy = hh if dy > 0 else -hh
        sx = dx * hh / abs(dy) if dy != 0 else 0
    return cx + sx, cy + sy


def draw_uml_association(draw, box_a, box_b, mult_a, mult_b, label, font, color="#334155"):
    pa = rect_edge_pt(box_a, box_b["cx"], box_b["cy"])
    pb = rect_edge_pt(box_b, box_a["cx"], box_a["cy"])
    draw.line([pa, pb], fill=color, width=2)

    dist = math.hypot(pb[0] - pa[0], pb[1] - pa[1]) or 1
    ux, uy = (pb[0] - pa[0]) / dist, (pb[1] - pa[1]) / dist

    def label_at(px, py, dx, dy, text):
        lw, lh = text_size(draw, text, font)
        draw.rectangle([px + dx - lw // 2 - 2, py + dy - lh // 2 - 1,
                         px + dx + lw // 2 + 2, py + dy + lh // 2 + 1], fill="#FAFAFA")
        draw.text((px + dx - lw // 2, py + dy - lh // 2), text, font=font, fill=color)

    label_at(pa[0], pa[1], ux * 26 + uy * 10, uy * 26 - ux * 10, mult_a)
    label_at(pb[0], pb[1], -ux * 26 + uy * 10, -uy * 26 - ux * 10, mult_b)
    mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
    label_at(mx, my, uy * 14, -ux * 14, label)


def make_class_diagram():
    W, H = 2000, 1520
    img = Image.new("RGB", (W, H), "#FAFAFA")
    draw = ImageDraw.Draw(img)

    f_title = load_font(FONT_BOLD, 16)
    f_body = load_font(FONT_REGULAR, 13)
    f_lbl = load_font(FONT_BOLD, 13)
    f16 = load_font(FONT_BOLD, 24)
    f11 = load_font(FONT_BOLD, 15)
    f9 = load_font(FONT_REGULAR, 13)

    title = "Diagrama de Classes (UML) — KUBUKA"
    tw, _ = text_size(draw, title, f16)
    draw.text(((W - tw) // 2, 16), title, font=f16, fill="#1E293B")

    # --- Class definitions (name, attrs, methods) ---
    user_attrs = [
        "- username : String",
        "- email : String",
        "- password : String",
        "- is_candidate : Boolean",
        "- is_recruiter : Boolean",
        "- is_admin : Boolean",
        "- recruiter_approved : Boolean",
        "- company : String",
    ]
    user_methods = ["+ has_resume() : Boolean"]

    resume_attrs = [
        "- file : File",
        "- parsed_text : String",
        "- summary : String",
        "- skills : String",
        "- experience : String",
        "- education : String",
        "- languages : String",
        "- score : Float",
        "- feedback : String",
        "- ai_processed : Boolean",
        "- created_at : DateTime",
    ]

    job_attrs = [
        "- title : String",
        "- company : String",
        "- description : String",
        "- requirements : String",
        "- location : String",
        "- salary_range : String",
        "- is_active : Boolean",
        "- deadline : Date",
        "- contact_email_primary : String",
        "- contact_email_secondary : String",
        "- allow_candidate_unavailability : Boolean",
        "- min_score_required : Float",
        "- created_at : DateTime",
    ]

    application_attrs = [
        "- similarity_score : Float",
        "- match_feedback : String",
        "- status : String «enum»",
        "- awaiting_score : Boolean",
        "- cv_file : File",
        "- cv_parsed_text : String",
        "- recruiter_notes : String",
        "- interview_date : DateTime",
        "- candidate_availability_enabled : Boolean",
        "- candidate_unavailability_reason : String",
        "- availability_responded : Boolean",
        "- applied_at : DateTime",
        "- updated_at : DateTime",
    ]

    auditlog_attrs = [
        "- action : String «enum»",
        "- detail : String",
        "- ip_address : String",
        "- timestamp : DateTime",
    ]

    notification_attrs = [
        "- message : String",
        "- is_read : Boolean",
        "- created_at : DateTime",
    ]

    # --- Layout: User as central hub, satellites arranged radially ---
    b_user = draw_uml_class(draw, 900, 740, 400, "User", user_attrs, user_methods, f_title, f_body,
                             border="#7C3AED", header_fill="#EDE9FE")
    b_resume = draw_uml_class(draw, 300, 240, 440, "Resume", resume_attrs, [], f_title, f_body,
                               border="#3B82F6", header_fill="#EFF6FF")
    b_job = draw_uml_class(draw, 1620, 240, 460, "Job", job_attrs, [], f_title, f_body,
                            border="#10B981", header_fill="#F0FDF4")
    b_application = draw_uml_class(draw, 1620, 780, 460, "Application", application_attrs, [], f_title, f_body,
                                    border="#0284C7", header_fill="#E0F2FE")
    b_auditlog = draw_uml_class(draw, 300, 1220, 420, "AuditLog", auditlog_attrs, [], f_title, f_body,
                                 border="#F59E0B", header_fill="#FFFBEB")
    b_notification = draw_uml_class(draw, 1620, 1300, 420, "Notification", notification_attrs, [], f_title, f_body,
                                     border="#EC4899", header_fill="#FDF2F8")

    # --- Associations (multiplicity from Django FK / OneToOne semantics) ---
    draw_uml_association(draw, b_user, b_resume, "1", "0..1", "possui", f_lbl, color="#3B82F6")
    draw_uml_association(draw, b_user, b_job, "1", "0..*", "cria", f_lbl, color="#10B981")
    draw_uml_association(draw, b_user, b_application, "1", "0..*", "submete", f_lbl, color="#0284C7")
    draw_uml_association(draw, b_job, b_application, "1", "0..*", "recebe", f_lbl, color="#0284C7")
    draw_uml_association(draw, b_user, b_auditlog, "1", "0..*", "regista", f_lbl, color="#F59E0B")
    draw_uml_association(draw, b_user, b_notification, "1", "0..*", "recebe", f_lbl, color="#EC4899")
    draw_uml_association(draw, b_application, b_notification, "1", "0..*", "gera", f_lbl, color="#EC4899")

    # --- Legend ---
    LX, LY = 20, H - 150
    rect(draw, LX, LY, LX + 430, H - 20, outline="#94A3B8", width=1, fill="#F1F5F9")
    draw.text((LX + 10, LY + 8), "Legenda", font=f11, fill="#1E293B")
    draw.line([(LX + 10, LY + 40), (LX + 45, LY + 40)], fill="#334155", width=2)
    draw.text((LX + 55, LY + 32), "Associação com multiplicidade (ex: 1 → 0..*)", font=f9, fill="#1E293B")
    draw.text((LX + 10, LY + 58), "Compartimentos: Nome / Atributos (-) / Métodos (+)", font=f9, fill="#1E293B")
    draw.text((LX + 10, LY + 80), "«enum» — campo com conjunto fixo de valores (choices)", font=f9, fill="#1E293B")
    draw.text((LX + 10, LY + 102), "1 = exactamente um · 0..1 = zero ou um · 0..* = zero ou muitos", font=f9, fill="#1E293B")

    out = os.path.join(OUT_DIR, "diagrama_classes.png")
    img.save(out, dpi=(150, 150))
    print(f"Saved: {out}")


if __name__ == "__main__":
    make_use_case_diagram()
    make_context_diagram()
    make_class_diagram()
    print("Diagrams generated successfully.")
