import json
import math
import os
import time
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import mediapipe as mp
import numpy as np
import qrcode
from PIL import Image, ImageDraw, ImageFont

# ⭐ INTEGRACIÓN NASA POWER + EONET
from nasa_integration import NASADataFetcher
NASA_API_KEY = os.getenv("NASA_API_KEY", "")


ROOT = Path(__file__).resolve().parent
POINTS_FILE = ROOT / "data" / "points.json"
MODEL_DIR = ROOT / "models"
HAND_MODEL_FILE = MODEL_DIR / "hand_landmarker.task"
HAND_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MIN_MODEL_SIZE_BYTES = 1_000_000
BACKGROUND_IMAGE_FILE = ROOT / "assets" / "images" / "cordillera_blanca.jpg"
WELCOME_ICON_HAND_FILE = ROOT / "assets" / "images" / "icon_hand.png"
WELCOME_ICON_POINT_FILE = ROOT / "assets" / "images" / "icon_point.png"
DESTINATIONS_DIR = ROOT / "assets" / "destinations"
FONT_TITLE_FILE = ROOT / "assets" / "fonts" / "Sora-SemiBold.ttf"
FONT_BODY_FILE = ROOT / "assets" / "fonts" / "Inter-Regular.ttf"
FONT_BODY_BOLD_FILE = ROOT / "assets" / "fonts" / "Inter-SemiBold.ttf"
FONT_TITLE_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/sora/Sora%5Bwght%5D.ttf"
FONT_BODY_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"
FONT_BODY_BOLD_URL = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"
FONT_BOLD_FILE = FONT_BODY_BOLD_FILE
FONT_REG_FILE = FONT_BODY_FILE
WELCOME_ICON_HAND_URL = "https://cdn.jsdelivr.net/gh/hfg-gmuend/openmoji@main/color/618x618/270B.png"
WELCOME_ICON_POINT_URL = "https://cdn.jsdelivr.net/gh/hfg-gmuend/openmoji@main/color/618x618/1F446.png"

WINDOW_NAME = "Presenta | Cordillera Blanca"
CANVAS_W = 1280
CANVAS_H = 720
MAP_W = 860
CARD_W = CANVAS_W - MAP_W
RIGHT_PANEL_X = MAP_W + 20
RIGHT_PANEL_MARGIN = 20
PREVIEW_W = 280
PREVIEW_H = 157
CARD_WEBCAM_GAP = 24
LEFT_WEBCAM_X = 28
LEFT_WEBCAM_Y = CANVAS_H - PREVIEW_H - RIGHT_PANEL_MARGIN

BLACK = (13, 13, 13)
GOLD = (76, 168, 201)
WHITE = (245, 245, 245)
GRAY = (136, 136, 136)
CARD_BLACK = (8, 8, 8)
SOFT_WHITE = (220, 220, 220)

HOVER_TIME_SEC = 0.22
DETAIL_ACTION_HOVER_SEC = 0.45
POINTER_SMOOTHING = 0.28
POINTER_GAIN_X = 1.25
POINTER_GAIN_Y = 1.25
MIN_DET_CONF = 0.6
MIN_TRACK_CONF = 0.55
IDLE_TIMEOUT_SEC = 30.0
WELCOME_FADE_SEC = 0.5

current_screen = "welcome"
active_destination = None
btn_ver_mas_rect = None
btn_hover_timer = 0.0
btn_flash_timer = 0.0
btn_active_point_id = None
detail_video_cap = None
detail_media_destination_id = None
detail_transition_start = 0.0
detail_back_btn_rect = None
detail_back_hover_timer = 0.0
detail_back_flash_timer = 0.0
detail_realtime_btn_rect = None
detail_realtime_hover_timer = 0.0
detail_realtime_flash_timer = 0.0


