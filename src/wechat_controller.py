#!/usr/bin/env python3
"""
微信控制器
处理微信自动化发送消息功能。
仅支持 NT 架构（WeChat 4.0+）；低于 4.0 的版本直接跳过。
"""

import asyncio
import io
import logging
import sys
import time
from typing import Any, Dict, Optional

import psutil
import pyautogui
import win32api
import win32con
import win32gui
import win32clipboard

class WeChatController:
    """微信自动化操作控制器（仅 NT 版本）。"""
    
    def __init__(self):
        # 设置日志级别为DEBUG
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.3

        self.wechat_version: Optional[str] = None
        self.is_nt_version: bool = False
        self._last_window_kind: Optional[str] = None
        self._detect_wechat_version()

    def _detect_wechat_version(self) -> Optional[str]:
        try:
            window_hwnd = self._find_wechat_window()
            window_is_nt = self._last_window_kind == "nt" and window_hwnd is not None

            for proc in psutil.process_iter(['name', 'exe']):
                name = proc.info.get('name') or ""
                if 'wechat' not in name.lower():
                    continue

                exe = proc.info.get('exe')
                if not exe:
                    continue

                version_info = win32api.GetFileVersionInfo(exe, "\\")
                version = f"{version_info['FileVersionMS'] >> 16}.{version_info['FileVersionMS'] & 0xFFFF}.{version_info['FileVersionLS'] >> 16}.{version_info['FileVersionLS'] & 0xFFFF}"
                self.wechat_version = version

                try:
                    major_version = int(version.split('.')[0])
                except Exception:
                    major_version = 0

                self.is_nt_version = window_is_nt or major_version >= 4
                if self.is_nt_version and major_version >= 4:
                    self.logger.info(f"Detected WeChat NT framework version: {version}")
                elif self.is_nt_version and window_is_nt:
                    self.logger.info(f"Detected WeChat NT framework window (file version: {version})")
                else:
                    self.logger.info(f"Detected WeChat legacy version (<4.0): {version} (will be skipped)")
                return version

            self.logger.warning("Could not detect WeChat process/version")
            self.wechat_version = None
            self.is_nt_version = window_is_nt
            return None
        except Exception as e:
            self.logger.error(f"Error detecting WeChat version: {e}")
            self.wechat_version = None
            self.is_nt_version = False
            return None

    def _find_wechat_window(self) -> Optional[int]:
        import re

        nt_windows = []
        legacy_windows = []

        def enum_windows_callback(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return True
            class_name = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)

            nt_class_patterns = [
                r"Qt\d+QWindowIcon",
                r"WeChatMainWndForPC",
                r"ChatWnd",
            ]
            for pattern in nt_class_patterns:
                if re.match(pattern, class_name):
                    nt_windows.append(hwnd)
                    return True

            if "微信" in window_text or "WeChat" in window_text:
                legacy_windows.append(hwnd)
            return True

        win32gui.EnumWindows(enum_windows_callback, None)
        if nt_windows:
            self._last_window_kind = "nt"
            return nt_windows[0]
        if legacy_windows:
            self._last_window_kind = "legacy"
            return legacy_windows[0]
        self._last_window_kind = None
        return None

    def _activate_window(self, hwnd: int) -> bool:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            return True
        except Exception as e:
            self.logger.error(f"Failed to activate window: {e}")
            return False

    def _find_and_click_input_box(self) -> bool:
        try:
            hwnd = self._find_wechat_window()
            if not hwnd:
                self.logger.error("WeChat window not found")
                return False

            rect = win32gui.GetWindowRect(hwnd)
            window_left, window_top, window_right, window_bottom = rect
            window_width = window_right - window_left

            input_positions = [
                (window_left + window_width // 2, window_bottom - 80),
                (window_left + window_width // 2, window_bottom - 120),
                (window_left + window_width // 3, window_bottom - 100),
                (window_left + window_width * 2 // 3, window_bottom - 100),
                (pyautogui.size()[0] // 2, int(pyautogui.size()[1] * 0.85)),
            ]

            for click_x, click_y in input_positions:
                try:
                    pyautogui.click(int(click_x), int(click_y))
                    time.sleep(0.4)
                    pyautogui.typewrite('a')
                    time.sleep(0.1)
                    pyautogui.press('backspace')
                    time.sleep(0.1)
                    return True
                except Exception:
                    continue

            self.logger.error("All input box positions failed")
            return False
        except Exception as e:
            self.logger.error(f"Failed to locate input box: {e}")
            return False

    def _paste_text_via_clipboard(self, text: str) -> Optional[str]:
        original_data: Optional[str] = None
        win32clipboard.OpenClipboard()
        try:
            try:
                data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                if isinstance(data, str):
                    original_data = data
            except Exception:
                original_data = None
        finally:
            win32clipboard.CloseClipboard()

        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.12)
        pyautogui.press('delete')
        time.sleep(0.25)

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()

        time.sleep(0.25)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.6)
        return original_data

    def _restore_clipboard(self, original_data: Optional[str]) -> None:
        if not original_data:
            return
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_data, win32clipboard.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception:
            return

    def _input_text_via_clipboard(self, text: str) -> bool:
        try:
            original_data = self._paste_text_via_clipboard(text)
            self._restore_clipboard(original_data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to input text via clipboard: {e}")
            return False

    def _search_contact_nt(self, contact_name: str) -> bool:
        original_data: Optional[str] = None
        try:
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(1.0)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.press('delete')
            time.sleep(0.2)

            original_data = self._paste_text_via_clipboard(contact_name)

            pyautogui.press('enter')
            time.sleep(1.0)

            pyautogui.press('enter')
            time.sleep(1.2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to search contact in NT: {e}")
            return False
        finally:
            self._restore_clipboard(original_data)

    def _send_text_nt(self, message: str) -> bool:
        try:
            if not self._find_and_click_input_box():
                try:
                    pyautogui.press('esc')
                    time.sleep(0.15)
                except Exception:
                    pass
                if not self._find_and_click_input_box():
                    return False

            original_data = self._paste_text_via_clipboard(message)

            try:
                pyautogui.press('enter')
                time.sleep(0.6)
                self._restore_clipboard(original_data)
                return True
            except Exception:
                try:
                    pyautogui.hotkey('ctrl', 'enter')
                    time.sleep(0.6)
                    self._restore_clipboard(original_data)
                    return True
                except Exception:
                    try:
                        pyautogui.hotkey('alt', 's')
                        time.sleep(0.6)
                        self._restore_clipboard(original_data)
                        return True
                    except Exception:
                        return False
        except Exception as e:
            self.logger.error(f"Failed to send text in NT: {e}")
            return False
    
    async def send_text_message(self, contact_name: str, message: str) -> Dict[str, Any]:
        """向指定联系人发送文本消息。"""
        result: Dict[str, Any] = {
            "ok": False,
            "contact_name": contact_name,
            "wechat_version": None,
            "is_nt_framework": False,
            "stage": None,
            "reason": None,
            "retry_used": None,
        }
        try:
            version = self._detect_wechat_version()
            result["wechat_version"] = version
            result["is_nt_framework"] = self.is_nt_version

            if not self.is_nt_version:
                result["stage"] = "version_check"
                result["reason"] = "non_nt_version_skipped"
                return result

            hwnd = self._find_wechat_window()
            if not hwnd:
                result["stage"] = "find_window"
                result["reason"] = "wechat_window_not_found"
                return result

            if not self._activate_window(hwnd):
                result["stage"] = "activate_window"
                result["reason"] = "failed_to_activate_window"
                return result
            if not self._search_contact_nt(contact_name):
                result["stage"] = "search_contact"
                result["reason"] = "search_failed"
                return result

            if self._send_text_nt(message):
                result["ok"] = True
                result["stage"] = "send_text"
                result["reason"] = None
                return result

            result["stage"] = "send_text"
            result["reason"] = "send_failed"
            return result

        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            result["stage"] = result["stage"] or "exception"
            result["reason"] = str(e)
            return result
    
    async def schedule_message(self, contact_name: str, message: str, delay_seconds: float) -> bool:
        """安排在延迟后发送消息。"""
        try:
            self.logger.info(f"Scheduling message to {contact_name} in {delay_seconds} seconds")
            
            async def delayed_send():
                await asyncio.sleep(delay_seconds)
                # 调用异步函数
                try:
                    await self.send_text_message(contact_name, message)
                except Exception as e:
                    self.logger.error(f"Error in delayed send: {e}")
            
            # 创建异步任务
            asyncio.create_task(delayed_send())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling message: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取微信控制器的当前状态。"""
        try:
            version = self._detect_wechat_version()
            hwnd = self._find_wechat_window()
            return {
                "wechat_available": hwnd is not None,
                "window_handle": hwnd,
                "wechat_version": version,
                "is_nt_framework": self.is_nt_version,
                "supported": self.is_nt_version,
                "framework_type": "NT framework (4.0+)" if self.is_nt_version else "Legacy (<4.0, skipped)"
            }
        except Exception as e:
            self.logger.error(f"Error checking status: {e}")
            return {
                "wechat_available": False,
                "error": str(e)
            }
