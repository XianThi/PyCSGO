from ctypes import *
from pydbg import *
from memorpy import *
import time
import win32api
import thread
import win32gui
import math
import winsound
import wmi
import admin

# OFFSET START #
crossHairIDOffset = 0xAA70
forceAttackOffset = 0x2F108C0
forceJumpOffset = 0x4F6746C
clientStateOffset = 0x5CB524
clientStateViewAnglesOffset = 0x4D0C
aimPunchOffset = 0x301C
clientStateInGameOffset = 0x100
flagsOffset = 0x100
vecOriginOffset = 0x134
shotsFiredOffset = 0xA2C0
boneMatrix = 0x2698
entityListOffset = 0x4AD0884
localPlayerIndexOffset = 0x178
localPlayerOffset = 0xAAD704
glowObjectOffset = 0x4FEB37C
glowIndexOffset = 0xA320
teamNumOffset = 0xF0
dormantOffset = 0xE9
healthOffset = 0xFC
bSpottedOffset = 0x939
# OFFSET END #

# OPTIONS START #
glowESPEnabled = True
triggerBotEnabled = True
autoBHOPEnabled = True
soundESPEnabled = True
rcsEnabled = True

maxSoundESPDistance = 780  # Default: 780, decent distance tbh
RCSPerfectPercent = 100  # Percent of RCS being perfect, 100% = perfect RCS
triggerBotKey = 0x12  # Default: right-click
triggerBotRandomMinimum = 1  # Minimum miliseconds to wait before shooting, there is a random int between 0-50 added to this in the code

# OPTIONS END #

foundProcess = False
end = False
csgoWindow = None
processID = 0
proc = None



# triggerBot: if entity in crosshair is an enemy, fire with a random delay between triggerBotRandomMinimum miliseconds to triggerBotRandomMinimum + 50 miliseconds
def triggerBot(process, client, clientState):
    global end
    global csgoWindow
    while not end:  # This function is threaded so might as well do this :>
        time.sleep(0.1)
        if not win32gui.GetForegroundWindow():
            continue
        if win32gui.GetForegroundWindow() == csgoWindow:
            if read(process, (clientState + clientStateInGameOffset)) == 6:  # If the client is in game
                localPlayer = read(process, (client + localPlayerOffset))  # Get LocalPlayer
                localPlayerTeam = read(process, (localPlayer + teamNumOffset))  # Get the team of the LocalPlayer
                crossHairID = read(process, (localPlayer + crossHairIDOffset))  # Get the Entity ID of the entity in crosshairs
                if crossHairID == 0:  # If no entity in crosshair
                    continue
                crossEntitypnt = (client + entityListOffset + ((crossHairID - 1) * 0x10))
                crossEntity = read(process, crossEntitypnt)  # Find entity based on ID defined by crossHairID

                crossEntityTeam = read(process, (crossEntity + teamNumOffset))  # Get team of Entity in Crosshair

                if crossEntityTeam != 2 and crossEntityTeam != 3:  # If the entity is not a terrorist or counter-terrorist
                    continue

                crossEntityDormant = read(process, (
                    crossEntity + dormantOffset))  # Get boolean that states whether entity in crosshair is dormant or not

                #if win32api.GetAsyncKeyState(triggerBotKey) and localPlayerTeam != crossEntityTeam and crossEntityDormant == 0:  # if triggerBotKey is held, the localPlayers team is not equal to entity in crosshair's team, and if the entity in crosshair is not dormant
                if  localPlayerTeam != crossEntityTeam and crossEntityDormant == 0:
                    time.sleep((triggerBotRandomMinimum + 1) / 1000.0)  # Sleep for random delay between triggerBotRandomMinimum miliseconds to triggerBotRandomMinimum + 50 miliseconds
                    #while crossHairID != 0 and win32api.GetAsyncKeyState(triggerBotKey):  # while there is an entity in my crosshairs and my triggerbot key is held down
                    while crossHairID != 0:
                        crossHairID = read(process, (
                            localPlayer + crossHairIDOffset))  # Re-get the crosshair ID to check if maybe no longer an entity in my crosshair
                        write(process, (client + forceAttackOffset), 5, 'int')  # Shoot
                        time.sleep(0.1)
                        write(process, (client + forceAttackOffset), 4, 'int')# Stop shooting


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


