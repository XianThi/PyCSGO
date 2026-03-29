from ctypes import *
import sys
from Status import Status
from pydbg import *
from Memory import Memory
from configparser import ConfigParser
import time
import win32api
import thread
import win32gui
import math
import winsound
import wmi
import admin
import os.path
import urllib
import json

maxSoundESPDistance = 780  # Default: 780, decent distance tbh
RCSPerfectPercent = 100  # Percent of RCS being perfect, 100% = perfect RCS
triggerBotKey = 0x12  # Default: right-click
triggerBotDelay = 1  # ms

csgoWindow = None
dbg = Memory()
config = ConfigParser(allow_no_value=True)
config.read("settings.ini")


class Entity(Structure):
    _fields_ = [
        ("dwBase", c_long),
        ("hp", c_int),
        ("team", c_int),
        ("is_dormant", c_bool),
        ("is_alive", c_bool),
        ("weapon_ammo", c_int),
    ]


global players
global me
players = list()
for i in range(130):
    players.append(Entity())
me = players[129]


def update(client):
    playerBase = dbg.read_int(client + getOffset(config, "localPlayerOffset"))
    updateEntityData(me, playerBase)
    # playerCount = dbg.read_int(client + getOffset(config, 'glowObjectOffset') + 0x4)
    playerCount = 64
    for cp in range(playerCount):
        entBase = dbg.read_int(
            client + getOffset(config, "entityListOffset") + cp * 0x10
        )
        if entBase == 0x0:
            continue
        updateEntityData(players[cp], entBase)
    return True


def updateEntityData(e, base):
    dormant = dbg.read_int(base + getOffset(config, "dormantOffset"))
    e.dwBase = base
    e.hp = dbg.read_int(base + getOffset(config, "healthOffset"))
    e.team = dbg.read_int(base + getOffset(config, "teamNumOffset"))
    if dormant == 1:
        e.is_dormant = True
    else:
        e.is_dormant = False
    if e.hp > 0 and e.team > 1 and e.team < 4:
        e.is_alive = True
    else:
        e.is_alive = False


def noFlash(clientState):
    global end
    global noFlashEnabled
    global csgoWindow
    while not end:
        time.sleep(0.1)
        if not noFlashEnabled:
            break
        if not win32gui.GetForegroundWindow():
            continue
        if win32gui.GetForegroundWindow() == csgoWindow:
            if (
                dbg.read_int(clientState + getOffset(config, "clientStateInGameOffset"))
                == 6
            ):  # If the client is in game
                localPlayer = me.dwBase
                dbg.write_float(
                    localPlayer + getOffset(config, "flashDurationOffset"), 0.0
                )  # flashduration set 0


