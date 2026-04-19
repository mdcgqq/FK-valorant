import os
import math
import time
import cv2
import numpy as np
from mss import mss
from driver import LGDriver
from ultralytics import YOLO

def initialize_model_and_driver(click_time, retries=3, delay=5):
    base_path = os.path.dirname(__file__)
    default_model_path = os.path.join(base_path, "assests", "nms", "640.onnx")
    model_path = os.getenv("MODEL_PATH", default_model_path)
    driver_path = os.path.join(base_path, 'driver/logitech.driver.dll')

    for attempt in range(retries):
        try:
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"模型文件不存在: {model_path}")
            model = YOLO(model_path, task="detect")
            driver = LGDriver(driver_path, click_time)
            return model, driver
        except Exception as e:
            print(f"模型或驱动加载失败 (尝试 {attempt + 1}/{retries}): {e}")
            if "logitech.driver.dll" in str(e):
                print("提示：请确保安装了 driver/lghub 目录中的驱动程序。")
            if "模型文件不存在" in str(e):
                print("提示：默认读取 assests/nms/640.onnx，可用 MODEL_PATH 覆盖为其他 onnx。")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                return None, None


def get_screen_center(monitor):
    return monitor['width'] // 2, monitor['height'] // 2


def capture_screen(sct, capture_area):
    screen_img = np.array(sct.grab(capture_area))
    return cv2.cvtColor(screen_img, cv2.COLOR_BGRA2BGR)


def detect_enemy(model, img, capture_x, capture_y, confidence_threshold):
    results = model.predict(img, imgsz=640, verbose=False)
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
    abs_x = abs(relative_x)
    abs_y = abs(relative_y)
    x1, y1, x2, y2 = head_xyxy
    xx = x2 - x1
    delta_size = size * (xx / 13)
    m_x = abs((x2 - x1) / 2)
    m_y = abs((y2 - y1) / 2)

    if abs_x < m_x and abs_y < m_y:
        if auto_fire:
            driver.click()
            time.sleep(sleep_time)
    else:
        if abs_x <= delta_size and abs_y <= delta_size:
            driver.move(relative_x, relative_y)
            if auto_fire:
                driver.click()
                time.sleep(sleep_time)


def perform_action_body(driver, relative_x, relative_y, sleep_time, size, body_xyxy, auto_fire=True):
    x1, y1, x2, y2 = body_xyxy
    delta_y = y2 - y1
    adjustment_factor = 0.34 + 0.1 * (1 - math.exp(-0.01 * (delta_y - 50)))
    relative_y -= delta_y * adjustment_factor
    abs_x = abs(relative_x)
    abs_y = abs(relative_y)
    xx = x2 - x1
    delta_size = size * (xx / 50)
    print(f"[瞄身判定] abs_x={abs_x:.1f} abs_y={abs_y:.1f} delta_size={delta_size:.1f} in_range={abs_x <= delta_size and abs_y <= delta_size}")

    if abs_x <= delta_size and abs_y <= delta_size:
        driver.move(relative_x, relative_y)
        if auto_fire:
            driver.click()
            time.sleep(sleep_time)
