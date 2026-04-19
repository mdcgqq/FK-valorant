import os
import tkinter as tk
import cv2
from PIL import Image, ImageTk
from config import (
    KEY_NAME_MAP, KEYBINDING_ACTIONS, get_display_name, save_config,
)

# win32con 虚拟键码 -> KEY_NAME_MAP 键名 的反向映射
_VK_TO_NAME = {}
for _name, (_code, _label) in KEY_NAME_MAP.items():
    _VK_TO_NAME[_code] = _name

# tkinter keysym -> VK 名称 映射（用于按键监听）
_KEYSYM_TO_VK = {
    "Home": "VK_HOME", "Escape": "VK_ESCAPE",
    "Shift_L": "VK_SHIFT", "Shift_R": "VK_SHIFT",
    "Control_L": "VK_CONTROL", "Control_R": "VK_CONTROL",
    "Alt_L": "VK_MENU", "Alt_R": "VK_MENU",
    "Insert": "VK_INSERT", "Delete": "VK_DELETE",
    "End": "VK_END", "Prior": "VK_PRIOR", "Next": "VK_NEXT",
    "Pause": "VK_PAUSE",
    "F1": "VK_F1", "F2": "VK_F2", "F3": "VK_F3", "F4": "VK_F4",
    "F5": "VK_F5", "F6": "VK_F6", "F7": "VK_F7", "F8": "VK_F8",
    "F9": "VK_F9", "F10": "VK_F10", "F11": "VK_F11", "F12": "VK_F12",
    "KP_0": "VK_NUMPAD0", "KP_1": "VK_NUMPAD1",
    "KP_2": "VK_NUMPAD2", "KP_3": "VK_NUMPAD3",
    "KP_4": "VK_NUMPAD4", "KP_5": "VK_NUMPAD5",
    "KP_6": "VK_NUMPAD6", "KP_7": "VK_NUMPAD7",
    "KP_8": "VK_NUMPAD8", "KP_9": "VK_NUMPAD9",
}

MODIFIER_KEYSYMS = {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R"}


def create_control_panel(root, sleep_time_var, click_time, display_var,
                         threshold, scale, size, smooth_speed, tk_window, config):
    root.geometry("280x320+10+25")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.5)

    frame = tk.Frame(root, bg="black")
    frame.pack(fill="both", expand=True)

    label_config = {"fg": "white", "bg": "black", "font": ("Arial", 12)}
    button_config = {"bg": "black", "fg": "white", "font": ("Arial", 12)}

    labels = [
        ("弹道恢复:", sleep_time_var),
        ("射击时间:", click_time),
        ("识别精度:", threshold),
        ("瞄准范围:", size),
        ("窗口大小:", scale),
        ("平滑速度:", smooth_speed),
    ]

    for i, (text, var) in enumerate(labels):
        tk.Label(frame, text=text, **label_config).grid(row=i, column=1, padx=5, pady=5)
        tk.Label(frame, textvariable=var, **label_config).grid(row=i, column=2, padx=5, pady=5)

    def create_buttons(row, b_var, min_val, max_val, step, round_digits=2):
        tk.Button(frame, text=" + ",
                  command=lambda: b_var.set(min(round(b_var.get() + step, round_digits), max_val)),
                  **button_config).grid(row=row, column=3, padx=5, pady=5)
        tk.Button(frame, text=" - ",
                  command=lambda: b_var.set(max(round(b_var.get() - step, round_digits), min_val)),
                  **button_config).grid(row=row, column=0, padx=5, pady=5)

    create_buttons(0, sleep_time_var, 0.01, 0.25, 0.01)
    create_buttons(1, click_time, 0.01, 0.25, 0.01)
    create_buttons(2, threshold, 0.1, 1.0, 0.1, 1)
    create_buttons(3, size, 10, 200, 10, 0)
    create_buttons(4, scale, 0.1, 1.0, 0.1, 1)
    create_buttons(5, smooth_speed, 0.2, 3.0, 0.1, 1)

    def toggle_display():
        display_var.set(not display_var.get())
        tk_window.withdraw() if not display_var.get() else tk_window.deiconify()

    btn_row = 6
    tk.Button(frame, text="显示/隐藏", command=toggle_display,
              **button_config).grid(row=btn_row, column=0, columnspan=2, padx=2, pady=5)

    def quit_app():
        root.destroy()
        os._exit(0)

    tk.Button(frame, text="退出", command=quit_app,
              bg="red", fg="white", font=("Arial", 12)
              ).grid(row=btn_row, column=2, padx=2, pady=5)

    def open_keybinding_window():
        create_keybinding_window(root, config)

    tk.Button(frame, text="快捷键", command=open_keybinding_window,
              **button_config).grid(row=btn_row, column=3, padx=2, pady=5)


