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
    m_pClippingWeapon = None

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
            offsets = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json()
            client_dll = requests.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json").json()

            client = offsets["client.dll"]
            classes = client_dll["client.dll"]["classes"]

            cls.dwEntityList = client["dwEntityList"]
            cls.dwLocalPlayerController = client["dwLocalPlayerController"]
            cls.dwLocalPlayerPawn = client["dwLocalPlayerPawn"]
            cls.dwViewMatrix = client["dwViewMatrix"]

            cls.m_iszPlayerName = classes["CBasePlayerController"]["fields"].get("m_iszPlayerName")
            cls.m_iHealth = classes["C_BaseEntity"]["fields"].get("m_iHealth")
            cls.m_ArmorValue = classes["C_CSPlayerPawn"]["fields"].get("m_ArmorValue")
            cls.m_iTeamNum = classes["C_BaseEntity"]["fields"].get("m_iTeamNum")
            cls.m_lifeState = classes["C_BaseEntity"]["fields"].get("m_lifeState")
            cls.m_vOldOrigin = classes["C_BasePlayerPawn"]["fields"].get("m_vOldOrigin")
            cls.m_hPlayerPawn = classes["CCSPlayerController"]["fields"].get("m_hPlayerPawn")
            cls.m_pGameSceneNode = classes["C_BaseEntity"]["fields"].get("m_pGameSceneNode")

            # 骨骼数组路径 (m_modelState + 0x80 / 128)
            try:
                m_model_state = classes["CSkeletonInstance"]["fields"]["m_modelState"]
                cls.m_pBoneArray = m_model_state + 128
            except KeyError:
                cls.m_pBoneArray = None
                print("[Offsets] Warning: Could not resolve m_pBoneArray path (CSkeletonInstance.m_modelState).")

            cls.dwPlantedC4 = client.get("dwPlantedC4")

            c4_fields = classes.get("C_PlantedC4", {}).get("fields", {})
            cls.m_flTimerLength = c4_fields.get("m_flTimerLength")
            cls.m_bBeingDefused = c4_fields.get("m_bBeingDefused")
            cls.m_flDefuseLength = c4_fields.get("m_flDefuseLength")
            cls.m_bBombDefused = c4_fields.get("m_bBombDefused")
            cls.m_bHasExploded = c4_fields.get("m_bHasExploded")

            scene_node_fields = classes.get("CGameSceneNode", {}).get("fields", {})
            cls.m_vecAbsOrigin = scene_node_fields.get("m_vecAbsOrigin")
            if cls.m_vecAbsOrigin is None:
                print("[Offsets] Warning: m_vecAbsOrigin not found in CGameSceneNode.fields.")

        except requests.exceptions.RequestException as e:
            print(f"[Offsets] Network error while fetching offsets: {e}")
            sys.exit(1)
        except (KeyError, TypeError) as e:
            print(f"[Offsets] JSON structure error (the dumper format may have changed): {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[Offsets] An unexpected error occurred: {e}")
            sys.exit(1)