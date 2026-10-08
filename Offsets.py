import sys
import requests


class Offsets:
    dwEntityList = None
    dwLocalPlayerController = None
    dwLocalPlayerPawn = None
    dwViewMatrix = None

    m_iszPlayerName = None
    m_iHealth = None
    m_ArmorValue = None
    m_iTeamNum = None
    m_lifeState = None
    m_vOldOrigin = None
    m_hPlayerPawn = None
    m_pGameSceneNode = None
    m_pBoneArray = None

    dwPlantedC4 = None
    m_flTimerLength = None
    m_bBeingDefused = None
    m_flDefuseLength = None
    m_bBombDefused = None
    m_bHasExploded = None
    m_vecAbsOrigin = None

    @classmethod
    def load(cls):
        try:
            offsets = requests.get(
                "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json",
                timeout=10,
            ).json()
            cd = requests.get(
                "https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json",
                timeout=10,
            ).json()

            cls.dwEntityList = offsets["client.dll"]["dwEntityList"]
            cls.dwLocalPlayerController = offsets["client.dll"]["dwLocalPlayerController"]
            cls.dwLocalPlayerPawn = offsets["client.dll"]["dwLocalPlayerPawn"]
            cls.dwViewMatrix = offsets["client.dll"]["dwViewMatrix"]
            cls.dwPlantedC4 = offsets["client.dll"]["dwPlantedC4"]

            C = cd["client.dll"]["classes"]
            cls.m_iszPlayerName = C["CBasePlayerController"]["fields"]["m_iszPlayerName"]
            cls.m_iHealth = C["C_BaseEntity"]["fields"]["m_iHealth"]
            cls.m_ArmorValue = C["C_CSPlayerPawn"]["fields"]["m_ArmorValue"]
            cls.m_iTeamNum = C["C_BaseEntity"]["fields"]["m_iTeamNum"]
            cls.m_lifeState = C["C_BaseEntity"]["fields"]["m_lifeState"]
            cls.m_vOldOrigin = C["C_BasePlayerPawn"]["fields"]["m_vOldOrigin"]
            cls.m_hPlayerPawn = C["CCSPlayerController"]["fields"]["m_hPlayerPawn"]
            cls.m_pGameSceneNode = C["C_BaseEntity"]["fields"]["m_pGameSceneNode"]
            cls.m_pBoneArray = C["CSkeletonInstance"]["fields"]["m_modelState"] + 128

            cls.m_flTimerLength = C["C_PlantedC4"]["fields"]["m_flTimerLength"]
            cls.m_bBeingDefused = C["C_PlantedC4"]["fields"]["m_bBeingDefused"]
            cls.m_flDefuseLength = C["C_PlantedC4"]["fields"]["m_flDefuseLength"]
            cls.m_bBombDefused = C["C_PlantedC4"]["fields"]["m_bBombDefused"]
            cls.m_bHasExploded = C["C_PlantedC4"]["fields"]["m_bHasExploded"]
            cls.m_vecAbsOrigin = C["CGameSceneNode"]["fields"]["m_vecAbsOrigin"]
        except Exception as e:
            print(f"[Offsets] failed: {e}")
            sys.exit(1)