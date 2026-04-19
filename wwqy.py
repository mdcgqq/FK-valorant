import os
import time
import tkinter as tk

import win32api
from mss import mss

from config import DEFAULT_CONFIG, check_keybinding, load_config, save_config
from detection import (
    capture_screen,
    detect_enemy,
    get_screen_center,
    initialize_model_and_driver,
    perform_action,
    perform_action_body,
)
from ui import create_control_panel

VK_RBUTTON = 0x02


def main():
    root = tk.Tk()
    config = load_config()

    sleep_time_var = tk.DoubleVar(value=config.get("sleep_time", DEFAULT_CONFIG["sleep_time"]))
    click_time = tk.DoubleVar(value=config.get("click_time", DEFAULT_CONFIG["click_time"]))
    threshold = tk.DoubleVar(value=config.get("threshold", DEFAULT_CONFIG["threshold"]))
    scale = tk.DoubleVar(value=config.get("scale", DEFAULT_CONFIG["scale"]))
    size = tk.DoubleVar(value=config.get("size", DEFAULT_CONFIG["size"]))
    smooth_speed = tk.DoubleVar(value=config.get("smooth_speed", DEFAULT_CONFIG["smooth_speed"]))

    def update_config(*args):
        config["sleep_time"] = sleep_time_var.get()
        config["click_time"] = click_time.get()
        config["threshold"] = threshold.get()
        config["scale"] = scale.get()
        config["size"] = size.get()
        config["smooth_speed"] = smooth_speed.get()
        save_config(config)

    for var in (sleep_time_var, click_time, threshold, scale, size, smooth_speed):
        var.trace_add("write", update_config)

    control_panel_visible = True
    create_control_panel(
        root,
        sleep_time_var,
        click_time,
        threshold,
        scale,
        size,
        smooth_speed,
        config,
    )

    model, driver = initialize_model_and_driver(click_time, smooth_speed)
    if model is None or driver is None:
        print("模型或驱动加载失败，程序退出。")
        root.destroy()
        return

    capture_x = 640
    capture_y = 640
    sct = mss()
    monitor = sct.monitors[1]
    screen_center_x, screen_center_y = get_screen_center(monitor)
    left = screen_center_x - capture_x // 2
    top = screen_center_y - capture_y // 2
    capture_area = {'top': top, 'left': left, 'width': capture_x, 'height': capture_y}

    previous_scale = scale.get()
    target_fps = 100
    frame_interval = 1.0 / target_fps
    fps_state = {'last_time': time.time(), 'count': 0}
    auto_fire = True

    while True:
        loop_start = time.time()
        head = []
        body = []

        fps_state['count'] += 1
        if loop_start - fps_state['last_time'] >= 1.0:
            elapsed = loop_start - fps_state['last_time']
            fps = fps_state['count'] / elapsed if elapsed > 0 else 0
            fps_state['count'] = 0
            fps_state['last_time'] = loop_start

        current_scale = scale.get()
        if current_scale != previous_scale:
            previous_scale = current_scale

        is_aiming = win32api.GetAsyncKeyState(VK_RBUTTON) < 0
        if is_aiming:
            frame_img = capture_screen(sct, capture_area)
            head, body = detect_enemy(model, frame_img, capture_x, capture_y, threshold.get())

            if head and len(head) > 2:
                print(f"[动作] 瞄头 dx={head[0]:.1f} dy={head[1]:.1f}")
                perform_action(driver, *head[:2], sleep_time_var.get(), size.get(), head[2], auto_fire)
            elif body and len(body) > 2:
                print(f"[动作] 瞄身 dx={body[0]:.1f} dy={body[1]:.1f}")
                perform_action_body(driver, *body[:2], sleep_time_var.get(), size.get(), body[2], auto_fire)

        kb = config.get("keybindings", {})

        if check_keybinding(kb.get("turbo_on", "")):
            click_time.set(0.01)
            size.set(80)

        if check_keybinding(kb.get("turbo_off", "")):
            click_time.set(0.12)
            size.set(60)

        if check_keybinding(kb.get("toggle_fire", "")):
            auto_fire = not auto_fire
            print(f"开火模式: {'开启' if auto_fire else '关闭（仅跟踪）'}")
            time.sleep(0.2)

        if check_keybinding(kb.get("toggle_panel", "")):
            if control_panel_visible:
                root.withdraw()
            else:
                root.deiconify()
            control_panel_visible = not control_panel_visible
            time.sleep(0.2)

        if check_keybinding(kb.get("exit", "")):
            print("退出程序中...")
            break

        root.update_idletasks()
        root.update()

        remaining = frame_interval - (time.time() - loop_start)
        if remaining > 0:
            time.sleep(remaining)


if __name__ == "__main__":
    print("主进程PID:", os.getpid())
    main()
