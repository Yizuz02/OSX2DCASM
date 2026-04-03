import sys
import math
import random
import time
from config import *
from life2dm import Life2DM
from matrizregla import MatrizRegla
from kernel import Kernel3x3
from widgets.button import Button
from widgets.slider import Slider

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

        self.show_panel = True

        self.theme_idx = 0

        # ── Objetos del automata 
        self.matriz_regla = MatrizRegla()
        self.life         = Life2DM()

        # ── Layout: posiciones Y de cada seccion 
        y = PAD

        # Boton ocultar panel
        self.btn_ocultar_panel = Button((PANEL_W - PAD - 40, y, 40, 20),
                                       "<<", toggle=False, bg=BTN_OFF_BG, bg_on=BTN_ON_BG)

        # Encabezado regla
        self.y_rule_hdr = y;  y += 18

        

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

        def btn_panel(label, col, yy, toggle=False,
                bg=BTN_OFF_BG, bg_on=(170, 55, 55)):
            return Button((PAD + col * (BW + BGAP), yy, BW, BH),
                          label, toggle=toggle, bg=bg, bg_on=bg_on)

        self.btn_conf_aleat  = btn_panel("Config. aleatoria",  0, y)
        self.btn_regla_aleat = btn_panel("Regla aleatoria",    1, y);  y += BH + BGAP
        self.btn_evol_paso   = btn_panel("Paso a paso",        0, y)
        self.btn_limpiar_reg = btn_panel("Limpiar regla",      1, y);  y += BH + BGAP
        self.btn_evolucion   = btn_panel("Evolucion", 0, y,
                                   toggle=True, bg=(45, 120, 60))
        self.btn_regla110    = btn_panel("Regla 110",          1, y);  y += BH + BGAP
        self.btn_limpiar_vis = btn_panel("Limpiar vista",      0, y)
        self.btn_agregar_kernel = btn_panel("Agregar kernel",      1, y);  y += BH + PAD * 2

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
        self._all_btns = self._action_btns + self.tema_btns + [self.btn_ocultar_panel]

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
        if self.show_panel:
            self._draw_panel()
        
            

        self.btn_ocultar_panel.draw(self.panel_surf, self.fm)
        self.screen.blit(self.panel_surf, (0, 0))

        # Espacio de evoluciones
        self.life.draw(self.theme)
        vr = pygame.Rect(
            self.scroll_x * CELL_PX, self.scroll_y * CELL_PX,
            SPACE_W,
            min(WIN_H, SPACE_H))
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
