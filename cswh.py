from ctypes import *
from pydbg import *
from memorpy import *
from ConfigParser import ConfigParser
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

foundProcess = False
end = False
csgoWindow = None
processID = 0
proc = None

config = ConfigParser(allow_no_value=True)
config.read('settings.ini')


class Entity(Structure):
    _fields_ = [
        ("dwBase", c_long),
        ("hp",c_int),
        ("team",c_int),
        ("is_dormant",c_bool),
        ("is_alive",c_bool),
        ("weapon_ammo",c_int)
    ]

class Status:
    def _displayMessage(self, message, level = None):
        # This can be modified easily
        if level is not None:
            print "[%s] %s" % (level, message)
        else:
            print "[default] %s" % (message)

    def debug(self, message):
        self._displayMessage(message, level = "###")
    def info(self, message):
        self._displayMessage(message, level = "-->")

global players
global me
players = list()
for i in range(130):
    players.append(Entity())
me = players[129]

def update(process,client):
    playerBase = read(process,(client+getOffset(config,'localPlayerOffset')))
    updateEntityData(process,me,playerBase)
    #playerCount = read(process, (client + getOffset(config, 'glowObjectOffset') + 0x4))
    playerCount = 64
    for cp in range(playerCount):
        entBase = read(process,(client+getOffset(config,'entityListOffset')+cp*0x10))
        if (entBase == 0x0):
            continue
        updateEntityData(process,players[cp],entBase)
    return True

def updateEntityData(process,e,base):
    dormant = read(process,(base+getOffset(config,'dormantOffset')))
    e.dwBase = base
    e.hp = read(process,(base+getOffset(config,'healthOffset')))
    e.team = read(process,(base+getOffset(config,'teamNumOffset')))
    if(dormant==1):
        e.is_dormant = True
    else:
        e.is_dormant = False
    if e.hp>0 and e.team>1 and e.team<4:
        e.is_alive = True
    else:
        e.is_alive = False


def noFlash(process,client,clientState):
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
            if read(process, (clientState + getOffset(config,'clientStateInGameOffset'))) == 6:  # If the client is in game
                localPlayer = me.dwBase
                write(process,(localPlayer+getOffset(config,'flashDurationOffset')),0.0,'float') #flashduration set 0


# triggerBot: if entity in crosshair is an enemy, fire with a random delay between triggerBotRandomMinimum miliseconds to triggerBotRandomMinimum + 50 miliseconds
def triggerBot(process, client, clientState):
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
            if read(process, (clientState + getOffset(config,'clientStateInGameOffset'))) == 6:  # If the client is in game
                localPlayer = me.dwBase
                localPlayerTeam = me.team
                crossHairID = read(process, (localPlayer + getOffset(config,'crossHairIDOffset')))  # Get the Entity ID of the entity in crosshairs
                if crossHairID == 0:  # If no entity in crosshair
                    continue
                crossEntitypnt = (client + getOffset(config,'entityListOffset') + ((crossHairID - 1) * 0x10))
                crossEntity = read(process, crossEntitypnt)  # Find entity based on ID defined by crossHairID

                crossEntityTeam = read(process, (crossEntity + getOffset(config,'teamNumOffset')))  # Get team of Entity in Crosshair

                if crossEntityTeam != 2 and crossEntityTeam != 3:  # If the entity is not a terrorist or counter-terrorist
                    continue

                crossEntityDormant = read(process, (
                    crossEntity + getOffset(config,'dormantOffset')))  # Get boolean that states whether entity in crosshair is dormant or not

                #if win32api.GetAsyncKeyState(triggerBotKey) and localPlayerTeam != crossEntityTeam and crossEntityDormant == 0:  # if triggerBotKey is held, the localPlayers team is not equal to entity in crosshair's team, and if the entity in crosshair is not dormant
                if  localPlayerTeam != crossEntityTeam and crossEntityDormant == 0:
                    time.sleep(triggerBotDelay/100)  # Sleep for triggerBotDelay
                    #while crossHairID != 0 and win32api.GetAsyncKeyState(triggerBotKey):  # while there is an entity in my crosshairs and my triggerbot key is held down
                    while crossHairID != 0:
                        crossHairID = read(process, (
                            localPlayer + getOffset(config,'crossHairIDOffset')))  # Re-get the crosshair ID to check if maybe no longer an entity in my crosshair
                        write(process, (client + getOffset(config,'forceAttackOffset')), 5, 'int')  # Shoot
                        time.sleep(0.1)
                        write(process, (client + getOffset(config,'forceAttackOffset')), 4, 'int')# Stop shooting


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

