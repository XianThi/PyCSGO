import struct

import Offsets



class BoneData:
    def __init__(self, pos):
        self.pos = pos

class BonePos:
    def __init__(self, pos):
        self.pos = pos
class BoneIndex:
    head = 6
    neck_0 = 5
    spine_1 = 4
    spine_2 = 2
    pelvis = 0

    arm_upper_L = 8
    arm_lower_L = 9
    hand_L = 10

    arm_upper_R = 13
    arm_lower_R = 14
    hand_R = 15

    leg_upper_L = 22
    leg_lower_L = 23
    ankle_L = 24

    leg_upper_R = 25
    leg_lower_R = 26
    ankle_R = 27

class Player:
    def __init__(self, index, list_entry, mem, offsets: Offsets.OffsetsConfig):
        self.index = index
        self.le = list_entry
        self.mem = mem
        self.offsets = offsets

        # public data
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

        # private
        self.pawn = 0
        self.controller = 0

    # =========================

    def update(self):
        if not self.get_controller():
            return False

        if not self.get_pawn():
            return False

        if not self.update_controller():
            return False

        if not self.update_pawn():
            return False

        return True

    # =========================

    def get_controller(self):
        try:
            self.controller = self.mem.read_ulonglong(
                self.le + (self.index + 1) * 0x70
            )
            return self.controller != 0
        except:
            return False

    # =========================

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

    def update_controller(self):
        try:
            self.steam_id = self.mem.read_ulonglong(
                self.controller + self.offsets.controller.m_steamID
            )

            self.bot = self.steam_id == 0

            self.name = self.mem.read_string(
                self.controller + self.offsets.controller.m_iszPlayerName,
                32
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

    def update_pawn(self):
        try:
            self.health = self.mem.read_int(
                self.pawn + self.offsets.pawn.m_iHealth
            )

            self.alive = self.health > 0

            if not self.alive:
                return True

            self.pos = self.mem.read_vec3(
                self.pawn + self.offsets.pawn.m_vOldOrigin
            )

            self.team = self.mem.read_int(
                self.pawn + self.offsets.pawn.m_iTeamNum
            )

            self.armor = self.mem.read_int(
                self.pawn + self.offsets.pawn.m_ArmorValue
            )

            self.defusing = self.mem.read_bool(
                self.pawn + self.offsets.pawn.m_bIsDefusing
            )

            self.spotted = self.mem.read_bool(
                self.pawn + self.offsets.pawn.m_entitySpottedState + self.offsets.pawn.m_bSpottedByMask
            )

            self.flashed = self.mem.read_float(
                self.pawn + self.offsets.pawn.m_flFlashOverlayAlpha
            ) > 0

            self.scoped = self.mem.read_bool(
                self.pawn + self.offsets.pawn.m_bIsScoped
            )

            self.update_skeleton()
            self.update_weapon()

            return True

        except:
            return False

    # =========================

    def update_skeleton(self):
        try:
            self.bone_list.clear()

            game_scene = self.mem.read_ulonglong(
                self.pawn + self.offsets.pawn.m_pGameSceneNode
            )

            if not game_scene:
                return False

            bone_array = self.mem.read_ulonglong(
                game_scene + (self.offsets.bone.m_modelState + 0x80)
            )

            if not bone_array:
                return False

            # 30 bones * (vec3 + padding)
            raw = self.mem.pm.read_bytes(bone_array, 30 * 0x20)

            for i in range(30):
                x = struct.unpack("<f", raw[i*0x20:i*0x20+4])[0]
                y = struct.unpack("<f", raw[i*0x20+4:i*0x20+8])[0]
                z = struct.unpack("<f", raw[i*0x20+8:i*0x20+12])[0]

                self.bone_list.append((x, y, z))

            return True

        except:
            return False

    # =========================

    def update_weapon(self):
        try:
            weapon = self.mem.read_ulonglong(
                self.pawn + self.offsets.pawn.m_pClippingWeapon
            )

            if not weapon:
                return False

            weapon = self.mem.read_ulonglong(weapon + 0x10)
            weapon = self.mem.read_ulonglong(weapon + 0x20)

            self.weapon = self.mem.read_string(weapon, 32)

            self.clean_weapon = self.weapon.replace("weapon_", "")

            return True

        except:
            return False
    def get_bounds(self, view_matrix, screen_size, w2s_func):
        origin = w2s_func(self.pos, view_matrix, screen_size)

        if not origin:
            return None

        if not self.bone_list:
            top_pos = (self.pos[0], self.pos[1], self.pos[2] + 65)
        else:
            top_pos = self.bone_list[BoneIndex.head]

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