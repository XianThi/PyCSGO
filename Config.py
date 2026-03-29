import configparser
import os
from typing import Optional, Dict, Any
from Status import Status
from Offsets import GameConfigObject

class GameConfig:
    CONFIG_FILE = 'offsets.ini'
    
    def __init__(self):
        self.config = configparser.ConfigParser(
            allow_no_value=True,
            delimiters=('=',),
            comment_prefixes=('#', ';')
        )
        self._load_or_create()
    
    def UpdateFromGithub(self, url: str):
        """GitHub'dan offsets güncelle"""
        import requests
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            for section, offsets in data.items():
                if not self.config.has_section(section.replace('.dll', '_dll')):
                    self.config.add_section(section.replace('.dll', '_dll'))
                for key, value in offsets.items():
                    self.config.set(section.replace('.dll', '_dll'), key.replace("dw",""), f'0x{value:X}')
            self._save()
            Status().info("Offsets updated from GitHub successfully.")
        except Exception as e:
            Status().info(f"Failed to update offsets from GitHub: {e}")

    def _load_or_create(self):
        if not os.path.exists(self.CONFIG_FILE):
            self._create_default_config()
        else:
            self.config.read(self.CONFIG_FILE, encoding='utf-8')
            self._ensure_all_sections()
    
    def _create_default_config(self):
        """Varsayılan offsets config oluştur"""
        # Ana offsets
        self.config.add_section('client_dll')
        self.config.set('client_dll', 'entityList', '0')
        self.config.set('client_dll', 'viewMatrix', '0')
        self.config.set('client_dll', 'localPlayerController', '0')
        self.config.set('client_dll', 'globalVars', '0')
        self.config.set('client_dll', 'plantedC4', '0')
        
        self.config.add_section('engine2_dll')
        self.config.set('engine2_dll', 'buildNumber', '0')
        
        # Nested offsets
        self._create_section('controller', {
            'm_iPing': '0x828', 'm_hPawn': '0x6C4', 'm_steamID': '0x780',
            'm_iszPlayerName': '0x6F8', 'm_bIsLocalPlayerController': '0x788',
            'm_pInGameMoneyServices': '0x808', 'm_iAccount': '0x40'
        })
        
        self._create_section('pawn', {
            'm_vOldOrigin': '0x1588', 'm_iHealth': '0x354', 'm_iTeamNum': '0x3F3',
            'm_bIsScoped': '0x26F8', 'm_ArmorValue': '0x272C', 'm_bIsDefusing': '0x26FA',
            'm_pGameSceneNode': '0x338', 'm_pClippingWeapon': '0x3DC0',
            'm_entitySpottedState': '0x26E0', 'm_bSpottedByMask': '0xC',
            'm_flFlashOverlayAlpha': '0x15EC'
        })
        
        self._create_section('bomb', {
            'm_isPlanted': '0x8', 'm_bC4Activated': '0x11B8',
            'm_nBombSite': '0x1174', 'm_vecAbsOrigin': '0xD0'
        })
        
        self._create_section('bone', {'m_modelState': '0x160'})
        
        self._create_section('global_vars', {
            'maxClients': '0x10', 'currentMapName': '0x180', 'currentTime': '0x2C'
        })
        
        self._create_section('signatures', {
            'viewMatrix': '48 8D 0D ?? ?? ?? ?? 48 C1 E0 06',
            'globalVars': '48 89 15 ?? ?? ?? ?? 48 89 42',
            'entityList': '48 8B 0D ?? ?? ?? ?? 48 89 7C 24 ?? 8B FA C1 EB',
            'localPlayerController': '48 8B 05 ?? ?? ?? ?? 41 89 BE',
            'plantedC4': '48 8b 15 ?? ?? ?? ?? 41 FF C0 48 8D 4C 24 ?? 44 89 05 ?? ?? ?? ??',
            'weaponC4': '48 89 05 ?? ?? ?? ?? F7 C1 ?? ?? ?? ?? 74 ?? 81 E1 ?? ?? ?? ?? 89 0D ?? ?? ?? ?? 8B 05 ?? ?? ?? ?? 89 1D ?? ?? ?? ?? EB ?? 48 8B 15 ?? ?? ?? ?? 48 8B 5C 24 ?? FF C0 89 05 ?? ?? ?? ?? 48 8B C6 48 89 34 EA 80 BE',
            'buildNumber': '89 05 ?? ?? ?? ?? 48 8d 0d ?? ?? ?? ?? ff 15 ?? ?? ?? ?? 48 8b 0d'
        })
        
        self._create_options()
        self._save()
    
    def _create_section(self, section_name: str, values: Dict[str, str]):
        self.config.add_section(section_name)
        for key, value in values.items():
            self.config.set(section_name, key, value)
    
    def _create_options(self):
        self.config.add_section('options')
        options = {
            'glowESPEnabled': 'True', 'triggerBotEnabled': 'True',
            'autoBHOPEnabled': 'True', 'soundESPEnabled': 'True', 'rcsEnabled': 'True'
        }
        for key, value in options.items():
            self.config.set('options', key, value)
    
    def _ensure_all_sections(self):
        required_sections = [
            'client_dll', 'engine2_dll', 'controller', 'pawn', 'bomb', 
            'bone', 'global_vars', 'signatures', 'options'
        ]
        for section in required_sections:
            if not self.config.has_section(section):
                print(f"Missing section '{section}', recreating...")
                self.config.add_section(section)
                self._save()
    
    def _save(self):
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get_offset(self, section: str, key: str, base: int = 0) -> int:
        """Hex offset oku ve integer'a çevir"""
        try:
            value = self.config.get(section, key)
            if value.startswith('0x'):
                return int(value, 16)
            return int(value)
        except Exception as e:
            print(f"[CONFIG ERROR] {section}.{key}: {e}")
            return base
    
    def set_offset(self, section: str, key: str, value: int):
        """Offset yaz (hex formatında)"""
        self.config.set(section, key, f'0x{value:X}')
        self._save()
    
    def get_option(self, key: str, default: bool = False) -> bool:
        """Boolean option oku"""
        try:
            value = self.config.get('options', key).lower()
            return value in ('true', '1', 'yes', 'on')
        except:
            return default
    
    def set_option(self, key: str, value: bool):
        """Boolean option yaz"""
        self.config.set('options', key, str(value))
        self._save()
    
    def to_object(self) -> GameConfigObject:
        """Offsets class yapısına uygun object döndür"""
        return GameConfigObject.from_config(self)