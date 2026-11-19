import sys
import ctypes
import win32gui
import win32con
import win32api
import win32com.client
from pathlib import Path

from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QCheckBox, QVBoxLayout,
    QDialog, QPushButton, QColorDialog, QStackedWidget, QWidget,
    QHBoxLayout, QLabel
)

from CSESP.ESP import ESP
from CSESP.Offsets import Offsets
from CSESP.Config import Config


class OverlayMenu(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedSize(540, 600)
        
        self.checkboxes = {}
        self.color_buttons = {}
        self._setup_ui()
        self._apply_styles()


    def _setup_ui(self):
        # Main transparent layout
        outer_layout = QtWidgets.QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        # Main container with rounded corners
        self.container = QtWidgets.QWidget()
        self.container.setObjectName("mainContainer")
        outer_layout.addWidget(self.container)

        main_layout = QtWidgets.QHBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== LEFT SIDEBAR ==========
        sidebar = QtWidgets.QWidget()
        sidebar.setFixedWidth(155)
        sidebar.setObjectName("sidebar")
        sidebar_layout = QtWidgets.QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 22, 14, 18)
        sidebar_layout.setSpacing(8)

        # Logo / Title
        title = QtWidgets.QLabel("Cheese It 2")
        title.setObjectName("logo")
        title.setAlignment(QtCore.Qt.AlignCenter)
        sidebar_layout.addWidget(title)

        sidebar_layout.addSpacing(18)

        # Category buttons
        self.btn_visual = self._create_sidebar_btn("Visual", True)
        self.btn_colors = self._create_sidebar_btn("Colors")
        self.btn_settings = self._create_sidebar_btn("Settings")

        self.btn_visual.clicked.connect(lambda: self._switch_page(0))
        self.btn_colors.clicked.connect(lambda: self._switch_page(1))
        self.btn_settings.clicked.connect(lambda: self._switch_page(2))

        sidebar_layout.addWidget(self.btn_visual)
        sidebar_layout.addWidget(self.btn_colors)
        sidebar_layout.addWidget(self.btn_settings)
        sidebar_layout.addStretch()

        # Status
        self.state_label = QtWidgets.QLabel("ESP: ON")
        self.state_label.setObjectName("status")
        self.state_label.setAlignment(QtCore.Qt.AlignCenter)
        sidebar_layout.addWidget(self.state_label)

        main_layout.addWidget(sidebar)

        # ========== RIGHT CONTENT ==========
        self.content_stack = QtWidgets.QStackedWidget()
        self.content_stack.setObjectName("content")

        # --- Page 0: Visual ---
        visual_page = QtWidgets.QWidget()
        visual_layout = QtWidgets.QVBoxLayout(visual_page)
        visual_layout.setContentsMargins(26, 26, 26, 26)
        visual_layout.setSpacing(8)

        visual_layout.addWidget(self._section_header("ESP Features"))

        features = [
            ("draw_box", "Bounding Box"),
            ("draw_names", "Player Names"),
            ("draw_health", "Health Bar"),
            ("draw_distance", "Distance"),
            ("draw_skeleton", "Skeleton"),
            ("draw_head", "Head Circle"),
            ("draw_lines", "Snap Lines"),
            ("draw_teammates", "Show Teammates"),
            ("draw_bomb", "Bomb Info"),
        ]

        for key, label in features:
            row = self._create_toggle_row(key, label)
            visual_layout.addWidget(row)

        visual_layout.addStretch()
        self.content_stack.addWidget(visual_page)

        # --- Page 1: Colors ---
        colors_page = QtWidgets.QWidget()
        colors_layout = QtWidgets.QVBoxLayout(colors_page)
        colors_layout.setContentsMargins(26, 26, 26, 26)
        colors_layout.setSpacing(18)

        colors_layout.addWidget(self._section_header("Team Colors"))

        for team, label in [("color_t", "Terrorist (T)"), ("color_ct", "Counter-Terrorist (CT)")]:
            row = QtWidgets.QHBoxLayout()
            name = QtWidgets.QLabel(label)
            name.setObjectName("rowLabel")
            
            btn = QPushButton()
            btn.setFixedSize(90, 32)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.config[team].name()};
                    border: 2px solid #4c3d6e;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid #a78bfa;
                }}
            """)
            btn.clicked.connect(lambda _, key=team, b=btn: self._on_color_picker(key, b))
            self.color_buttons[team] = btn
            
            row.addWidget(name)
            row.addStretch()
            row.addWidget(btn)
            colors_layout.addLayout(row)

        colors_layout.addStretch()
        self.content_stack.addWidget(colors_page)

        # --- Page 2: Settings ---
        settings_page = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_page)
        settings_layout.setContentsMargins(26, 26, 26, 26)
        settings_layout.setSpacing(18)

        settings_layout.addWidget(self._section_header("Hotkeys & Controls"))

        # Keybind
        keybind_row = QtWidgets.QHBoxLayout()
        keybind_label = QtWidgets.QLabel("Toggle ESP Key")
        keybind_label.setObjectName("rowLabel")
        keybind_row.addWidget(keybind_label)
        keybind_row.addStretch()
        
        self.keybind_button = QPushButton(self.config["toggle_keybind"])
        self.keybind_button.setFixedSize(110, 34)
        self.keybind_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.keybind_button.setObjectName("actionBtn")
        self.keybind_button.clicked.connect(self._on_keybind_select)
        keybind_row.addWidget(self.keybind_button)
        settings_layout.addLayout(keybind_row)

        settings_layout.addSpacing(24)

        # Reset
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.setObjectName("dangerBtn")
        reset_btn.setCursor(QtCore.Qt.PointingHandCursor)
        reset_btn.setFixedHeight(38)
        reset_btn.clicked.connect(self._reset_to_defaults)
        settings_layout.addWidget(reset_btn)

        settings_layout.addStretch()
        self.content_stack.addWidget(settings_page)

        main_layout.addWidget(self.content_stack)


    def _create_sidebar_btn(self, text, active=False):
        btn = QPushButton(text)
        btn.setObjectName("sidebarBtn")
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setFixedHeight(40)
        return btn


    def _section_header(self, text):
        label = QtWidgets.QLabel(text)
        label.setObjectName("sectionHeader")
        return label


    def _create_toggle_row(self, key, label):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 5, 0, 5)

        name = QtWidgets.QLabel(label)
        name.setObjectName("rowLabel")

        cb = QCheckBox()
        cb.setChecked(self.config[key])
        cb.stateChanged.connect(lambda state, k=key: self._on_feature_toggle(k, state))
        self.checkboxes[key] = cb

        layout.addWidget(name)
        layout.addStretch()
        layout.addWidget(cb)
        return container


    def _switch_page(self, index):
        self.content_stack.setCurrentIndex(index)
        self.btn_visual.setChecked(index == 0)
        self.btn_colors.setChecked(index == 1)
        self.btn_settings.setChecked(index == 2)


    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background: transparent;
            }
            
            #mainContainer {
                background-color: #0f0b1a;
                border-radius: 16px;
                border: 1px solid #2a2040;
            }
            
            #sidebar {
                background-color: #160f28;
                border-top-left-radius: 16px;
                border-bottom-left-radius: 16px;
                border-right: 1px solid #2a2040;
            }
            
            #logo {
                color: #c4b5fd;
                font-size: 18px;
                font-weight: 700;
                font-family: 'Segoe UI';
                letter-spacing: 0.5px;
                padding: 4px 0;
            }
            
            #status {
                color: #4ade80;
                font-size: 12px;
                font-weight: 600;
                padding: 9px 6px;
                background-color: #1a122e;
                border-radius: 10px;
                border: 1px solid #2e2545;
            }
            
            #sidebarBtn {
                background-color: transparent;
                color: #a1a1aa;
                border: none;
                border-radius: 10px;
                text-align: left;
                padding-left: 16px;
                font-size: 14px;
                font-family: 'Segoe UI';
                font-weight: 500;
            }
            #sidebarBtn:hover {
                background-color: #251b3a;
                color: #e4e4e7;
            }
            #sidebarBtn:checked {
                background-color: #7c3aed;
                color: white;
                font-weight: 600;
            }
            
            #content {
                background-color: transparent;
                border-top-right-radius: 16px;
                border-bottom-right-radius: 16px;
            }
            
            #sectionHeader {
                color: #c4b5fd;
                font-size: 15px;
                font-weight: 600;
                margin-bottom: 6px;
                font-family: 'Segoe UI';
            }
            
            #rowLabel {
                color: #e4e4e7;
                font-size: 13.5px;
                font-family: 'Segoe UI';
            }
            
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 44px;
                height: 24px;
                border-radius: 12px;
                background-color: #3f3f46;
            }
            QCheckBox::indicator:checked {
                background-color: #7c3aed;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3f3f46;
            }
            
            QPushButton {
                background-color: #2a2040;
                color: #e4e4e7;
                border: 1px solid #3f3f46;
                border-radius: 10px;
                padding: 7px 14px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3b2d5c;
                border-color: #7c3aed;
            }
            
            #actionBtn {
                background-color: #2a2040;
                border-radius: 10px;
                font-weight: 600;
            }
            #actionBtn:hover {
                background-color: #3b2d5c;
                border-color: #a78bfa;
            }
            
            #dangerBtn {
                background-color: #3f1d2e;
                color: #f87171;
                border: 1px solid #7f1d1d;
                border-radius: 10px;
                font-weight: 600;
            }
            #dangerBtn:hover {
                background-color: #5c2438;
                border-color: #ef4444;
                color: #fca5a5;
            }
            
            QLabel {
                color: #e4e4e7;
                font-family: 'Segoe UI';
            }
        """)


    def set_esp_state(self, enabled: bool):
        if enabled:
            self.state_label.setText("ESP: ON")
            self.state_label.setStyleSheet("""
                color: #4ade80;
                font-size: 12px;
                font-weight: 600;
                padding: 9px 6px;
                background-color: #1a122e;
                border-radius: 10px;
                border: 1px solid #2e2545;
            """)
        else:
            self.state_label.setText("ESP: OFF")
            self.state_label.setStyleSheet("""
                color: #f87171;
                font-size: 12px;
                font-weight: 600;
                padding: 9px 6px;
                background-color: #1a122e;
                border-radius: 10px;
                border: 1px solid #2e2545;
            """)


    def _on_feature_toggle(self, key, state):
        self.config[key] = bool(state)
        self.config.save()


    def _on_color_picker(self, key, button):
        color = QColorDialog.getColor(initial=self.config[key], parent=self)
        if color.isValid():
            self.config[key] = color
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    border: 2px solid #4c3d6e;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid #a78bfa;
                }}
            """)
            win32gui.SetForegroundWindow(int(self.winId()))
            self.config.save()


    def _on_keybind_select(self):
        original_text = self.keybind_button.text()
        self.keybind_button.setText("Press key...")
        
        original_key_press = self.keyPressEvent
        revert_timer = QtCore.QTimer(self)
        revert_timer.setSingleShot(True)
        revert_timer.timeout.connect(lambda: self._revert_keybind_button(original_text, original_key_press))
        revert_timer.start(3000)
        
        def keyPressEvent(event):
            revert_timer.stop()
            key = event.key()
            key_name = QtGui.QKeySequence(key).toString()
            
            if key_name:
                self.config["toggle_keybind"] = key_name
                self.keybind_button.setText(key_name)
                self.config.save()
                self.keyPressEvent = original_key_press
            else:
                self._revert_keybind_button(original_text, original_key_press)
        
        self.keyPressEvent = keyPressEvent


    def _revert_keybind_button(self, original_text, original_key_press):
        self.keybind_button.setText(original_text)
        self.keyPressEvent = original_key_press


    def _reset_to_defaults(self):
        for label in self.checkboxes:
            self.checkboxes[label].setChecked(self.config.default_config[label])
            self.config[label] = self.config.default_config[label]

        for team, button in self.color_buttons.items():
            default_color = self.config._dict_to_qcolor(self.config.default_config[team])
            self.config[team] = default_color
            button.setStyleSheet(f"""
                QPushButton {{
                    background-color: {default_color.name()};
                    border: 2px solid #4c3d6e;
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid #a78bfa;
                }}
            """)

        self.config.save()


    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            if hasattr(self.parent(), "_toggle_menu"):
                self.parent()._toggle_menu()
            event.accept()
        else:
            super().keyPressEvent(event)


class OverlayRenderer:
    def __init__(self, esp, config, window_size):
        self.esp = esp
        self.config = config
        self.window_size = window_size
        self.scene = QGraphicsScene()


    def update(self):
        self.scene.clear()
        
        if not self._is_window_focused("Counter-Strike 2"):
            return

        self.esp.update_entities()

        if self.config["draw_bomb"]:
            self._draw_bomb()

        for entity in self.esp.entities:
            if not entity.pos:
                continue
            if entity.lifestate == 258:
                continue
            if entity.team == self.esp.local_player.team and not self.config["draw_teammates"]:
                continue
            self._draw_entity(entity)


    def _draw_bomb(self):
        try:
            bomb_info = self.esp.get_bomb_info()
            if not bomb_info or not bomb_info["planted"] or bomb_info["is_defused"] or bomb_info["has_exploded"]:
                return

            bomb_screen = self._world_to_screen(bomb_info["position"])
            if not bomb_screen:
                return
            if bomb_info["time_remaining"] > 0:
                if bomb_info["being_defused"]:
                    text = f'BOMB {bomb_info["time_remaining"]:.1f}s | DEFUSING {bomb_info["defuse_time_remaining"]:.1f}s'
                else:
                    text = f'BOMB {bomb_info["time_remaining"]:.1f}s'
                
                bomb_text = self.scene.addText(text, QtGui.QFont('Arial', 10, QtGui.QFont.Bold))
                bomb_text.setPos(bomb_screen[0], bomb_screen[1])
                bomb_text.setDefaultTextColor(QtGui.QColor(255, 0, 0))
        except Exception as e:
            print(f"Error drawing bomb: {e}")


    def _draw_entity(self, entity):
        head_pos = self._get_bone_position(entity, 6)
        feet_pos = entity.pos
        if not head_pos or not feet_pos:
            return

        head_screen = self._world_to_screen(head_pos)
        feet_screen = self._world_to_screen(feet_pos)
        if not head_screen or not feet_screen:
            return

        if any(self.config[key] for key in ["draw_box", "draw_health", "draw_names", "draw_distance"]):
            self._draw_player_box(head_screen, feet_screen, entity)

        if self.config["draw_skeleton"] or self.config["draw_head"]:
            self._draw_skeleton(entity)

        if self.config["draw_lines"]:
            self._draw_line_to_entity(feet_screen, entity.team)


    def _draw_player_box(self, head_screen, feet_screen, entity):
        base_height = feet_screen[1] - head_screen[1]
        height = base_height * 1.12
        width = height / 2.2
        center_x = (head_screen[0] + feet_screen[0]) / 2
        box_x = center_x - width / 2
        box_y = feet_screen[1] - height

        team_color = self.config["color_t"] if entity.team == 2 else self.config["color_ct"]

        if self.config["draw_box"]:
            box = QtWidgets.QGraphicsRectItem(box_x, box_y, width, height)
            box.setPen(QtGui.QPen(team_color, 2))
            self.scene.addItem(box)

        if self.config["draw_health"]:
            self._draw_health_bar(box_x, box_y, height, entity)

        if self.config["draw_names"]:
            self._draw_name(box_x, box_y, width, entity.name)

        if self.config["draw_distance"]:
            dist = self._calculate_distance(self.esp.local_player.pos, entity.pos)
            self._draw_distance(box_x, box_y, width, height, dist)


    def _draw_health_bar(self, x, y, height, entity):
        health_height = height * (entity.health / 100)
        health_color = self._get_health_color(entity.health)
        health_bar = QtWidgets.QGraphicsRectItem(x - 10, y + height - health_height, 3, health_height)
        health_bar.setBrush(QtGui.QBrush(health_color))
        self.scene.addItem(health_bar)

        armor_height = height * (entity.armor / 100)
        armor_bar = QtWidgets.QGraphicsRectItem(x - 6, y + height - armor_height, 3, armor_height)
        armor_bar.setBrush(QtGui.QBrush(QtGui.QColor(0, 150, 255, 180)))
        self.scene.addItem(armor_bar)


    def _draw_name(self, x, y, width, name):
        name_item = self.scene.addText(name, QtGui.QFont('Arial', 8))
        name_item.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        name_item.setPos(x + width / 2 - name_item.boundingRect().width() / 2, y - name_item.boundingRect().height() - 2)


    def _draw_distance(self, x, y, width, height, distance):
        distance_item = self.scene.addText(distance, QtGui.QFont('Arial', 8))
        distance_item.setDefaultTextColor(QtGui.QColor(255, 255, 255))
        distance_item.setPos(x + width / 2 - distance_item.boundingRect().width() / 2, y + height + 2)


    def _draw_line_to_entity(self, feet_screen, team):
        screen_center_x = self.window_size[0] // 2
        screen_bottom_y = self.window_size[1] - 150
        line = QtWidgets.QGraphicsLineItem(screen_center_x, screen_bottom_y, feet_screen[0], feet_screen[1])
        line.setPen(QtGui.QPen(self.config["color_t"] if team == 2 else self.config["color_ct"], 1))
        self.scene.addItem(line)


    def _draw_skeleton(self, entity):
        bone_ids = {
            "head": 6,
            "neck": 5,
            "spine": 4,
            "pelvis": 0,
            "right_shoulder": 10,
            "right_elbow": 11,
            "right_hand": 12,
            "left_shoulder": 7,
            "left_elbow": 8,
            "left_hand": 9,
            "right_hip": 16,
            "right_knee": 17,
            "right_foot": 18,
            "left_hip": 13,
            "left_knee": 14,
            "left_foot": 15
        }

        bone_screen = {}
        for name, index in bone_ids.items():
            bone_pos = self._get_bone_position(entity, index)
            if bone_pos:
                screen = self._world_to_screen(bone_pos)
                if screen:
                    bone_screen[name] = screen

        connections = [
            ("head", "neck"), ("neck", "spine"), ("spine", "pelvis"),
            ("neck", "left_shoulder"), ("left_shoulder", "left_elbow"), ("left_elbow", "left_hand"),
            ("neck", "right_shoulder"), ("right_shoulder", "right_elbow"), ("right_elbow", "right_hand"),
            ("pelvis", "left_hip"), ("left_hip", "left_knee"), ("left_knee", "left_foot"),
            ("pelvis", "right_hip"), ("right_hip", "right_knee"), ("right_knee", "right_foot")
        ]

        if self.config["draw_skeleton"]:
            pen = QtGui.QPen(QtGui.QColor(255, 255, 255, 255), 3)
            pen.setCosmetic(True) 

            for a, b in connections:
                if a in bone_screen and b in bone_screen:
                    line = QtWidgets.QGraphicsLineItem(*bone_screen[a], *bone_screen[b])
                    line.setPen(pen)
                    self.scene.addItem(line)

        if self.config["draw_head"] and "head" in bone_screen:
            self._draw_head_circle(bone_screen["head"], entity.team == self.esp.local_player.team)


    def _draw_head_circle(self, head_pos, is_teammate):
        x, y = head_pos
        radius = 5
        circle = QtWidgets.QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
        if is_teammate:
            circle.setPen(QtGui.QPen(QtGui.QColor(0, 255, 0), 1.5))
            circle.setBrush(QtGui.QBrush(QtGui.QColor(0, 255, 0, 100)))
        else:
            circle.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0), 1.5))
            circle.setBrush(QtGui.QBrush(QtGui.QColor(255, 0, 0, 100)))
        self.scene.addItem(circle)


    def _get_health_color(self, health):
        if health > 75:
            return QtGui.QColor(0, 255, 0, 180)
        elif health > 50:
            return QtGui.QColor(255, 255, 0, 180)
        elif health > 25:
            return QtGui.QColor(255, 165, 0, 180)
        return QtGui.QColor(255, 0, 0, 180)


    def _get_bone_position(self, entity, bone_index):
        try:
            scene_node = self.esp.pm.read_ulonglong(entity.pawn + Offsets.m_pGameSceneNode)
            bone_array = self.esp.pm.read_ulonglong(scene_node + Offsets.m_pBoneArray)
            return tuple(self.esp.pm.read_float(bone_array + bone_index * 32 + i * 4) for i in range(3))
        except Exception:
            return None


    def _world_to_screen(self, pos):
        try:
            matrix = [self.esp.pm.read_float(self.esp.client + Offsets.dwViewMatrix + i * 4) for i in range(16)]
            
            x = matrix[0] * pos[0] + matrix[1] * pos[1] + matrix[2] * pos[2] + matrix[3]
            y = matrix[4] * pos[0] + matrix[5] * pos[1] + matrix[6] * pos[2] + matrix[7]
            w = matrix[12] * pos[0] + matrix[13] * pos[1] + matrix[14] * pos[2] + matrix[15]
            
            if w < 0.01:
                return None
                
            inv_w = 1.0 / w
            return (
                self.window_size[0] / 2 * (1 + x * inv_w),
                self.window_size[1] / 2 * (1 - y * inv_w)
            )
        except Exception:
            return None


    def _calculate_distance(self, point1, point2):
        x1, y1, z1 = point1
        x2, y2, z2 = point2
        
        dx = x2 - x1
        dy = y2 - y1
        dz = z2 - z1
        
        distance = (dx * dx + dy * dy + dz * dz) ** 0.5
        return f"{distance:.0f}m"


    def _is_window_focused(self, title):
        hwnd = win32gui.FindWindow(None, title)
        return hwnd and win32gui.GetForegroundWindow() == hwnd


class ESPOverlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.esp = ESP()
        if not self.esp.initialize():
            sys.exit("[Overlay] Failed to initialize ESP")

        self.window_size = self._get_game_window_size()
        if not self.window_size[0]:
            sys.exit("[Overlay] Could not find CS2 window")

        self.config = Config(Path(__name__).parent / "options.json")
        self.renderer = OverlayRenderer(self.esp, self.config, self.window_size)
        self.menu = OverlayMenu(self.config, self)
        
        self.menu_visible = False
        self.esp_enabled = True
        self._setup_overlay_window()
        self._setup_graphics()
        self._setup_timers()


    def _setup_overlay_window(self):
        self.setGeometry(0, 0, *self.window_size)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE, win32gui.GetWindowLong(self.winId(), win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT)

        try:
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.winId()), 0x00000011)
        except Exception as e:
            print(f"[Overlay] Failed to set stream-proof: {e}")


    def _setup_graphics(self):
        self.view = QGraphicsView(self.renderer.scene, self)
        self.view.setGeometry(0, 0, *self.window_size)
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.view.setSceneRect(0, 0, *self.window_size)


    def _setup_timers(self):
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self._update_overlay)
        timer.start(16)

        keybind_timer = QtCore.QTimer(self)
        keybind_timer.timeout.connect(self._check_toggle_keybind)
        keybind_timer.start(100)

        key_timer = QtCore.QTimer(self)
        key_timer.timeout.connect(self._check_insert_key)
        key_timer.start(100)


    def _update_overlay(self):
        if self.esp_enabled:
            self.renderer.update()
        else:
            self.renderer.scene.clear()


    def _check_insert_key(self):
        VK_INSERT = 0x2D
        if win32api.GetAsyncKeyState(VK_INSERT) & 0x8000:
            if self._is_window_focused(title="Counter-Strike 2") or self._is_window_focused(hwnd=int(self.menu.winId())):
                if not hasattr(self, "_insert_pressed") or not self._insert_pressed:
                    self._toggle_menu()
                    self._insert_pressed = True
        else:
            self._insert_pressed = False


    def _check_toggle_keybind(self):
        if not self._is_window_focused(title="Counter-Strike 2"):
            return
        
        key_name = self.config["toggle_keybind"]
        if not key_name:
            return
        
        key_sequence = QtGui.QKeySequence(key_name)
        if key_sequence.isEmpty():
            return
        
        qt_key = key_sequence[0]
        windows_vk = self._qt_key_to_vk(qt_key)
        
        if windows_vk and win32api.GetAsyncKeyState(windows_vk) & 0x8000:
            if not hasattr(self, "_toggle_key_pressed") or not self._toggle_key_pressed:
                self._toggle_key_pressed = True
                self.esp_enabled = not self.esp_enabled
                self.menu.set_esp_state(self.esp_enabled)
        else:
            self._toggle_key_pressed = False


    def _qt_key_to_vk(self, qt_key):
        key = qt_key.key()
        
        if key >= QtCore.Qt.Key_F1 and key <= QtCore.Qt.Key_F24:
            return win32con.VK_F1 + (key - QtCore.Qt.Key_F1)
        elif key == QtCore.Qt.Key_Insert:
            return win32con.VK_INSERT
        elif key == QtCore.Qt.Key_Delete:
            return win32con.VK_DELETE
        elif key == QtCore.Qt.Key_Home:
            return win32con.VK_HOME
        elif key == QtCore.Qt.Key_End:
            return win32con.VK_END
        elif key == QtCore.Qt.Key_PageUp:
            return win32con.VK_PRIOR
        elif key == QtCore.Qt.Key_PageDown:
            return win32con.VK_NEXT
        elif key >= QtCore.Qt.Key_A and key <= QtCore.Qt.Key_Z:
            return ord(chr(key).upper())
        elif key >= QtCore.Qt.Key_0 and key <= QtCore.Qt.Key_9:
            return ord(chr(key))
        
        return None


    def _toggle_menu(self):
        self.menu_visible = not self.menu_visible
        self.menu.setVisible(self.menu_visible)

        ex_style = win32gui.GetWindowLong(self.winId(), win32con.GWL_EXSTYLE)

        if self.menu_visible:
            screen_width = self.window_size[0]
            menu_width = self.menu.width()
            self.menu.move(screen_width - menu_width - 40, 40)
            
            win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE, ex_style & ~win32con.WS_EX_TRANSPARENT)

            shell = win32com.client.Dispatch("WScript.Shell")
            shell.SendKeys('%')
            win32gui.SetForegroundWindow(int(self.menu.winId()))

            menu_geom = self.menu.frameGeometry()
            x = menu_geom.left() + menu_geom.width() // 2
            y = menu_geom.top() + menu_geom.height() // 2
            win32api.SetCursorPos((x, y))
        else:
            win32gui.SetWindowLong(self.winId(), win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_TRANSPARENT)
            hwnd_game = win32gui.FindWindow(None, "Counter-Strike 2")
            if hwnd_game:
                win32gui.SetForegroundWindow(hwnd_game)


    def _get_game_window_size(self):
        hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        if hwnd:
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            return (right - left, bottom - top)
        return (None, None)


    def _is_window_focused(self, title=None, hwnd=None):
        if title:
            hwnd = win32gui.FindWindow(None, title)
        elif hwnd is None:
            return False
        return hwnd and win32gui.GetForegroundWindow() == hwnd


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    overlay = ESPOverlay()
    overlay.show()
    sys.exit(app.exec())