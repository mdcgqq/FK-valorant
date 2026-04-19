import os
import time
import tkinter as tk
from mss import mss
import cv2

from config import load_config, save_config, check_keybinding, DEFAULT_CONFIG
from detection import (
    initialize_model_and_driver, get_screen_center,
    capture_screen, detect_enemy, perform_action, perform_action_body,
)
from ui import create_control_panel, create_tk_window, display_image_with_detections

VK_RBUTTON = 0x02


def main():
    root = tk.Tk()
    config = load_config()

    sleep_time_var = tk.DoubleVar(value=config.get("sleep_time", DEFAULT_CONFIG["sleep_time"]))
    click_time = tk.DoubleVar(value=config.get("click_time", DEFAULT_CONFIG["click_time"]))
    display_var = tk.BooleanVar(value=config.get("display", DEFAULT_CONFIG["display"]))
    threshold = tk.DoubleVar(value=config.get("threshold", DEFAULT_CONFIG["threshold"]))
    scale = tk.DoubleVar(value=config.get("scale", DEFAULT_CONFIG["scale"]))
    size = tk.DoubleVar(value=config.get("size", DEFAULT_CONFIG["size"]))

    def update_config(*args):
        config["sleep_time"] = sleep_time_var.get()
        config["click_time"] = click_time.get()
        config["display"] = display_var.get()
        config["threshold"] = threshold.get()
        config["scale"] = scale.get()
        config["size"] = size.get()
        save_config(config)

    for var in (sleep_time_var, click_time, display_var, threshold, scale, size):
        var.trace_add("write", update_config)

    tk_window = create_tk_window(root, scale)
    control_panel_visible = True
    create_control_panel(root, sleep_time_var, click_time, display_var,
                         threshold, scale, size, tk_window, config)

    model, driver = initialize_model_and_driver(click_time)
    if model is None or driver is None:
        print("模型或驱动加载失败，程序退出。")
        root.destroy()
        return

    import win32api

    def _capture_all_screen():
        pass

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

        fps_state['count'] += 1
        if loop_start - fps_state['last_time'] >= 1.0:
            elapsed = loop_start - fps_state['last_time']
            fps = fps_state['count'] / elapsed if elapsed > 0 else 0
            if tk_window and hasattr(tk_window, 'fps_label'):
                tk_window.fps_label.config(text=f"FPS: {fps:.1f}")
            fps_state['count'] = 0
            fps_state['last_time'] = loop_start

        current_scale = scale.get()
        if current_scale != previous_scale:
            w = int(640 * current_scale)
            h = int(640 * current_scale)
            tk_window.geometry(f"{w}x{h}+10+280")
            previous_scale = current_scale

        def _save_img(img):
            # 1. 确保存放图片的目录存在
            # exist_ok=True 表示如果目录已经存在，不会报错
            os.makedirs("logs/imgs", exist_ok=True)
            
            # 2. 生成文件名
            # 使用时间戳作为文件名，保证每次截图的文件名唯一，不会覆盖
            # 格式例如: 1745073759.png
            filename = f"logs/imgs/{int(time.time())}.png"
            
            # 3. 保存图像
            # cv2.imwrite 可以直接保存 numpy 数组
            cv2.imwrite(filename, img)
            print(f"图片已保存: {filename}")

        if win32api.GetAsyncKeyState(VK_RBUTTON) < 0:
            # print("[右键] 检测到按下，开始截图识别...")
            img = capture_screen(sct, capture_area)
            _save_img(img)
            head, body = detect_enemy(model, img, capture_x, capture_y, threshold.get())
            # print(f"[识别] head={bool(head)}, body={bool(body)}, auto_fire={auto_fire}")
            if head and len(head) > 2:
                print(f"[动作] 瞄头 dx={head[0]:.1f} dy={head[1]:.1f}")
                perform_action(driver, *head[:2], sleep_time_var.get(), size.get(), head[2], auto_fire)
                continue
            if body and len(body) > 2:
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

        if display_var.get():
            img = capture_screen(sct, capture_area)
            head, body = detect_enemy(model, img, capture_x, capture_y, threshold.get())
            display_image_with_detections(img, head, body, scale.get(), tk_window)

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
