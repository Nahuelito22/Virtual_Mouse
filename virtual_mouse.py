"""
AI Virtual Mouse — control del cursor con gestos de la mano (MediaPipe + OpenCV).
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
import pyautogui


class Mode(Enum):
    ACTIVE = auto()
    PAUSED = auto()
    SCROLL = auto()
    DRAG = auto()


@dataclass
class Config:
    cam_index: int = 0
    cam_width: int = 640
    cam_height: int = 480
    frame_reduction: int = 100
    smoothening: float = 5.0
    pinch_threshold: float = 35.0
    click_cooldown: float = 0.45
    double_click_cooldown: float = 0.7
    right_click_cooldown: float = 0.55
    exit_hold_seconds: float = 0.8
    drag_hold_seconds: float = 0.35
    scroll_sensitivity: float = 0.08
    min_detection_confidence: float = 0.7
    min_tracking_confidence: float = 0.6
    max_num_hands: int = 1
    window_name: str = "AI Virtual Mouse"


# Colores BGR
COLOR_MOUSE = (255, 0, 255)
COLOR_LEFT = (0, 255, 0)
COLOR_DOUBLE = (255, 165, 0)
COLOR_RIGHT = (0, 0, 255)
COLOR_EXIT = (0, 255, 255)
COLOR_SCROLL = (255, 200, 0)
COLOR_DRAG = (0, 200, 255)
COLOR_UI = (255, 255, 255)
COLOR_DIM = (180, 180, 180)


class GestureCooldown:
    def __init__(self) -> None:
        self._last: dict[str, float] = {}

    def ready(self, name: str, cooldown: float) -> bool:
        now = time.monotonic()
        last = self._last.get(name, 0.0)
        if now - last >= cooldown:
            self._last[name] = now
            return True
        return False


class VirtualMouse:
    def __init__(self, config: Config) -> None:
        self.cfg = config
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0

        self.screen_w, self.screen_h = pyautogui.size()
        self.cap: Optional[cv2.VideoCapture] = None
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=config.max_num_hands,
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        self.prev_x = 0.0
        self.prev_y = 0.0
        self.mode = Mode.PAUSED
        self.cooldowns = GestureCooldown()
        self.show_help = True
        self.show_landmarks = True
        self.fps = 0.0
        self._fps_counter = 0
        self._fps_timer = time.monotonic()

        self._pinch_start: Optional[float] = None
        self._exit_start: Optional[float] = None
        self._scroll_prev_y: Optional[float] = None
        self._is_dragging = False
        self._status_msg = ""
        self._status_until = 0.0

    def open_camera(self) -> None:
        self.cap = cv2.VideoCapture(self.cfg.cam_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.cfg.cam_index)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"No se pudo abrir la cámara (índice {self.cfg.cam_index}). "
                "Comprueba que esté conectada y no la use otra app."
            )
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.cam_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.cam_height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def close(self) -> None:
        if self._is_dragging:
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
            self._is_dragging = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.hands.close()
        cv2.destroyAllWindows()

    def set_status(self, msg: str, seconds: float = 1.2) -> None:
        self._status_msg = msg
        self._status_until = time.monotonic() + seconds

    @staticmethod
    def distance(p1: tuple[int, int], p2: tuple[int, int]) -> float:
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def fingers_up(self, lm, handedness: str) -> list[int]:
        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        fingers: list[int] = []

        # Pulgar: depende de mano (imagen ya espejada → lógica invertida visualmente)
        if handedness == "Right":
            fingers.append(1 if lm[tips[0]].x > lm[pips[0]].x else 0)
        else:
            fingers.append(1 if lm[tips[0]].x < lm[pips[0]].x else 0)

        for i in range(1, 5):
            fingers.append(1 if lm[tips[i]].y < lm[pips[i]].y else 0)
        return fingers

    def tip_px(self, lm, idx: int) -> tuple[int, int]:
        return (
            int(lm[idx].x * self.cfg.cam_width),
            int(lm[idx].y * self.cfg.cam_height),
        )

    def update_fps(self) -> None:
        self._fps_counter += 1
        now = time.monotonic()
        elapsed = now - self._fps_timer
        if elapsed >= 0.5:
            self.fps = self._fps_counter / elapsed
            self._fps_counter = 0
            self._fps_timer = now

    def move_cursor(self, x_index: int, y_index: int) -> None:
        fr = self.cfg.frame_reduction
        x_mapped = np.interp(x_index, (fr, self.cfg.cam_width - fr), (0, self.screen_w))
        y_mapped = np.interp(y_index, (fr, self.cfg.cam_height - fr), (0, self.screen_h))

        cur_x = self.prev_x + (x_mapped - self.prev_x) / self.cfg.smoothening
        cur_y = self.prev_y + (y_mapped - self.prev_y) / self.cfg.smoothening

        cur_x = float(np.clip(cur_x, 0, self.screen_w - 1))
        cur_y = float(np.clip(cur_y, 0, self.screen_h - 1))

        try:
            pyautogui.moveTo(cur_x, cur_y, _pause=False)
        except Exception:
            pass

        self.prev_x, self.prev_y = cur_x, cur_y

    def end_drag(self) -> None:
        if self._is_dragging:
            try:
                pyautogui.mouseUp(_pause=False)
            except Exception:
                pass
            self._is_dragging = False
            self.set_status("Drag fin")

    def handle_gestures(
        self,
        frame: np.ndarray,
        lm,
        fingers: list[int],
        handedness: str,
    ) -> bool:
        """Procesa gestos. Retorna False si hay que salir."""
        thumb = self.tip_px(lm, 4)
        index = self.tip_px(lm, 8)
        middle = self.tip_px(lm, 12)
        ring = self.tip_px(lm, 16)
        pinky = self.tip_px(lm, 20)

        # Pausa / reanudar
        if fingers == [0, 0, 0, 0, 0]:
            if self.mode != Mode.PAUSED:
                self.end_drag()
                self.mode = Mode.PAUSED
                self._pinch_start = None
                self._exit_start = None
                self._scroll_prev_y = None
            return True

        if fingers == [1, 1, 1, 1, 1] and self.mode == Mode.PAUSED:
            self.mode = Mode.ACTIVE
            self.set_status("Activo")
            return True

        if self.mode == Mode.PAUSED:
            return True

        thr = self.cfg.pinch_threshold
        dist_exit = self.distance(thumb, pinky)
        dist_left = self.distance(thumb, index)
        dist_double = self.distance(thumb, middle)
        dist_right = self.distance(thumb, ring)

        # Salir: mantener meñique + pulgar
        if dist_exit < thr and fingers[4] == 1:
            if self._exit_start is None:
                self._exit_start = time.monotonic()
            held = time.monotonic() - self._exit_start
            progress = min(held / self.cfg.exit_hold_seconds, 1.0)
            cv2.line(frame, thumb, pinky, COLOR_EXIT, 3)
            cv2.putText(
                frame,
                f"Salir {int(progress * 100)}%",
                (self.cfg.cam_width // 2 - 80, self.cfg.cam_height // 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                COLOR_EXIT,
                2,
            )
            if held >= self.cfg.exit_hold_seconds:
                self.set_status("Cerrando...")
                return False
            return True
        self._exit_start = None

        # Scroll: índice + medio arriba, resto abajo
        if fingers[1] == 1 and fingers[2] == 1 and fingers[3] == 0 and fingers[4] == 0:
            self.end_drag()
            self.mode = Mode.SCROLL
            mid_y = (index[1] + middle[1]) / 2.0
            if self._scroll_prev_y is not None:
                delta = self._scroll_prev_y - mid_y
                amount = int(delta * self.cfg.scroll_sensitivity * 10)
                if abs(amount) >= 1:
                    try:
                        pyautogui.scroll(amount, _pause=False)
                    except Exception:
                        pass
            self._scroll_prev_y = mid_y
            cv2.line(frame, index, middle, COLOR_SCROLL, 2)
            cv2.putText(frame, "SCROLL", (index[0] - 20, index[1] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_SCROLL, 2)
            return True
        self._scroll_prev_y = None
        if self.mode == Mode.SCROLL:
            self.mode = Mode.ACTIVE

        # Clics por pellizco (prioridad: left/drag > double > right)
        pinching_left = dist_left < thr
        pinching_double = dist_double < thr and not pinching_left
        pinching_right = dist_right < thr and not pinching_left and not pinching_double

        if pinching_left:
            cv2.circle(frame, index, 12, COLOR_LEFT, cv2.FILLED)
            cv2.line(frame, thumb, index, COLOR_LEFT, 2)
            if self._pinch_start is None:
                self._pinch_start = time.monotonic()
            held = time.monotonic() - self._pinch_start

            if held >= self.cfg.drag_hold_seconds:
                if not self._is_dragging:
                    try:
                        pyautogui.mouseDown(_pause=False)
                    except Exception:
                        pass
                    self._is_dragging = True
                    self.mode = Mode.DRAG
                    self.set_status("Drag")
                self.move_cursor(index[0], index[1])
                cv2.putText(frame, "DRAG", (index[0] - 10, index[1] - 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_DRAG, 2)
            else:
                # Solo mueve mientras carga el drag
                self.move_cursor(index[0], index[1])
            return True

        # Soltó el pellizco izquierdo
        if self._pinch_start is not None and not pinching_left:
            held = time.monotonic() - self._pinch_start
            if self._is_dragging:
                self.end_drag()
                self.mode = Mode.ACTIVE
            elif held < self.cfg.drag_hold_seconds:
                if self.cooldowns.ready("left", self.cfg.click_cooldown):
                    try:
                        pyautogui.click(_pause=False)
                    except Exception:
                        pass
                    self.set_status("Clic izq")
            self._pinch_start = None

        if pinching_double:
            cv2.circle(frame, middle, 12, COLOR_DOUBLE, cv2.FILLED)
            cv2.line(frame, thumb, middle, COLOR_DOUBLE, 2)
            if self.cooldowns.ready("double", self.cfg.double_click_cooldown):
                try:
                    pyautogui.doubleClick(_pause=False)
                except Exception:
                    pass
                self.set_status("Doble clic")
            return True

        if pinching_right:
            cv2.circle(frame, ring, 12, COLOR_RIGHT, cv2.FILLED)
            cv2.line(frame, thumb, ring, COLOR_RIGHT, 2)
            if self.cooldowns.ready("right", self.cfg.right_click_cooldown):
                try:
                    pyautogui.rightClick(_pause=False)
                except Exception:
                    pass
                self.set_status("Clic der")
            return True

        # Movimiento normal: índice arriba
        if fingers[1] == 1:
            self.mode = Mode.ACTIVE
            fr = self.cfg.frame_reduction
            cv2.rectangle(
                frame,
                (fr, fr),
                (self.cfg.cam_width - fr, self.cfg.cam_height - fr),
                COLOR_MOUSE,
                2,
            )
            cv2.circle(frame, index, 8, COLOR_MOUSE, cv2.FILLED)
            self.move_cursor(index[0], index[1])

        return True

    def draw_ui(self, frame: np.ndarray) -> None:
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 70), (20, 20, 20), cv2.FILLED)
        cv2.rectangle(overlay, (0, h - 50), (w, h), (20, 20, 20), cv2.FILLED)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        mode_colors = {
            Mode.ACTIVE: (0, 220, 0),
            Mode.PAUSED: (0, 0, 220),
            Mode.SCROLL: COLOR_SCROLL,
            Mode.DRAG: COLOR_DRAG,
        }
        mode_labels = {
            Mode.ACTIVE: "ACTIVO",
            Mode.PAUSED: "PAUSADO",
            Mode.SCROLL: "SCROLL",
            Mode.DRAG: "DRAG",
        }
        color = mode_colors[self.mode]
        label = mode_labels[self.mode]

        cv2.circle(frame, (28, 35), 10, color, cv2.FILLED)
        cv2.putText(frame, label, (48, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
        cv2.putText(
            frame,
            f"{self.fps:.0f} FPS",
            (w - 110, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            COLOR_UI,
            2,
        )

        if time.monotonic() < self._status_until and self._status_msg:
            cv2.putText(
                frame,
                self._status_msg,
                (w // 2 - 60, 42),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                COLOR_UI,
                2,
            )

        if self.mode == Mode.PAUSED:
            hint = "Abre la mano para activar  |  Q salir  |  H ayuda"
        else:
            hint = "Puno=pausa | Indice=mover | Pinch=clic | Ind+Med=scroll | Q=salir"
        cv2.putText(frame, hint, (12, h - 18), cv2.FONT_HERSHEY_PLAIN, 1.05, COLOR_DIM, 1)

        if self.show_help:
            lines = [
                "GESTOS",
                "Indice arriba ........ mover",
                "Pulgar+Indice ........ clic / drag",
                "Pulgar+Medio ......... doble clic",
                "Pulgar+Anular ........ clic derecho",
                "Indice+Medio ......... scroll",
                "Pulgar+Menique (hold) salir",
                "Puno / mano abierta .. pausa / activo",
                "",
                "TECLAS",
                "Q  salir   H  ayuda   L  landmarks",
                "+/- suavizado",
            ]
            box_h = 22 * len(lines) + 20
            box_w = 320
            x0, y0 = w - box_w - 10, 80
            panel = frame.copy()
            cv2.rectangle(panel, (x0, y0), (x0 + box_w, y0 + box_h), (15, 15, 15), cv2.FILLED)
            cv2.addWeighted(panel, 0.75, frame, 0.25, 0, frame)
            for i, line in enumerate(lines):
                col = COLOR_UI if i == 0 or line == "TECLAS" else COLOR_DIM
                thick = 2 if i == 0 or line == "TECLAS" else 1
                cv2.putText(
                    frame,
                    line,
                    (x0 + 12, y0 + 22 + i * 22),
                    cv2.FONT_HERSHEY_PLAIN,
                    1.1,
                    col,
                    thick,
                )

    def handle_keys(self, key: int) -> bool:
        """Retorna False si hay que salir."""
        if key in (ord("q"), ord("Q"), 27):
            return False
        if key in (ord("h"), ord("H")):
            self.show_help = not self.show_help
        elif key in (ord("l"), ord("L")):
            self.show_landmarks = not self.show_landmarks
        elif key in (ord("+"), ord("=")):
            self.cfg.smoothening = min(20.0, self.cfg.smoothening + 1)
            self.set_status(f"Suave {self.cfg.smoothening:.0f}")
        elif key in (ord("-"), ord("_")):
            self.cfg.smoothening = max(1.0, self.cfg.smoothening - 1)
            self.set_status(f"Suave {self.cfg.smoothening:.0f}")
        return True

    def run(self) -> int:
        try:
            self.open_camera()
        except RuntimeError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1

        print("AI Virtual Mouse iniciado. Q = salir | H = ayuda")
        print(f"Pantalla: {self.screen_w}x{self.screen_h} | Camara: {self.cfg.cam_index}")

        try:
            while True:
                assert self.cap is not None
                ok, frame = self.cap.read()
                if not ok or frame is None:
                    self.set_status("Sin frame de camara", 0.5)
                    if cv2.waitKey(30) & 0xFF in (ord("q"), ord("Q"), 27):
                        break
                    continue

                # Ajustar tamaño si la cámara no respeta el request
                if frame.shape[1] != self.cfg.cam_width or frame.shape[0] != self.cfg.cam_height:
                    frame = cv2.resize(frame, (self.cfg.cam_width, self.cfg.cam_height))

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                results = self.hands.process(rgb)
                rgb.flags.writeable = True

                keep_running = True
                if results.multi_hand_landmarks:
                    hand_landmarks = results.multi_hand_landmarks[0]
                    lm = hand_landmarks.landmark

                    # Imagen espejada: la etiqueta de MediaPipe queda invertida
                    handedness = "Right"
                    if results.multi_handedness:
                        raw = results.multi_handedness[0].classification[0].label
                        handedness = "Left" if raw == "Right" else "Right"

                    if self.show_landmarks:
                        self.mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp.solutions.hands.HAND_CONNECTIONS,
                            self.mp_styles.get_default_hand_landmarks_style(),
                            self.mp_styles.get_default_hand_connections_style(),
                        )

                    fingers = self.fingers_up(lm, handedness)
                    keep_running = self.handle_gestures(frame, lm, fingers, handedness)
                else:
                    self.end_drag()
                    self._pinch_start = None
                    self._exit_start = None
                    self._scroll_prev_y = None

                self.update_fps()
                self.draw_ui(frame)
                cv2.imshow(self.cfg.window_name, frame)

                key = cv2.waitKey(1) & 0xFF
                if not keep_running or not self.handle_keys(key):
                    break
        except KeyboardInterrupt:
            print("\nInterrumpido por el usuario.")
        finally:
            self.close()

        print("AI Virtual Mouse cerrado.")
        return 0


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Virtual Mouse — controla el cursor con gestos de la mano.",
    )
    parser.add_argument("--camera", "-c", type=int, default=0, help="Índice de la cámara (default: 0)")
    parser.add_argument("--width", type=int, default=640, help="Ancho de captura")
    parser.add_argument("--height", type=int, default=480, help="Alto de captura")
    parser.add_argument("--smooth", type=float, default=5.0, help="Factor de suavizado (1-20)")
    parser.add_argument("--pinch", type=float, default=35.0, help="Umbral de pellizco en px")
    parser.add_argument("--no-help", action="store_true", help="Ocultar panel de ayuda al inicio")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    cfg = Config(
        cam_index=args.camera,
        cam_width=args.width,
        cam_height=args.height,
        smoothening=max(1.0, args.smooth),
        pinch_threshold=args.pinch,
    )
    app = VirtualMouse(cfg)
    if args.no_help:
        app.show_help = False
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
