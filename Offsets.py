from dataclasses import dataclass, asdict, field
from typing import Dict, Any

@dataclass
class ControllerOffsets:
    m_iPing: int = 0x828
    m_hPawn: int = 0x6C4
    m_steamID: int = 0x780
    m_iszPlayerName: int = 0x6F8
    m_bIsLocalPlayerController: int = 0x788
    m_pInGameMoneyServices: int = 0x808
    m_iAccount: int = 0x40

@dataclass
class PawnOffsets:
    m_vOldOrigin: int = 0x1588
    m_iHealth: int = 0x354
    m_iTeamNum: int = 0x3F3
    m_bIsScoped: int = 0x26F8
    m_ArmorValue: int = 0x272C
    m_bIsDefusing: int = 0x26FA
    m_pGameSceneNode: int = 0x338
    m_pClippingWeapon: int = 0x3DC0
    m_entitySpottedState: int = 0x26E0
    m_bSpottedByMask: int = 0xC
    m_flFlashOverlayAlpha: int = 0x15EC

@dataclass
class BombOffsets:
    m_isPlanted: int = 0x8
    m_bC4Activated: int = 0x11B8
    m_nBombSite: int = 0x1174
    m_vecAbsOrigin: int = 0xD0

@dataclass
class BoneOffsets:
    m_modelState: int = 0x160

@dataclass
class GlobalVarsOffsets:
    maxClients: int = 0x10
    currentMapName: int = 0x180
    currentTime: int = 0x2C

@dataclass
class Signatures:
    viewMatrix: str = "48 8D 0D ?? ?? ?? ?? 48 C1 E0 06"
    globalVars: str = "48 89 15 ?? ?? ?? ?? 48 89 42"
    entityList: str = "48 8B 0D ?? ?? ?? ?? 48 89 7C 24 ?? 8B FA C1 EB"
    localPlayerController: str = "48 8B 05 ?? ?? ?? ?? 41 89 BE"
    plantedC4: str = "48 8b 15 ?? ?? ?? ?? 41 FF C0 48 8D 4C 24 ?? 44 89 05 ?? ?? ?? ??"
    weaponC4: str = ("48 89 05 ?? ?? ?? ?? "
                     "F7 C1 ?? ?? ?? ?? "
                     "74 ?? "
                     "81 E1 ?? ?? ?? ?? "
                     "89 0D ?? ?? ?? ?? "
                     "8B 05 ?? ?? ?? ?? "
                     "89 1D ?? ?? ?? ?? "
                     "EB ?? "
                     "48 8B 15 ?? ?? ?? ?? "
                     "48 8B 5C 24 ?? "
                     "FF C0 "
                     "89 05 ?? ?? ?? ?? "
                     "48 8B C6 48 89 34 EA 80 BE")
    buildNumber: str = "89 05 ?? ?? ?? ?? 48 8d 0d ?? ?? ?? ?? ff 15 ?? ?? ?? ?? 48 8b 0d"

@dataclass
class GameOptions:
    glowESPEnabled: bool = True
    triggerBotEnabled: bool = True
    autoBHOPEnabled: bool = True
    soundESPEnabled: bool = True
    rcsEnabled: bool = True
    
    @classmethod
    def from_config(cls, config):
        """GameOptions from config"""
        fields = cls.__dataclass_fields__
        data = {k: config.get_option(k) for k in fields}
        return cls(**data)
@dataclass
class OffsetsConfig:
    # client.dll
    entityList: int = 0
    viewMatrix: int = 0
    localPlayerController: int = 0
    globalVars: int = 0
    plantedC4: int = 0
    
    # engine2.dll
    buildNumber: int = 0
    
    controller: ControllerOffsets = field(default_factory=ControllerOffsets)
    pawn: PawnOffsets = field(default_factory=PawnOffsets)
    bomb: BombOffsets = field(default_factory=BombOffsets)
    bone: BoneOffsets = field(default_factory=BoneOffsets)
    global_vars: GlobalVarsOffsets = field(default_factory=GlobalVarsOffsets)
    signatures: Signatures = field(default_factory=Signatures)
    
    @classmethod
    def from_config(cls, config):
        """Config'den OffsetsConfig oluştur - HATA BURADA ÇÖZÜLDÜ!"""
        # Ana offsets
        client_offsets = {
            'entityList': config.get_offset('client_dll', 'entityList'),
            'viewMatrix': config.get_offset('client_dll', 'viewMatrix'),
            'localPlayerController': config.get_offset('client_dll', 'localPlayerController'),
            'globalVars': config.get_offset('client_dll', 'globalVars'),
            'plantedC4': config.get_offset('client_dll', 'plantedC4'),
            'buildNumber': config.get_offset('engine2_dll', 'buildNumber')
        }
        
        # Nested offsets
        controller_data = {
            k: config.get_offset('controller', k)
            for k in ControllerOffsets.__dataclass_fields__
        }

        pawn_data = {
            k: config.get_offset('pawn', k)
            for k in PawnOffsets.__dataclass_fields__
        }

        bomb_data = {
            k: config.get_offset('bomb', k)
            for k in BombOffsets.__dataclass_fields__
        }

        bone_data = {
            'm_modelState': config.get_offset('bone', 'm_modelState')
        }

        global_vars_data = {
            k: config.get_offset('global_vars', k)
            for k in GlobalVarsOffsets.__dataclass_fields__
        }
        
        signatures_data = {
            k: config.config.get('signatures', k) 
            for k in Signatures.__dataclass_fields__
        }
        
        return cls(
            **client_offsets,
            controller=ControllerOffsets(**controller_data),
            pawn=PawnOffsets(**pawn_data),
            bomb=BombOffsets(**bomb_data),
            bone=BoneOffsets(**bone_data),
            global_vars=GlobalVarsOffsets(**global_vars_data),
            signatures=Signatures(**signatures_data)
        )

@dataclass
class GameConfigObject:
    offsets: OffsetsConfig
    options: GameOptions
    
    @classmethod
    def from_config(cls, config):
        """Ana config object oluştur"""
        return cls(
            offsets=OffsetsConfig.from_config(config),
            options=GameOptions.from_config(config)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)