# triggerBot: if entity in crosshair is an enemy, fire with a random delay between triggerBotRandomMinimum miliseconds to triggerBotRandomMinimum + 50 miliseconds
def triggerBot(client, clientState):
    global end
    global csgoWindow
    global triggerBotEnabled

    while not end:  # This function is threaded so might as well do this :>
        time.sleep(0.1)
        if not triggerBotEnabled:
            break
        if not win32gui.GetForegroundWindow():
            continue
        if win32gui.GetForegroundWindow() == csgoWindow:
            if (
                dbg.read_int(clientState + getOffset(config, "clientStateInGameOffset"))
                == 6
            ):  # If the client is in game
                localPlayer = me.dwBase
                localPlayerTeam = me.team
                crossHairID = dbg.read_int(
                    localPlayer + getOffset(config, "crossHairIDOffset")
                )  # Get the Entity ID of the entity in crosshairs
                if crossHairID == 0:  # If no entity in crosshair
                    continue
                crossEntitypnt = dbg.read_int(
                    client
                    + getOffset(config, "entityListOffset")
                    + ((crossHairID - 1) * 0x10)
                )  # Find entity based on ID defined by crossHairID
                crossEntity = dbg.read_int(
                    crossEntitypnt
                )  # Get the base of the entity in crosshair

                crossEntityTeam = dbg.read_int(
                    crossEntity + getOffset(config, "teamNumOffset")
                )  # Get team of Entity in Crosshair

                if (
                    crossEntityTeam != 2 and crossEntityTeam != 3
                ):  # If the entity is not a terrorist or counter-terrorist
                    continue

                crossEntityDormant = dbg.read_int(
                    crossEntity + getOffset(config, "dormantOffset")
                )  # Get boolean that states whether entity in crosshair is dormant or not

                # if win32api.GetAsyncKeyState(triggerBotKey) and localPlayerTeam != crossEntityTeam and crossEntityDormant == 0:  # if triggerBotKey is held, the localPlayers team is not equal to entity in crosshair's team, and if the entity in crosshair is not dormant
                if localPlayerTeam != crossEntityTeam and crossEntityDormant == 0:
                    time.sleep(triggerBotDelay / 100)  # Sleep for triggerBotDelay
                    # while crossHairID != 0 and win32api.GetAsyncKeyState(triggerBotKey):  # while there is an entity in my crosshairs and my triggerbot key is held down
                    while crossHairID != 0:
                        crossHairID = dbg.read_int(
                            localPlayer + getOffset(config, "crossHairIDOffset")
                        )  # Re-get the crosshair ID to check if maybe no longer an entity in my crosshair
                        dbg.write_int(
                            client + getOffset(config, "forceAttackOffset"), 5
                        )  # Shoot
                        time.sleep(0.1)
                        dbg.write_int(
                            client + getOffset(config, "forceAttackOffset"), 4
                        )  # Stop shooting


# normalizeAngles: Normalize a pair of angles
def normalizeAngles(viewAngleX, viewAngleY):
    if viewAngleX < -89.0:
        viewAngleX = 89.0
    if viewAngleX > 89.0:
        viewAngleX = 89.0
    if viewAngleY < -180.0:
        viewAngleY += 360.0
    if viewAngleY > 180.0:
        viewAngleY -= 360.0

    return viewAngleX, viewAngleY


def drawGlow(glowPointer, glowCurrentPlayerGlowIndex, r, g, b):
    dbg.write_float(glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x4), r)
    dbg.write_float(glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x8), g)
    dbg.write_float(glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0xC), b)
    dbg.write_float(glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x10), 1.0)
    dbg.write_int(glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x24), 1)
    dbg.write_int(glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x25), 0)


# glowESP: Enables glow around each entity
def glowESP(client):
    glowPointer = dbg.read_int(
        client + getOffset(config, "glowObjectOffset")
    )  # Get the glow Pointer
    # playerCount = dbg.read_int(client + getOffset(config,'glowObjectOffset') + 0x4)
    playerCount = 64
    for i in range(1, playerCount):  # For each player until the max players available
        glowCurrentPlayer = dbg.read_int(
            client + getOffset(config, "entityListOffset") + ((i - 1) * 16)
        )
        if glowCurrentPlayer == 0x0:
            break  # Break out of the for loop, we have reached the current max players
        updateEntityData(players[i], glowCurrentPlayer)
        player = players[i]
        ## burdan ekle
        glowCurrentPlayerGlowIndex = dbg.read_int(
            player.dwBase + getOffset(config, "glowIndexOffset")
        )  # Get the glowIndex of the glowCurrentPlayer entity
        if player.team == 0 or player.is_dormant == True:
            continue
        if me.team == player.team:
            r = 0.0
            g = 0.0
            b = 1.0
        else:
            if player.hp > 75:
                r = 0.0
                g = 1.0
                b = 0.0
            elif player.hp > 50:
                r = 0.5
                g = 0.5
                b = 0.0
            elif player.hp > 25:
                r = 1.0
                g = 0.5
                b = 0.0
            else:
                r = 1.0
                g = 0.0
                b = 0.0
        drawGlow(glowPointer, glowCurrentPlayerGlowIndex, r, g, b)


