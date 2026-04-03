from config import *

#  MATRIZ DE REGLA  16 x 32
 
class MatrizRegla:
    """512 bits de la regla organizados en 16 filas x 32 columnas."""
    BW = PANEL_W * 0.9 // 32  # ancho de cada boton
    BH = BW
    BM = int(BW * 0.1)             # margen entre botones

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