def create_keybinding_window(root, config):
    win = tk.Toplevel(root)
    win.title("快捷键设置")
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-alpha", 0.85)
    win.configure(bg="black")
    win.geometry("320x220+10+310")

    frame = tk.Frame(win, bg="black")
    frame.pack(fill="both", expand=True, padx=8, pady=8)

    label_cfg = {"fg": "white", "bg": "black", "font": ("Arial", 10)}
    btn_cfg = {"bg": "#333", "fg": "white", "font": ("Arial", 9), "width": 6}

    keybindings = config.get("keybindings", {})
    rows = {}

    for i, (action, label) in enumerate(KEYBINDING_ACTIONS.items()):
        tk.Label(frame, text=label, **label_cfg).grid(row=i, column=0, sticky="w", padx=4, pady=4)

        current = keybindings.get(action, "")
        key_label = tk.Label(frame, text=get_display_name(current), fg="#00ff00", bg="black",
                             font=("Arial", 10), width=14, anchor="w")
        key_label.grid(row=i, column=1, padx=4, pady=4)

        btn = tk.Button(frame, text="修改", **btn_cfg)
        btn.grid(row=i, column=2, padx=4, pady=4)
        rows[action] = (key_label, btn)

        btn.configure(command=lambda a=action: start_listening(a))

    listening_state = {"action": None, "modifiers": set()}

    def start_listening(action):
        if listening_state["action"]:
            return
        listening_state["action"] = action
        listening_state["modifiers"] = set()
        key_label, btn = rows[action]
        key_label.config(text="请按键...", fg="yellow")
        btn.config(state="disabled")
        win.focus_force()
        win.bind("<KeyPress>", on_key_press)
        win.bind("<KeyRelease>", on_key_release)

    def on_key_press(event):
        action = listening_state["action"]
        if not action:
            return
        keysym = event.keysym
        if keysym in MODIFIER_KEYSYMS:
            vk = _KEYSYM_TO_VK.get(keysym)
            if vk:
                listening_state["modifiers"].add(vk)
            return

        vk = _KEYSYM_TO_VK.get(keysym)
        if not vk:
            return

        parts = sorted(listening_state["modifiers"]) + [vk]
        new_binding = "+".join(parts)

        keybindings[action] = new_binding
        config["keybindings"] = keybindings
        save_config(config)

        finish_listening(action, new_binding)

    def on_key_release(event):
        keysym = event.keysym
        vk = _KEYSYM_TO_VK.get(keysym)
        if vk:
            listening_state["modifiers"].discard(vk)

    def finish_listening(action, new_binding):
        listening_state["action"] = None
        listening_state["modifiers"] = set()
        win.unbind("<KeyPress>")
        win.unbind("<KeyRelease>")
        key_label, btn = rows[action]
        key_label.config(text=get_display_name(new_binding), fg="#00ff00")
        btn.config(state="normal")

    close_btn = tk.Button(frame, text="关闭", command=win.destroy,
                          bg="#555", fg="white", font=("Arial", 10))
    close_btn.grid(row=len(KEYBINDING_ACTIONS), column=0, columnspan=3, pady=8)


def create_tk_window(root, scale):
    width = int(640 * scale.get())
    height = int(640 * scale.get())

    tk_window = tk.Toplevel(root)
    tk_window.overrideredirect(True)
    tk_window.attributes("-topmost", True)
    tk_window.geometry(f"{width}x{height}+10+280")
    tk_window.attributes("-alpha", 1)
    tk_window.withdraw()

    tk_window.img_label = tk.Label(tk_window)
    tk_window.img_label.pack(fill="both", expand=True)

    tk_window.fps_label = tk.Label(tk_window, text="FPS: 0", fg="white", bg="black")
    tk_window.fps_label.place(relx=0.1, rely=0.1, anchor=tk.CENTER)

    return tk_window


def display_image_with_detections(img, closest_enemy_head, closest_enemy, scale, tk_window):
    if closest_enemy_head:
        _, _, xyxy, conf = closest_enemy_head
        x1, y1, x2, y2 = map(int, xyxy)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(img, f"Enemy Head : {conf:0.3}", (x1, y1 - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 1, cv2.LINE_AA)

    if closest_enemy:
        _, _, xyxy, conf = closest_enemy
        x1, y1, x2, y2 = map(int, xyxy)
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(img, f"Enemy : {conf:0.3}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1, cv2.LINE_AA)

    height, width = img.shape[:2]
    resized_img = cv2.resize(img, (int(width * scale), int(height * scale)))
    image = Image.fromarray(cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB))
    tk_img = ImageTk.PhotoImage(image)
    tk_window.img_label.config(image=tk_img)
    tk_window.img_label.image = tk_img