class GestureMapApp:
    def __init__(self) -> None:
        self.points = self._load_points()
        self.capture = cv2.VideoCapture(0)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)

        self.hand_backend: str = ""
        self.hands = None
        self.hand_landmarker = None
        self._setup_hand_tracker()

        self.pointer: Optional[Tuple[int, int]] = None
        self.raw_pointer: Optional[Tuple[int, int]] = None
        self.hover_candidate: Optional[str] = None
        self.hover_start: float = 0.0
        self.active_point_id: Optional[str] = None
        self.card_anim_t: float = 0.0
        self.card_target_visible: bool = False
        self.debug = True
        self.frame_count = 0
        self.hand_visible = False
        self.idle_timer = 0.0
        self.map_fade_start = 0.0
        self.welcome_btn_hover_timer = 0.0

        self._ensure_cdn_fonts()

        self.background = self._load_background_image()
        self.font_title = self._load_font(FONT_TITLE_FILE, 34)
        self.font_subtitle = self._load_font(FONT_BODY_FILE, 18)
        self.font_point = self._load_font(FONT_BODY_FILE, 14)
        self.font_card_title = self._load_font(FONT_TITLE_FILE, 28)
        self.font_card_subtitle = self._load_font(FONT_BODY_BOLD_FILE, 17)
        self.font_card_body = self._load_font(FONT_BODY_FILE, 17)
        self.font_card_desc = self._load_font(FONT_BODY_FILE, 15)
        self.font_hud = self._load_font(FONT_BODY_FILE, 13)
        self.font_welcome_title = self._load_font(FONT_TITLE_FILE, 72)
        self.font_welcome_subtitle = self._load_font(FONT_BODY_FILE, 32)
        self.font_welcome_instruction = self._load_font(FONT_BODY_FILE, 44)
        self.font_welcome_button = self._load_font(FONT_BODY_BOLD_FILE, 28)
        self.welcome_icons: Dict[str, Optional[Image.Image]] = {"hand": None, "point": None}
        self._ensure_welcome_icons()

        self.last_frame_time = time.time()
        self.card_render: Optional[Tuple[int, int, int, int, Dict]] = None
        self.webcam_rect: Optional[Tuple[int, int, int, int]] = None
        self.destination_image_cache: Dict[str, np.ndarray] = {}
        self.detail_qr_cache: Dict[str, np.ndarray] = {}
        self.detail_fallback_cache: Dict[str, np.ndarray] = {}
        self.sat_cache = {}
        self.sat_pending = set()

        # ⭐ INTEGRACIÓN NASA
        self.nasa_fetcher = NASADataFetcher(NASA_API_KEY)
        self.nasa_data: Dict[str, Dict] = {}
        self.realtime_requested_id: Optional[str] = None

    def _load_points(self) -> List[Dict]:
        with POINTS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)


    def _ensure_cdn_fonts(self) -> None:
        FONT_TITLE_FILE.parent.mkdir(parents=True, exist_ok=True)
        font_sources = [
            (FONT_TITLE_FILE, FONT_TITLE_URL),
            (FONT_BODY_FILE, FONT_BODY_URL),
            (FONT_BODY_BOLD_FILE, FONT_BODY_BOLD_URL),
        ]

        for font_file, url in font_sources:
            if font_file.exists() and font_file.stat().st_size > 10_000:
                continue
            try:
                urllib.request.urlretrieve(url, str(font_file))
            except Exception:
                pass

    def run(self) -> None:
        if not self.capture.isOpened():
            raise RuntimeError("No se pudo abrir la webcam.")

        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW_NAME, CANVAS_W, CANVAS_H)

        while True:
            ok, frame = self.capture.read()
            if not ok:
                break

            frame = cv2.flip(frame, 1)
            self.frame_count += 1
            now = time.time()
            dt = max(1e-3, now - self.last_frame_time)
            self.last_frame_time = now

            self._update_pointer_from_frame(frame)
            self._update_interaction_logic(now, dt)

            # ⭐ ACTUALIZAR CACHE LOCAL DE DATOS NASA
            current_destination_id = self.active_point_id
            if current_destination_id is None and active_destination is not None:
                current_destination_id = active_destination.get("id")

            if current_destination_id:
                nasa_data = self.nasa_fetcher.get_destination_data(current_destination_id)
                if nasa_data:
                    self.nasa_data[current_destination_id] = nasa_data
                    if self.debug:
                        print(f"[NASA] ✅ Datos recibidos para {current_destination_id}: T={nasa_data.get('temperature')}°C, Fires={len(nasa_data.get('fires', []))}")

            canvas = self._draw_scene(frame, dt)
            cv2.imshow(WINDOW_NAME, canvas)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord("q")):
                break
            if key in (ord("d"),):
                self.debug = not self.debug

        self.capture.release()
        if self.hand_backend == "legacy" and self.hands is not None:
            self.hands.close()
        if self.hand_backend == "tasks" and self.hand_landmarker is not None:
            self.hand_landmarker.close()
        self._release_detail_media()
        cv2.destroyAllWindows()

    def _setup_hand_tracker(self) -> None:
        if hasattr(mp, "solutions"):
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                max_num_hands=1,
                min_detection_confidence=MIN_DET_CONF,
                min_tracking_confidence=MIN_TRACK_CONF,
            )
            self.hand_backend = "legacy"
            return

        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        self._ensure_task_model()

        options = self._build_tasks_options(mp_python, vision)
        try:
            self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
        except (FileNotFoundError, RuntimeError):
            # If model file got truncated/corrupted, download a fresh copy once.
            self._ensure_task_model(force=True)
            options = self._build_tasks_options(mp_python, vision)
            self.hand_landmarker = vision.HandLandmarker.create_from_options(options)
        self.hand_backend = "tasks"

    def _build_tasks_options(self, mp_python, vision):
        model_bytes = HAND_MODEL_FILE.read_bytes()
        return vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=model_bytes),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,
            min_hand_detection_confidence=MIN_DET_CONF,
            min_hand_presence_confidence=MIN_DET_CONF,
            min_tracking_confidence=MIN_TRACK_CONF,
        )

    def _ensure_task_model(self, force: bool = False) -> None:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        needs_download = force or (not HAND_MODEL_FILE.exists())

        if not needs_download and HAND_MODEL_FILE.stat().st_size < MIN_MODEL_SIZE_BYTES:
            needs_download = True

        if not needs_download:
            return

        try:
            urllib.request.urlretrieve(HAND_MODEL_URL, str(HAND_MODEL_FILE))
        except Exception as exc:
            raise RuntimeError(
                "No se pudo descargar el modelo hand_landmarker.task. "
                "Conectate a internet una vez o copia el archivo en models/hand_landmarker.task"
            ) from exc

    def _ensure_welcome_icons(self) -> None:
        icon_sources = [
            ("hand", WELCOME_ICON_HAND_FILE, WELCOME_ICON_HAND_URL),
            ("point", WELCOME_ICON_POINT_FILE, WELCOME_ICON_POINT_URL),
        ]

        for key, icon_file, url in icon_sources:
            if not icon_file.exists():
                try:
                    urllib.request.urlretrieve(url, str(icon_file))
                except Exception:
                    pass

            if icon_file.exists():
                try:
                    self.welcome_icons[key] = Image.open(icon_file).convert("RGBA")
                except Exception:
                    self.welcome_icons[key] = None

    def _get_welcome_icon(self, key: str, size: int) -> Optional[Image.Image]:
        base_icon = self.welcome_icons.get(key)
        if base_icon is None:
            return None
        return base_icon.resize((size, size), Image.LANCZOS)

    def _update_pointer_from_frame(self, frame: np.ndarray) -> None:
        global current_screen

        tip = self._detect_index_tip(frame)
        self.hand_visible = tip is not None
        if tip is None:
            self.raw_pointer = None
            self.pointer = None
            return

        tip_x, tip_y = tip
        fx, fy = frame.shape[1], frame.shape[0]
        x_cam = int(np.clip(tip_x * fx, 0, fx - 1))
        y_cam = int(np.clip(tip_y * fy, 0, fy - 1))

        left_bound = 40
        right_bound = CANVAS_W - 40 if current_screen in ("detail", "realtime") else MAP_W - 40
        top_bound = 50
        bottom_bound = CANVAS_H - 40
        map_x = int(np.interp(x_cam, [0, fx], [left_bound, right_bound]))
        map_y = int(np.interp(y_cam, [0, fy], [top_bound, bottom_bound]))
        center_x = (left_bound + right_bound) / 2.0
        center_y = (top_bound + bottom_bound) / 2.0
        map_x = int(center_x + (map_x - center_x) * POINTER_GAIN_X)
        map_y = int(center_y + (map_y - center_y) * POINTER_GAIN_Y)
        map_x = int(np.clip(map_x, left_bound, right_bound))
        map_y = int(np.clip(map_y, top_bound, bottom_bound))
        self.raw_pointer = (map_x, map_y)

        if self.pointer is None:
            self.pointer = self.raw_pointer
        else:
            dx = map_x - self.pointer[0]
            dy = map_y - self.pointer[1]
            dist = math.hypot(dx, dy)
            alpha = POINTER_SMOOTHING + min(0.25, dist / 800.0)
            alpha = min(0.6, alpha)
            px = int((1 - alpha) * self.pointer[0] + alpha * map_x)
            py = int((1 - alpha) * self.pointer[1] + alpha * map_y)
            self.pointer = (px, py)

    def _detect_index_tip(self, frame: np.ndarray) -> Optional[Tuple[float, float]]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self.hand_backend == "legacy":
            results = self.hands.process(rgb)
            if not results.multi_hand_landmarks:
                return None
            landmarks = results.multi_hand_landmarks[0].landmark
            if not self._is_open_hand_gesture(landmarks):
                return None
            tip = landmarks[8]
            return (tip.x, tip.y)

        if self.hand_backend == "tasks":
            from mediapipe.tasks.python import vision

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(time.time() * 1000)
            result = self.hand_landmarker.detect_for_video(mp_image, timestamp_ms)
            if not result.hand_landmarks:
                return None
            landmarks = result.hand_landmarks[0]
            if not self._is_open_hand_gesture(landmarks):
                return None
            tip = landmarks[8]
            return (tip.x, tip.y)

        return None

    def _is_open_hand_gesture(self, landmarks) -> bool:
        def finger_angle(tip_idx: int, pip_idx: int, mcp_idx: int) -> Optional[float]:
            tip = landmarks[tip_idx]
            pip = landmarks[pip_idx]
            mcp = landmarks[mcp_idx]

            v1x = tip.x - pip.x
            v1y = tip.y - pip.y
            v1z = tip.z - pip.z
            v2x = mcp.x - pip.x
            v2y = mcp.y - pip.y
            v2z = mcp.z - pip.z
            n1 = math.sqrt(v1x * v1x + v1y * v1y + v1z * v1z)
            n2 = math.sqrt(v2x * v2x + v2y * v2y + v2z * v2z)
            if n1 < 1e-6 or n2 < 1e-6:
                return None
            cos_angle = (v1x * v2x + v1y * v2y + v1z * v2z) / (n1 * n2)
            cos_angle = max(-1.0, min(1.0, cos_angle))
            return math.degrees(math.acos(cos_angle))

        try:
            thumb_angle = finger_angle(4, 3, 2)
            index_angle = finger_angle(8, 6, 5)
            middle_angle = finger_angle(12, 10, 9)
            ring_angle = finger_angle(16, 14, 13)
            pinky_angle = finger_angle(20, 18, 17)

            if None not in (thumb_angle, index_angle, middle_angle, ring_angle, pinky_angle):
                thumb_extended = thumb_angle >= 150.0
                index_extended = index_angle >= 160.0
                middle_extended = middle_angle >= 160.0
                ring_extended = ring_angle >= 160.0
                pinky_extended = pinky_angle >= 160.0
                return thumb_extended and index_extended and middle_extended and ring_extended and pinky_extended

            index_tip = landmarks[8]
            index_pip = landmarks[6]
            middle_tip = landmarks[12]
            middle_pip = landmarks[10]
            ring_tip = landmarks[16]
            ring_pip = landmarks[14]
            pinky_tip = landmarks[20]
            pinky_pip = landmarks[18]
            thumb_tip = landmarks[4]
            thumb_ip = landmarks[3]

            index_extended = index_tip.y < index_pip.y - 0.012
            middle_extended = middle_tip.y < middle_pip.y - 0.012
            ring_extended = ring_tip.y < ring_pip.y - 0.012
            pinky_extended = pinky_tip.y < pinky_pip.y - 0.012
            thumb_extended = abs(thumb_tip.x - thumb_ip.x) > 0.02
            return (
                thumb_extended
                and index_extended
                and middle_extended
                and ring_extended
                and pinky_extended
            )
        except Exception:
            return False

    def _update_interaction_logic(self, now: float, dt: float) -> None:
        global current_screen, active_destination, btn_ver_mas_rect, btn_hover_timer, btn_flash_timer, btn_active_point_id
        global detail_transition_start, detail_back_btn_rect, detail_back_hover_timer, detail_back_flash_timer
        global detail_realtime_btn_rect, detail_realtime_hover_timer, detail_realtime_flash_timer

        if self.hand_visible:
            self.idle_timer = 0.0
        elif current_screen == "map":
            self.idle_timer += dt
            if self.idle_timer >= IDLE_TIMEOUT_SEC:
                current_screen = "welcome"
                self.idle_timer = 0.0
                self.map_fade_start = 0.0
                self.welcome_btn_hover_timer = 0.0
                self.hover_candidate = None
                self.active_point_id = None
                self.card_target_visible = False
                self.card_anim_t = 0.0
                btn_active_point_id = None
                btn_ver_mas_rect = None
                active_destination = None
                btn_hover_timer = 0.0
                btn_flash_timer = 0.0
                return

        if current_screen == "welcome":
            self.hover_candidate = None
            self.active_point_id = None
            self.card_target_visible = False
            self.card_anim_t = 0.0
            btn_active_point_id = None
            btn_ver_mas_rect = None
            active_destination = None
            btn_hover_timer = 0.0
            btn_flash_timer = 0.0

            bx, by, bw, bh = self._welcome_start_button_rect()
            pointer_over_welcome_button = False
            if self.pointer is not None:
                px, py = self.pointer
                pointer_over_welcome_button = bx <= px <= bx + bw and by <= py <= by + bh

            if pointer_over_welcome_button:
                self.welcome_btn_hover_timer = min(1.5, self.welcome_btn_hover_timer + dt)
                if self.welcome_btn_hover_timer >= 1.5:
                    current_screen = "map"
                    self.map_fade_start = now
                    self.welcome_btn_hover_timer = 0.0
            else:
                self.welcome_btn_hover_timer = 0.0
            return

        hovered_id = self._find_hovered_point_id()

        if hovered_id != self.hover_candidate:
            self.hover_candidate = hovered_id
            self.hover_start = now
        else:
            if hovered_id and (now - self.hover_start) >= HOVER_TIME_SEC:
                if self.active_point_id != hovered_id:
                    self.active_point_id = hovered_id
                    self.card_target_visible = True

                    # ⭐ DISPARAR PETICIÓN ASINCRÓNICA A NASA
                    point_data = next((p for p in self.points if p["id"] == hovered_id), None)
                    if point_data and "latitude" in point_data and "longitude" in point_data:
                        print(f"[NASA] 🚀 Fetch disparado para {point_data['name']} ({hovered_id})")
                        self.nasa_fetcher.fetch_destination_data_async(
                            destination_id=hovered_id,
                            latitude=point_data["latitude"],
                            longitude=point_data["longitude"],
                            radius_km=50
                        )

                btn_active_point_id = hovered_id

        if hovered_id is None and self.active_point_id is not None:
            if self.pointer is None:
                self.card_target_visible = False

        selected_button_point = next((p for p in self.points if p["id"] == btn_active_point_id), None)
        pointer_over_button = False
        if self.pointer is not None and selected_button_point is not None:
            bx, by, bw, bh = self._floating_button_rect(selected_button_point)
            px, py = self.pointer
            pointer_over_button = bx <= px <= bx + bw and by <= py <= by + bh
            btn_ver_mas_rect = (bx, by, bw, bh)
        else:
            btn_ver_mas_rect = None

        if current_screen == "detail":
            btn_hover_timer = 0.0
            btn_ver_mas_rect = None
            if active_destination is not None:
                detail_realtime_btn_rect = self._detail_realtime_button_rect(active_destination)
            else:
                detail_realtime_btn_rect = None

            pointer_over_back = False
            if self.pointer is not None and detail_back_btn_rect is not None:
                bx, by, bw, bh = detail_back_btn_rect
                px, py = self.pointer
                pointer_over_back = bx <= px <= bx + bw and by <= py <= by + bh

            if detail_back_flash_timer > 0.0:
                detail_back_flash_timer = max(0.0, detail_back_flash_timer - dt)
                if detail_back_flash_timer <= 0.0:
                    current_screen = "map"
                    active_destination = None
                    detail_back_hover_timer = 0.0
                    detail_back_btn_rect = None
                    detail_transition_start = 0.0
                    self._release_detail_media()
                return

            if pointer_over_back:
                detail_back_hover_timer = min(1.5, detail_back_hover_timer + dt)
                if detail_back_hover_timer >= DETAIL_ACTION_HOVER_SEC:
                    detail_back_flash_timer = 0.08
            else:
                detail_back_hover_timer = 0.0

            pointer_over_realtime = False
            if self.pointer is not None and detail_realtime_btn_rect is not None:
                bx, by, bw, bh = detail_realtime_btn_rect
                px, py = self.pointer
                pointer_over_realtime = bx <= px <= bx + bw and by <= py <= by + bh

            if pointer_over_realtime:
                detail_realtime_hover_timer = min(DETAIL_ACTION_HOVER_SEC, detail_realtime_hover_timer + dt)
                if detail_realtime_hover_timer >= DETAIL_ACTION_HOVER_SEC:
                    detail_realtime_flash_timer = 0.08
            else:
                detail_realtime_hover_timer = 0.0

            if detail_realtime_flash_timer > 0.0:
                detail_realtime_flash_timer = max(0.0, detail_realtime_flash_timer - dt)
                if detail_realtime_flash_timer <= 0.0:
                    if active_destination is not None and active_destination.get("id") != self.realtime_requested_id:
                        point_data = next((p for p in self.points if p["id"] == active_destination.get("id")), None)
                        if point_data and "latitude" in point_data and "longitude" in point_data:
                            self.nasa_fetcher.fetch_destination_data_async(
                                destination_id=point_data["id"],
                                latitude=point_data["latitude"],
                                longitude=point_data["longitude"],
                                radius_km=50,
                            )
                            self.realtime_requested_id = point_data["id"]
                    current_screen = "realtime"
                    detail_transition_start = now
                    detail_realtime_hover_timer = 0.0
                    detail_realtime_btn_rect = None
                return
            return

        if current_screen == "realtime":
            btn_hover_timer = 0.0
            btn_ver_mas_rect = None
            detail_realtime_btn_rect = None

            pointer_over_back = False
            if self.pointer is not None and detail_back_btn_rect is not None:
                bx, by, bw, bh = detail_back_btn_rect
                px, py = self.pointer
                pointer_over_back = bx <= px <= bx + bw and by <= py <= by + bh

            if detail_back_flash_timer > 0.0:
                detail_back_flash_timer = max(0.0, detail_back_flash_timer - dt)
                if detail_back_flash_timer <= 0.0:
                    current_screen = "detail"
                    detail_back_hover_timer = 0.0
                    detail_back_btn_rect = None
                    detail_transition_start = 0.0
                return

            if pointer_over_back:
                detail_back_hover_timer = min(1.5, detail_back_hover_timer + dt)
                if detail_back_hover_timer >= DETAIL_ACTION_HOVER_SEC:
                    detail_back_flash_timer = 0.08
            else:
                detail_back_hover_timer = 0.0
            return

        if btn_active_point_id is None:
            btn_hover_timer = 0.0
            btn_flash_timer = 0.0
            if current_screen != "map":
                current_screen = "map"
            return

        if hovered_id is not None and hovered_id != btn_active_point_id:
            btn_hover_timer = 0.0
            btn_flash_timer = 0.0
            current_screen = "map"
            active_destination = None
            btn_active_point_id = None
            btn_ver_mas_rect = None
            detail_realtime_hover_timer = 0.0
            detail_realtime_flash_timer = 0.0
            return

        if btn_flash_timer > 0.0:
            btn_flash_timer = max(0.0, btn_flash_timer - dt)
            if btn_flash_timer <= 0.0:
                current_screen = "detail"
                detail_transition_start = now
                detail_back_hover_timer = 0.0
                detail_back_flash_timer = 0.0
                detail_realtime_hover_timer = 0.0
                detail_realtime_flash_timer = 0.0
            return

        if pointer_over_button:
            btn_hover_timer = min(1.5, btn_hover_timer + dt)
            if btn_hover_timer >= DETAIL_ACTION_HOVER_SEC and btn_flash_timer <= 0.0:
                active_destination = selected_button_point.copy() if selected_button_point is not None else None
                btn_flash_timer = 0.08
        else:
            btn_hover_timer = 0.0
            if hovered_id is None:
                btn_active_point_id = None
                btn_ver_mas_rect = None
                current_screen = "map"
                active_destination = None
                detail_realtime_hover_timer = 0.0
                detail_realtime_flash_timer = 0.0

        speed = 4.4
        if self.card_target_visible:
            self.card_anim_t = min(1.0, self.card_anim_t + speed * dt)
        else:
            self.card_anim_t = max(0.0, self.card_anim_t - speed * dt)
            if self.card_anim_t <= 0.02:
                self.active_point_id = None

    def _find_hovered_point_id(self) -> Optional[str]:
        if self.pointer is None:
            return None

        px, py = self.pointer
        for point in self.points:
            cx, cy = self._point_to_pixel(point)
            r = int(point.get("radius", 25))
            if math.hypot(px - cx, py - cy) <= r:
                return point["id"]
        return None

    def _point_to_pixel(self, point: Dict) -> Tuple[int, int]:
        x = int(point["x"] * MAP_W)
        y = int(point["y"] * CANVAS_H)
        return x, y

    def _draw_scene(self, frame: np.ndarray, dt: float) -> np.ndarray:
        if current_screen == "welcome":
            return self.draw_welcome_screen(frame)

        if current_screen == "realtime":
            canvas = self.draw_realtime_dashboard(self.active_point_id, self.pointer)
            if self.debug:
                self._draw_debug(canvas, dt)
            return canvas

        if current_screen == "detail":
            canvas = self.draw_detail_screen(frame, active_destination, self.pointer)
            if self.debug:
                self._draw_debug(canvas, dt)
            return canvas

        canvas = self.background.copy()
        self._draw_background(canvas)
        self._draw_routes(canvas)
        self._draw_points(canvas)

        self.card_render = None
        self.webcam_rect = None
        self._draw_floating_button(canvas)
        self._draw_pointer(canvas)
        self._draw_card(canvas)
        self._draw_webcam_preview(canvas, frame)

        if self.debug:
            self._draw_debug(canvas, dt)

        canvas = self._draw_text_layers(canvas, dt)

        if self.map_fade_start > 0.0:
            elapsed = max(0.0, time.time() - self.map_fade_start)
            alpha = max(0.0, 1.0 - (elapsed / WELCOME_FADE_SEC))
            if alpha > 0.0:
                overlay = np.zeros_like(canvas)
                canvas = cv2.addWeighted(overlay, alpha, canvas, 1.0 - alpha, 0)
            else:
                self.map_fade_start = 0.0

        return canvas

    @staticmethod
    def _welcome_start_button_rect() -> Tuple[int, int, int, int]:
        bw, bh = 220, 55
        bx = (CANVAS_W - bw) // 2
        by = int(CANVAS_H * 0.70) - (bh // 2)
        return (bx, by, bw, bh)

    def draw_welcome_screen(self, frame: np.ndarray) -> np.ndarray:
        canvas = self.background.copy()

        # Keep a 65% black overlay for readability.
        dark_overlay = np.zeros_like(canvas)
        canvas = cv2.addWeighted(dark_overlay, 0.65, canvas, 0.35, 0)

        self.webcam_rect = None
        self._draw_webcam_preview(canvas, frame)

        img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(img, "RGBA")

        gold_rgba = (201, 168, 76, 255)
        white_rgba = (245, 245, 245, 255)

        def centered_text(text: str, font, y: int, fill: Tuple[int, int, int, int]) -> int:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(((CANVAS_W - tw) // 2, y), text, font=font, fill=fill)
            return th

        title_y = int(CANVAS_H * 0.20)
        title_h = centered_text("CORDILLERA BLANCA", self.font_welcome_title, title_y, white_rgba)

        subtitle_y = title_y + title_h + 20
        subtitle_h = centered_text("Explorador Gestual · Ancash, Perú", self.font_welcome_subtitle, subtitle_y, gold_rgba)

        sep_y = subtitle_y + subtitle_h + 25
        sep_w = 60
        draw.line(
            ((CANVAS_W - sep_w) // 2, sep_y, (CANVAS_W + sep_w) // 2, sep_y),
            fill=gold_rgba,
            width=3,
        )

        instruction_y = int(CANVAS_H * 0.55)
        icon_size = 52
        gap = 14
        arrow_text = "→"
        label_1 = "Muestra tu mano"
        label_2 = "Apunta al botón"

        hand_icon = self._get_welcome_icon("hand", icon_size)
        point_icon = self._get_welcome_icon("point", icon_size)

        b1 = draw.textbbox((0, 0), label_1, font=self.font_welcome_instruction)
        b2 = draw.textbbox((0, 0), label_2, font=self.font_welcome_instruction)
        ba = draw.textbbox((0, 0), arrow_text, font=self.font_welcome_instruction)
        t1_w = b1[2] - b1[0]
        t2_w = b2[2] - b2[0]
        arrow_w = ba[2] - ba[0]

        hand_w = icon_size if hand_icon is not None else 0
        point_w = icon_size if point_icon is not None else 0

        total_w = hand_w + gap + t1_w + (gap * 2) + arrow_w + (gap * 2) + point_w + gap + t2_w
        x = (CANVAS_W - total_w) // 2

        if hand_icon is not None:
            img.alpha_composite(hand_icon, dest=(x, instruction_y - 6))
            x += icon_size + gap
        else:
            draw.text((x, instruction_y), "🖐", font=self.font_welcome_instruction, fill=white_rgba)
            fb = draw.textbbox((0, 0), "🖐", font=self.font_welcome_instruction)
            x += (fb[2] - fb[0]) + gap

        draw.text((x, instruction_y), label_1, font=self.font_welcome_instruction, fill=white_rgba)
        x += t1_w + (gap * 2)

        draw.text((x, instruction_y), arrow_text, font=self.font_welcome_instruction, fill=white_rgba)
        x += arrow_w + (gap * 2)

        if point_icon is not None:
            img.alpha_composite(point_icon, dest=(x, instruction_y - 6))
            x += icon_size + gap
        else:
            draw.text((x, instruction_y), "☝️", font=self.font_welcome_instruction, fill=white_rgba)
            fb = draw.textbbox((0, 0), "☝️", font=self.font_welcome_instruction)
            x += (fb[2] - fb[0]) + gap

        draw.text((x, instruction_y), label_2, font=self.font_welcome_instruction, fill=white_rgba)

        bx, by, bw, bh = self._welcome_start_button_rect()
        progress = max(0.0, min(1.0, self.welcome_btn_hover_timer / 1.5))
        draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=10, fill=gold_rgba)
        if progress > 0.0:
            fill_w = max(1, int(bw * progress))
            draw.rounded_rectangle((bx, by, bx + fill_w, by + bh), radius=10, fill=(245, 221, 148, 150))
        draw.rounded_rectangle((bx, by, bx + bw, by + bh), radius=10, outline=(0, 0, 0, 80), width=1)

        label = "▶ COMENZAR"
        label_bbox = draw.textbbox((0, 0), label, font=self.font_welcome_button)
        lw = label_bbox[2] - label_bbox[0]
        lh = label_bbox[3] - label_bbox[1]
        draw.text((bx + (bw - lw) // 2, by + (bh - lh) // 2 - 1), label, font=self.font_welcome_button, fill=(0, 0, 0, 255))

        canvas = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)
        self._draw_pointer(canvas)
        return canvas

    def _draw_background(self, canvas: np.ndarray) -> None:
        # Left section: keep photo and darken for legible overlays.
        left_overlay = canvas.copy()
        cv2.rectangle(left_overlay, (0, 0), (MAP_W, CANVAS_H), BLACK, -1)
        cv2.addWeighted(left_overlay, 0.44, canvas, 0.56, 0, canvas)

        # Right section: independent dark UI panel.
        panel_overlay = canvas.copy()
        cv2.rectangle(panel_overlay, (MAP_W, 0), (CANVAS_W, CANVAS_H), (10, 10, 10), -1)
        cv2.addWeighted(panel_overlay, 0.9, canvas, 0.1, 0, canvas)

        # Soft vertical gradient in right panel for depth.
        panel_w = CANVAS_W - MAP_W
        for ix in range(panel_w):
            t = ix / max(1, panel_w - 1)
            shade = int(8 + t * 14)
            x = MAP_W + ix
            canvas[:, x] = (shade, shade, shade)

        # Strong divider between sections.
        cv2.line(canvas, (MAP_W, 0), (MAP_W, CANVAS_H), GOLD, 1, cv2.LINE_AA)
        glow = canvas.copy()
        cv2.rectangle(glow, (MAP_W - 2, 0), (MAP_W + 2, CANVAS_H), GOLD, -1)
        cv2.addWeighted(glow, 0.08, canvas, 0.92, 0, canvas)

        # Cinematic vignette only on left section.
        vignette = np.zeros_like(canvas)
        cv2.circle(vignette, (MAP_W // 2, CANVAS_H // 2), 470, (35, 35, 35), -1, cv2.LINE_AA)
        vignette[:, MAP_W:] = 0
        cv2.addWeighted(vignette, 0.2, canvas, 0.8, 0, canvas)

    def _draw_routes(self, canvas: np.ndarray) -> None:
        route_color = (100, 125, 145)
        ordered = [self._point_to_pixel(p) for p in self.points]
        if len(ordered) >= 2:
            pts = np.array(ordered, np.int32)
            cv2.polylines(canvas, [pts], False, route_color, 2, cv2.LINE_AA)

            for i in range(0, len(ordered) - 1):
                p0 = ordered[i]
                p1 = ordered[i + 1]
                mid = ((p0[0] + p1[0]) // 2, (p0[1] + p1[1]) // 2)
                cv2.circle(canvas, mid, 2, GOLD, -1, cv2.LINE_AA)

    def _draw_points(self, canvas: np.ndarray) -> None:
        t = self.frame_count * 0.08

        for point in self.points:
            cx, cy = self._point_to_pixel(point)
            base_r = max(9, int(point.get("radius", 25) * 0.45))
            point_id = point["id"]
            is_active = point_id == self.active_point_id
            is_candidate = point_id == self.hover_candidate

            speed = 1.8 if is_active else 1.1
            pulse = 0.5 + 0.5 * math.sin(t * speed + cx * 0.011)
            ring_boost = 9 if is_candidate else 0

            for i, alpha in enumerate([0.24, 0.16, 0.1]):
                radius = int(base_r + i * 10 + pulse * (9 + i * 2) + ring_boost)
                self._draw_glow(canvas, (cx, cy), radius, GOLD, alpha)

            core_color = GOLD if (is_active or is_candidate) else WHITE
            core_radius = 4 if not is_active else 5
            cv2.circle(canvas, (cx, cy), core_radius + 2, (45, 45, 45), -1, cv2.LINE_AA)
            cv2.circle(canvas, (cx, cy), core_radius, core_color, -1, cv2.LINE_AA)

    def _draw_webcam_preview(self, canvas: np.ndarray, frame: np.ndarray) -> None:
        self._draw_webcam_preview_at(canvas, frame, LEFT_WEBCAM_X, LEFT_WEBCAM_Y)

    def _draw_webcam_preview_at(self, canvas: np.ndarray, frame: np.ndarray, x0: int, y0: int) -> None:
        preview_w = PREVIEW_W
        preview_h = PREVIEW_H
        x1, y1 = x0 + preview_w, y0 + preview_h
        self.webcam_rect = (x0, y0, x1, y1)

        self._draw_glass_panel(canvas, x0 - 10, y0 - 10, preview_w + 20, preview_h + 20, 18, alpha=0.35)
        preview = cv2.resize(frame, (preview_w, preview_h))
        self._paste_rounded(canvas, preview, x0, y0, preview_w, preview_h, 16)
        self._draw_rounded_border(canvas, x0, y0, preview_w, preview_h, 16, GOLD, 2)

    @staticmethod
    def _cover_crop(src: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
        src_h, src_w = src.shape[:2]
        if src_h <= 0 or src_w <= 0:
            return np.zeros((target_h, target_w, 3), dtype=np.uint8)

        scale = max(target_w / src_w, target_h / src_h)
        resized_w = max(target_w, int(math.ceil(src_w * scale)))
        resized_h = max(target_h, int(math.ceil(src_h * scale)))
        resized = cv2.resize(src, (resized_w, resized_h), interpolation=cv2.INTER_AREA)

        start_x = max(0, (resized_w - target_w) // 2)
        start_y = max(0, (resized_h - target_h) // 2)
        cropped = resized[start_y:start_y + target_h, start_x:start_x + target_w]
        if cropped.shape[0] != target_h or cropped.shape[1] != target_w:
            cropped = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)
        return cropped

    def _release_detail_media(self) -> None:
        global detail_video_cap, detail_media_destination_id

        if detail_video_cap is not None:
            detail_video_cap.release()
        detail_video_cap = None
        detail_media_destination_id = None

    def _load_detail_media(self, destination: Dict) -> None:
        global detail_video_cap, detail_media_destination_id

        destination_id = str(destination.get("id", ""))
        if destination_id == detail_media_destination_id:
            return

        self._release_detail_media()
        detail_media_destination_id = destination_id

        video_path = DESTINATIONS_DIR / f"{destination_id}.mp4"
        if video_path.exists():
            cap = cv2.VideoCapture(str(video_path))
            if cap.isOpened():
                detail_video_cap = cap
            else:
                cap.release()

    def _get_detail_visual(self, destination: Dict, width: int, height: int) -> np.ndarray:
        global detail_video_cap

        self._load_detail_media(destination)

        frame = None
        if detail_video_cap is not None:
            ok, frame = detail_video_cap.read()
            if not ok:
                detail_video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = detail_video_cap.read()
            if not ok:
                frame = None

        if frame is None:
            destination_id = str(destination.get("id", ""))
            if destination_id not in self.detail_fallback_cache:
                file_name = destination.get("image", f"{destination_id}.jpg")
                file_path = DESTINATIONS_DIR / file_name
                img = self._imread_unicode_safe(file_path)
                if img is None:
                    img = self._load_destination_image(destination)
                self.detail_fallback_cache[destination_id] = img
            frame = self.detail_fallback_cache[destination_id]

        src_h, src_w = frame.shape[:2]
        if src_h <= 0 or src_w <= 0:
            return np.zeros((height, width, 3), dtype=np.uint8)

        # Keep original aspect ratio at all times and crop from the center.
        if src_h > src_w:
            scale = height / src_h
            resized_h = height
            resized_w = max(1, int(round(src_w * scale)))
            if resized_w < width:
                scale = width / src_w
                resized_w = width
                resized_h = max(1, int(round(src_h * scale)))
        else:
            scale = width / src_w
            resized_w = width
            resized_h = max(1, int(round(src_h * scale)))
            if resized_h < height:
                scale = height / src_h
                resized_h = height
                resized_w = max(1, int(round(src_w * scale)))

        resized = cv2.resize(frame, (resized_w, resized_h), interpolation=cv2.INTER_AREA)
        start_x = max(0, (resized_w - width) // 2)
        start_y = max(0, (resized_h - height) // 2)
        return resized[start_y:start_y + height, start_x:start_x + width]

    def _get_detail_qr(self, destination: Dict) -> np.ndarray:
        destination_id = str(destination.get("id", destination.get("name", "destino")))
        if destination_id in self.detail_qr_cache:
            return self.detail_qr_cache[destination_id]

        name = str(destination.get("name", "Destino"))
        query = urllib.parse.quote_plus(f"{name} Ancash Peru")
        url = f"https://www.google.com/maps/search/{query}"

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color=(201, 168, 76), back_color=(10, 10, 10)).convert("RGB")
        img = img.resize((120, 120), Image.NEAREST)
        qr_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        self.detail_qr_cache[destination_id] = qr_bgr
        return qr_bgr

    def draw_detail_screen(self, frame: np.ndarray, destination: Optional[Dict], pointer_pos: Optional[Tuple[int, int]]) -> np.ndarray:
        global detail_transition_start, detail_back_btn_rect, detail_back_hover_timer, detail_back_flash_timer
        global detail_realtime_btn_rect, detail_realtime_hover_timer, detail_realtime_flash_timer

        canvas = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)
        if destination is None:
            detail_back_btn_rect = None
            return canvas

        left_w = int(CANVAS_W * 0.6)
        right_x = left_w
        right_w = CANVAS_W - left_w

        visual = self._get_detail_visual(destination, left_w, CANVAS_H)
        canvas[:, :left_w] = visual

        grad_start = int(CANVAS_H * 0.6)
        rows = CANVAS_H - grad_start
        if rows > 0:
            alpha = np.linspace(0.0, 0.78, rows, dtype=np.float32).reshape(rows, 1, 1)
            left_roi = canvas[grad_start:CANVAS_H, :left_w].astype(np.float32)
            canvas[grad_start:CANVAS_H, :left_w] = np.clip(left_roi * (1.0 - alpha), 0, 255).astype(np.uint8)

        cv2.rectangle(canvas, (right_x, 0), (CANVAS_W, CANVAS_H), (10, 10, 10), -1)

        img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(img, "RGBA")

        name_font = self._load_font(FONT_TITLE_FILE, 44)
        type_font = self._load_font(FONT_BODY_BOLD_FILE, 22)
        draw.text((34, CANVAS_H - 128), str(destination.get("name", "Destino")), font=name_font, fill=(245, 245, 245, 255))
        draw.text((36, CANVAS_H - 76), str(destination.get("type", "")), font=type_font, fill=(201, 168, 76, 255))

        panel_pad = 30
        content_x = right_x + panel_pad
        content_w = right_w - panel_pad * 2
        y = 34

        badge_text = str(destination.get("type", "")).upper()
        badge_font = self._load_font(FONT_BODY_BOLD_FILE, 14)
        bb = draw.textbbox((0, 0), badge_text, font=badge_font)
        badge_w = (bb[2] - bb[0]) + 24
        badge_h = (bb[3] - bb[1]) + 14
        draw.rounded_rectangle((content_x, y, content_x + badge_w, y + badge_h), radius=9, fill=(201, 168, 76, 255))
        draw.text((content_x + 12, y + 6), badge_text, font=badge_font, fill=(0, 0, 0, 255))

        y += badge_h + 16
        title_font = self._load_font(FONT_TITLE_FILE, 34)
        title_lines = self._wrap_text(str(destination.get("name", "Destino")), 20)
        for line in title_lines[:2]:
            draw.text((content_x, y), line, font=title_font, fill=(245, 245, 245, 255))
            y += 38

        sep_color = (201, 168, 76, 102)
        y += 8
        draw.line((content_x, y, content_x + content_w, y), fill=sep_color, width=1)

        label_font = self._load_font(FONT_REG_FILE, 12)
        value_font = self._load_font(FONT_BODY_BOLD_FILE, 13)
        y += 18
        approx_cost = destination.get("cost_huaraz")
        if not approx_cost:
            diff = str(destination.get("difficulty", "")).lower()
            if "alta" in diff:
                approx_cost = "S/ 520"
            elif "media" in diff:
                approx_cost = "S/ 280"
            else:
                approx_cost = "S/ 160"

        info_rows = [
            ("Cómo llegar", str(destination.get("como_llegar", "No disponible")), (245, 245, 245, 255)),
            ("Costo aprox", str(destination.get("costo", str(approx_cost))), (245, 245, 245, 255)),
            ("Clima típico", str(destination.get("clima", "No disponible")), (245, 245, 245, 255)),
            ("Qué llevar", str(destination.get("que_llevar", "No disponible")), (245, 245, 245, 255)),
            ("Advertencia", str(destination.get("advertencia", "Consultar guía local")), (255, 215, 0, 255)),
        ]
        label_col_w = 120
        value_col_x = content_x + label_col_w + 12
        value_col_w = content_w - label_col_w - 12
        row_gap = 10
        for label, value, value_color in info_rows:
            draw.text((content_x, y), label, font=label_font, fill=(136, 136, 136, 255))
            wrapped_values = self._wrap_text(value, 26)
            for i, line in enumerate(wrapped_values[:2]):
                draw.text((value_col_x, y + i * 17), line, font=value_font, fill=value_color)
            y += max(24, len(wrapped_values[:2]) * 17 + row_gap)

        detail_realtime_btn_rect = self._detail_realtime_button_rect(destination)
        realtime_flash = detail_realtime_flash_timer > 0.0
        if current_screen == "detail":
            qr_size = 80
            bottom_row_h = 200
            bottom_row_y = CANVAS_H - 20 - bottom_row_h
            qr_y = y + 16
            qr_text_x = content_x + qr_size + 16
            qr_center_y = qr_y + (qr_size // 2)

            qr_img = self._get_detail_qr(destination)
            qr_resized = cv2.resize(qr_img, (qr_size, qr_size), interpolation=cv2.INTER_NEAREST)
            qr_rgb = cv2.cvtColor(qr_resized, cv2.COLOR_BGR2RGB)
            img.paste(Image.fromarray(qr_rgb), (content_x, qr_y))

            qr_text_font = self._load_font(FONT_REG_FILE, 12)
            qr_label = "Escanea para\nver en Maps"
            qr_bbox = draw.multiline_textbbox((0, 0), qr_label, font=qr_text_font, spacing=2)
            qr_text_h = qr_bbox[3] - qr_bbox[1]
            draw.multiline_text(
                (qr_text_x, qr_center_y - (qr_text_h // 2)),
                qr_label,
                font=qr_text_font,
                fill=(136, 136, 136, 255),
                spacing=2,
            )

            qr_sep_y = qr_y + qr_size + 14
            draw.line((content_x, qr_sep_y, content_x + content_w, qr_sep_y), fill=sep_color, width=1)

            button_x, button_y, button_w, button_h = detail_realtime_btn_rect
            if realtime_flash:
                draw.rounded_rectangle((button_x, button_y, button_x + button_w, button_y + button_h), radius=10, fill=(245, 245, 245, 255))
                realtime_text_fill = (10, 10, 10, 255)
            else:
                draw.rounded_rectangle((button_x, button_y, button_x + button_w, button_y + button_h), radius=10, fill=(0, 0, 0, 0))
                progress = max(0.0, min(1.0, detail_realtime_hover_timer / 1.5))
                if progress > 0.0:
                    fill_w = max(1, int(button_w * progress))
                    draw.rounded_rectangle((button_x, button_y, button_x + fill_w, button_y + button_h), radius=10, fill=(201, 168, 76, 90))
                draw.rounded_rectangle(
                    (button_x, button_y, button_x + button_w, button_y + button_h),
                    radius=10,
                    outline=(201, 168, 76, 255),
                    width=2,
                )
                realtime_text_fill = (245, 245, 245, 255)

            realtime_font = self._load_font(FONT_BODY_BOLD_FILE, 12)
            realtime_label = "En vivo"
            rb = draw.textbbox((0, 0), realtime_label, font=realtime_font)
            rw = rb[2] - rb[0]
            rh = rb[3] - rb[1]
            draw.text((button_x + (button_w - rw) // 2, button_y + (button_h - rh) // 2 - 1), realtime_label, font=realtime_font, fill=realtime_text_fill)

            back_x = content_x
            back_h = 50
            back_y = bottom_row_y + (bottom_row_h - back_h) // 2
            back_w = int(content_w * 0.34)
            webcam_w = content_w - back_w
            webcam_x = content_x + content_w - webcam_w
            webcam_h = bottom_row_h
            webcam_y = bottom_row_y
            detail_back_btn_rect = (back_x, back_y, back_w, back_h)
            back_flash = detail_back_flash_timer > 0.0
            if back_flash:
                draw.rounded_rectangle((back_x, back_y, back_x + back_w, back_y + back_h), radius=12, fill=(245, 245, 245, 255))
                text_fill = (10, 10, 10, 255)
            else:
                draw.rounded_rectangle((back_x, back_y, back_x + back_w, back_y + back_h), radius=12, fill=(0, 0, 0, 0))
                progress = max(0.0, min(1.0, detail_back_hover_timer / 1.5))
                if progress > 0.0:
                    fill_w = max(1, int(back_w * progress))
                    draw.rounded_rectangle((back_x, back_y, back_x + fill_w, back_y + back_h), radius=12, fill=(201, 168, 76, 90))
                draw.rounded_rectangle(
                    (back_x, back_y, back_x + back_w, back_y + back_h),
                    radius=12,
                    outline=(201, 168, 76, 255),
                    width=2,
                )
                text_fill = (245, 245, 245, 255)

            back_font = self._load_font(FONT_BOLD_FILE, 16)
            back_label = "← VOLVER"
            b = draw.textbbox((0, 0), back_label, font=back_font)
            tw = b[2] - b[0]
            th = b[3] - b[1]
            draw.text((back_x + (back_w - tw) // 2, back_y + (back_h - th) // 2 - 1), back_label, font=back_font, fill=text_fill)
        else:
            draw.rounded_rectangle((content_x, button_y, content_x + content_w, button_y + button_h), radius=10, fill=(0, 0, 0, 0))
            draw.rounded_rectangle((content_x, button_y, content_x + content_w, button_y + button_h), radius=10, outline=(201, 168, 76, 255), width=2)
            title_font = self._load_font(FONT_BODY_BOLD_FILE, 12)
            title = "DATOS EN TIEMPO REAL"
            tb = draw.textbbox((0, 0), title, font=title_font)
            tw = tb[2] - tb[0]
            th = tb[3] - tb[1]
            draw.text((content_x + 18, button_y - 2), title, font=title_font, fill=(201, 168, 76, 255))

            nasa_info = self.nasa_data.get(str(destination.get("id", "")), {})
            temp_value = nasa_info.get("temperature")
            fires = nasa_info.get("fires", [])
            closest_fire = min(fires, key=lambda item: item.get("distance_km", 9999)) if fires else None
            last_update = nasa_info.get("timestamp")
            source_text = nasa_info.get("source", "NASA POWER + NASA EONET")

            section_y = button_y + button_h + 22
            section_gap = 16
            section_w = (content_w - section_gap) // 2
            section_h = 68

            metrics = [
                ("TEMP. ACTUAL", f"{temp_value:.1f}°C" if temp_value is not None else "Cargando..."),
                ("INCENDIOS", f"{len(fires)} activos" if fires else "0 activos"),
                ("RIESGO", "ALTO" if fires else "BAJO"),
                ("MÁS CERCANO", f"{closest_fire.get('distance_km', 0):.1f} km" if closest_fire else "Sin eventos"),
            ]

            metric_font = self._load_font(FONT_BOLD_FILE, 16)
            metric_value_font = self._load_font(FONT_BOLD_FILE, 20)
            for idx, (metric_label, metric_value) in enumerate(metrics):
                col = idx % 2
                row = idx // 2
                box_x = content_x + col * (section_w + section_gap)
                box_y = section_y + row * (section_h + section_gap)
                draw.rounded_rectangle((box_x, box_y, box_x + section_w, box_y + section_h), radius=14, fill=(18, 18, 18, 255), outline=(201, 168, 76, 120), width=1)
                draw.text((box_x + 14, box_y + 10), metric_label, font=metric_font, fill=(136, 136, 136, 255))
                draw.text((box_x + 14, box_y + 31), metric_value, font=metric_value_font, fill=(245, 245, 245, 255))

            note_y = section_y + section_h * 2 + section_gap + 12
            note_font = self._load_font(FONT_REG_FILE, 13)
            note_lines = [
                f"Actualizado: {time.strftime('%H:%M:%S', time.localtime(last_update))}" if last_update else "Actualizando datos...",
                f"Fuente: {source_text}",
            ]
            for idx, line in enumerate(note_lines):
                draw.text((content_x, note_y + idx * 18), line, font=note_font, fill=(210, 210, 210, 225))

            back_x = content_x
            back_h = 50
            bottom_row_h = 200
            bottom_row_y = CANVAS_H - 20 - bottom_row_h
            back_y = bottom_row_y + (bottom_row_h - back_h) // 2
            back_w = int(content_w * 0.45)
            webcam_w = content_w - back_w
            webcam_x = content_x + content_w - webcam_w
            webcam_h = bottom_row_h
            webcam_y = bottom_row_y
            detail_back_btn_rect = (back_x, back_y, back_w, back_h)
            back_flash = detail_back_flash_timer > 0.0
            if back_flash:
                draw.rounded_rectangle((back_x, back_y, back_x + back_w, back_y + back_h), radius=12, fill=(245, 245, 245, 255))
                text_fill = (10, 10, 10, 255)
            else:
                draw.rounded_rectangle((back_x, back_y, back_x + back_w, back_y + back_h), radius=12, fill=(0, 0, 0, 0))
                progress = max(0.0, min(1.0, detail_back_hover_timer / 1.5))
                if progress > 0.0:
                    fill_w = max(1, int(back_w * progress))
                    draw.rounded_rectangle((back_x, back_y, back_x + fill_w, back_y + back_h), radius=12, fill=(201, 168, 76, 90))
                draw.rounded_rectangle(
                    (back_x, back_y, back_x + back_w, back_y + back_h),
                    radius=12,
                    outline=(201, 168, 76, 255),
                    width=2,
                )
                text_fill = (245, 245, 245, 255)

            back_font = self._load_font(FONT_BOLD_FILE, 18)
            back_label = "← VOLVER AL DETALLE"
            b = draw.textbbox((0, 0), back_label, font=back_font)
            tw = b[2] - b[0]
            th = b[3] - b[1]
            draw.text((back_x + (back_w - tw) // 2, back_y + (back_h - th) // 2 - 1), back_label, font=back_font, fill=text_fill)

        canvas[:] = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)

        webcam_view = self._cover_crop(frame, webcam_w, webcam_h)
        self._draw_glass_panel(canvas, webcam_x - 4, webcam_y - 4, webcam_w + 8, webcam_h + 8, 10, alpha=0.35)
        self._paste_rounded(canvas, webcam_view, webcam_x, webcam_y, webcam_w, webcam_h, 9)
        self._draw_rounded_border(canvas, webcam_x, webcam_y, webcam_w, webcam_h, 9, GOLD, 2)

        if detail_transition_start <= 0.0:
            detail_transition_start = time.time()
        elapsed = max(0.0, time.time() - detail_transition_start)
        fade_duration = 0.3
        if elapsed < fade_duration:
            alpha = 1.0 - (elapsed / fade_duration)
            overlay = np.zeros_like(canvas)
            canvas = cv2.addWeighted(overlay, alpha, canvas, 1.0 - alpha, 0)

        if pointer_pos is not None:
            px, py = pointer_pos
            cv2.circle(canvas, (int(px), int(py)), 12, (76, 168, 201), -1, cv2.LINE_AA)
            cv2.circle(canvas, (int(px), int(py)), 4, (245, 245, 245), -1, cv2.LINE_AA)

        return canvas

    def draw_realtime_dashboard(self, active_point_id: Optional[str], pointer_pos: Optional[Tuple[int, int]]) -> np.ndarray:
        global detail_transition_start, detail_back_btn_rect, detail_back_hover_timer, detail_back_flash_timer

        canvas = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)

        # Clean dashboard background.
        for y in range(CANVAS_H):
            t = y / max(1, CANVAS_H - 1)
            shade = int(8 + t * 16)
            canvas[y, :] = (shade, shade, shade)

        img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(img, "RGBA")

        destination = active_destination if active_destination is not None else next((p for p in self.points if p["id"] == active_point_id), None)
        if destination is None:
            detail_back_btn_rect = None
            return canvas

        destination_id = str(destination.get("id", ""))
        nasa_info = self.nasa_data.get(destination_id, {})
        temp_value = nasa_info.get("temperature")
        fires = nasa_info.get("fires", [])
        closest_fire = min(fires, key=lambda item: item.get("distance_km", 9999)) if fires else None
        last_update = nasa_info.get("timestamp")
        title_font = self._load_font(FONT_TITLE_FILE, 36)
        subtitle_font = self._load_font(FONT_REG_FILE, 18)
        section_font = self._load_font(FONT_BODY_BOLD_FILE, 15)
        value_font = self._load_font(FONT_BODY_BOLD_FILE, 26)
        small_font = self._load_font(FONT_REG_FILE, 13)

        draw.text((34, 22), "ESTADO EN VIVO", font=title_font, fill=(245, 245, 245, 255))
        draw.text((36, 66), f"{destination.get('name', 'Destino')} · {destination.get('type', '')}", font=subtitle_font, fill=(201, 168, 76, 255))

        header_sep_y = 98
        draw.line((34, header_sep_y, CANVAS_W - 34, header_sep_y), fill=(201, 168, 76, 120), width=1)

        update_text = time.strftime('%H:%M', time.localtime(last_update)) if last_update else "Pendiente"
        draw.text((36, 108), f"Actualizado: {update_text}", font=small_font, fill=(136, 136, 136, 255))

        # Metric cards
        card_top = 146
        card_gap = 16
        card_w = (CANVAS_W - 34 * 2 - card_gap * 2) // 3
        card_h = 102

        if temp_value is None:
            temp_text = "Cargando..."
            temp_state = "Sin dato aún"
        else:
            temp_text = f"{temp_value:.1f}°C"
            temp_state = "Temperatura actual"

        fire_state = f"{len(fires)} cerca" if fires else "Ninguno"
        if fires:
            fire_label = "ALERTA"
            fire_color = (255, 120, 90, 255)
        else:
            fire_label = "SEGURO"
            fire_color = (126, 206, 120, 255)

        risk_value = 20
        if temp_value is not None:
            risk_value += max(0, int((temp_value - 5) * 2))
        risk_value += min(40, len(fires) * 18)
        risk_value = max(0, min(100, risk_value))
        if risk_value >= 65:
            risk_label = "ALTO"
            risk_color = (255, 120, 90, 255)
        elif risk_value >= 35:
            risk_label = "MEDIO"
            risk_color = (245, 195, 80, 255)
        else:
            risk_label = "BAJO"
            risk_color = (126, 206, 120, 255)

        cards = [
            ("CLIMA AHORA", temp_text, temp_state, (90, 150, 255, 255)),
            ("INCENDIOS CERCANOS", fire_state, fire_label, fire_color),
            ("NIVEL DE CUIDADO", risk_label, "Recomendacion", risk_color),
        ]

        for idx, (card_title, card_value, card_note, accent_color) in enumerate(cards):
            x = 34 + idx * (card_w + card_gap)
            y = card_top
            draw.rounded_rectangle((x, y, x + card_w, y + card_h), radius=16, fill=(16, 16, 16, 255), outline=accent_color, width=2)
            draw.text((x + 16, y + 14), card_title, font=section_font, fill=(136, 136, 136, 255))
            draw.text((x + 16, y + 38), card_value, font=value_font, fill=(245, 245, 245, 255))
            draw.text((x + 16, y + 68), card_note, font=subtitle_font, fill=accent_color)

        # Bottom wide panel
        bottom_y = 268
        bottom_h = 208
        draw.rounded_rectangle((34, bottom_y, CANVAS_W - 34, bottom_y + bottom_h), radius=18, fill=(14, 14, 14, 255), outline=(201, 168, 76, 120), width=1)

        left_x = 58
        y = bottom_y + 16
        draw.text((left_x, y), "RECOMENDACION DE HOY", font=section_font, fill=(201, 168, 76, 255))
        y += 32

        if risk_label == "ALTO":
            rec_lines = self._wrap_text("Evita el recorrido hoy. Consulta un guia local antes de salir.", 46)
        elif risk_label == "MEDIO":
            rec_lines = self._wrap_text("Ve con precaucion y lleva abrigo adicional.", 46)
        else:
            rec_lines = self._wrap_text("Condiciones normales para visitar. Mantente atento al clima.", 46)

        for line in rec_lines[:3]:
            draw.text((left_x, y), line, font=subtitle_font, fill=(245, 245, 245, 255))
            y += 24

        y += 6
        detail_rows = [
            ("Incendio mas cercano", closest_fire.get("title", "Sin reportes") if closest_fire else "Sin reportes"),
            ("Distancia", f"{closest_fire.get('distance_km', 0):.1f} km" if closest_fire else "N/A"),
        ]

        for label, value in detail_rows:
            draw.text((left_x, y), label, font=small_font, fill=(136, 136, 136, 255))
            draw.text((left_x + 200, y), value, font=small_font, fill=(245, 245, 245, 255))
            y += 22

        sat_w, sat_h = 240, 150
        sat_x = CANVAS_W - 34 - sat_w
        sat_y = bottom_y + 26
        draw.rounded_rectangle(
            (sat_x, sat_y, sat_x + sat_w, sat_y + sat_h),
            radius=14,
            fill=(16, 16, 16, 255),
            outline=(201, 168, 76, 120),
            width=1,
        )
        draw.text((sat_x + 12, sat_y + 10), "VISTA SATELITAL", font=small_font, fill=(136, 136, 136, 255))

        sat_tile = None
        lat = destination.get("latitude")
        lon = destination.get("longitude")
        if lat is not None and lon is not None:
            try:
                lat = float(lat)
                lon = float(lon)
                date_hint = time.strftime("%Y-%m-%d", time.gmtime(last_update)) if last_update else None
                sat_tile = self._get_sat_tile(lat, lon, zoom=9, date_hint=date_hint)
            except (TypeError, ValueError):
                sat_tile = Noneqq

        if sat_tile is None:
            fallback_text = "Cargando imagen..." if lat is not None and lon is not None else "Sin ubicacion"
            draw.text((sat_x + 12, sat_y + 60), fallback_text, font=small_font, fill=(136, 136, 136, 255))

        # Back button
        back_w = 170
        back_h = 44
        back_x = 34
        back_y = CANVAS_H - 162
        detail_back_btn_rect = (back_x, back_y, back_w, back_h)
        back_flash = detail_back_flash_timer > 0.0
        if back_flash:
            draw.rounded_rectangle((back_x, back_y, back_x + back_w, back_y + back_h), radius=12, fill=(245, 245, 245, 255))
            back_text_fill = (10, 10, 10, 255)
        else:
            draw.rounded_rectangle((back_x, back_y, back_x + back_w, back_y + back_h), radius=12, fill=(0, 0, 0, 0))
            progress = max(0.0, min(1.0, detail_back_hover_timer / 1.5))
            if progress > 0.0:
                fill_w = max(1, int(back_w * progress))
                draw.rounded_rectangle((back_x, back_y, back_x + fill_w, back_y + back_h), radius=12, fill=(201, 168, 76, 90))
            draw.rounded_rectangle((back_x, back_y, back_x + back_w, back_y + back_h), radius=12, outline=(201, 168, 76, 255), width=2)
            back_text_fill = (245, 245, 245, 255)

        back_font = self._load_font(FONT_BODY_BOLD_FILE, 16)
        back_label = "← VOLVER"
        b = draw.textbbox((0, 0), back_label, font=back_font)
        tw = b[2] - b[0]
        th = b[3] - b[1]
        draw.text((back_x + (back_w - tw) // 2, back_y + (back_h - th) // 2 - 1), back_label, font=back_font, fill=back_text_fill)

        canvas[:] = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)

        if sat_tile is not None:
            img_x = sat_x + 10
            img_y = sat_y + 30
            img_w = sat_w - 20
            img_h = sat_h - 38
            sat_view = self._cover_crop(sat_tile, img_w, img_h)
            self._paste_rounded(canvas, sat_view, img_x, img_y, img_w, img_h, 10)
            self._draw_rounded_border(canvas, img_x, img_y, img_w, img_h, 10, GOLD, 2)

        if detail_transition_start <= 0.0:
            detail_transition_start = time.time()
        elapsed = max(0.0, time.time() - detail_transition_start)
        fade_duration = 0.22
        if elapsed < fade_duration:
            alpha = 1.0 - (elapsed / fade_duration)
            overlay = np.zeros_like(canvas)
            canvas = cv2.addWeighted(overlay, alpha, canvas, 1.0 - alpha, 0)

        if pointer_pos is not None:
            px, py = pointer_pos
            cv2.circle(canvas, (int(px), int(py)), 12, (76, 168, 201), -1, cv2.LINE_AA)
            cv2.circle(canvas, (int(px), int(py)), 4, (245, 245, 245), -1, cv2.LINE_AA)

        return canvas

    def _draw_pointer(self, canvas: np.ndarray) -> None:
        if self.pointer is None:
            return

        px, py = self.pointer
        pulse = 0.5 + 0.5 * math.sin(self.frame_count * 0.3)
        self._draw_glow(canvas, (px, py), int(24 + pulse * 7), GOLD, 0.18)
        cv2.circle(canvas, (px, py), 16, GOLD, 2, cv2.LINE_AA)
        cv2.circle(canvas, (px, py), 4, WHITE, -1, cv2.LINE_AA)

    def _floating_button_rect(self, point: Dict) -> Tuple[int, int, int, int]:
        cx, cy = self._point_to_pixel(point)
        return (cx - 60, cy - 55, 120, 32)

    def _detail_realtime_button_rect(self, destination: Dict) -> Tuple[int, int, int, int]:
        left_w = int(CANVAS_W * 0.6)
        right_x = left_w
        right_w = CANVAS_W - left_w

        panel_pad = 30
        content_x = right_x + panel_pad
        content_w = right_w - panel_pad * 2

        label_font = self._load_font(FONT_REG_FILE, 12)
        value_font = self._load_font(FONT_BOLD_FILE, 13)
        approx_cost = destination.get("cost_huaraz")
        if not approx_cost:
            diff = str(destination.get("difficulty", "")).lower()
            if "alta" in diff:
                approx_cost = "S/ 520"
            elif "media" in diff:
                approx_cost = "S/ 280"
            else:
                approx_cost = "S/ 160"

        info_rows = [
            ("Cómo llegar", str(destination.get("como_llegar", "No disponible")), (245, 245, 245, 255)),
            ("Costo aprox", str(destination.get("costo", str(approx_cost))), (245, 245, 245, 255)),
            ("Clima típico", str(destination.get("clima", "No disponible")), (245, 245, 245, 255)),
            ("Qué llevar", str(destination.get("que_llevar", "No disponible")), (245, 245, 245, 255)),
            ("Advertencia", str(destination.get("advertencia", "Consultar guía local")), (255, 215, 0, 255)),
        ]
        y = 34
        badge_text = str(destination.get("type", "")).upper()
        badge_font = self._load_font(FONT_BOLD_FILE, 14)
        bb = self._measure_text_bbox(badge_text, badge_font)
        badge_h = (bb[3] - bb[1]) + 14
        y += badge_h + 16

        title_font = self._load_font(FONT_BOLD_FILE, 34)
        title_lines = self._wrap_text(str(destination.get("name", "Destino")), 20)
        for line in title_lines[:2]:
            tb = self._measure_text_bbox(line, title_font)
            y += (tb[3] - tb[1]) + 4

        y += 8
        y += 1
        y += 18
        row_gap = 10
        for label, value, _ in info_rows:
            wrapped_values = self._wrap_text(value, 26)
            label_bbox = self._measure_text_bbox(label, label_font)
            value_bbox = self._measure_text_bbox(wrapped_values[0] if wrapped_values else "", value_font)
            y += max(24, max(label_bbox[3] - label_bbox[1], value_bbox[3] - value_bbox[1]) + row_gap)

        back_h = 50
        bottom_row_h = 200
        bottom_row_y = CANVAS_H - 20 - bottom_row_h
        qr_size = 80
        qr_y = y + 16
        qr_sep_y = qr_y + qr_size + 14
        button_w = max(120, int(content_w * 0.34))
        button_h = 28
        # Place the CTA slightly further left to avoid overlapping the webcam preview
        button_x = content_x + 2
        back_y = bottom_row_y + (bottom_row_h - back_h) // 2
        button_y = back_y - button_h - 10
        return (button_x, button_y, button_w, button_h)

    @staticmethod
    def _measure_text_bbox(text: str, font):
        dummy = Image.new("RGB", (1, 1), (0, 0, 0))
        draw = ImageDraw.Draw(dummy)
        return draw.textbbox((0, 0), text, font=font)

    def _draw_floating_button(self, canvas: np.ndarray) -> None:
        global btn_ver_mas_rect, btn_hover_timer, btn_flash_timer, btn_active_point_id, current_screen, active_destination

        if current_screen == "detail" or btn_active_point_id is None:
            btn_ver_mas_rect = None
            return

        point = next((p for p in self.points if p["id"] == btn_active_point_id), None)
        if point is None:
            btn_ver_mas_rect = None
            return

        x, y, w, h = self._floating_button_rect(point)
        btn_ver_mas_rect = (x, y, w, h)

        button_flash = btn_flash_timer > 0.0
        button_fill = (245, 245, 245) if button_flash else (201, 168, 76)
        button_text = "VER MÁS"

        img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).convert("RGBA")
        draw = ImageDraw.Draw(img, "RGBA")

        draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=(*button_fill, 255))

        progress = max(0.0, min(1.0, btn_hover_timer / 1.5))
        if progress > 0.0 and not button_flash:
            progress_w = max(1, int(w * progress))
            draw.rounded_rectangle((x, y, x + progress_w, y + h), radius=8, fill=(245, 221, 148, 140))
            draw.rounded_rectangle((x, y, x + w, y + h), radius=8, outline=(0, 0, 0, 30), width=1)

        font = self._load_font(FONT_BOLD_FILE, 13)
        label = "▶  VER MÁS"
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text(
            (x + (w - text_w) // 2, y + (h - text_h) // 2 - 1),
            label,
            font=font,
            fill=(0, 0, 0, 255),
        )

        canvas[:] = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)

    def _draw_card(self, canvas: np.ndarray) -> None:
        if self.active_point_id is None:
            return

        point = next((p for p in self.points if p["id"] == self.active_point_id), None)
        if point is None:
            return

        t = self.card_anim_t
        ease = t * t * (3 - 2 * t)
        x_base = RIGHT_PANEL_X
        y = 84
        base_w = CARD_W - 40
        webcam_top = CANVAS_H - PREVIEW_H - RIGHT_PANEL_MARGIN
        max_card_h = webcam_top - CARD_WEBCAM_GAP - y
        h = min(435, max(330, max_card_h))

        scale = 0.94 + 0.06 * ease
        w = int(base_w * scale)
        x = x_base + (base_w - w)

        if x < 0 or y < 0 or x + w > CANVAS_W or y + h > CANVAS_H:
            return

        def cover_crop(src: np.ndarray, target_w: int, target_h: int) -> np.ndarray:
            src_h, src_w = src.shape[:2]
            if src_h <= 0 or src_w <= 0:
                return np.zeros((target_h, target_w, 3), dtype=np.uint8)

            scale_factor = max(target_w / src_w, target_h / src_h)
            resized_w = max(target_w, int(math.ceil(src_w * scale_factor)))
            resized_h = max(target_h, int(math.ceil(src_h * scale_factor)))
            resized = cv2.resize(src, (resized_w, resized_h), interpolation=cv2.INTER_AREA)

            start_x = max(0, (resized_w - target_w) // 2)
            start_y = max(0, (resized_h - target_h) // 2)
            cropped = resized[start_y:start_y + target_h, start_x:start_x + target_w]

            if cropped.shape[0] != target_h or cropped.shape[1] != target_w:
                cropped = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)
            return cropped

        roi = canvas[y:y + h, x:x + w].copy()

        bg = roi.copy()
        cv2.rectangle(bg, (0, 0), (w - 1, h - 1), (10, 10, 10), -1)
        cv2.addWeighted(bg, 0.92, roi, 0.08, 0, roi)
        cv2.rectangle(roi, (0, 0), (2, h - 1), GOLD, -1)

        photo_h = 200
        photo = cover_crop(self._load_destination_image(point), w, photo_h)
        roi[0:photo_h, 0:w] = photo

        pil_img = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img, "RGBA")

        def text_size(text: str, font) -> Tuple[int, int]:
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]

        max_text_w = w - 40
        title_size = 28
        title_font = self._load_font(FONT_BOLD_FILE, title_size)
        title_w, title_h = text_size(point["name"], title_font)
        while title_w > max_text_w and title_size > 22:
            title_size -= 1
            title_font = self._load_font(FONT_BOLD_FILE, title_size)
            title_w, title_h = text_size(point["name"], title_font)

        type_font = self._load_font(FONT_REG_FILE, 16)
        label_font = self._load_font(FONT_REG_FILE, 14)
        value_font = self._load_font(FONT_BOLD_FILE, 14)
        desc_font = self._load_font(FONT_REG_FILE, 13)

        title_x = 20
        title_y = photo_h + 20
        draw.text((title_x, title_y), point["name"], font=title_font, fill=(201, 168, 76, 255))

        type_text = str(point.get("type", ""))
        type_y = title_y + title_h + 3
        draw.text((title_x, type_y), type_text, font=type_font, fill=(170, 170, 170, 255))

        sep_color = (201, 168, 76, 102)
        sep1_y = type_y + text_size(type_text, type_font)[1] + 12
        draw.line((20, sep1_y, w - 20, sep1_y), fill=sep_color, width=1)

        data_y = sep1_y + 16

        # ⭐ OBTENER DATOS NASA SI ESTÁN DISPONIBLES
        nasa_temp = None
        fires_count = 0
        if point["id"] in self.nasa_data:
            nasa_info = self.nasa_data[point["id"]]
            nasa_temp = nasa_info.get("temperature")
            fires_count = len(nasa_info.get("fires", []))

        data_rows = [
            ("Altitud", f"{point['altitude_m']} msnm"),
            ("Duración", str(point.get("duration", ""))),
            ("Mejor época", str(point.get("best_season", ""))),
            ("Dificultad", str(point.get("difficulty", ""))),
        ]

        # ⭐ AGREGAR DATOS NASA SI DISPONIBLES
        if nasa_temp is not None:
            data_rows.append(("Temperatura", f"{nasa_temp:.1f}°C"))

        if nasa_temp is not None:
            if fires_count > 0:
                fire_display = f"⚠️ {fires_count} evento(s)"
            else:
                fire_display = "✓ Sin fuego"
            data_rows.append(("Estado fuego", fire_display))

        row_y = data_y
        row_gap = 16
        for label, value in data_rows:
            label_w, label_h = text_size(label, label_font)
            value_w, value_h = text_size(value, value_font)
            draw.text((20, row_y), label, font=label_font, fill=(136, 136, 136, 255))
            draw.text((w - 20 - value_w, row_y), value, font=value_font, fill=(245, 245, 245, 255))
            row_y += max(label_h, value_h) + row_gap

        sep2_y = row_y - 2
        draw.line((20, sep2_y, w - 20, sep2_y), fill=sep_color, width=1)

        desc_y = sep2_y + 16
        desc_lines = self._wrap_text(point.get("description", ""), 35)
        desc_color = (176, 176, 176, 180)
        desc_line_h = text_size("Ag", desc_font)[1] + 5
        for i, line in enumerate(desc_lines):
            line_y = desc_y + i * desc_line_h
            if line_y + desc_line_h > h - 18:
                break
            draw.text((20, line_y), line, font=desc_font, fill=desc_color)

        roi[:] = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        base_roi = canvas[y:y + h, x:x + w]
        canvas[y:y + h, x:x + w] = cv2.addWeighted(roi, ease, base_roi, 1 - ease, 0)

    def _draw_debug(self, canvas: np.ndarray, dt: float) -> None:
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, CANVAS_H - 44), (CANVAS_W, CANVAS_H), BLACK, -1)
        cv2.addWeighted(overlay, 0.66, canvas, 0.34, 0, canvas)

    def _draw_text_layers(self, canvas: np.ndarray, dt: float) -> np.ndarray:
        img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img, "RGBA")

        draw.text((28, 22), "CORDILLERA BLANCA", font=self.font_title, fill=(245, 245, 245, 255))
        draw.text((30, 62), "Explorador gestual | Ancash, Peru", font=self.font_subtitle, fill=(136, 136, 136, 255))

        for point in self.points:
            cx, cy = self._point_to_pixel(point)
            is_active = point["id"] == self.active_point_id
            color = (201, 168, 76, 255) if is_active else (230, 230, 230, 220)
            draw.text((cx + 10, cy - 18), point["name"], font=self.font_point, fill=color)

        if self.webcam_rect is not None:
            wx0, wy0, _, _ = self.webcam_rect
            draw.text((wx0 + 10, wy0 - 28), "GESTURE CAM", font=self.font_subtitle, fill=(201, 168, 76, 255))

        if self.card_render is not None:
            x, y, w, h, point = self.card_render
            draw.text((x + 18, y + 18), point["name"], font=self.font_card_title, fill=(201, 168, 76, 255))
            draw.text((x + 18, y + 54), point["type"], font=self.font_card_subtitle, fill=(210, 210, 210, 230))

            y_data = y + min(360, h - 102)
            lines = [
                f"⛰ Altitud  {point['altitude_m']} msnm",
                f"🕐 Duracion  {point['duration']}",
                f"📅 Mejor epoca  {point['best_season']}",
                f"Dificultad  {point['difficulty']}",
            ]
            for line in lines:
                draw.text((x + 18, y_data), line, font=self.font_card_body, fill=(245, 245, 245, 238))
                y_data += 26

            wrapped = self._wrap_text(point.get("description", ""), 34)
            y_data += 4
            for line in wrapped[:2]:
                draw.text((x + 18, y_data), line, font=self.font_card_desc, fill=(245, 245, 245, 192))
                y_data += 21

        if self.debug:
            fps = int(1.0 / max(1e-4, dt))
            debug_text = (
                f"FPS {fps}   |   Pointer {self.pointer}   |   Hover {self.hover_candidate}   |   "
                f"Active {self.active_point_id}   |   D debug   Q/ESC salir"
            )
            draw.text((24, CANVAS_H - 30), debug_text, font=self.font_hud, fill=(136, 136, 136, 235))

        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def _load_background_image(self) -> np.ndarray:
        img = self._imread_unicode_safe(BACKGROUND_IMAGE_FILE)
        if img is None:
            fallback = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)
            for y in range(CANVAS_H):
                t = y / max(1, CANVAS_H - 1)
                c = int(30 + t * 40)
                fallback[y, :] = (c, c, c)
            return fallback
        return cv2.resize(img, (CANVAS_W, CANVAS_H), interpolation=cv2.INTER_AREA)

    @staticmethod
    def _imread_unicode_safe(path: Path) -> Optional[np.ndarray]:
        # cv2.imread may fail on Windows paths with non-ASCII characters.
        try:
            data = np.fromfile(str(path), dtype=np.uint8)
            if data.size == 0:
                return None
            return cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            return None

    @staticmethod
    def _load_font(path: Path, size: int):
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            return ImageFont.load_default()

    def _load_destination_image(self, point: Dict) -> np.ndarray:
        point_id = point["id"]
        if point_id in self.destination_image_cache:
            return self.destination_image_cache[point_id]

        file_name = point.get("image", f"{point_id}.jpg")
        file_path = DESTINATIONS_DIR / file_name
        img = self._imread_unicode_safe(file_path)
        if img is None:
            # Use a subtle fallback block when destination photo is missing.
            fallback = np.zeros((220, 380, 3), dtype=np.uint8)
            fallback[:] = (20, 20, 20)
            cv2.rectangle(fallback, (0, 0), (380, 220), (48, 48, 48), 2)
            cv2.line(fallback, (20, 180), (360, 40), GOLD, 2, cv2.LINE_AA)
            cv2.circle(fallback, (70, 70), 20, GOLD, 2, cv2.LINE_AA)
            img = fallback

        self.destination_image_cache[point_id] = img
        return img

    def _draw_destination_photo(self, canvas: np.ndarray, point: Dict, x: int, y: int, w: int, h: int) -> None:
        photo = self._load_destination_image(point)
        self._paste_rounded(canvas, photo, x, y, w, h, 14)
        self._draw_rounded_border(canvas, x, y, w, h, 14, (58, 58, 58), 1)

        label_h = 24
        overlay = canvas.copy()
        cv2.rectangle(overlay, (x, y + h - label_h), (x + w, y + h), BLACK, -1)
        cv2.addWeighted(overlay, 0.55, canvas, 0.45, 0, canvas)

    def _draw_locator_widget(self, canvas: np.ndarray, point: Dict, x: int, y: int, w: int, h: int) -> None:
        overlay = canvas.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (16, 16, 16), -1)
        cv2.addWeighted(overlay, 0.8, canvas, 0.2, 0, canvas)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (52, 52, 52), 1)

        for i in range(1, 4):
            gx = x + int(i * w / 4)
            gy = y + int(i * h / 4)
            cv2.line(canvas, (gx, y + 6), (gx, y + h - 6), (36, 36, 36), 1)
            cv2.line(canvas, (x + 6, gy), (x + w - 6, gy), (36, 36, 36), 1)

        for p in self.points:
            px, py = self._point_to_pixel(p)
            nx = x + int((px / MAP_W) * (w - 16)) + 8
            ny = y + int((py / CANVAS_H) * (h - 16)) + 8
            color = GOLD if p["id"] == point["id"] else (140, 140, 140)
            r = 3 if p["id"] == point["id"] else 2
            cv2.circle(canvas, (nx, ny), r, color, -1, cv2.LINE_AA)

    def _draw_elevation_widget(self, canvas: np.ndarray, point: Dict, x: int, y: int, w: int, h: int) -> None:
        overlay = canvas.copy()
        cv2.rectangle(overlay, (x, y), (x + w, y + h), (16, 16, 16), -1)
        cv2.addWeighted(overlay, 0.8, canvas, 0.2, 0, canvas)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (52, 52, 52), 1)

        min_alt = min(int(p["altitude_m"]) for p in self.points)
        max_alt = max(int(p["altitude_m"]) for p in self.points)
        span = max(1, max_alt - min_alt)

        baseline_y = y + h - 14
        left_x = x + 10
        right_x = x + w - 10
        cv2.line(canvas, (left_x, baseline_y), (right_x, baseline_y), (62, 62, 62), 1)

        for p in self.points:
            rel = (int(p["altitude_m"]) - min_alt) / span
            px = left_x + int(rel * (right_x - left_x))
            color = GOLD if p["id"] == point["id"] else (120, 120, 120)
            bar_h = 24 if p["id"] == point["id"] else 14
            cv2.line(canvas, (px, baseline_y), (px, baseline_y - bar_h), color, 2)

    @staticmethod
    def _draw_glow(canvas: np.ndarray, center: Tuple[int, int], radius: int, color: Tuple[int, int, int], alpha: float) -> None:
        overlay = canvas.copy()
        cv2.circle(overlay, center, max(1, radius), color, -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)

    @staticmethod
    def _rounded_mask(width: int, height: int, radius: int) -> np.ndarray:
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.rectangle(mask, (radius, 0), (width - radius, height), 255, -1)
        cv2.rectangle(mask, (0, radius), (width, height - radius), 255, -1)
        cv2.circle(mask, (radius, radius), radius, 255, -1)
        cv2.circle(mask, (width - radius, radius), radius, 255, -1)
        cv2.circle(mask, (radius, height - radius), radius, 255, -1)
        cv2.circle(mask, (width - radius, height - radius), radius, 255, -1)
        return mask

    def _paste_rounded(self, canvas: np.ndarray, src: np.ndarray, x: int, y: int, w: int, h: int, radius: int) -> None:
        radius = max(2, min(radius, min(w, h) // 2))
        clip = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)
        mask = self._rounded_mask(w, h, radius)
        inv = cv2.bitwise_not(mask)

        roi = canvas[y:y + h, x:x + w]
        bg = cv2.bitwise_and(roi, roi, mask=inv)
        fg = cv2.bitwise_and(clip, clip, mask=mask)
        roi[:] = cv2.add(bg, fg)

    def _draw_rounded_border(
        self,
        canvas: np.ndarray,
        x: int,
        y: int,
        w: int,
        h: int,
        radius: int,
        color: Tuple[int, int, int],
        thickness: int,
    ) -> None:
        radius = max(2, min(radius, min(w, h) // 2))
        cv2.line(canvas, (x + radius, y), (x + w - radius, y), color, thickness, cv2.LINE_AA)
        cv2.line(canvas, (x + radius, y + h), (x + w - radius, y + h), color, thickness, cv2.LINE_AA)
        cv2.line(canvas, (x, y + radius), (x, y + h - radius), color, thickness, cv2.LINE_AA)
        cv2.line(canvas, (x + w, y + radius), (x + w, y + h - radius), color, thickness, cv2.LINE_AA)

        cv2.ellipse(canvas, (x + radius, y + radius), (radius, radius), 180, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(canvas, (x + w - radius, y + radius), (radius, radius), 270, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(canvas, (x + radius, y + h - radius), (radius, radius), 90, 0, 90, color, thickness, cv2.LINE_AA)
        cv2.ellipse(canvas, (x + w - radius, y + h - radius), (radius, radius), 0, 0, 90, color, thickness, cv2.LINE_AA)

    def _draw_glass_panel(self, canvas: np.ndarray, x: int, y: int, w: int, h: int, radius: int, alpha: float) -> None:
        overlay = canvas.copy()
        mask = self._rounded_mask(w, h, radius)
        roi = overlay[y:y + h, x:x + w]
        dark = np.zeros_like(roi)
        dark[:] = (18, 18, 18)
        blended = cv2.addWeighted(dark, 0.9, roi, 0.1, 0)
        roi[:] = np.where(mask[:, :, None] == 255, blended, roi)
        cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)

    def _latlon_to_tile(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        lat = max(-85.0, min(85.0, lat))
        lat_rad = math.radians(lat)
        n = 2.0 ** zoom
        x = int((lon + 180.0) / 360.0 * n)
        y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
        return x, y

    def _get_sat_tile(self, lat: float, lon: float, zoom: int, date_hint: Optional[str]) -> Optional[np.ndarray]:
        key = (round(lat, 4), round(lon, 4), zoom)
        if key in self.sat_cache:
            return self.sat_cache[key]
        if key in self.sat_pending:
            return None

        self.sat_pending.add(key)

        def worker() -> None:
            try:
                tile_x, tile_y = self._latlon_to_tile(lat, lon, zoom)
                layers = [
                    "MODIS_Terra_CorrectedReflectance_TrueColor",
                    "VIIRS_SNPP_CorrectedReflectance_TrueColor",
                ]

                date_candidates: List[str] = []
                if date_hint:
                    try:
                        base = datetime.strptime(date_hint, "%Y-%m-%d")
                        for offset in (0, -1, -3, -7):
                            date_candidates.append((base + timedelta(days=offset)).strftime("%Y-%m-%d"))
                    except ValueError:
                        date_candidates = []

                if not date_candidates:
                    base = datetime.utcnow()
                    for offset in (-1, -3, -7, -30):
                        date_candidates.append((base + timedelta(days=offset)).strftime("%Y-%m-%d"))

                if "2024-01-01" not in date_candidates:
                    date_candidates.append("2024-01-01")

                for date_str in date_candidates:
                    for layer in layers:
                        url = (
                            "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
                            f"{layer}/default/{date_str}/GoogleMapsCompatible_Level9/{zoom}/{tile_y}/{tile_x}.jpg"
                        )
                        try:
                            req = urllib.request.Request(url, headers={"User-Agent": "Presenta/1.0"})
                            with urllib.request.urlopen(req, timeout=3) as resp:
                                data = np.frombuffer(resp.read(), dtype=np.uint8)
                            img = cv2.imdecode(data, cv2.IMREAD_COLOR)
                            if img is not None:
                                self.sat_cache[key] = img
                                return
                        except Exception:
                            continue
            finally:
                self.sat_pending.discard(key)

        threading.Thread(target=worker, daemon=True).start()
        return None

    @staticmethod
    def _wrap_text(text: str, chars_per_line: int) -> List[str]:
        words = text.split()
        lines: List[str] = []
        current: List[str] = []

        for w in words:
            proposal = " ".join(current + [w]).strip()
            if len(proposal) <= chars_per_line:
                current.append(w)
            else:
                if current:
                    lines.append(" ".join(current))
                current = [w]

        if current:
            lines.append(" ".join(current))
        return lines


def main() -> None:
    app = GestureMapApp()
    try:
        app.run()
    except KeyboardInterrupt:
        # Allow clean exit from terminal without noisy traceback.
        pass


if __name__ == "__main__":
    main()