# BHOP: Automatically start jumping if in game, on the ground, and space is held
def BHOP(client, localPlayer, clientState):
    global end
    global csgoWindow
    global autoBHOPEnabled
    while not end:
        if not autoBHOPEnabled:
            break
        if (
            win32gui.GetForegroundWindow() == csgoWindow
            and dbg.read_int(clientState + getOffset(config, "clientStateInGameOffset"))
            == 6
        ):  # If client is in game
            flags = dbg.read_int(
                localPlayer + getOffset(config, "flagsOffset")
            )  # Get client flags
            if flags & (1 << 0) and win32api.GetAsyncKeyState(
                0x20
            ):  # If localPlayer on the ground and if space is held
                dbg.write_int(
                    client + getOffset(config, "forceJumpOffset"), 6
                )  # Autojump
            flags = dbg.read_int(
                localPlayer + getOffset(config, "flagsOffset")
            )  # Get the latest flags again
        time.sleep(0.01)


def soundESP(client, localPlayer):
    global maxSoundESPDistance
    global end
    global soundESPEnabled
    global csgoWindow

    while not end:
        time.sleep(0.1)
        if not soundESPEnabled:
            break
        if win32gui.GetForegroundWindow() == csgoWindow:
            closestPlayer = 99999.0
            # playerCount = dbg.read_int(client + getOffset(config,'glowObjectOffset') + 0xC)
            playerCount = 64
            for i in range(0, playerCount):
                ent = players[i]
                if ent.dwBase == 0x0:
                    break

                entDormant = dbg.read_int(
                    ent.dwBase + getOffset(config, "dormantOffset")
                )  # Get boolean that states whether glowCurrentPlayer entity is dormant or not
                if entDormant != 0:
                    continue

                myTeamID = dbg.read_int(
                    localPlayer + getOffset(config, "teamNumOffset")
                )  # Get the team ID of the localPlayer
                entityBaseTeamID = dbg.read_int(
                    ent.dwBase + getOffset(config, "teamNumOffset")
                )  # Get the team ID of the ent entity

                if entityBaseTeamID != 2 and entityBaseTeamID != 3:
                    continue

                localPlayerX = dbg.read_float(
                    localPlayer + getOffset(config, "vecOriginOffset")
                )  # Get the X coordinate of the vecOrigin of the localPlayer
                localPlayerY = dbg.read_float(
                    localPlayer + getOffset(config, "vecOriginOffset") + 0x4
                )  # Get the Y coordinate of the vecOrigin of the localPlayer
                localPlayerZ = dbg.read_float(
                    localPlayer + getOffset(config, "vecOriginOffset") + 0x8
                )  # Get the Z coordinate of the vecOrigin of the localPlayer

                entityX = dbg.read_float(
                    ent.dwBase + getOffset(config, "vecOriginOffset")
                )  # Get the X coordinate of the vecOrigin of the ent
                entityY = dbg.read_float(
                    ent.dwBase + getOffset(config, "vecOriginOffset") + 0x4
                )  # Get the Y coordinate of the vecOrigin of the ent
                entityZ = dbg.read_float(
                    ent.dwBase + getOffset(config, "vecOriginOffset") + 0x8
                )  # Get the Z coordinate of the vecOrigin of the ent

                distance = math.sqrt(
                    (
                        pow((entityX - localPlayerX), 2)
                        + pow((entityY - localPlayerY), 2)
                        + pow((entityZ - localPlayerZ), 2)
                    )
                )  # Get the distance between localPlayer and ent
                if (
                    myTeamID != entityBaseTeamID
                    and distance != 0
                    and closestPlayer > distance
                ):  # If not on localPlayer team and team is either 2 or 3 and distance isnt 0 and distance is less than closestPlayer
                    closestPlayer = distance
            if (
                closestPlayer != 1000.0 and closestPlayer < maxSoundESPDistance
            ):  # If closestPlayer isnt default value and closestPlayer is closer than maxSoundESPDistance
                durMath = (
                    1.000 / maxSoundESPDistance
                )  # Generate baseline mathematical thingy - use ur brain
                winsound.Beep(2500, int((durMath * closestPlayer) * 1000))