def drawGlow(process,glowPointer,glowCurrentPlayerGlowIndex,r,g,b):
    write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x4)), r, 'float')
    write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x8)), g, 'float')
    write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0xC)), b, 'float')
    write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x10)), 1.0, 'float')
    write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x24)), 1, 'int')
    write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x25)), 0, 'int')

# glowESP: Enables glow around each entity
def glowESP(process, client):
    glowPointer = read(process, (client + getOffset(config,'glowObjectOffset')))  # Get the glow Pointer
    #playerCount = read(process, (client + getOffset(config,'glowObjectOffset') + 0x4))
    playerCount = 64
    for i in range(1, playerCount):  # For each player until the max players available
        glowCurrentPlayer = read(process,(client+getOffset(config,'entityListOffset')+((i-1)*16)))
        if glowCurrentPlayer == 0x0:
            break  # Break out of the for loop, we have reached the current max players
        updateEntityData(process, players[i], glowCurrentPlayer)
        player = players[i]
## burdan ekle
        glowCurrentPlayerGlowIndex = read(process, (player.dwBase + getOffset(config,'glowIndexOffset')))  # Get the glowIndex of the glowCurrentPlayer entity
        if player.team == 0 or player.is_dormant == True:
			continue
        if (me.team == player.team):
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
        drawGlow(process, glowPointer, glowCurrentPlayerGlowIndex, r, g, b)



# BHOP: Automatically start jumping if in game, on the ground, and space is held
def BHOP(process, client, localPlayer, clientState):
    global end
    global csgoWindow
    global autoBHOPEnabled
    while not end:
        if not autoBHOPEnabled:
            break
        if win32gui.GetForegroundWindow() == csgoWindow and read(process, (
                    clientState + getOffset(config,'clientStateInGameOffset'))) == 6:  # If client is in game
            flags = read(process, (localPlayer + getOffset(config,'flagsOffset')))  # Get client flags
            if flags & (1 << 0) and win32api.GetAsyncKeyState(
                    0x20):  # If localPlayer on the ground and if space is held
                write(process, (client + getOffset(config,'forceJumpOffset')), 6, 'int')  # Autojump
            flags = read(process, (localPlayer + getOffset(config,'flagsOffset')))  # Get the latest flags again
        time.sleep(0.01)


