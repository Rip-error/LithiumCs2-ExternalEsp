import time
import pymem
import pymem.process

from Lithium.Offsets import Offsets
from Lithium.Entity import Entity


class ESP:
    def __init__(self):
        self.pm = None
        self.client = None
        self.entities = []
        self.local_player = None

    def initialize(self) -> bool:
        try:
            self.pm = pymem.Pymem("cs2.exe")
            self.client = pymem.process.module_from_name(
                self.pm.process_handle, "client.dll"
            ).lpBaseOfDll
            Offsets.load()
            return True
        except Exception as e:
            print(f"[ESP Init] {e}")
            return False

    def get_bomb_info(self):
        try:
            planted = self.pm.read_bool(self.client + Offsets.dwPlantedC4 - 8)
            if not planted:
                for attr in ("_bomb_planted_time", "_defuse_start_time"):
                    if hasattr(self, attr):
                        delattr(self, attr)
                return None

            pre = self.pm.read_ulonglong(self.client + Offsets.dwPlantedC4)
            bomb = self.pm.read_ulonglong(pre)
            if not bomb:
                return None

            scene = self.pm.read_ulonglong(bomb + Offsets.m_pGameSceneNode)
            pos = (
                self.pm.read_float(scene + Offsets.m_vecAbsOrigin),
                self.pm.read_float(scene + Offsets.m_vecAbsOrigin + 4),
                self.pm.read_float(scene + Offsets.m_vecAbsOrigin + 8),
            )
            tl = self.pm.read_float(bomb + Offsets.m_flTimerLength)
            bd = self.pm.read_bool(bomb + Offsets.m_bBeingDefused)
            dl = self.pm.read_float(bomb + Offsets.m_flDefuseLength)
            idf = self.pm.read_bool(bomb + Offsets.m_bBombDefused)
            hex_ = self.pm.read_bool(bomb + Offsets.m_bHasExploded)

            if not hasattr(self, "_bomb_planted_time"):
                self._bomb_planted_time = time.time()

            if bd and not hasattr(self, "_defuse_start_time"):
                self._defuse_start_time = time.time()
                self._initial_defuse_length = dl
            elif not bd and hasattr(self, "_defuse_start_time"):
                del self._defuse_start_time
                del self._initial_defuse_length

            time_rem = 0 if idf else max(0, tl - (time.time() - self._bomb_planted_time))
            def_rem = 0
            if bd and hasattr(self, "_defuse_start_time"):
                def_rem = max(0, self._initial_defuse_length - (time.time() - self._defuse_start_time))

            return {
                "planted": True, "position": pos,
                "time_remaining": time_rem, "being_defused": bd,
                "defuse_time_remaining": def_rem,
                "is_defused": idf, "has_exploded": hex_,
            }
        except Exception as e:
            print(f"[Bomb] {e}")
            return None

    def update_entities(self):
        self.entities.clear()
        try:
            lc = self.pm.read_ulonglong(self.client + Offsets.dwLocalPlayerController)
            lp = self.pm.read_ulonglong(self.client + Offsets.dwLocalPlayerPawn)
            if not lc or not lp:
                return

            self.local_player = Entity(lc, lp)
            self.local_player.team = self.pm.read_int(lp + Offsets.m_iTeamNum)
            self.local_player.pos = tuple(
                self.pm.read_float(lp + Offsets.m_vOldOrigin + i * 4) for i in range(3)
            )

            lst = self.pm.read_ulonglong(self.client + Offsets.dwEntityList)
            if not lst:
                return
            for i in range(1, 65):
                self._process_entity(lst, i, lc)
        except Exception as e:
            print(f"[Update] {e}")

    def _process_entity(self, lst, idx, lc):
        try:
            le = self.pm.read_ulonglong(lst + (8 * (idx & 0x7FFF) >> 9) + 16)
            if not le:
                return
            ctrl = self.pm.read_ulonglong(le + 112 * (idx & 0x1FF))
            if ctrl == lc:
                return
            ph = self.pm.read_ulonglong(ctrl + Offsets.m_hPlayerPawn)
            pe = self.pm.read_ulonglong(lst + (8 * ((ph & 0x7FFF) >> 9)) + 16)
            pawn = self.pm.read_ulonglong(pe + 112 * (ph & 0x1FF))
            if not pawn:
                return

            e = Entity(ctrl, pawn)
            e.health = self.pm.read_int(pawn + Offsets.m_iHealth)
            if not 0 < e.health <= 100:
                return
            e.armor = self.pm.read_int(pawn + Offsets.m_ArmorValue)
            e.team = self.pm.read_int(pawn + Offsets.m_iTeamNum)
            e.lifestate = self.pm.read_int(pawn + Offsets.m_lifeState)
            e.name = self.pm.read_string(ctrl + Offsets.m_iszPlayerName)
            e.pos = tuple(
                self.pm.read_float(pawn + Offsets.m_vOldOrigin + i * 4) for i in range(3)
            )
            self.entities.append(e)
        except Exception:
            pass