def RCS(client, clientState):
    oldAimPunchX = 0  # Initializing var (going to be used to store the last aimPunchX)
    oldAimPunchY = 0  # Initializing var (going to be used to store the last aimPunchY)
    global RCSPerfectPercent  # Defines how much RCS we are gonna do

    while True:
        if (
            win32gui.GetForegroundWindow() == csgoWindow
            and dbg.read_int(clientState + getOffset(config, "clientStateInGameOffset"))
            == 6
        ):  # If we are actually playing in game
            localPlayer = dbg.read_int(
                client + getOffset(config, "localPlayerOffset")
            )  # Get the localPlayer
            if (
                dbg.read_int(localPlayer + getOffset(config, "shotsFiredOffset")) > 1
            ):  # If we have fired more than 1 shots
                viewAngleX = dbg.read_float(
                    clientState + getOffset(config, "clientStateViewAnglesOffset")
                )  # Get the X viewAngle
                viewAngleY = dbg.read_float(
                    clientState + getOffset(config, "clientStateViewAnglesOffset") + 0x4
                )  # Get the Y viewAngle

                aimPunchX = dbg.read_float(
                    localPlayer + getOffset(config, "aimPunchOffset")
                )  # Get the X aimPunch
                aimPunchY = dbg.read_float(
                    localPlayer + getOffset(config, "aimPunchOffset") + 0x4
                )  # Get the Y aimPunch

                viewAngleX -= (aimPunchX - oldAimPunchX) * (
                    RCSPerfectPercent * 0.02
                )  # Subtract our AimPunch from our ViewAngle
                viewAngleY -= (aimPunchY - oldAimPunchY) * (
                    RCSPerfectPercent * 0.02
                )  # Subtract our AimPunch from our ViewAngle

                viewAngleX, viewAngleY = normalizeAngles(
                    viewAngleX, viewAngleY
                )  # Normalize our ViewAngles

                dbg.write_float(
                    clientState + getOffset(config, "clientStateViewAnglesOffset"),
                    viewAngleX,
                )
                dbg.write_float(
                    clientState
                    + getOffset(config, "clientStateViewAnglesOffset")
                    + 0x4,
                    viewAngleY,
                )

                oldAimPunchX = aimPunchX
                oldAimPunchY = aimPunchY
            else:
                oldAimPunchX = 0
                oldAimPunchY = 0
        time.sleep(0.1)


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")


def createSettings(config):
    config.add_section("Offsets")
    config.set("Offsets", "crossHairIDOffset", "")
    config.set("Offsets", "forceAttackOffset", "")
    config.set("Offsets", "forceJumpOffset", "")
    config.set("Offsets", "clientStateOffset", "")
    config.set("Offsets", "clientStateViewAnglesOffset", "")
    config.set("Offsets", "aimPunchOffset", "")
    config.set("Offsets", "clientStateInGameOffset", "")
    config.set("Offsets", "flagsOffset", "")
    config.set("Offsets", "vecOriginOffset", "")
    config.set("Offsets", "shotsFiredOffset", "")
    config.set("Offsets", "boneMatrix", "")
    config.set("Offsets", "entityListOffset", "")
    config.set("Offsets", "localPlayerIndexOffset", "")
    config.set("Offsets", "localPlayerOffset", "")
    config.set("Offsets", "glowObjectOffset", "")
    config.set("Offsets", "glowIndexOffset", "")
    config.set("Offsets", "teamNumOffset", "")
    config.set("Offsets", "dormantOffset", "0xE9")
    config.set("Offsets", "healthOffset", "")
    config.set("Offsets", "bSpottedOffset", "")
    config.set("Offsets", "flashDurationOffset")
    config.add_section("Options")
    config.set("Options", "glowESPEnabled", "True")
    config.set("Options", "triggerBotEnabled", "True")
    config.set("Options", "autoBHOPEnabled", "True")
    config.set("Options", "soundESPEnabled", "True")
    config.set("Options", "rcsEnabled", "True")
    with open("settings.ini", "w") as configfile:
        config.write(configfile)


