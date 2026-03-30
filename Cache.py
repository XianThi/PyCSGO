import threading
import time

import keyboard

from Bomb import Bomb
from Game import Game
from Globals import Globals
from Offsets import GameOptions
from Player import Player
from Utils import RenderPlayer


class Snapshot:
    def __init__(
        self,
        game: Game,
        bomb: Bomb,
        globals_: Globals,
        players: list[Player],
        options: GameOptions = None,
    ):
        self.game = game
        self.bomb = bomb
        self.globals = globals_
        self.players = players
        self.options = options


class Cache:
    def __init__(self, mem, offsets, options: GameOptions):
        self.mem = mem
        self.offsets = offsets
        self.options = options

        self.game = Game(mem, offsets)
        self.bomb = Bomb(mem, offsets)
        self.globals = Globals(mem, offsets)

        self.last = 0
        self.refresh_delay = 0.016  # 60 FPS
        self.last_entity_update = 0
        self.entity_update_interval = 0.2  # 200 ms

        self.esp_enabled = self.options.glowESPEnabled
        self.trigger_bot_enabled = self.options.triggerBotEnabled
        self.auto_bhop_enabled = self.options.autoBHOPEnabled
        self.sound_esp_enabled = self.options.soundESPEnabled
        self.rcs_enabled = self.options.rcsEnabled
        self._player_cache = {}
        self._player_list: list[Player] = []
        self._player_lock = threading.Lock()

    # =========================
    @property
    def players(self):
        with self._player_lock:
            return self._player_list.copy()

    def refresh(self):
        if not self.mem.pm:
            return False
        # view matrix her frame
        if not self.game.update():
            return False
        now = time.time()
        if now - self.last_entity_update > self.entity_update_interval:
            self.game.update_entity_list()
            self.last_entity_update = now

        # rate limit
        if now - self.last < self.refresh_delay:
            return True

        # heavy updates
        self.globals.update()
        self.bomb.update()
        valid_indices = set()

        for i in range(self.globals.max_clients):
            player = self._player_cache.get(i)
            if player is None:
                player = Player(i, self.game.list_entry, self.mem, self.offsets)
                self._player_cache[i] = player

            if not player.update():
                # Oyuncu geçersizse (ölü, bağlantısı kopmuş vs.) listeden çıkar, ama cache'de tut (belki geri gelir)
                continue

            valid_indices.add(i)
        with self._player_lock:
            self._player_list = [self._player_cache[i] for i in valid_indices]

        self.last = now
        # toggle kontrolleri vs...
        if keyboard.is_pressed("f1"):
            self.esp_enabled = not self.esp_enabled
            time.sleep(0.2)  # debounce
        return True

    # =========================

    def checkKeyboard(self, key):
        # toggle esp
        if key == 0x45:  # E
            self.esp_enabled = not self.esp_enabled

        # toggle trigger bot
        if key == 0x54:  # T
            self.trigger_bot_enabled = not self.trigger_bot_enabled

        # toggle auto bhop
        if key == 0x42:  # B
            self.auto_bhop_enabled = not self.auto_bhop_enabled

        # toggle sound esp
        if key == 0x52:  # R
            self.sound_esp_enabled = not self.sound_esp_enabled

        # toggle rcs
        if key == 0x56:  # V
            self.rcs_enabled = not self.rcs_enabled

    def snapshot(self):
        with self._player_lock:
            render_players = [RenderPlayer(p) for p in self._player_list]
        return Snapshot(self.game, self.bomb, self.globals, render_players, self.options)
