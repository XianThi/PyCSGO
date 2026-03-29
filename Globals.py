import Offsets


class Globals:
    def __init__(self, mem, offsets: Offsets.OffsetsConfig):
        self.mem = mem
        self.offsets = offsets

        self.max_clients = 0
        self.current_time = 0
        self.map_name = ""
        self.in_match = False

        self.localplayer = 0
        self.address = 0

    # =========================

    def update(self):
        if not self.mem.pm:
            return False

        try:
            # globalVars pointer
            self.address = self.mem.read_ulonglong(
                self.mem.client + self.offsets.globalVars
            )

            if not self.address:
                return False

            # current time
            self.current_time = self.mem.read_float(
                self.address + self.offsets.global_vars.currentTime
            )

            # max clients
            self.max_clients = self.mem.read_int(
                self.address + self.offsets.global_vars.maxClients
            )

            # match kontrolü
            self.in_match = self.max_clients > 1

            # map name pointer
            map_name_addr = self.mem.read_ulonglong(
                self.address + self.offsets.global_vars.currentMapName
            )

            if not map_name_addr:
                return False

            # string oku
            self.map_name = self.mem.read_string(map_name_addr, 32)

            return True

        except:
            return False
