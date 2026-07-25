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


if __name__ == "__main__":
    make_use_case_diagram()
    make_context_diagram()
    print("Diagrams generated successfully.")
