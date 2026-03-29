from Cache import Cache
from Memory import Memory
from Config import GameConfig
from Overlay import AntiDetectionOverlay
from Status import Status
import threading

# SABITLER
WIDTH, HEIGHT = 1920, 1080
status = Status()
config = GameConfig()


def main():
    status.debug("CS2 External Cheat")
    status.debug("Updating Offsets...")
    config.UpdateFromGithub(
        "https://raw.githubusercontent.com/a2x/cs2-dumper/refs/heads/main/output/offsets.json"
    )
    mem = Memory()
    status.debug("Attaching to process...")
    if not mem.attach("cs2.exe"):
        status.info("cs2.exe not found")
        return
    status.debug("cs2.exe found. getting modules...")
    if not mem.update_modules():
        status.info("Modules not found")
    status.info("client.dll: " + hex(mem.client))
    status.info("engine2.dll: " + hex(mem.engine))
    cfg = config.to_object()
    cache = Cache(mem, cfg.offsets, cfg.options)
    t = threading.Thread(target=memory_loop, args=(cache,), daemon=True)
    t.start()

    # 🎨 RENDER
    overlay = AntiDetectionOverlay(cache=cache, WIDTH=WIDTH, HEIGHT=HEIGHT)
    overlay.run()


def memory_loop(cache):
    while True:
        cache.refresh()


if __name__ == "__main__":
    main()
