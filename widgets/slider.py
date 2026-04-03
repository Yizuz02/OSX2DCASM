from config import *

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