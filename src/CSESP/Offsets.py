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
            # Updated URLs to sezzyaep/CS2-OFFSETS
            offsets_url = "https://raw.githubusercontent.com/sezzyaep/CS2-OFFSETS/main/offsets.json"
            client_dll_url = "https://raw.githubusercontent.com/sezzyaep/CS2-OFFSETS/main/client_dll.json"

            offsets = requests.get(offsets_url).json()
            client_dll = requests.get(client_dll_url).json()

            client = offsets["client.dll"]
            classes = client_dll["client.dll"]["classes"]

            # Module offsets (direct integers)
            cls.dwEntityList = client["dwEntityList"]
            cls.dwLocalPlayerController = client["dwLocalPlayerController"]
            cls.dwLocalPlayerPawn = client["dwLocalPlayerPawn"]
            cls.dwViewMatrix = client["dwViewMatrix"]

            # Helper to extract offset from a field definition
            def get_field_offset(class_name, field_name):
                try:
                    return classes[class_name]["fields"][field_name]["offset"]
                except (KeyError, TypeError):
                    return None

            cls.m_iszPlayerName = get_field_offset("CBasePlayerController", "m_iszPlayerName")
            cls.m_iHealth = get_field_offset("C_BaseEntity", "m_iHealth")
            cls.m_ArmorValue = get_field_offset("C_CSPlayerPawn", "m_ArmorValue")
            cls.m_iTeamNum = get_field_offset("C_BaseEntity", "m_iTeamNum")
            cls.m_lifeState = get_field_offset("C_BaseEntity", "m_lifeState")
            cls.m_vOldOrigin = get_field_offset("C_BasePlayerPawn", "m_vOldOrigin")
            cls.m_hPlayerPawn = get_field_offset("CCSPlayerController", "m_hPlayerPawn")
            cls.m_pGameSceneNode = get_field_offset("C_BaseEntity", "m_pGameSceneNode")

            # Bone array path (same logic, but note sezzyaep's JSON does not define a
            # CSkeletonInstance class, so this will remain None unless you adapt it
            # to the actual bone‑array offset. The original code already handled this
            # gracefully.)
            try:
                m_model_state = classes["CSkeletonInstance"]["fields"]["m_modelState"]["offset"]
                cls.m_pBoneArray = m_model_state + 128
            except (KeyError, TypeError):
                cls.m_pBoneArray = None
                print("[Offsets] Warning: Could not resolve m_pBoneArray path (CSkeletonInstance.m_modelState).")

            cls.dwPlantedC4 = client.get("dwPlantedC4")

            c4_fields = classes.get("C_PlantedC4", {}).get("fields", {})

            def c4_field_offset(field_name):
                try:
                    return c4_fields[field_name]["offset"]
                except (KeyError, TypeError):
                    return None

            cls.m_flTimerLength = c4_field_offset("m_flTimerLength")
            cls.m_bBeingDefused = c4_field_offset("m_bBeingDefused")
            cls.m_flDefuseLength = c4_field_offset("m_flDefuseLength")
            cls.m_bBombDefused = c4_field_offset("m_bBombDefused")
            cls.m_bHasExploded = c4_field_offset("m_bHasExploded")

            scene_node_fields = classes.get("CGameSceneNode", {}).get("fields", {})
            try:
                cls.m_vecAbsOrigin = scene_node_fields["m_vecAbsOrigin"]["offset"]
            except (KeyError, TypeError):
                cls.m_vecAbsOrigin = None
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