def soundESP(process, client, localPlayer):
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
            #playerCount = read(process, (client + getOffset(config,'glowObjectOffset') + 0xC))
            playerCount = 64
            for i in range(0, playerCount):
                ent = players[i]
                if ent.dwBase is 0x0:
                    break

                entDormant = read(process, (
                    ent.dwBase + getOffset(config,'dormantOffset')))  # Get boolean that states whether glowCurrentPlayer entity is dormant or not

                if entDormant != 0:
                    continue

                myTeamID = read(process, (localPlayer + getOffset(config,'teamNumOffset')))  # Get the team ID of the localPlayer
                entityBaseTeamID = read(process, (ent.dwBase + getOffset(config,'teamNumOffset')))  # Get the team ID of the ent entity

                if entityBaseTeamID != 2 and entityBaseTeamID != 3:
                    continue

                localPlayerX = read(process, (localPlayer + getOffset(config,'vecOriginOffset')),
                                    "float")  # Get the X coordinate of the vecOrigin of the localPlayer
                localPlayerY = read(process, (localPlayer + getOffset(config,'vecOriginOffset') + 0x4),
                                    'float')  # Get the Y coordinate of the vecOrigin of the localPlayer
                localPlayerZ = read(process, (localPlayer + getOffset(config,'vecOriginOffset') + 0x8),
                                    'float')  # Get the Z coordinate of the vecOrigin of the localPlayer

                entityX = read(process, (ent.dwBase + getOffset(config,'vecOriginOffset')),
                               'float')  # Get the X coordinate of the vecOrigin of the ent
                entityY = read(process, (ent.dwBase + getOffset(config,'vecOriginOffset') + 0x4),
                               'float')  # Get the Y coordinate of the vecOrigin of the ent
                entityZ = read(process, (ent.dwBase + getOffset(config,'vecOriginOffset') + 0x8),
                               'float')  # Get the Z coordinate of the vecOrigin of the ent

                distance = math.sqrt((pow((entityX - localPlayerX), 2) + pow((entityY - localPlayerY), 2) + pow(
                    (entityZ - localPlayerZ), 2)))  # Get the distance between localPlayer and ent

                if myTeamID != entityBaseTeamID and distance != 0 and closestPlayer > distance:  # If not on localPlayer team and team is either 2 or 3 and distance isnt 0 and distance is less than closestPlayer
                    closestPlayer = distance
            if closestPlayer != 1000.0 and closestPlayer < maxSoundESPDistance:  # If closestPlayer isnt default value and closestPlayer is closer than maxSoundESPDistance
                durMath = 1.000 / maxSoundESPDistance  # Generate baseline mathematical thingy - use ur brain
                winsound.Beep(2500, int((durMath * closestPlayer) * 1000))



def RCS(process, client, clientState):
    oldAimPunchX = 0  # Initializing var (going to be used to store the last aimPunchX)
    oldAimPunchY = 0  # Initializing var (going to be used to store the last aimPunchY)
    global RCSPerfectPercent  # Defines how much RCS we are gonna do

    while True:
        if win32gui.GetForegroundWindow() == csgoWindow and read(process, (
                    clientState + getOffset(config,'clientStateInGameOffset'))) == 6:  # If we are actually playing in game
            localPlayer = read(process, (client + getOffset(config,'localPlayerOffset')))  # Get the localPlayer
            if read(process, (localPlayer + getOffset(config,'shotsFiredOffset'))) > 1:  # If we have fired more than 1 shots
                viewAngleX = read(process, (clientState + getOffset(config,'clientStateViewAnglesOffset')), 'float')  # Get the X viewAngle
                viewAngleY = read(process, (clientState + getOffset(config,'clientStateViewAnglesOffset') + 0x4),
                                  'float')  # Get the Y viewAngle

                aimPunchX = read(process, (localPlayer + getOffset(config,'aimPunchOffset')), 'float')  # Get the X aimPunch
                aimPunchY = read(process, (localPlayer + getOffset(config,'aimPunchOffset') + 0x4), 'float')  # Get the Y aimPunch

                viewAngleX -= (aimPunchX - oldAimPunchX) * (
                    RCSPerfectPercent * 0.02)  # Subtract our AimPunch from our ViewAngle
                viewAngleY -= (aimPunchY - oldAimPunchY) * (
                    RCSPerfectPercent * 0.02)  # Subtract our AimPunch from our ViewAngle

                viewAngleX, viewAngleY = normalizeAngles(viewAngleX, viewAngleY)  # Normalize our ViewAngles

                write(process, (clientState + getOffset(config,'clientStateViewAnglesOffset')), viewAngleX, 'float')
                write(process, (clientState + getOffset(config,'clientStateViewAnglesOffset') + 0x4), viewAngleY, 'float')

                oldAimPunchX = aimPunchX
                oldAimPunchY = aimPunchY
            else:
                oldAimPunchX = 0
                oldAimPunchY = 0
        time.sleep(0.1)


def getDLL(name, PID):
    hModule = CreateToolhelp32Snapshot(TH32CS_CLASS.SNAPMODULE, PID)
    if hModule is not None:
        module_entry = MODULEENTRY32()
        module_entry.dwSize = sizeof(module_entry)
        success = Module32First(hModule, byref(module_entry))
        while success:
            if module_entry.th32ProcessID == PID:
                if module_entry.szModule == name:
                    return module_entry.modBaseAddr
            success = Module32Next(hModule, byref(module_entry))

        CloseHandle(hModule)
    return 0


