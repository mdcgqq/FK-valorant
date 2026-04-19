import os
import math
import time
import cv2
import numpy as np
from driver import LGDriver
from ultralytics import YOLO


def _resolve_model_path(base_path):
    env_model_path = os.getenv("MODEL_PATH", "").strip()
    if env_model_path:
        return env_model_path

    model_size = os.getenv("MODEL_SIZE", "640").strip()
    candidate = os.path.join(base_path, "assests", "nms", f"{model_size}.onnx")
    if os.path.exists(candidate):
        return candidate

    # Fallback to 640 as yolo26 default export
    return os.path.join(base_path, "assests", "nms", "640.onnx")


def _infer_imgsz_from_model_path(model_path, default_size=640):
    stem = os.path.splitext(os.path.basename(model_path))[0]
    return int(stem) if stem.isdigit() else default_size


def initialize_model_and_driver(click_time, smooth_speed=None, retries=3, delay=5):
    base_path = os.path.dirname(__file__)
    model_path = _resolve_model_path(base_path)
    model_imgsz = _infer_imgsz_from_model_path(model_path)
    driver_path = os.path.join(base_path, 'driver/logitech.driver.dll')

    for attempt in range(retries):
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"模型文件不存在: {model_path}")
            model = YOLO(model_path, task="detect")
            model.fk_imgsz = model_imgsz
            print(f"[模型] 已加载 yolo26 ONNX: {model_path} (imgsz={model_imgsz})")
            driver = LGDriver(driver_path, click_time, smooth_speed)
            return model, driver
        except Exception as e:
            print(f"模型或驱动加载失败 (尝试 {attempt + 1}/{retries}): {e}")
            if "logitech.driver.dll" in str(e):
                print("提示：请确保安装了 driver/lghub 目录中的驱动程序。")
            if "模型文件不存在" in str(e):
                print("提示：默认读取 assests/nms/640.onnx，可用 MODEL_PATH 或 MODEL_SIZE 覆盖。")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return None, None


def get_screen_center(monitor):
    return (
        monitor.get('left', 0) + monitor['width'] // 2,
        monitor.get('top', 0) + monitor['height'] // 2,
    )


def capture_screen(sct, capture_area):
    screen_img = np.array(sct.grab(capture_area))
    return cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)


def _clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def _calculate_smoothed_move(relative_x, relative_y, gain_x, gain_y, max_step, deadzone):
    if abs(relative_x) <= deadzone:
        move_x = 0
    else:
        move_x = int(round(_clamp(relative_x * gain_x, -max_step, max_step)))
        if move_x == 0:
            move_x = 1 if relative_x > 0 else -1

    if abs(relative_y) <= deadzone:
        move_y = 0
    else:
        move_y = int(round(_clamp(relative_y * gain_y, -max_step, max_step)))
        if move_y == 0:
            move_y = 1 if relative_y > 0 else -1

    return move_x, move_y


def _trigger_shot(driver, sleep_time, auto_fire):
    if auto_fire:
        driver.click()
        time.sleep(sleep_time)


