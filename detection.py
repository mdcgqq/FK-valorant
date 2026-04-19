import os
import sys
import math
import time
import cv2
import torch
import numpy as np
from mss import mss
from driver import LGDriver


def initialize_model_and_driver(click_time, retries=3, delay=5):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    repo_path = os.path.join(base_path, './yolov5-master')
    model_path = os.path.join(base_path, 'runs/train/exp3/weights/best.pt')
    driver_path = os.path.join(base_path, 'driver/logitech.driver.dll')
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    for attempt in range(retries):
        try:
            model = torch.hub.load(repo_or_dir=repo_path,
                                   model='custom',
                                   path=model_path,
                                   source='local').to(device)
            driver = LGDriver(driver_path, click_time)
            return model, driver
        except Exception as e:
            print(f"模型或驱动加载失败 (尝试 {attempt + 1}/{retries}): {e}")
            if "logitech.driver.dll" in str(e):
                print("提示：请确保安装了 driver/lghub 目录中的驱动程序。")
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
    results = model(img, size=640)
    detections = results.xyxy[0].cpu().numpy()
    enemy_head_results = []
    enemy_results = []

    for *xyxy, conf, cls in detections:
        if conf < confidence_threshold:
            continue
        center_x = (xyxy[0] + xyxy[2]) / 2
        center_y = (xyxy[1] + xyxy[3]) / 2
        relative_x = center_x - capture_x // 2
        relative_y = center_y - capture_y // 2
        distance_to_center = np.sqrt(relative_x ** 2 + relative_y ** 2)
        if model.names[int(cls)] == 'enemy_head':
            enemy_head_results.append((relative_x, relative_y + 4, xyxy, conf, distance_to_center))
        elif model.names[int(cls)] == 'enemy':
            enemy_results.append((relative_x, relative_y, xyxy, conf, distance_to_center))

    closest_enemy_head = min(enemy_head_results, key=lambda x: x[4])[:4] if enemy_head_results else []
    closest_enemy = min(enemy_results, key=lambda x: x[4])[:4] if enemy_results else []
    return closest_enemy_head, closest_enemy


def perform_action(driver, relative_x, relative_y, sleep_time, size, head_xyxy):
    abs_x = abs(relative_x)
    abs_y = abs(relative_y)
    x1, y1, x2, y2 = head_xyxy
    xx = x2 - x1
    delta_size = size * (xx / 13)
    m_x = abs((x2 - x1) / 2)
    m_y = abs((y2 - y1) / 2)

    if abs_x < m_x and abs_y < m_y:
        driver.click()
        time.sleep(sleep_time)
    else:
        if abs_x <= delta_size and abs_y <= delta_size:
            driver.move(relative_x, relative_y)
            driver.click()
            time.sleep(sleep_time)


def perform_action_body(driver, relative_x, relative_y, sleep_time, size, body_xyxy):
    x1, y1, x2, y2 = body_xyxy
    delta_y = y2 - y1
    adjustment_factor = 0.34 + 0.1 * (1 - math.exp(-0.01 * (delta_y - 50)))
    relative_y -= delta_y * adjustment_factor
    abs_x = abs(relative_x)
    abs_y = abs(relative_y)
    xx = x2 - x1
    delta_size = size * (xx / 50)

    if abs_x <= delta_size and abs_y <= delta_size:
        driver.move(relative_x, relative_y)
        driver.click()
        time.sleep(sleep_time)
