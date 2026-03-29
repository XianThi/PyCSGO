import struct

import Offsets


class Game:
    def __init__(self, mem, offsets: Offsets.OffsetsConfig):
        self.mem = mem
        self.offsets = offsets

        self.view_matrix = None
        self.entity_list = 0
        self.list_entry = 0

    # =========================

    def update(self):
        if not self.mem.pm:
            return False
        if not self.update_matrix():
            print("Failed to update view matrix")
            return False

        return True

    # =========================

    def update_matrix(self):
        try:
            addr = self.mem.client + self.offsets.viewMatrix

            # view matrix = 4x4 float (16 float)
            raw = self.mem.pm.read_bytes(addr, 64)

            self.view_matrix = struct.unpack("16f", raw)

            return True
        except:
            return False

    # =========================

    def update_entity_list(self):
        try:
            self.entity_list = self.mem.read_ulonglong(
                self.mem.client + self.offsets.entityList
            )

            self.list_entry = self.mem.read_ulonglong(self.entity_list + 0x10)

            return True
        except:
            return False