# glowESP: Enables glow around each entity
def glowESP(process, client):
    glowLocalBase = read(process, (client + localPlayerOffset))  # Get the localPlayer
    glowPointer = read(process, (client + glowObjectOffset))  # Get the glow Pointer
    myTeamID = read(process, (glowLocalBase + teamNumOffset))  # Get the localPlayer team ID
    playerCount = read(process, (client + glowObjectOffset + 0x4))
    for i in range(1, playerCount):  # For each player until the max players available
        glowCurrentPlayer = read(process, (
            client + entityListOffset + ((i - 1) * 0x10)))  # Get current entity based on for-loop variable i

        if glowCurrentPlayer == 0x0:  # If the entity is invalid
            break  # Break out of the for loop, we have reached the current max players

        glowCurrentPlayerDormant = read(process, (
            glowCurrentPlayer + dormantOffset))  # Get boolean that states whether glowCurrentPlayer entity is dormant or not
        glowCurrentPlayerGlowIndex = read(process, (
            glowCurrentPlayer + glowIndexOffset))  # Get the glowIndex of the glowCurrentPlayer entity

        entityBaseTeamID = read(process,
                                (glowCurrentPlayer + teamNumOffset))  # Get the team ID of the glowCurrentPlayer entity

        if entityBaseTeamID == 0 or glowCurrentPlayerDormant != 0:  # If the glowCurrentPlayer entity is on an irrelevant team (0) or if the glowCurrentPlayer entity is dormant
            continue  # Continue the for-loop
        else:
            if myTeamID != entityBaseTeamID:  # If localPlayer team is not glowCurrentPlayer entity team
                write(process, (glowCurrentPlayer + bSpottedOffset), 1, 'int')  # Set glowCurrentPlayer bspotted to True

            # fucking nigger python with no switch statements kill me
            if entityBaseTeamID == 2:  # If glowCurrentPlayer entity is a terrorist
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x4)), 1.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x8)), 0.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0xC)), 0.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x10)), 1.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x24)), 1, 'int')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x25)), 0, 'int')
            elif entityBaseTeamID == 3:  # else if glowCurrentPlayer entity is a counter-terrorist
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x4)), 0.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x8)), 0.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0xC)), 1.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x10)), 1.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x24)), 1, 'int')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x25)), 0, 'int')
            else:
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x4)), 0.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x8)), 1.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0xC)), 0.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x10)), 1.0, 'float')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x24)), 1, 'int')
                write(process, (glowPointer + ((glowCurrentPlayerGlowIndex * 0x38) + 0x25)), 0, 'int')


# BHOP: Automatically start jumping if in game, on the ground, and space is held
def BHOP(process, client, localPlayer, clientState):
    global end
    global csgoWindow

    while not end:
        if win32gui.GetForegroundWindow() == csgoWindow and read(process, (
                    clientState + clientStateInGameOffset)) == 6:  # If client is in game
            flags = read(process, (localPlayer + flagsOffset))  # Get client flags
            if flags & (1 << 0) and win32api.GetAsyncKeyState(
                    0x20):  # If localPlayer on the ground and if space is held
                write(process, (client + forceJumpOffset), 6, 'int')  # Autojump
            flags = read(process, (localPlayer + flagsOffset))  # Get the latest flags again
        time.sleep(0.01)


