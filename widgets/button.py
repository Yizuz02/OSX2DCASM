from config import *

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