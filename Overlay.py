from datetime import datetime
import random

from Cache import Cache
from ESP import Esp
import pygame
import win32gui
import win32con
import win32api
import time
import sys

class AntiDetectionOverlay:
    def __init__(self,cache:Cache,WIDTH=1920, HEIGHT=1080):
        self.cache = cache
        self.WIDTH = WIDTH
        self.HEIGHT = HEIGHT
        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.WIDTH, self.HEIGHT), 
            pygame.NOFRAME | pygame.HWSURFACE | pygame.DOUBLEBUF | pygame.SCALED
        )
        pygame.display.set_caption("Spotify.exe - Premium")  # Signature spoof
        
        # Icon spoof (opsiyonel)
        try:
            icon = pygame.image.load("icon.png")
            pygame.display.set_icon(icon)
        except:
            pass
        self.hwnd = pygame.display.get_wm_info()["window"]
        self.apply_bypass()
        self.esp = Esp()
        self.esp_enabled = self.cache.esp_enabled
        self.big_font = pygame.font.SysFont(None, 30)

    def get_smart_title(self):
        """Duruma göre akıllı title"""
        hour = datetime.now().hour
        if 9 <= hour <= 17:  # Çalışma saatleri
            return random.choice(["Microsoft Teams", "Outlook", "Excel"])
        elif 18 <= hour <= 22:  # Akşam
            return random.choice(["Netflix", "YouTube", "Discord"])
        else:  # Gece
            return random.choice(["Task Manager", "cmd.exe", "PowerShell"])
    def apply_bypass(self):
        """Tüm bypass teknikleri"""
        # Click-through + Layered
        ex_style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            self.hwnd,
            win32con.GWL_EXSTYLE,
            ex_style
            | win32con.WS_EX_LAYERED
            | win32con.WS_EX_TOPMOST
            | win32con.WS_EX_TRANSPARENT   # 🔥 input geçirme
        )
        win32gui.SetLayeredWindowAttributes(
            self.hwnd,
            0x000000,  # siyah transparan
            255,
            win32con.LWA_COLORKEY
        )
        win32gui.SetWindowPos(
            self.hwnd,
            win32con.HWND_TOPMOST,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE
        )
        # Opacity 100% ama input transparent
        #win32gui.SetLayeredWindowAttributes(self.hwnd, 0, 255, win32con.LWA_ALPHA)
        
        # Title spoof
        win32gui.SetWindowText(self.hwnd, self.get_smart_title())
        # Process name spoof (advanced)
        #self.spoof_process_name()
    
    # def spoof_process_name(self):
    #     """Process signature değiştir (ileri seviye)"""
    #     # PsSetCreateProcessNotifyRoutine ile hook (C++ gerekir)
    #     # Python'da basit alternatif: thread name değiştir
    #     ctypes.windll.kernel32.SetThreadDescription(
    #         ctypes.windll.kernel32.GetCurrentThread(), 
    #         b"SpotifyWorkerThread"
    #     )
    
    # def update_game_position(self):
    #     """Game window ile sync kal"""
    #     game_hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
    #     if game_hwnd:
    #         rect = win32gui.GetWindowRect(game_hwnd)
    #         win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST,
    #                              rect[0], rect[1], 
    #                              rect[2]-rect[0], rect[3]-rect[1], 0)
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # Game position sync
            # self.update_game_position()
            
            # Render (ESP örneği)
            self.screen.fill((0, 0, 0))
            snap = self.cache.snapshot()
            if not snap:
                pygame.display.flip()
                continue
            # toggle
            if self.is_pressed(win32con.VK_F1):
                self.esp_enabled = not self.esp_enabled
            if not self.esp_enabled:
                text = self.big_font.render("ESP OFF", True, (255, 0, 0))
                self.screen.blit(text, (50, 50))
            else:
                self.esp.render(self.screen, snap)
            pygame.display.flip()
            clock.tick(120)
        
        pygame.quit()
        sys.exit()

    def is_pressed(self, vk):
        state = win32api.GetAsyncKeyState(vk)
        return (state & 0x8000) and (state & 1)