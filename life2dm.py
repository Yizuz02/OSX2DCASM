import time
from config import *

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