def getSettings(config, caption, key):
    result = config.get(caption, key)
    if result:
        return result
    else:
        return False


def writeSettings(config, caption, key, val):
    config.set(caption, key, val)
    with open("settings.ini", "w") as configfile:
        config.write(configfile)


def getOffset(config, offset):
    result = getSettings(config, "Offsets", offset)
    if result:
        return int(result, 16)
    else:
        print("%s not found. Check settings.ini file.", offset)
        exit(1)


def AllStatus(st):
    global triggerBotEnabled
    global autoBHOPEnabled
    global glowESPEnabled
    global soundESPEnabled
    global rcsEnabled
    global noFlashEnabled

    while True:
        if win32api.GetAsyncKeyState(0x74):
            glowESPEnabled = not glowESPEnabled
            changeStat(st)
            time.sleep(1)
        if win32api.GetAsyncKeyState(0x75):
            rcsEnabled = not rcsEnabled
            changeStat(st)
            time.sleep(1)
        if win32api.GetAsyncKeyState(0x76):
            soundESPEnabled = not soundESPEnabled
            changeStat(st)
            time.sleep(1)
        if win32api.GetAsyncKeyState(0x77):
            triggerBotEnabled = not triggerBotEnabled
            changeStat(st)
            time.sleep(1)
        if win32api.GetAsyncKeyState(0x78):
            autoBHOPEnabled = not autoBHOPEnabled
            changeStat(st)
            time.sleep(1)
        if win32api.GetAsyncKeyState(0x79):
            noFlashEnabled = not noFlashEnabled
            changeStat(st)
            time.sleep(1)


def updateConfigfromGithub(config):
    import requests

    url = "https://raw.githubusercontent.com/frk1/hazedumper/master/csgo.json"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        writeSettings(
            config,
            "Offsets",
            "entitylistoffset",
            hex(data["signatures"]["dwEntityList"]),
        )
        writeSettings(
            config,
            "Offsets",
            "localplayerindexoffset",
            hex(data["signatures"]["dwClientState_GetLocalPlayer"]),
        )
        writeSettings(
            config,
            "Offsets",
            "localplayeroffset",
            hex(data["signatures"]["dwLocalPlayer"]),
        )
        writeSettings(
            config,
            "Offsets",
            "glowobjectoffset",
            hex(data["signatures"]["dwGlowObjectManager"]),
        )
        writeSettings(
            config,
            "Offsets",
            "forceattackoffset",
            hex(data["signatures"]["dwForceAttack"]),
        )
        writeSettings(
            config, "Offsets", "forcejumpoffset", hex(data["signatures"]["dwForceJump"])
        )
        writeSettings(
            config,
            "Offsets",
            "clientstateoffset",
            hex(data["signatures"]["dwClientState"]),
        )
        writeSettings(
            config,
            "Offsets",
            "clientstateviewanglesoffset",
            hex(data["signatures"]["dwClientState_ViewAngles"]),
        )
        writeSettings(
            config,
            "Offsets",
            "clientstateingameoffset",
            hex(data["signatures"]["dwClientState_State"]),
        )
        writeSettings(
            config,
            "Offsets",
            "crossHairIDOffset",
            hex(data["netvars"]["m_iCrosshairId"]),
        )
        writeSettings(
            config, "Offsets", "aimpunchoffset", hex(data["netvars"]["m_aimPunchAngle"])
        )
        writeSettings(
            config, "Offsets", "flagsoffset", hex(data["netvars"]["m_fFlags"])
        )
        writeSettings(
            config, "Offsets", "vecoriginoffset", hex(data["netvars"]["m_vecOrigin"])
        )
        writeSettings(
            config, "Offsets", "shotsfiredoffset", hex(data["netvars"]["m_iShotsFired"])
        )
        writeSettings(
            config, "Offsets", "bonematrix", hex(data["netvars"]["m_dwBoneMatrix"])
        )
        writeSettings(
            config, "Offsets", "glowindexoffset", hex(data["netvars"]["m_iGlowIndex"])
        )
        writeSettings(
            config, "Offsets", "teamnumoffset", hex(data["netvars"]["m_iTeamNum"])
        )
        writeSettings(
            config, "Offsets", "healthoffset", hex(data["netvars"]["m_iHealth"])
        )
        writeSettings(
            config, "Offsets", "bspottedoffset", hex(data["netvars"]["m_bSpotted"])
        )
        writeSettings(
            config,
            "Offsets",
            "flashdurationoffset",
            hex(data["netvars"]["m_flFlashDuration"]),
        )
    except Exception as e:
        Status().info(f"Failed to update offsets from GitHub: {e}")