def write(dbg, offset, val, type='int'):
    if (isinstance(val, int)):
        return dbg.write(offset,struct.pack('i',val),4)
    if (isinstance(val, long)):
        return dbg.write(offset, struct.pack('l',val), 4)
    if (isinstance(val, float)):
        return dbg.write(offset, struct.pack('f',val), 4)


def read(dbg, offset, type="int"):
    if type == "int":
        res = struct.unpack("<i", (dbg.read(offset, 4)))
        return res[0]
    if type == "float":
        res = struct.unpack("<f", (pydbg.read(dbg, offset, 4)))
        return res[0]



def query_yes_no(question, default="yes"):
        """Ask a yes/no question via raw_input() and return their answer.

        "question" is a string that is presented to the user.
        "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

        The "answer" return value is True for "yes" or False for "no".
        """
        valid = {"yes": True, "y": True, "ye": True,
                 "no": False, "n": False}
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
            choice = raw_input().lower()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' "
                                 "(or 'y' or 'n').\n")

def createSettings(config):
    config.add_section('Offsets')
    config.set('Offsets','crossHairIDOffset','')
    config.set('Offsets','forceAttackOffset','')
    config.set('Offsets','forceJumpOffset','')
    config.set('Offsets','clientStateOffset','')
    config.set('Offsets','clientStateViewAnglesOffset','')
    config.set('Offsets','aimPunchOffset','')
    config.set('Offsets','clientStateInGameOffset','')
    config.set('Offsets','flagsOffset','')
    config.set('Offsets','vecOriginOffset','')
    config.set('Offsets','shotsFiredOffset','')
    config.set('Offsets','boneMatrix','')
    config.set('Offsets','entityListOffset','')
    config.set('Offsets','localPlayerIndexOffset','')
    config.set('Offsets','localPlayerOffset','')
    config.set('Offsets','glowObjectOffset','')
    config.set('Offsets','glowIndexOffset','')
    config.set('Offsets','teamNumOffset','')
    config.set('Offsets','dormantOffset','0xE9')
    config.set('Offsets','healthOffset','')
    config.set('Offsets','bSpottedOffset','')
    config.set('Offsets','flashDurationOffset')
    config.add_section('Options')
    config.set('Options','glowESPEnabled','True')
    config.set('Options','triggerBotEnabled','True')
    config.set('Options','autoBHOPEnabled','True')
    config.set('Options','soundESPEnabled','True')
    config.set('Options','rcsEnabled','True')
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

def getSettings(config,caption,key):
    result = config.get(caption,key)
    if (result):
        return result
    else:
        return False
def writeSettings(config,caption,key,val):
    config.set(caption,key,val)
    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

