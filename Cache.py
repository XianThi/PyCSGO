import time

import keyboard

from Bomb import Bomb
from Game import Game
from Globals import Globals
from Offsets import GameOptions
from Player import Player


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

        self.players = []

        self.last = 0
        self.refresh_delay = 0.005  # 5ms

        self.esp_enabled = self.options.glowESPEnabled
        self.trigger_bot_enabled = self.options.triggerBotEnabled
        self.auto_bhop_enabled = self.options.autoBHOPEnabled
        self.sound_esp_enabled = self.options.soundESPEnabled
        self.rcs_enabled = self.options.rcsEnabled

    # =========================

    def refresh(self):
        if not self.mem.pm:
            return False

        now = time.time()

        # view matrix her frame
        if not self.game.update():
            return False

        # rate limit
        if now - self.last < self.refresh_delay:
            return True

        # heavy updates
        self.game.update_entity_list()
        self.globals.update()
        self.bomb.update()

        scan = []

        for i in range(self.globals.max_clients):
            player = Player(i, self.game.list_entry, self.mem, self.offsets)

            if not player.update():
                continue

            scan.append(player)

        # swap
        self.players = scan
        self.last = now
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
        return Snapshot(
            self.game, self.bomb, self.globals, self.players.copy(), self.options
        )
