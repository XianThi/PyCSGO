import struct
import time
import Offsets


class Player:
    def __init__(self, index, list_entry, mem, offsets: Offsets.OffsetsConfig):
        self.index = index
        self.le = list_entry
        self.mem = mem
        self.offsets = offsets

        # PUBLIC
        self.pos = (0, 0, 0)
        self.ping = 0
        self.team = 0
        self.health = 0
        self.armor = 0
        self.money = 0
        self.bot = True
        self.alive = False
        self.scoped = False
        self.flashed = False
        self.spotted = False
        self.defusing = False
        self.localplayer = False
        self.name = ""
        self.steam_id = 0
        self.weapon = ""
        self.clean_weapon = ""
        self.bone_list = []

        # PRIVATE
        self.pawn = 0
        self.controller = 0

        # CACHE / TIMERS
        self.last_slow_update = 0
        self.slow_update_interval = 0.5  # 500ms
        self._pawn_read_size = self._calc_max_pawn_offset()


    def _calc_max_pawn_offset(self):
            offsets = [
                self.offsets.pawn.m_iHealth,
                self.offsets.pawn.m_vOldOrigin + 12,
                self.offsets.pawn.m_pGameSceneNode + 8,
                self.offsets.pawn.m_iTeamNum,
                self.offsets.pawn.m_ArmorValue,
                self.offsets.pawn.m_bIsDefusing,
                self.offsets.pawn.m_entitySpottedState + self.offsets.pawn.m_bSpottedByMask,
                self.offsets.pawn.m_flFlashOverlayAlpha,
                self.offsets.pawn.m_bIsScoped,
            ]
            return max(offsets) + 32   # padding
    # =========================
    # MAIN UPDATE
    # =========================
    def update(self, force_slow=False):
        """
        Update the player.
        force_slow: if True, will update low-freq data
        """

        # -----------------------
        # pointer cache
        # -----------------------
        if not self.controller or not self.pawn:
            if not self.get_controller():
                return False
            if not self.get_pawn():
                return False

        # -----------------------
        # fast update (every frame)
        # -----------------------
        if not self.update_pawn():
            return False

        # -----------------------
        # slow update (tiered)
        # -----------------------
        now = time.time()
        if force_slow or now - self.last_slow_update > self.slow_update_interval:
            self.update_controller()
            self.update_weapon()
            self.last_slow_update = now

        return True

    # =========================
    # POINTER CACHE
    # =========================
    def get_controller(self):
        try:
            self.controller = self.mem.read_ulonglong(self.le + (self.index + 1) * 0x70)
            return self.controller != 0
        except:
            return False

    def get_pawn(self):
        try:
            entity_pawn_address = self.mem.read_ulonglong(
                self.controller + self.offsets.controller.m_hPawn
            )
            if not entity_pawn_address:
                return False

            entity_list = self.mem.read_ulonglong(
                self.mem.client + self.offsets.entityList
            )
            if not entity_list:
                return False

            list_entry = self.mem.read_ulonglong(
                entity_list + 0x10 + 0x8 * ((entity_pawn_address & 0x7FFF) >> 9)
            )
            if not list_entry:
                return False

            self.pawn = self.mem.read_ulonglong(
                list_entry + 0x70 * (entity_pawn_address & 0x1FF)
            )
            return self.pawn != 0

        except:
            return False

    # =========================
    # FAST PAWN UPDATE (EVERY FRAME)
    # =========================
    def update_pawn(self):
        try:
            # --- STRUCT READ ---
            raw = self.mem.pm.read_bytes(self.pawn, self._pawn_read_size) 

            self.health = struct.unpack_from("<i", raw, self.offsets.pawn.m_iHealth)[0]
            self.alive = self.health > 0
            if not self.alive:
                return True

            self.pos = (
                struct.unpack_from("<f", raw, self.offsets.pawn.m_vOldOrigin)[0],
                struct.unpack_from("<f", raw, self.offsets.pawn.m_vOldOrigin + 4)[0],
                struct.unpack_from("<f", raw, self.offsets.pawn.m_vOldOrigin + 8)[0],
            )

            self.team = struct.unpack_from("<i", raw, self.offsets.pawn.m_iTeamNum)[0]
            self.armor = struct.unpack_from("<i", raw, self.offsets.pawn.m_ArmorValue)[0]

            self.defusing = struct.unpack_from(
                "<?", raw, self.offsets.pawn.m_bIsDefusing
            )[0]
            self.spotted = struct.unpack_from(
                "<?",
                raw,
                self.offsets.pawn.m_entitySpottedState
                + self.offsets.pawn.m_bSpottedByMask,
            )[0]
            self.flashed = (
                struct.unpack_from("<f", raw, self.offsets.pawn.m_flFlashOverlayAlpha)[
                    0
                ]
                > 0
            )
            self.scoped = struct.unpack_from("<?", raw, self.offsets.pawn.m_bIsScoped)[
                0
            ]

            self.update_skeleton(raw)
            return True

        except:
            return False

    # =========================
    # SLOW CONTROLLER UPDATE (TIERED)
    # =========================
    def update_controller(self):
        try:
            self.steam_id = self.mem.read_ulonglong(
                self.controller + self.offsets.controller.m_steamID
            )
            self.bot = self.steam_id == 0
            self.name = self.mem.read_string(
                self.controller + self.offsets.controller.m_iszPlayerName, 32
            )
            self.localplayer = self.mem.read_bool(
                self.controller + self.offsets.controller.m_bIsLocalPlayerController
            )
            self.ping = self.mem.read_int(
                self.controller + self.offsets.controller.m_iPing
            )

            money_services = self.mem.read_ulonglong(
                self.controller + self.offsets.controller.m_pInGameMoneyServices
            )
            if money_services:
                self.money = self.mem.read_int(
                    money_services + self.offsets.controller.m_iAccount
                )

            return True
        except:
            return False

    # =========================
    # SLOW WEAPON UPDATE (TIERED)
    # =========================
    def update_weapon(self):
        try:
            weapon_ptr = self.mem.read_ulonglong(
                self.pawn + self.offsets.pawn.m_pClippingWeapon
            )
            if not weapon_ptr:
                return False
            weapon_ptr = self.mem.read_ulonglong(weapon_ptr + 0x10)
            weapon_ptr = self.mem.read_ulonglong(weapon_ptr + 0x20)
            self.weapon = self.mem.read_string(weapon_ptr, 32)
            self.clean_weapon = self.weapon.replace("weapon_", "")
            return True
        except:
            return False

    # =========================
    # SKELETON (FAST)
    # =========================
    def update_skeleton(self, raw_pawn=None):
        try:
            self.bone_list.clear()
            game_scene = (
                struct.unpack_from("<Q", raw_pawn, self.offsets.pawn.m_pGameSceneNode)[
                    0
                ]
                if raw_pawn
                else self.mem.read_ulonglong(
                    self.pawn + self.offsets.pawn.m_pGameSceneNode
                )
            )
            if not game_scene:
                return False

            bone_array = self.mem.read_ulonglong(
                game_scene + (self.offsets.bone.m_modelState + 0x80)
            )
            if not bone_array:
                return False

            raw_bones = self.mem.pm.read_bytes(bone_array, 30 * 0x20)
            for i in range(30):
                x, y, z = struct.unpack_from("<fff", raw_bones, i * 0x20)
                self.bone_list.append((x, y, z))
            return True
        except:
            return False

    # =========================
    # BOUNDS
    # =========================
    def get_bounds(self, view_matrix, screen_size, w2s_func):
        origin = w2s_func(self.pos, view_matrix, screen_size)
        if not origin:
            return None

        top_pos = (
            self.bone_list[6]
            if self.bone_list
            else (self.pos[0], self.pos[1], self.pos[2] + 65)
        )
        top = w2s_func(top_pos, view_matrix, screen_size)
        if not top:
            return None

        height = origin[1] - top[1]
        width = height / 2.4

        x1 = top[0] - width / 2
        y1 = top[1] - width / 4
        x2 = origin[0] + width / 2
        y2 = origin[1]

        return (x1, y1), (x2, y2)
