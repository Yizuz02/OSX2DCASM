import sys
import math
import random
import time
import pygame
import numpy as np


#  TEMAS DE COLOR

COLOR_THEMES = [
    {"name": "Neon",    "bg": ( 13, 13, 13), "grid": ( 25, 40, 25), "cell": (  0,255,100)},
    {"name": "Clasico", "bg": (245,245,245), "grid": (180,180,180), "cell": ( 20, 20, 20)},
    {"name": "Cian",    "bg": (  5, 10, 18), "grid": ( 10, 22, 36), "cell": (  0,210,255)},
    {"name": "Fuego",   "bg": ( 10,  0,  0), "grid": ( 28,  5,  0), "cell": (255,100,  0)},
    {"name": "Matrix",  "bg": (  0,  0,  0), "grid": (  0, 28,  0), "cell": ( 50,255, 50)},
    {"name": "Purpura", "bg": ( 10,  0, 18), "grid": ( 22,  0, 40), "cell": (210, 60,255)},
    {"name": "Sepia",   "bg": (245,230,200), "grid": (210,185,148), "cell": ( 90, 55, 25)},
    {"name": "Ocean",   "bg": (  0, 16, 32), "grid": (  0, 34, 68), "cell": (  0,175,255)},
]

 
#  CONSTANTES DEL AUTOMATA
 
GRID_W  = 255    # columnas del espacio (RING  / FACTOR)
GRID_H  = 255      # filas    del espacio (LINES / FACTOR)
CELL_PX = 8       # pixeles por celda

 
#  LAYOUT DE LA VENTANA
 
PANEL_W = 470
SPACE_W = GRID_W * CELL_PX   # 600
SPACE_H = GRID_H * CELL_PX   # 600
WIN_W   = PANEL_W + SPACE_W
WIN_H   = max(SPACE_H + 20, 870)
PAD     = 8

# Paleta del panel
P_BG     = ( 28,  28,  32)
P_FG     = (220, 220, 225)
P_LABEL  = (140, 140, 155)
P_VALUE  = (  0, 230, 120)
P_BORDER = ( 55,  55,  65)
P_ACCENT = ( 70, 170,  90)

BTN_OFF_BG  = ( 50,  50,  58)
BTN_OFF_FG  = (190, 190, 200)
BTN_ON_BG   = ( 72, 195, 105)
BTN_ON_FG   = ( 10,  10,  10)
BTN_HOV     = ( 75,  75,  88)


 
#  UTILIDADES
 
def draw_text(surf, font, text, pos, color, align="left"):
    img = font.render(str(text), True, color)
    x, y = pos
    if   align == "right":  x -= img.get_width()
    elif align == "center": x -= img.get_width() // 2
    surf.blit(img, (x, y))


def rule_binary(n):
    """Entero -> lista de 8 bits (LSB primero)."""
    return [(n >> i) & 1 for i in range(8)]


 
#  LOGICA DEL AUTOMATA  (numpy para velocidad)
 