def changeStat(st):
    global triggerBotEnabled
    global autoBHOPEnabled
    global glowESPEnabled
    global soundESPEnabled
    global rcsEnabled
    print("\n" * 100)
    if glowESPEnabled == True:
        st.info("Glow ESP : " + "ON" + " (F5)")
    else:
        st.info("Glow ESP : " + "OFF" + " (F5)")
    if rcsEnabled == True:
        st.info("RCS : " + "ON" + " (F6)")
    else:
        st.info("RCS : " + "OFF" + " (F6)")
    if soundESPEnabled == True:
        st.info("Sound ESP : " + "ON" + " (F7)")
    else:
        st.info("Sound ESP : " + "OFF" + " (F7)")
    if triggerBotEnabled == True:
        st.info("Trigger Bot : " + "ON" + " (F8)")
    else:
        st.info("Trigger Bot : " + "OFF" + " (F8)")
    if autoBHOPEnabled == True:
        st.info("BunnyHop : " + "ON" + " (F9)")
    else:
        st.info("BunnyHop : " + "OFF" + " (F9)")
    if noFlashEnabled == True:
        st.info("No Flash : " + "ON" + " (F10)")
    else:
        st.info("No Flash : " + "OFF" + " (F10)")


# main: Main function, starts all the threads, does glow esp, waits for end key, etc :)
def main():
    global triggerBotEnabled
    global autoBHOPEnabled
    global glowESPEnabled
    global soundESPEnabled
    global rcsEnabled
    global noFlashEnabled
    global end
    global csgoWindow

    if not os.path.isfile("settings.ini"):
        file = open("settings.ini", "w")
        file.close()
        createSettings(config)
        glow = query_yes_no("Enable Glow ESP?")
        writeSettings(config, "Options", "glowESPEnabled", glow)
        trigger = query_yes_no("Enable Trigger?")
        writeSettings(config, "Options", "triggerBotEnabled", trigger)
        bunny = query_yes_no("Enable Bunny HOP?")
        writeSettings(config, "Options", "autoBHOPEnabled", bunny)
        sound = query_yes_no("Enable Sound ESP?")
        writeSettings(config, "Options", "soundESPEnabled", sound)
        rcs = query_yes_no("Enable RCS?")
        writeSettings(config, "Options", "rcsEnabled", rcs)
        flash = query_yes_no("Enable NoFlash?")
        writeSettings(config, "Options", "noFlashEnabled", flash)

    st = Status()
    st.debug("Updating offsets...")
    updateConfigfromGithub(config)
    st.debug("Offsets updated...")
    if getSettings(config, "Options", "triggerBotEnabled") == "True":
        triggerBotEnabled = True
    else:
        triggerBotEnabled = False
    if getSettings(config, "Options", "autoBHOPEnabled") == "True":
        autoBHOPEnabled = True
    else:
        autoBHOPEnabled = False
    if getSettings(config, "Options", "glowESPEnabled") == "True":
        glowESPEnabled = True
    else:
        glowESPEnabled = False
    if getSettings(config, "Options", "soundESPEnabled") == "True":
        soundESPEnabled = True
    else:
        soundESPEnabled = False
    if getSettings(config, "Options", "rcsEnabled") == "True":
        rcsEnabled = True
    else:
        rcsEnabled = False
    if getSettings(config, "Options", "noFlashEnabled") == "True":
        noFlashEnabled = True
    else:
        noFlashEnabled = False
    st.debug("waiting for csgo.exe...")
    while not dbg.attach("csgo.exe"):
        pass
    st.debug("csgo.exe found. getting modules...")
    client = dbg.get_module_base_pymem("client.dll")  # Get client.dll module
    st.debug("client.dll. : " + str(client))
    engine = dbg.get_module_base_pymem("engine.dll")  # Get engine.dll module
    st.debug("engine.dll. : " + str(engine))
    clientState = dbg.read_int(
        engine + getOffset(config, "clientStateOffset")
    )  # Get clientState pointer
    st.debug("ClientState : " + str(clientState))
    st.debug("waiting for LocalPlayer...")
    localPlayer = 0
    while localPlayer == 0:
        localPlayer = dbg.read_int(
            client + getOffset(config, "localPlayerOffset")
        )  # Get localPlayer pointer
    st.debug("LocalPlayer: " + str(localPlayer))
    csgoWindow = win32gui.FindWindow(None, "Counter-Strike: Global Offensive")
    if csgoWindow is None:
        st.debug("csgo windows not found.")
        exit(1)
    st.debug("hack started. END to exit.")
    try:
        thread.start_new_thread(update, (client))
    except:
        st.debug("Updater has an error.")
    if noFlashEnabled:
        try:
            thread.start_new_thread(noFlash, (clientState,))
        except:
            st.debug("Could not start noflash thread :(")
    if triggerBotEnabled:
        try:
            thread.start_new_thread(
                triggerBot,
                (
                    client,
                    clientState,
                ),
            )  # Start triggerBot function threaded
        except:
            st.debug("Could not start triggerbot thread :(")

    if autoBHOPEnabled:
        try:
            thread.start_new_thread(
                BHOP,
                (
                    client,
                    localPlayer,
                    clientState,
                ),
            )  # Start BHOP function threaded
        except:
            st.debug("Could not start bhop thread :(")

    if soundESPEnabled:
        try:
            thread.start_new_thread(
                soundESP,
                (
                    client,
                    localPlayer,
                ),
            )  # Start soundESP function threaded
        except:
            st.debug("Could not start soundESP thread :(")

    if rcsEnabled:
        try:
            thread.start_new_thread(
                RCS,
                (
                    client,
                    clientState,
                ),
            )  # Start RCS function threaded
        except:
            st.debug("Could not start rcs thread :(")
    try:
        thread.start_new_thread(AllStatus, (st,))
    except:
        st.debug("status not working..")
    changeStat(st)

    while not win32api.GetAsyncKeyState(0x23):  # While END key isn't touched
        inGame = dbg.read_int(
            clientState + getOffset(config, "clientStateInGameOffset")
        )
        if inGame == 6:  # If client is in game
            if glowESPEnabled and win32gui.GetForegroundWindow() == csgoWindow:
                glowESP(client)  # Call glowESP function non-threaded
            time.sleep(0.01)
    end = True  # Tells the threads to stop looping, prevents future problems
    time.sleep(0.01)


if __name__ == "__main__":
    #    if not admin.isUserAdmin():
    #        admin.runAsAdmin()
    #    else:
    #        main()
    main()