def getOffset(config,offset):
    result = getSettings(config,'Offsets',offset)
    if (result):
        return int(result,16)
    else:
        print offset + ' not found. Check settings.ini file.'
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
    url = "https://raw.githubusercontent.com/frk1/hazedumper/master/csgo.json"
    response = urllib.urlopen(url)
    data = json.loads(response.read())
    writeSettings(config, 'Offsets', 'entitylistoffset', hex(data['signatures']['dwEntityList']))
    writeSettings(config, 'Offsets', 'localplayerindexoffset', hex(data['signatures']['dwClientState_GetLocalPlayer']))
    writeSettings(config, 'Offsets', 'localplayeroffset', hex(data['signatures']['dwLocalPlayer']))
    writeSettings(config, 'Offsets', 'glowobjectoffset', hex(data['signatures']['dwGlowObjectManager']))
    writeSettings(config, 'Offsets', 'forceattackoffset', hex(data['signatures']['dwForceAttack']))
    writeSettings(config, 'Offsets', 'forcejumpoffset', hex(data['signatures']['dwForceJump']))
    writeSettings(config, 'Offsets', 'clientstateoffset', hex(data['signatures']['dwClientState']))
    writeSettings(config, 'Offsets', 'clientstateviewanglesoffset', hex(data['signatures']['dwClientState_ViewAngles']))
    writeSettings(config, 'Offsets', 'clientstateingameoffset', hex(data['signatures']['dwClientState_State']))
    writeSettings(config, 'Offsets', 'crossHairIDOffset', hex(data['netvars']['m_iCrosshairId']))
    writeSettings(config, 'Offsets', 'aimpunchoffset', hex(data['netvars']['m_aimPunchAngle']))
    writeSettings(config, 'Offsets', 'flagsoffset', hex(data['netvars']['m_fFlags']))
    writeSettings(config, 'Offsets', 'vecoriginoffset', hex(data['netvars']['m_vecOrigin']))
    writeSettings(config, 'Offsets', 'shotsfiredoffset', hex(data['netvars']['m_iShotsFired']))
    writeSettings(config, 'Offsets', 'bonematrix', hex(data['netvars']['m_dwBoneMatrix']))
    writeSettings(config, 'Offsets', 'glowindexoffset', hex(data['netvars']['m_iGlowIndex']))
    writeSettings(config, 'Offsets', 'teamnumoffset', hex(data['netvars']['m_iTeamNum']))
    writeSettings(config, 'Offsets', 'healthoffset', hex(data['netvars']['m_iHealth']))
    writeSettings(config, 'Offsets', 'bspottedoffset', hex(data['netvars']['m_bSpotted']))
    writeSettings(config, 'Offsets', 'flashdurationoffset', hex(data['netvars']['m_flFlashDuration']))

