from Cache import Snapshot
from Player import Player
from Utils import world_to_screen
import pygame

WIDTH, HEIGHT = 1920, 1080
CONNECTIONS = [
    (5, 4),
    (4, 2),
    (2, 0),
    (5, 8),
    (8, 9),
    (9, 10),
    (5, 13),
    (13, 14),
    (14, 15),
    (0, 22),
    (22, 23),
    (23, 24),
    (0, 25),
    (25, 26),
    (26, 27),
]
class Esp:
    def __init__(self):
        self.font = pygame.font.SysFont("consolas", 14)

    def render(self, screen, snap:Snapshot):
        if not snap.options.glowESPEnabled:
            return

        vm = snap.game.view_matrix
        players = snap.players

        local_team = None
        localplayer = None

        for p in players:
            if not p.alive:
                continue

            if p.localplayer:
                local_team = p.team
                localplayer = p
                continue

        for p in players:
            if not p.alive or p.localplayer:
                continue

            mate = (p.team == local_team)

            self.render_player(screen, p, vm, mate)

        # extra
        if snap.bomb:
            self.render_bomb(screen, snap.bomb, vm, localplayer)
    
    def render_player(self, screen, p:Player, vm, mate):
        bounds = p.get_bounds(vm, (WIDTH, HEIGHT), world_to_screen)
        if not bounds:
            return

        (x1, y1), (x2, y2) = bounds

        # BOX
        if True: 
            pass
            #color = (0,0,255) if mate else (255,0,0)
            #pygame.draw.rect(screen, color, (x1, y1, x2-x1, y2-y1), 1)

        # SKELETON
        if True:
            self.render_skeleton(screen, p, vm, mate)

        # HEAD TRACKER
        self.render_head(screen, p, bounds, vm, mate)

        # HP BAR
        self.render_health(screen, p, bounds)

        # NAME
        #self.render_name(screen, p, bounds)

    def render_skeleton(self, screen, p, vm, mate):
        color = (0,255,255) if mate else (255,255,0)

        for b1, b2 in CONNECTIONS:

            if b1 >= len(p.bone_list) or b2 >= len(p.bone_list):
                continue

            bone1 = p.bone_list[b1]
            bone2 = p.bone_list[b2]

            s1 = world_to_screen(bone1,vm, (WIDTH, HEIGHT))
            s2 = world_to_screen(bone2,vm, (WIDTH, HEIGHT))

            if not s1 or not s2:
                continue

            pygame.draw.line(screen, color, s1, s2, 1)
    def render_head(self, screen, p, bounds, vm, mate):
        if not p.bone_list:
            return

        head = p.bone_list[6] # BONE_INDEX.head = 6
        screen_pos = world_to_screen(head, vm, (WIDTH, HEIGHT))

        if not screen_pos:
            return

        (x1, y1), (x2, y2) = bounds
        width = x2 - x1

        color = (0,255,0) if mate else (255,0,0)

        pygame.draw.circle(screen, color, screen_pos, int(width/6), 1)
    
    def render_health(self, screen, p, bounds):
        (x1, y1), (x2, y2) = bounds

        height = y2 - y1
        hp = max(0, min(100, p.health))

        filled = height * (hp / 100)

        # bar
        pygame.draw.rect(screen, (0,255,0),
            (x1-6, y2-filled, 3, filled))

        # outline
        pygame.draw.rect(screen, (0,0,0),
            (x1-6, y1, 3, height), 1)
        
    def render_name(self, screen, p, bounds):
        (x1, y1), (x2, y2) = bounds

        text = p.name
        surf = self.font.render(text, True, (255,255,255))

        screen.blit(surf, (x1, y1 - 15))
    
    def render_tracer(self, screen, p, vm, mate):
        screen_pos = world_to_screen(p.pos, vm, (WIDTH, HEIGHT))

        if not screen_pos:
            return

        center = (WIDTH//2, HEIGHT//2)

        color = (0,255,255) if mate else (255,255,0)

        pygame.draw.line(screen, color, center, screen_pos, 1)

    def render_bomb(self, screen, bomb, vm, localplayer):
        pos = world_to_screen(bomb.pos,vm, (WIDTH, HEIGHT))
        if not pos:
            return

        text = f"{bomb.site} - {int(bomb.time_left)}s"

        surf = self.font.render(text, True, (255,255,255))
        screen.blit(surf, (pos[0], pos[1]))