def detect_enemy(model, img, capture_x, capture_y, confidence_threshold):
    infer_size = getattr(model, "fk_imgsz", 640)
    results = model.predict(img, imgsz=infer_size, verbose=False)
    first = results[0]
    boxes = first.boxes
    xyxy = boxes.xyxy.cpu().numpy() if boxes is not None and boxes.xyxy is not None else np.empty((0, 4))
    conf = boxes.conf.cpu().numpy() if boxes is not None and boxes.conf is not None else np.empty((0,))
    cls = boxes.cls.cpu().numpy() if boxes is not None and boxes.cls is not None else np.empty((0,))
    if len(xyxy) > 0:
        detections = np.hstack((xyxy, conf.reshape(-1, 1), cls.reshape(-1, 1)))
    else:
        detections = np.empty((0, 6))
    names = first.names
    if len(detections) > 0:
        print(f"[模型] 检测数={len(detections)}")
        for *xyxy, conf, cls in detections:
            print(f"  -> {names[int(cls)]} conf={conf:.3f} {'✓' if conf >= confidence_threshold else '✗'}")
    enemy_head_results = []
    enemy_results = []

    for *xyxy, conf, cls in detections:
        class_name = str(names[int(cls)]).strip().lower()
        center_x = (xyxy[0] + xyxy[2]) / 2
        center_y = (xyxy[1] + xyxy[3]) / 2
        relative_x = center_x - capture_x // 2
        relative_y = center_y - capture_y // 2
        distance_to_center = np.sqrt(relative_x ** 2 + relative_y ** 2)
        if conf >= confidence_threshold and class_name in ('enemy_head', 'head'):
            enemy_head_results.append((relative_x, relative_y + 4, xyxy, conf, distance_to_center))
        elif conf >= confidence_threshold and class_name in ('enemy', 'body'):
            enemy_results.append((relative_x, relative_y, xyxy, conf, distance_to_center))

    closest_enemy_head = min(enemy_head_results, key=lambda x: x[4])[:4] if enemy_head_results else []
    closest_enemy = min(enemy_results, key=lambda x: x[4])[:4] if enemy_results else []
    return closest_enemy_head, closest_enemy


def perform_action(driver, relative_x, relative_y, sleep_time, size, head_xyxy, auto_fire=True):
    x1, y1, x2, y2 = head_xyxy
    head_width = x2 - x1
    head_height = y2 - y1
    delta_size = max(size * (head_width / 13), 20)
    center_window_x = max(head_width / 2, 3)
    center_window_y = max(head_height / 2, 3)
    abs_x = abs(relative_x)
    abs_y = abs(relative_y)

    if abs_x < center_window_x and abs_y < center_window_y:
        _trigger_shot(driver, sleep_time, auto_fire)
        return

    if abs_x <= delta_size and abs_y <= delta_size:
        move_x, move_y = _calculate_smoothed_move(
            relative_x,
            relative_y,
            gain_x=0.24,
            gain_y=0.22,
            max_step=30,
            deadzone=3,
        )
        print(
            f"[瞄头判定] abs_x={abs_x:.1f} abs_y={abs_y:.1f} "
            f"delta_size={delta_size:.1f} move_x={move_x} move_y={move_y}"
        )
        if move_x != 0 or move_y != 0:
            driver.smooth_move(move_x, move_y)
        if abs_x <= center_window_x + 2 and abs_y <= center_window_y + 2:
            _trigger_shot(driver, sleep_time, auto_fire)


def perform_action_body(driver, relative_x, relative_y, sleep_time, size, body_xyxy, auto_fire=True):
    x1, y1, x2, y2 = body_xyxy
    delta_y = y2 - y1
    adjustment_factor = 0.34 + 0.1 * (1 - math.exp(-0.01 * (delta_y - 50)))
    relative_y -= delta_y * adjustment_factor
    abs_x = abs(relative_x)
    abs_y = abs(relative_y)
    body_width = x2 - x1
    delta_size = max(size * (body_width / 50), 18)
    in_range = abs_x <= delta_size and abs_y <= delta_size
    print(f"[瞄身判定] abs_x={abs_x:.1f} abs_y={abs_y:.1f} delta_size={delta_size:.1f} in_range={in_range}")

    if in_range:
        move_x, move_y = _calculate_smoothed_move(
            relative_x,
            relative_y,
            gain_x=0.22,
            gain_y=0.20,
            max_step=28,
            deadzone=4,
        )
        print(f"[瞄身移动] move_x={move_x} move_y={move_y}")
        if move_x != 0 or move_y != 0:
            driver.smooth_move(move_x, move_y)
        if abs_x <= 6 and abs_y <= 6:
            _trigger_shot(driver, sleep_time, auto_fire)