def changeStat(st):
    global triggerBotEnabled
    global autoBHOPEnabled
    global glowESPEnabled
    global soundESPEnabled
    global rcsEnabled
    clear = "\n" * 100
    print clear
    if glowESPEnabled == True:
        st.info('Glow ESP : ' + "ON" + " (F5)")
    else:
        st.info('Glow ESP : ' + "OFF" + " (F5)")
    if rcsEnabled == True:
        st.info('RCS : '+ 'ON' + ' (F6)')
    else:
        st.info('RCS : ' + 'OFF' + ' (F6)')
    if soundESPEnabled == True:
        st.info('Sound ESP : '+ 'ON' + ' (F7)')
    else:
        st.info('Sound ESP : ' + 'OFF' + ' (F7)')
    if triggerBotEnabled == True:
        st.info('Trigger Bot : ' + 'ON' + ' (F8)')
    else:
        st.info('Trigger Bot : ' + 'OFF' + ' (F8)')
    if autoBHOPEnabled == True:
        st.info('BunnyHop : ' + 'ON' + ' (F9)')
    else:
        st.info('BunnyHop : ' + 'OFF' + ' (F9)')
    if noFlashEnabled == True:
        st.info('No Flash : ' + 'ON' + ' (F10)')
    else:
        st.info('No Flash : ' + 'OFF' + ' (F10)')

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
    global bulundu
    bulundu = False
    processHandle = None
    if not os.path.isfile('settings.ini'):
        file = open('settings.ini','w')
        file.close()
        createSettings(config)
        glow = query_yes_no('Enable Glow ESP?')
        writeSettings(config,'Options','glowESPEnabled',glow)
        trigger = query_yes_no('Enable Trigger?')
        writeSettings(config,'Options','triggerBotEnabled',trigger)
        bunny = query_yes_no('Enable Bunny HOP?')
        writeSettings(config,'Options','autoBHOPEnabled',bunny)
        sound = query_yes_no('Enable Sound ESP?')
        writeSettings(config,'Options','soundESPEnabled',sound)
        rcs = query_yes_no('Enable RCS?')
        writeSettings(config,'Options','rcsEnabled',rcs)
        flash = query_yes_no('Enable NoFlash?')
        writeSettings(config,'Options','noFlashEnabled',flash)

    st = Status()
    st.debug("Updating offsets...")
    updateConfigfromGithub(config)
    st.debug("Offsets updated...")
    st.debug("waiting for csgo.exe...")
    while True:
        c = wmi.WMI()
        for pr in c.Win32_Process():
            if pr.Name == "csgo.exe":
                processID = int(pr.ProcessId)
                dbg = pydbg()
                dbg.open_process(processID)
                processHandle = dbg
                bulundu = True
                break
        if bulundu == True:
            break
    if getSettings(config,'Options','triggerBotEnabled') == 'True':
        triggerBotEnabled = True
    else:
        triggerBotEnabled = False
    if getSettings(config,'Options','autoBHOPEnabled') == 'True':
        autoBHOPEnabled = True
    else:
        autoBHOPEnabled = False
    if getSettings(config,'Options','glowESPEnabled') == 'True':
        glowESPEnabled = True
    else:
        glowESPEnabled = False
    if getSettings(config,'Options','soundESPEnabled') == 'True':
        soundESPEnabled = True
    else:
        soundESPEnabled = False
    if getSettings(config,'Options','rcsEnabled') == 'True':
        rcsEnabled = True
    else:
        rcsEnabled = False
    if getSettings(config,'Options','noFlashEnabled') == 'True':
        noFlashEnabled = True
    else:
        noFlashEnabled = False
    st.debug("csgo.exe found. getting modules...")
    client = getDLL("client.dll", processID)  # Get client.dll module
    st.debug("client.dll. : "+ str(client))
    engine = getDLL("engine.dll", processID)  # Get engine.dll module
    st.debug("engine.dll. : "+ str(engine))
    clientState = read(processHandle, (engine + getOffset(config,'clientStateOffset')))  # Get clientState pointer
    st.debug("ClientState : "+ str(clientState))
    st.debug("waiting for LocalPlayer...")
    localPlayer = 0
    while localPlayer == 0:
        localPlayer = read(processHandle, (client + getOffset(config,'localPlayerOffset')))  # Get localPlayer pointer
    st.debug("LocalPlayer: "+ str(localPlayer))
    csgoWindow = win32gui.FindWindow(None, "Counter-Strike: Global Offensive")
    if csgoWindow is None:
        st.debug("csgo windows not found.")
        exit(1)
    st.debug("hack started. END to exit.")
    try:
        thread.start_new_thread(update,(processHandle, client))
    except:
        st.debug("Updater has an error.")
    if noFlashEnabled:
        try:
            thread.start_new_thread(noFlash,(processHandle,client,clientState,))
        except:
            st.debug("Could not start noflash thread :(")
    if triggerBotEnabled:
        try:
            thread.start_new_thread(triggerBot,
                                    (processHandle, client, clientState,))  # Start triggerBot function threaded
        except:
            st.debug("Could not start triggerbot thread :(")

    if autoBHOPEnabled:
        try:
            thread.start_new_thread(BHOP,
                                    (processHandle, client, localPlayer, clientState,))  # Start BHOP function threaded
        except:
            st.debug("Could not start bhop thread :(")

    if soundESPEnabled:
        try:
            thread.start_new_thread(soundESP, (processHandle, client, localPlayer,))  # Start soundESP function threaded
        except:
            st.debug("Could not start soundESP thread :(")

    if rcsEnabled:
        try:
            thread.start_new_thread(RCS, (processHandle, client, clientState,))  # Start RCS function threaded
        except:
            st.debug("Could not start rcs thread :(")
    try:
        thread.start_new_thread(AllStatus,(st,))
    except:
        st.debug("status not working..")
    changeStat(st)

    while not win32api.GetAsyncKeyState(0x23):  # While END key isn't touched
        if read(processHandle,
                (clientState + getOffset(config, 'clientStateInGameOffset'))) == 6:  # If client is in game
            if glowESPEnabled and win32gui.GetForegroundWindow() == csgoWindow:
                glowESP(processHandle, client)  # Call glowESP function non-threaded
            time.sleep(0.01)
    end = True  # Tells the threads to stop looping, prevents future problems
    time.sleep(0.01)

if __name__ == "__main__":
    if not admin.isUserAdmin():
        admin.runAsAdmin()
    else:
        main()
