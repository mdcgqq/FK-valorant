import math
import ctypes
import time
import random


class LGDriver:
    def __init__(self, dll_path, click_time, smooth_speed=None):
        self.click_time = click_time
        self.smooth_speed = smooth_speed
        self.lg_driver = ctypes.CDLL(dll_path)
        self.ok = self.lg_driver.device_open() == 1
        if not self.ok:
            raise Exception("驱动加载失败!")

    def press(self, code):
        if not self.ok:
            return
        self.lg_driver.mouse_down(code)

    def release(self, code):
        if not self.ok:
            return
        self.lg_driver.mouse_up(code)

    def click(self, code=1):
        if not self.ok:
            return
        self.lg_driver.mouse_down(code)
        click_time = self.click_time.get()
        time_variation = random.uniform(-0.02, 0.03)
        adjusted_click_time = max(click_time + time_variation, 0)
        self.microsecond_sleep(adjusted_click_time * 1000)
        self.lg_driver.mouse_up(code)

    def scroll(self, a):
        if not self.ok:
            return
        self.lg_driver.scroll(a)

    def move(self, x, y):
        if not self.ok:
            return
        if x == 0 and y == 0:
            return
        self.lg_driver.moveR(int(x), int(y), True)

    @staticmethod
    def microsecond_sleep(sleep_time):
        kernel32 = ctypes.WinDLL('kernel32')
        freq = ctypes.c_int64()
        start = ctypes.c_int64()
        end = ctypes.c_int64()
        kernel32.QueryPerformanceFrequency(ctypes.byref(freq))
        kernel32.QueryPerformanceCounter(ctypes.byref(start))
        target_ticks = int(freq.value * sleep_time / 1e6)
        while True:
            kernel32.QueryPerformanceCounter(ctypes.byref(end))
            if end.value - start.value >= target_ticks:
                break

    def smooth_move(self, x, y, min_steps=5, max_steps=20, scale_factor=5):
        if not self.ok:
            return
        if x == 0 and y == 0:
            return
        speed_multiplier = self.smooth_speed.get() if self.smooth_speed is not None else 1.0
        speed_multiplier = max(speed_multiplier, 0.1)
        scaled_min_steps = max(1, int(round(min_steps / speed_multiplier)))
        scaled_max_steps = max(scaled_min_steps, int(round(max_steps / speed_multiplier)))
        scaled_scale_factor = max(scale_factor * speed_multiplier, 0.5)
        distance = math.sqrt(x ** 2 + y ** 2)
        steps = int(min(max(distance / scaled_scale_factor, scaled_min_steps), scaled_max_steps))
        error_x = 0.0
        error_y = 0.0
        step_x_float = x / steps
        step_y_float = y / steps
        for _ in range(steps):
            error_x += step_x_float
            error_y += step_y_float
            move_x = int(round(error_x))
            move_y = int(round(error_y))
            error_x -= move_x
            error_y -= move_y
            self.lg_driver.moveR(move_x, move_y, True)
            self.microsecond_sleep(2000)