def soundESP(process, client, localPlayer):
    global maxSoundESPDistance
    global end
    global csgoWindow

    while not end:
        time.sleep(0.01)

        if win32gui.GetForegroundWindow() == csgoWindow:
            closestPlayer = 99999.0
            playerCount = read(process, (client + glowObjectOffset + 0x4))
            for i in range(0, playerCount):
                ent = read(process, (
                    client + entityListOffset + ((i - 1) * 0x10)))  # Get current entity based on for-loop variable i

                if ent is 0x0:
                    break

                entDormant = read(process, (
                    ent + dormantOffset))  # Get boolean that states whether glowCurrentPlayer entity is dormant or not

                if entDormant != 0:
                    continue

                myTeamID = read(process, (localPlayer + teamNumOffset))  # Get the team ID of the localPlayer
                entityBaseTeamID = read(process, (ent + teamNumOffset))  # Get the team ID of the ent entity

                if entityBaseTeamID != 2 and entityBaseTeamID != 3:
                    continue

                localPlayerX = read(process, (localPlayer + vecOriginOffset),
                                    "float")  # Get the X coordinate of the vecOrigin of the localPlayer
                localPlayerY = read(process, (localPlayer + vecOriginOffset + 0x4),
                                    'float')  # Get the Y coordinate of the vecOrigin of the localPlayer
                localPlayerZ = read(process, (localPlayer + vecOriginOffset + 0x8),
                                    'float')  # Get the Z coordinate of the vecOrigin of the localPlayer

                entityX = read(process, (ent + vecOriginOffset),
                               'float')  # Get the X coordinate of the vecOrigin of the ent
                entityY = read(process, (ent + vecOriginOffset + 0x4),
                               'float')  # Get the Y coordinate of the vecOrigin of the ent
                entityZ = read(process, (ent + vecOriginOffset + 0x8),
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
                    clientState + clientStateInGameOffset)) == 6:  # If we are actually playing in game
            localPlayer = read(process, (client + localPlayerOffset))  # Get the localPlayer
            if read(process, (localPlayer + shotsFiredOffset)) > 1:  # If we have fired more than 1 shots
                viewAngleX = read(process, (clientState + clientStateViewAnglesOffset), 'float')  # Get the X viewAngle
                viewAngleY = read(process, (clientState + clientStateViewAnglesOffset + 0x4),
                                  'float')  # Get the Y viewAngle

                aimPunchX = read(process, (localPlayer + aimPunchOffset), 'float')  # Get the X aimPunch
                aimPunchY = read(process, (localPlayer + aimPunchOffset + 0x4), 'float')  # Get the Y aimPunch

                viewAngleX -= (aimPunchX - oldAimPunchX) * (
                    RCSPerfectPercent * 0.02)  # Subtract our AimPunch from our ViewAngle
                viewAngleY -= (aimPunchY - oldAimPunchY) * (
                    RCSPerfectPercent * 0.02)  # Subtract our AimPunch from our ViewAngle

                viewAngleX, viewAngleY = normalizeAngles(viewAngleX, viewAngleY)  # Normalize our ViewAngles

                write(process, (clientState + clientStateViewAnglesOffset), viewAngleX, 'float')
                write(process, (clientState + clientStateViewAnglesOffset + 0x4), viewAngleY, 'float')

                oldAimPunchX = aimPunchX
                oldAimPunchY = aimPunchY
            else:
                oldAimPunchX = 0
                oldAimPunchY = 0
        time.sleep(0.01)


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


# main: Main function, starts all the threads, does glow esp, waits for end key, etc :)
def main():
    global triggerBotEnabled
    global autoBHOPEnabled
    global glowESPEnabled
    global soundESPEnabled
    global end
    global csgoWindow
    global rcsEnabled
    global bulundu
    bulundu = False
    processHandle = None
    print("waiting for csgo.exe...")
    while True:
        c = wmi.WMI()
        for pr in c.Win32_Process():
            if pr.Name == "csgo.exe":
                processID = int(pr.ProcessId)
                dbg = pydbg()
                dbg.open_process(processID)
                processHandle = dbg
                bulundu = True
                break;
        if bulundu == True:
            break;

    print("csgo.exe found. getting modules...")
    client = getDLL("client.dll", processID)  # Get client.dll module
    print("client.dll. : ", client)
    engine = getDLL("engine.dll", processID)  # Get engine.dll module
    print("engine.dll. : ", engine)
    clientState = read(processHandle, (engine + clientStateOffset))  # Get clientState pointer
    print("ClientState : ",clientState)
    print("waiting for LocalPlayer...")
    localPlayer = 0
    while localPlayer == 0:
        localPlayer = read(processHandle, (client + localPlayerOffset))  # Get localPlayer pointer
    print("LocalPlayer: ", localPlayer)
    csgoWindow = win32gui.FindWindow(None, "Counter-Strike: Global Offensive")
    if csgoWindow is None:
        print("csgo windows not found.")
        exit(1)
    print("hack started. END to exit.")
    if triggerBotEnabled:
        try:
            thread.start_new_thread(triggerBot,
                                    (processHandle, client, clientState,))  # Start triggerBot function threaded
        except:
            print("Could not start triggerbot thread :(")

    if autoBHOPEnabled:
        try:
            thread.start_new_thread(BHOP,
                                    (processHandle, client, localPlayer, clientState,))  # Start BHOP function threaded
        except:
            print("Could not start bhop thread :(")

    if soundESPEnabled:
        try:
            thread.start_new_thread(soundESP, (processHandle, client, localPlayer,))  # Start soundESP function threaded
        except:
            print("Could not start playerCounter thread :(")

    if rcsEnabled:
        try:
            thread.start_new_thread(RCS, (processHandle, client, clientState,))  # Start RCS function threaded
        except:
            print("Could not start rcs thread :(")

    while not win32api.GetAsyncKeyState(0x23):  # While END key isn't touched
        if read(processHandle, (clientState + clientStateInGameOffset)) == 6:  # If client is in game
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
