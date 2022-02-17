import sys
import winreg
from pathlib import Path

import win32con
import win32gui

dog_root = Path(__file__).parent
dog_py = dog_root / 'dog.py'
dog_win32 = dog_root / 'win32'

with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as conn:
    env = winreg.OpenKey(conn, 'Environment', access=winreg.KEY_ALL_ACCESS)
    winreg.SetValueEx(
        env, 'DOG', 0, winreg.REG_SZ, '"{}" "{}"'.format(sys.executable, dog_py)
    )

    current_path, type = winreg.QueryValueEx(env, 'Path')
    if str(dog_win32) not in current_path:
        new_path = f'{current_path};{dog_win32}'
        winreg.SetValueEx(env, 'Path', 0, type, new_path)

win32gui.SendMessage(
    win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment'
)
