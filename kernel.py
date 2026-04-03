from config import *
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

