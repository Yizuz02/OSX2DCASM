import numpy as np
import pygame

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

#  CONFIGURACION DE PANTALLA Y AUTOMATA

pygame.display.init()
info = pygame.display.Info()
SCREEN_W = info.current_w
SCREEN_H = info.current_h

#  CONSTANTES DEL AUTOMATA
 
GRID_W  = 255    # columnas del espacio (RING  / FACTOR)
GRID_H  = 255      # filas    del espacio (LINES / FACTOR)
CELL_PX = int(SCREEN_W / GRID_W)      # pixeles por celda

 
#  LAYOUT DE LA VENTANA

PANEL_W = int(SCREEN_W * 0.4)
SPACE_W = GRID_W * CELL_PX
SPACE_H = GRID_H * CELL_PX
WIN_W   = SPACE_W
WIN_H   = min(SPACE_H + 20, int(SCREEN_H * 0.9))
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