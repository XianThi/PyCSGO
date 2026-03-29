import struct
import psutil
import pymem


class Memory:
    def __init__(self):
        self.pm = None
        self.pid = None
        self.client = 0
        self.engine = 0

    def get_module_base_pymem(self, name):
        try:
            module = pymem.process.module_from_name(self.pm.process_handle, name)
            return module.lpBaseOfDll
        except:
            return 0

    def attach(self, process_name="cs2.exe"):
        for proc in psutil.process_iter(["pid", "name"]):
            if proc.info["name"] == process_name:
                self.pid = proc.info["pid"]
                self.pm = pymem.Pymem(self.pid)
                return True
        return False

    # =========================
    # MODULES

    def update_modules(self):
        self.client = self.get_module_base_pymem("client.dll")
        self.engine = self.get_module_base_pymem("engine2.dll")
        return self.client != 0

    def read_int(self, addr):
        return struct.unpack("<i", self.pm.read_bytes(addr, 4))[0]

    def read_ulonglong(self, addr):
        return struct.unpack("<Q", self.pm.read_bytes(addr, 8))[0]

    def read_float(self, addr):
        return struct.unpack("<f", self.pm.read_bytes(addr, 4))[0]

    def read_vec3(self, addr):
        return (
            self.read_float(addr),
            self.read_float(addr + 4),
            self.read_float(addr + 8),
        )

    def read_bool(self, addr):
        return struct.unpack("<?", self.pm.read_bytes(addr, 1))[0]

    def read_string(self, addr, size=32):
        raw = self.pm.read_bytes(addr, size)
        return raw.split(b"\x00", 1)[0].decode(errors="ignore")

    # =========================
    # WRITE

    def write_int(self, addr, val):
        self.pm.write_bytes(addr, struct.pack("<i", val), 4)

    def write_float(self, addr, val):
        self.pm.write_bytes(addr, struct.pack("<f", val), 4)

    def write_ulonglong(self, addr, val):
        self.pm.write_bytes(addr, struct.pack("<Q", val), 8)
