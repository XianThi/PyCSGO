import time


class BombSite:
    Unknown = -1
    A = 0
    B = 1


class Bomb:
    prev_is_planted = False
    plant_time = 0

    def __init__(self, mem, offsets):
        self.mem = mem
        self.offsets = offsets

        self.pos = (0, 0, 0)
        self.time_left = 0.0
        self.is_planted = False
        self.site = BombSite.Unknown

        self.address = 0

    # =========================

    def update(self):
        if not self.mem.pm:
            return False

        try:
            # planted check
            self.is_planted = self.mem.read_int(
                self.mem.client + self.offsets.plantedC4 - self.offsets.bomb.m_isPlanted
            ) != 0

            if not self.is_planted:
                Bomb.prev_is_planted = False
                return True

            # bomb entity pointer
            self.address = self.mem.read_ulonglong(
                self.mem.client + self.offsets.plantedC4
            )

            self.address = self.mem.read_ulonglong(self.address)

            if not self.address:
                return False

            # site
            site = self.mem.read_int(
                self.address + self.offsets.bomb.m_nBombSite
            )

            self.site = BombSite.B if site == 1 else BombSite.A

            # position
            node = self.mem.read_ulonglong(
                self.address + self.offsets.pawn.m_pGameSceneNode
            )

            if node:
                self.pos = self.mem.read_vec3(
                    node + self.offsets.bomb.m_vecAbsOrigin
                )

            # plant time logic
            if not Bomb.prev_is_planted:
                Bomb.plant_time = time.time()

            self.time_left = 41 - (time.time() - Bomb.plant_time)

            Bomb.prev_is_planted = True

            return True

        except:
            return False