class Life2DM:
    """
    Automata celular 2D vecindad de Moore completa.
    state   : ndarray uint8 [GRID_H, GRID_W]
    rule    : ndarray uint8 [512]  — rule[idx] = 0 o 1
    """
    def __init__(self):
        self.state   = np.zeros((GRID_H, GRID_W), dtype=np.uint8)
        self.rule    = np.zeros(512,              dtype=np.uint8)
        self.gen     = 0
        self.running = False
        self.surf    = pygame.Surface((SPACE_W, SPACE_H))
        self.dirty   = True

     
    def sync_rule_from_matrix(self, matrix_data):
        """matrix_data: lista[16][32]  -> self.rule[512]"""
        print(matrix_data)
        for i in range(16):
            for j in range(32):
                idx = i * 32 + j
                if idx < 512:
                    self.rule[idx] = matrix_data[i][j]
        print(self.rule)

     
    def step(self):
        s = self.state
        # Vecinos con toroide usando roll
        nw = np.roll(np.roll(s,  1, 0),  1, 1)
        n  = np.roll(s,  1, 0)
        ne = np.roll(np.roll(s,  1, 0), -1, 1)
        w  = np.roll(s,  1, 1)
        c  = s
        e  = np.roll(s, -1, 1)
        sw = np.roll(np.roll(s, -1, 0),  1, 1)
        ss = np.roll(s, -1, 0)
        se = np.roll(np.roll(s, -1, 0), -1, 1)

        # Identificador: 9 bits (mismo orden que el original)
        idx = (nw.astype(np.uint16)        |
               n .astype(np.uint16) <<  1  |
               ne.astype(np.uint16) <<  2  |
               w .astype(np.uint16) <<  3  |
               c .astype(np.uint16) <<  4  |
               e .astype(np.uint16) <<  5  |
               sw.astype(np.uint16) <<  6  |
               ss.astype(np.uint16) <<  7  |
               se.astype(np.uint16) <<  8)

        self.state = self.rule[idx].astype(np.uint8)
        self.gen  += 1
        self.dirty = True

    def tick(self):
        if self.running:
            self.step()

     
    def reset(self):
        self.state[:] = 0
        self.gen   = 0
        self.dirty = True

    def random_fill(self, density):
        rng = np.random.default_rng(int(time.time() * 1000) & 0xFFFFFFFF)
        self.state = (rng.random((GRID_H, GRID_W)) < density).astype(np.uint8)
        self.gen   = 0
        self.dirty = True

    def rule110_fill(self, density):
        nb  = rule_binary(110)
        rng = np.random.default_rng(int(time.time() * 1000) & 0xFFFFFFFF)
        row = (rng.random(GRID_W) < density).astype(np.uint8)
        self.state[:] = 0
        self.state[0] = row
        for i in range(1, GRID_H):
            new_row = np.zeros(GRID_W, dtype=np.uint8)
            for j in range(GRID_W):
                l = int(row[(j - 1) % GRID_W])
                cv = int(row[j])
                r  = int(row[(j + 1) % GRID_W])
                new_row[j] = nb[l * 4 + cv * 2 + r]
            self.state[i] = new_row
            row = new_row
        self.gen   = 0
        self.dirty = True

    def toggle_cell(self, cx, cy):
        if 0 <= cx < GRID_W and 0 <= cy < GRID_H:
            self.state[cy, cx] ^= 1
            self.dirty = True

    def count_alive(self):
        return int(self.state.sum())

     
    def draw(self, theme):
        """Redibuja la surface del espacio solo cuando dirty=True."""
        if not self.dirty:
            return
        bg   = theme["bg"]
        grid = theme["grid"]
        cell = theme["cell"]

        # Construir array RGB rapidamente con numpy
        # Dimensiones: (SPACE_H, SPACE_W, 3)
        rgb = np.empty((SPACE_H, SPACE_W, 3), dtype=np.uint8)
        rgb[:] = bg

        # Rellenar celdas vivas
        ys, xs = np.where(self.state == 1)
        for cx, cy in zip(xs, ys):
            px = cx * CELL_PX + 1
            py = cy * CELL_PX + 1
            rgb[py : py + CELL_PX - 1, px : px + CELL_PX - 1] = cell

        # Volcar a surface (surfarray espera shape (W, H, 3))
        pygame.surfarray.blit_array(self.surf,
                                    np.ascontiguousarray(
                                        np.transpose(rgb, (1, 0, 2))))

        # Malla
        for x in range(0, SPACE_W + 1, CELL_PX):
            pygame.draw.line(self.surf, grid, (x, 0), (x, SPACE_H))
        for y in range(0, SPACE_H + 1, CELL_PX):
            pygame.draw.line(self.surf, grid, (0, y), (SPACE_W, y))

        self.dirty = False


 
#  MATRIZ DE REGLA  16 x 32
 
