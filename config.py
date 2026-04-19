import os
import json
import win32con

CONFIG_FILE = "config.json"

KEY_NAME_MAP = {
    "VK_HOME": (win32con.VK_HOME, "Home"),
    "VK_ESCAPE": (win32con.VK_ESCAPE, "Esc"),
    "VK_SHIFT": (win32con.VK_SHIFT, "Shift"),
    "VK_CONTROL": (win32con.VK_CONTROL, "Ctrl"),
    "VK_MENU": (win32con.VK_MENU, "Alt"),
    "VK_F1": (win32con.VK_F1, "F1"),
    "VK_F2": (win32con.VK_F2, "F2"),
    "VK_F3": (win32con.VK_F3, "F3"),
    "VK_F4": (win32con.VK_F4, "F4"),
    "VK_F5": (win32con.VK_F5, "F5"),
    "VK_F6": (win32con.VK_F6, "F6"),
    "VK_F7": (win32con.VK_F7, "F7"),
    "VK_F8": (win32con.VK_F8, "F8"),
    "VK_F9": (win32con.VK_F9, "F9"),
    "VK_F10": (win32con.VK_F10, "F10"),
    "VK_F11": (win32con.VK_F11, "F11"),
    "VK_F12": (win32con.VK_F12, "F12"),
    "VK_INSERT": (win32con.VK_INSERT, "Insert"),
    "VK_DELETE": (win32con.VK_DELETE, "Delete"),
    "VK_END": (win32con.VK_END, "End"),
    "VK_PRIOR": (win32con.VK_PRIOR, "PageUp"),
    "VK_NEXT": (win32con.VK_NEXT, "PageDown"),
    "VK_PAUSE": (win32con.VK_PAUSE, "Pause"),
    "VK_NUMPAD0": (win32con.VK_NUMPAD0, "Num0"),
    "VK_NUMPAD1": (win32con.VK_NUMPAD1, "Num1"),
    "VK_NUMPAD2": (win32con.VK_NUMPAD2, "Num2"),
    "VK_NUMPAD3": (win32con.VK_NUMPAD3, "Num3"),
    "VK_NUMPAD4": (win32con.VK_NUMPAD4, "Num4"),
    "VK_NUMPAD5": (win32con.VK_NUMPAD5, "Num5"),
    "VK_NUMPAD6": (win32con.VK_NUMPAD6, "Num6"),
    "VK_NUMPAD7": (win32con.VK_NUMPAD7, "Num7"),
    "VK_NUMPAD8": (win32con.VK_NUMPAD8, "Num8"),
    "VK_NUMPAD9": (win32con.VK_NUMPAD9, "Num9"),
}

KEYBINDING_ACTIONS = {
    "toggle_panel": "隐藏/显示面板",
    "exit": "退出程序",
    "turbo_on": "极速模式开",
    "turbo_off": "极速模式关",
    "toggle_fire": "开火模式切换",
}

DEFAULT_CONFIG = {
    "sleep_time": 0.1,
    "click_time": 0.12,
    "display": False,
    "threshold": 0.3,
    "scale": 0.5,
    "size": 60,
    "keybindings": {
        "toggle_panel": "VK_HOME",
        "exit": "VK_SHIFT+VK_ESCAPE",
        "turbo_on": "VK_F6",
        "turbo_off": "VK_F5",
        "toggle_fire": "VK_F7",
    }
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            if "keybindings" in config:
                for k, v in DEFAULT_CONFIG["keybindings"].items():
                    if k not in config["keybindings"]:
                        config["keybindings"][k] = v
            return config
        except Exception as e:
            print("加载配置失败，使用默认配置。", e)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print("保存配置失败：", e)


def get_display_name(key_str):
    parts = key_str.split("+")
    names = []
    for p in parts:
        p = p.strip()
        if p in KEY_NAME_MAP:
            names.append(KEY_NAME_MAP[p][1])
        else:
            names.append(p)
    return " + ".join(names)


def resolve_keybinding(key_str):
    parts = key_str.split("+")
    codes = []
    for p in parts:
        p = p.strip()
        if p in KEY_NAME_MAP:
            codes.append(KEY_NAME_MAP[p][0])
    return codes


def check_keybinding(key_str):
    import win32api
    codes = resolve_keybinding(key_str)
    if not codes:
        return False
    return all(win32api.GetAsyncKeyState(c) < 0 for c in codes)