class MatrizRegla:
    """512 bits de la regla organizados en 16 filas x 32 columnas."""
    BW, BH, BM = 11, 12, 1   # ancho, alto, margen de cada boton

    def __init__(self):
        self.data = [[0] * 32 for _ in range(16)] 
        self.data[0][0] = 1  

    def toggle(self, row, col):
        self.data[row][col] ^= 1

    def clear(self):
        for i in range(16):
            for j in range(32):
                self.data[i][j] = 0
                if i==0 and j==0:
                    self.data[i][j] = 1

    def randomize(self, p=0.4):
        rng = random.Random(int(time.time()))
        i = int(rng.random()*16)
        j = int(rng.random()*32)
        self.data[i][j] = 1

    def set_from_rule_array(self, rule_np):
        """Carga desde un ndarray[512]."""
        for idx in range(512):
            r, c = divmod(idx, 32)
            self.data[r][c] = int(rule_np[idx])

    def to_rule_array(self):
        rule = np.zeros(512, dtype=np.uint8)
        for i in range(16):
            for j in range(32):
                idx = i * 32 + j
                if idx < 512:
                    rule[idx] = self.data[i][j]
        return rule

     
    def build_rects(self, x0, y0):
        """Genera los Rect para hit-testing."""
        return [
            [pygame.Rect(x0 + j * (self.BW + self.BM),
                         y0 + i * (self.BH + self.BM),
                         self.BW, self.BH)
             for j in range(32)]
            for i in range(16)
        ]

    @property
    def total_w(self): return 32 * (self.BW + self.BM)
    @property
    def total_h(self): return 16 * (self.BH + self.BM)

    def handle_click(self, pos, rects):
        for i in range(16):
            for j in range(32):
                if rects[i][j].collidepoint(pos):
                    self.toggle(i, j)
                    return i, j
        return None

    def draw(self, surf, rects, font):
        for i in range(16):
            for j in range(32):
                v  = self.data[i][j]
                bg = BTN_ON_BG  if v else BTN_OFF_BG
                fg = BTN_ON_FG  if v else BTN_OFF_FG
                r  = rects[i][j]
                pygame.draw.rect(surf, bg, r, border_radius=1)
                t  = font.render(str(v), True, fg)
                surf.blit(t, (r.centerx - t.get_width()  // 2,
                              r.centery - t.get_height() // 2))


 
#  KERNEL 3x3 (vecindad de Moore editable)
 
class Kernel3x3:
    """
    Representa los 9 bits del kernel (vecindad de Moore).
    Orden de bits:  NW N NE / W C E / SW S SE
    bit 0 = NW, bit 1 = N, bit 2 = NE,
    bit 3 = W,  bit 4 = C, bit 5 = E,
    bit 6 = SW, bit 7 = S, bit 8 = SE

    Al clicar una celda se recalcula la regla completa:
        rule[idx] = 1  si  (idx & mask) == mask
    Es decir: se activan todas las entradas de la regla en las que
    los vecinos marcados en el kernel estan presentes.
    """
    CELL_S = 22   # px de cada celda del kernel
    LABELS = ["NW", "N ", "NE",
              "W ", "C ", "E ",
              "SW", "S ", "SE"]

    def __init__(self, x, y):
        self.x     = x
        self.y     = y
        self.bits  = [0] * 9
        self.rects = [
            pygame.Rect(x + (i % 3) * self.CELL_S,
                        y + (i // 3) * self.CELL_S,
                        self.CELL_S - 2,
                        self.CELL_S - 2)
            for i in range(9)
        ]

    @property
    def total_w(self): return self.CELL_S * 3
    @property
    def total_h(self): return self.CELL_S * 3

    @property
    def mask(self):
        m = 0
        for i, b in enumerate(self.bits):
            m |= b << i
        return m

    def handle_click(self, pos):
        """Toggle del bit clickeado; devuelve su indice o None."""
        for i, r in enumerate(self.rects):
            if r.collidepoint(pos):
                self.bits[i] ^= 1
                return i
        return None

    def apply_to_matrix(self, matriz_regla):
        """
        Recalcula la regla completa segun el kernel y la escribe
        en la MatrizRegla.  Devuelve el ndarray[512].
        """
        m    = self.mask
        print(f"Kernel mask: {m:09b} ({m})")
        for idx in range(512):
            if (idx) == int(m):
                matriz_regla.data[idx // 32][idx % 32] = 1
        rule = matriz_regla.to_rule_array()
        return rule

    def draw(self, surf, font):
        for i, r in enumerate(self.rects):
            v  = self.bits[i]
            bg = BTN_ON_BG  if v else BTN_OFF_BG
            fg = BTN_ON_FG  if v else BTN_OFF_FG
            pygame.draw.rect(surf, bg, r, border_radius=3)
            pygame.draw.rect(surf, P_BORDER, r, 1, border_radius=3)
            lbl = font.render(self.LABELS[i], True, fg)
            surf.blit(lbl, (r.centerx - lbl.get_width()  // 2,
                            r.centery - lbl.get_height() // 2))
            
    def clear(self):
        for i in range(9):
            self.bits[i] = 0


 
#  WIDGETS GENERICOS
 
class Button:
    def __init__(self, rect, label, toggle=False,
                 bg=BTN_OFF_BG, fg=BTN_OFF_FG,
                 bg_on=(170, 55, 55), fg_on=(240, 240, 240)):
        self.rect   = pygame.Rect(rect)
        self.label  = label
        self.toggle = toggle
        self.active = False
        self.bg     = bg;  self.fg    = fg
        self.bg_on  = bg_on; self.fg_on = fg_on
        self._hov   = False

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            self._hov = self.rect.collidepoint(ev.pos)
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                if self.toggle:
                    self.active = not self.active
                return True
        return False

    def draw(self, surf, font):
        if self.toggle and self.active:
            bg, fg = self.bg_on, self.fg_on
        elif self._hov:
            bg, fg = BTN_HOV, P_FG
        else:
            bg, fg = self.bg, self.fg
        pygame.draw.rect(surf, bg, self.rect, border_radius=4)
        pygame.draw.rect(surf, P_BORDER, self.rect, 1, border_radius=4)
        t = font.render(self.label, True, fg)
        surf.blit(t, (self.rect.centerx - t.get_width()  // 2,
                      self.rect.centery - t.get_height() // 2))


class Slider:
    def __init__(self, rect, vmin=0.0, vmax=1.0, value=0.5):
        self.rect  = pygame.Rect(rect)
        self.vmin  = vmin; self.vmax = vmax; self.value = value
        self._drag = False

    @property
    def norm(self):
        return (self.value - self.vmin) / max(self.vmax - self.vmin, 1e-9)

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.rect.collidepoint(ev.pos):
                self._drag = True; self._set(ev.pos[0])
        if ev.type == pygame.MOUSEBUTTONUP   and ev.button == 1:
            self._drag = False
        if ev.type == pygame.MOUSEMOTION and self._drag:
            self._set(ev.pos[0])

    def _set(self, mx):
        t = (mx - self.rect.x) / max(self.rect.width, 1)
        self.value = self.vmin + max(0.0, min(1.0, t)) * (self.vmax - self.vmin)

    def draw(self, surf, font):
        pygame.draw.rect(surf, (45, 45, 52), self.rect, border_radius=4)
        fw = int(self.norm * self.rect.width)
        if fw > 0:
            pygame.draw.rect(surf, P_ACCENT,
                             (self.rect.x, self.rect.y, fw, self.rect.height),
                             border_radius=4)
        tx = self.rect.x + fw
        pygame.draw.circle(surf, (215, 215, 215), (tx, self.rect.centery), 7)
        pygame.draw.circle(surf, P_BORDER,         (tx, self.rect.centery), 7, 1)
        t = font.render(f"{self.value:.2f}", True, P_LABEL)
        surf.blit(t, (self.rect.right + 6,
                      self.rect.centery - t.get_height() // 2))


 
#  APLICACION PRINCIPAL
 
class ACOSXM:
    FPS = 30

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("ACOSXM - Automata Celular Vecindad de Moore")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock  = pygame.time.Clock()

        # Fuentes
        self.fn  = pygame.font.SysFont("monospace",  9)
        self.fm  = pygame.font.SysFont("monospace", 11)
        self.fb  = pygame.font.SysFont("monospace", 11, bold=True)
        self.fxs = pygame.font.SysFont("monospace",  8)

        self.theme_idx = 0

        # ── Objetos del automata 
        self.matriz_regla = MatrizRegla()
        self.life         = Life2DM()

        # ── Layout: posiciones Y de cada seccion 
        y = PAD

        # Encabezado regla
        self.y_rule_hdr = y;  y += 14

        # Numeracion de columnas de la matriz
        self.y_colnum = y;    y += 10

        # Matriz 16x32
        self.y_mat = y
        MAT_X0 = PAD + 16
        self.mat_rects = self.matriz_regla.build_rects(MAT_X0, y)
        y += self.matriz_regla.total_h + PAD + 4

        # Separador visual
        self.y_sep1 = y - 4

        # Encabezado kernel
        self.y_kern_hdr = y; y += 14

        # Kernel 3x3  (izquierda)
        KERN_X = PAD
        self.kernel = Kernel3x3(KERN_X, y)

        # Info del kernel (a la derecha del kernel)
        self.x_kern_info = KERN_X + self.kernel.total_w + 16
        self.y_kern_info = y
        y += self.kernel.total_h + PAD + 4

        # Separador
        self.y_sep2 = y - 4

        # Botones de accion
        BW, BH, BGAP = 183, 22, 4

        def btn(label, col, yy, toggle=False,
                bg=BTN_OFF_BG, bg_on=(170, 55, 55)):
            return Button((PAD + col * (BW + BGAP), yy, BW, BH),
                          label, toggle=toggle, bg=bg, bg_on=bg_on)

        self.btn_conf_aleat  = btn("Config. aleatoria",  0, y)
        self.btn_regla_aleat = btn("Regla aleatoria",    1, y);  y += BH + BGAP
        self.btn_evol_paso   = btn("Paso a paso",        0, y)
        self.btn_limpiar_reg = btn("Limpiar regla",      1, y);  y += BH + BGAP
        self.btn_evolucion   = btn("Evolucion", 0, y,
                                   toggle=True, bg=(45, 120, 60))
        self.btn_regla110    = btn("Regla 110",          1, y);  y += BH + BGAP
        self.btn_limpiar_vis = btn("Limpiar vista",      0, y);  y += BH + PAD * 2
        self.btn_agregar_kernel = btn("Agregar kernel",      1, y);  y += BH + PAD * 2

        # Slider densidad
        self.y_den_lbl = y; y += 13
        self.slider_den = Slider((PAD, y, PANEL_W - 65, 12), value=0.5)
        y += 20 + PAD

        # Selector de tema
        self.y_tema_lbl = y; y += 13
        TBW = (PANEL_W - PAD) // len(COLOR_THEMES) - 2
        self.tema_btns = []
        for idx, t in enumerate(COLOR_THEMES):
            bx = PAD + idx * (TBW + 2)
            self.tema_btns.append(
                Button((bx, y, TBW, 17), t["name"][:6],
                       bg=(38, 38, 46), fg=BTN_OFF_FG))
        y += 17 + PAD

        # Info
        self.y_info = y

        # Listas para iterar
        self._action_btns = [
            self.btn_conf_aleat, self.btn_regla_aleat,
            self.btn_evol_paso,  self.btn_limpiar_reg,
            self.btn_evolucion,  self.btn_regla110,
            self.btn_limpiar_vis, self.btn_agregar_kernel
        ]
        self._all_btns = self._action_btns + self.tema_btns

        # Surface del panel
        self.panel_surf = pygame.Surface((PANEL_W, WIN_H))

        # Scroll y cursor
        self.scroll_x = 0; self.scroll_y = 0
        self.cur_cx   = 0; self.cur_cy   = 0

     
    @property
    def theme(self):
        return COLOR_THEMES[self.theme_idx]

     
    def run(self):
        while True:
            self.clock.tick(self.FPS)
            self._events()
            self.life.tick()
            self._draw()

     
    def _events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()

            # Scroll
            if ev.type == pygame.MOUSEWHEEL:
                mx, _ = pygame.mouse.get_pos()
                if mx >= PANEL_W:
                    self.scroll_y = max(0, min(GRID_H - 1,
                                               self.scroll_y - ev.y))
                    self.scroll_x = max(0, min(GRID_W - 1,
                                               self.scroll_x - ev.x))

            # Clic en espacio de evoluciones
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                if mx >= PANEL_W:
                    cx = (mx - PANEL_W) // CELL_PX + self.scroll_x
                    cy = my              // CELL_PX + self.scroll_y
                    self.life.toggle_cell(cx, cy)
                    self.cur_cx, self.cur_cy = cx, cy

            # Arrastrar en espacio
            if ev.type == pygame.MOUSEMOTION and ev.buttons[0]:
                mx, my = ev.pos
                if mx >= PANEL_W:
                    cx = (mx - PANEL_W) // CELL_PX + self.scroll_x
                    cy = my              // CELL_PX + self.scroll_y
                    if (cx, cy) != (self.cur_cx, self.cur_cy):
                        self.life.toggle_cell(cx, cy)
                        self.cur_cx, self.cur_cy = cx, cy

            # Slider
            self.slider_den.handle_event(ev)

            # Botones de accion + tema
            for b in self._all_btns:
                if b.handle_event(ev):
                    self._on_btn(b)

            # Clic en la matriz de la regla
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                res = self.matriz_regla.handle_click(ev.pos, self.mat_rects)
                if res is not None:
                    # Sincronizar con Life2DM
                    self.life.sync_rule_from_matrix(self.matriz_regla.data)

            # Clic en el kernel 3x3
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                bit = self.kernel.handle_click(ev.pos)

     
    def _on_btn(self, b):
        d = self.slider_den.value

        if   b is self.btn_conf_aleat:
            self.life.random_fill(d)

        elif b is self.btn_regla_aleat:
            self.matriz_regla.randomize()
            self.life.sync_rule_from_matrix(self.matriz_regla.data)

        elif b is self.btn_evol_paso:
            self.life.step()

        elif b is self.btn_limpiar_reg:
            self.matriz_regla.clear()
            self.life.rule[:] = 0
            self.kernel.clear()

        elif b is self.btn_evolucion:
            self.life.running = b.active

        elif b is self.btn_regla110:
            self.life.rule110_fill(d)

        elif b is self.btn_limpiar_vis:
            if self.life.running:
                self.life.running = False
                self.btn_evolucion.active = False
            self.life.reset()

        elif b is self.btn_agregar_kernel:
            rule = self.kernel.apply_to_matrix(self.matriz_regla)
            self.life.rule = rule

        else:
            for idx, tb in enumerate(self.tema_btns):
                if b is tb:
                    self.theme_idx = idx
                    self.life.dirty = True
                    break

     
    def _draw(self):
        self.screen.fill((10, 10, 12))

        # Panel
        self._draw_panel()
        self.screen.blit(self.panel_surf, (0, 0))

        # Espacio de evoluciones
        self.life.draw(self.theme)
        vr = pygame.Rect(
            self.scroll_x * CELL_PX, self.scroll_y * CELL_PX,
            min(WIN_W - PANEL_W, SPACE_W),
            min(WIN_H,            SPACE_H))
        self.screen.blit(self.life.surf, (PANEL_W, 0), area=vr)

        # Separador panel / espacio
        pygame.draw.line(self.screen, P_BORDER,
                         (PANEL_W, 0), (PANEL_W, WIN_H), 2)

        # Titulo del espacio
        t = self.fb.render(
            f"Espacio de evoluciones  —  {self.theme['name']}",
            True, (110, 110, 128))
        self.screen.blit(t, (PANEL_W + 6, 4))

        pygame.display.flip()

     
    def _draw_panel(self):
        surf = self.panel_surf
        surf.fill(P_BG)

        # ── Encabezado matriz    ───────────────────
        draw_text(surf, self.fb, "Regla de evolucion  (16 x 32 = 512 bits)",
                  (PAD, self.y_rule_hdr), P_FG)

        # Numeracion de columnas (cada 8)
        for j in range(0, 32, 8):
            rx = PAD + 16 + j * (MatrizRegla.BW + MatrizRegla.BM)
            draw_text(surf, self.fxs, str(j), (rx, self.y_colnum), P_LABEL)

        # Numeracion de filas
        for i in range(16):
            ry = self.y_mat + i * (MatrizRegla.BH + MatrizRegla.BM)
            draw_text(surf, self.fxs, str(i), (PAD, ry + 2), P_LABEL)

        # Matriz 16x32
        self.matriz_regla.draw(surf, self.mat_rects, self.fxs)

        # Separador
        pygame.draw.line(surf, P_BORDER,
                         (PAD, self.y_sep1), (PANEL_W - PAD, self.y_sep1))

        # ── Kernel 3x3    ──────────────────────────
        draw_text(surf, self.fb, "Kernel",
                  (PAD, self.y_kern_hdr), P_FG)

        self.kernel.draw(surf, self.fxs)

        # Info del kernel a su derecha
        xi = self.x_kern_info
        yi = self.y_kern_info
        lineas = [
            "Clic en cada celda del",
            "kernel para activarla.",
            "La regla se recalcula:",
            "rule[i]=1 si todos los",
            "bits del kernel activos",
            "estan en el indice i.",
        ]
        for ln in lineas:
            draw_text(surf, self.fn, ln, (xi, yi), P_LABEL)
            yi += 11
        yi += 4
        draw_text(surf, self.fn,  "Mascara:", (xi, yi), P_LABEL)
        draw_text(surf, self.fb,
                  f"{self.kernel.mask:09b}  ({self.kernel.mask})",
                  (xi + 55, yi), P_VALUE)

        # Separador
        pygame.draw.line(surf, P_BORDER,
                         (PAD, self.y_sep2), (PANEL_W - PAD, self.y_sep2))

        # ── Botones de accion    ───────────────────
        for b in self._action_btns:
            b.draw(surf, self.fm)

        # ── Slider densidad    ─────────────────────
        draw_text(surf, self.fxs, "Densidad",
                  (PAD, self.y_den_lbl), P_LABEL)
        self.slider_den.draw(surf, self.fxs)

        # ── Selector de tema    ────────────────────
        draw_text(surf, self.fxs, "Modo de color",
                  (PAD, self.y_tema_lbl), P_LABEL)
        for idx, b in enumerate(self.tema_btns):
            if idx == self.theme_idx:
                hl = b.rect.inflate(4, 4)
                pygame.draw.rect(surf, COLOR_THEMES[idx]["cell"],
                                 hl, border_radius=4)
            b.draw(surf, self.fxs)

        # ── Info de estado    ──────────────────────
        y = self.y_info

        def kv(label, val):
            nonlocal y
            draw_text(surf, self.fm, label,      (PAD,       y), P_LABEL)
            draw_text(surf, self.fb, str(val),   (PAD + 118, y), P_VALUE)
            y += 14

        kv("Generaciones:", self.life.gen)
        kv("Celulas vivas:", self.life.count_alive())
        kv("Cursor  x:",     self.cur_cx)
        kv("Cursor  y:",     self.cur_cy)

        est   = "   CORRIENDO" if self.life.running else "   DETENIDO"
        sym   = "▶" if self.life.running else "■"
        color = (75, 220, 95) if self.life.running else (190, 70, 70)
        draw_text(surf, self.fb, sym + est, (PAD, y), color)
        y += 16

        # Ayuda
        y += 4
        for h in ["ESC: salir",
                  "Rueda: scroll",
                  "Clic+arrastrar: dibujar celulas"]:
            draw_text(surf, self.fxs, h, (PAD, y), (68, 68, 80))
            y += 11

        # Borde del panel
        pygame.draw.rect(surf, P_BORDER, (0, 0, PANEL_W, WIN_H), 1)


 
if __name__ == "__main__":
    ACOSXM().run()