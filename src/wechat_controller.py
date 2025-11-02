#!/usr/bin/env python3
"""
微信控制器
处理微信自动化发送消息功能。
支持NT框架（WeChat 4.0及以上版本）。
"""

import asyncio
import time
import threading
import logging
import re
from typing import Optional, Tuple, Dict, List
import pyautogui
import win32gui
import win32con
import win32api
import win32process
import win32clipboard
import psutil


class WeChatController:
    """微信自动化操作控制器，支持NT框架。"""
    
    def __init__(self):
        # 设置日志级别为DEBUG
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        # 配置 pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.3  # 减少延迟以提高性能
        self.logger.debug("WeChatController initialized with DEBUG logging")
        
        # NT框架相关配置
        self.nt_framework_support = True
        self.wechat_version = None
        self.is_nt_version = False
    
    def _detect_wechat_version(self) -> Optional[str]:
        """检测微信版本信息。"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                if proc.info['name'] and 'wechat' in proc.info['name'].lower():
                    if proc.info['exe']:
                        try:
                            # 获取文件版本信息
                            version_info = win32api.GetFileVersionInfo(proc.info['exe'], "\\")
                            version = f"{version_info['FileVersionMS'] >> 16}.{version_info['FileVersionMS'] & 0xFFFF}.{version_info['FileVersionLS'] >> 16}.{version_info['FileVersionLS'] & 0xFFFF}"
                            self.wechat_version = version
                            
                            # 检查是否为NT框架版本（4.0及以上）
                            major_version = int(version.split('.')[0])
                            if major_version >= 4:
                                self.is_nt_version = True
                                self.logger.info(f"Detected WeChat NT framework version: {version}")
                            else:
                                self.is_nt_version = False
                                self.logger.info(f"Detected WeChat legacy version: {version}")
                            
                            return version
                        except Exception as e:
                            self.logger.warning(f"Could not get version info for {proc.info['exe']}: {e}")
            
            self.logger.warning("Could not detect WeChat version")
            return None
        except Exception as e:
            self.logger.error(f"Error detecting WeChat version: {e}")
            return None
    
    def _find_wechat_window(self) -> Optional[int]:
        """查找微信主窗口句柄，支持NT框架。"""
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_text = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                
                # NT框架窗口类名检测
                nt_class_patterns = [
                    r"Qt\d+QWindowIcon",  # QT框架窗口
                    r"WeChatMainWndForPC",  # 微信主窗口
                    r"ChatWnd",  # 聊天窗口
                ]
                
                # 传统窗口检测
                legacy_patterns = ["微信", "WeChat"]
                
                # 检查NT框架窗口
                for pattern in nt_class_patterns:
                    if re.match(pattern, class_name):
                        windows.append((hwnd, "nt", class_name))
                        return True
                
                # 检查传统窗口
                for pattern in legacy_patterns:
                    if pattern in window_text:
                        windows.append((hwnd, "legacy", window_text))
                        return True
            
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        if windows:
            # 优先选择NT框架窗口
            nt_windows = [w for w in windows if w[1] == "nt"]
            if nt_windows:
                hwnd = nt_windows[0][0]
                self.logger.info(f"Found WeChat NT framework window: {hwnd} (class: {nt_windows[0][2]})")
                return hwnd
            else:
                hwnd = windows[0][0]
                self.logger.info(f"Found WeChat legacy window: {hwnd} (text: {windows[0][2]})")
                return hwnd
        else:
            self.logger.error("WeChat window not found")
            return None
    
    def _activate_window(self, hwnd: int) -> bool:
        """激活窗口并将其置于前台。"""
        try:
            # 如果窗口最小化则恢复
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            # 置于前台
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            return True
        except Exception as e:
            self.logger.error(f"Failed to activate window: {e}")
            return False
    
    def _find_and_click_input_box(self) -> bool:
        """智能定位并点击微信输入框。"""
        try:
            self.logger.info("Attempting to locate and click input box")
            
            # 获取微信窗口信息
            hwnd = self._find_wechat_window()
            if not hwnd:
                self.logger.error("WeChat window not found")
                return False
            
            # 获取窗口位置和大小
            rect = win32gui.GetWindowRect(hwnd)
            window_left, window_top, window_right, window_bottom = rect
            window_width = window_right - window_left
            window_height = window_bottom - window_top
            
            self.logger.info(f"WeChat window rect: {rect}")
            
            # 尝试多个可能的输入框位置
            input_positions = [
                # 位置1: 窗口底部中央偏下
                (window_left + window_width // 2, window_bottom - 80),
                # 位置2: 窗口底部中央
                (window_left + window_width // 2, window_bottom - 120),
                # 位置3: 窗口底部左侧
                (window_left + window_width // 3, window_bottom - 100),
                # 位置4: 窗口底部右侧
                (window_left + window_width * 2 // 3, window_bottom - 100),
                # 位置5: 屏幕中下部（备选方案）
                (pyautogui.size()[0] // 2, int(pyautogui.size()[1] * 0.85))
            ]
            
            for i, (click_x, click_y) in enumerate(input_positions, 1):
                try:
                    self.logger.info(f"Trying input position {i}: ({click_x}, {click_y})")
                    pyautogui.click(click_x, click_y)
                    time.sleep(0.5)
                    
                    # 测试是否成功获得焦点（尝试输入一个字符然后删除）
                    pyautogui.typewrite('a')
                    time.sleep(0.2)
                    pyautogui.press('backspace')
                    time.sleep(0.2)
                    
                    self.logger.info(f"Successfully clicked input box at position {i}")
                    return True
                    
                except Exception as e:
                    self.logger.warning(f"Position {i} failed: {e}")
                    continue
            
            self.logger.error("All input box positions failed")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to find and click input box: {e}")
            return False
    
    def _input_text_via_keyboard(self, text: str) -> bool:
        """通过剪贴板输入文本，确保中文字符正确处理。"""
        try:
            import win32clipboard
            
            # 保存当前剪贴板内容
            win32clipboard.OpenClipboard()
            try:
                original_data = win32clipboard.GetClipboardData()
            except:
                original_data = None
            win32clipboard.CloseClipboard()
            
            # 清空输入框
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('delete')
            time.sleep(0.2)
            
            # 设置剪贴板内容为UTF-8编码的文本
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            time.sleep(0.1)
            
            # 粘贴文本
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            
            # 恢复原始剪贴板内容
            if original_data is not None:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(original_data)
                win32clipboard.CloseClipboard()
            
            self.logger.info(f"Successfully input text via clipboard: {text}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to input text via clipboard: {e}")
            return False
    
    def _search_contact_nt(self, contact_name: str) -> bool:
        """在NT框架微信中搜索联系人。"""
        try:
            self.logger.debug(f"开始搜索联系人: {contact_name}")
            
            # 方法1: 使用全局搜索 (Ctrl+F)
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(1.0)  # 增加等待时间确保搜索框完全打开
            
            # 清空搜索框
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.press('delete')
            time.sleep(0.3)
            
            # 输入联系人姓名
            self.logger.debug(f"输入联系人名称: {contact_name}")
            if not self._input_text_via_keyboard(contact_name):
                self.logger.error("输入联系人名称失败")
                return False
                
            # 按下回车键直接搜索
            self.logger.debug("按下回车键执行搜索")
            pyautogui.press('enter')
            time.sleep(2.0)  # 增加等待时间确保搜索完成
            
            # 检查是否有搜索结果并选择第一个
            self.logger.debug("选择第一个搜索结果")
            pyautogui.press('down')
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(1.5)  # 增加等待时间确保聊天窗口打开
            
            self.logger.debug(f"成功找到并选择联系人: {contact_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to search contact in NT framework: {e}")
            return False
    
    def _search_contact_legacy(self, contact_name: str) -> bool:
        """在传统微信中搜索联系人。"""
        try:
            # 使用 Ctrl+F 打开搜索
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.5)
            
            # 清空搜索框并输入联系人姓名
            if not self._input_text_via_keyboard(contact_name):
                return False
            time.sleep(1)
            
            # 按回车键搜索
            pyautogui.press('enter')
            time.sleep(1)
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to search contact in legacy version: {e}")
            return False
    
    def _search_contact(self, contact_name: str) -> bool:
        """在微信中搜索联系人，自动适配NT框架和传统版本。"""
        if self.is_nt_version:
            return self._search_contact_nt(contact_name)
        else:
            return self._search_contact_legacy(contact_name)
    
    def _send_text_nt(self, message: str) -> bool:
        """在NT框架微信中发送文本消息。"""
        try:
            self.logger.info("Starting NT framework message send process")
            
            # 使用智能输入框定位
            if not self._find_and_click_input_box():
                self.logger.error("Failed to locate input box")
                return False
            
            # 使用键盘输入消息
            if not self._input_text_via_keyboard(message):
                self.logger.error("Failed to input message via keyboard")
                return False
            
            # 尝试多种发送方式
            send_success = False
            
            # 方式1: Enter键发送
            try:
                pyautogui.press('enter')
                time.sleep(0.8)
                self.logger.info("Attempted send with Enter key")
                send_success = True
            except Exception as e:
                self.logger.warning(f"Enter key send failed: {e}")
            
            # 方式2: 如果Enter失败，尝试Ctrl+Enter
            if not send_success:
                try:
                    pyautogui.hotkey('ctrl', 'enter')
                    time.sleep(0.8)
                    self.logger.info("Attempted send with Ctrl+Enter")
                    send_success = True
                except Exception as e:
                    self.logger.warning(f"Ctrl+Enter send failed: {e}")
            
            # 方式3: 如果还是失败，尝试Alt+S（某些版本的发送快捷键）
            if not send_success:
                try:
                    pyautogui.hotkey('alt', 's')
                    time.sleep(0.8)
                    self.logger.info("Attempted send with Alt+S")
                    send_success = True
                except Exception as e:
                    self.logger.warning(f"Alt+S send failed: {e}")
            
            if send_success:
                self.logger.info("Message sent successfully using NT framework")
                return True
            else:
                self.logger.error("All send methods failed in NT framework")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send text in NT framework: {e}")
            return False
    
    def _send_text_legacy(self, message: str) -> bool:
        """在传统微信中发送文本消息。"""
        try:
            self.logger.info("Starting legacy framework message send process")
            
            # 使用智能输入框定位
            if not self._find_and_click_input_box():
                self.logger.error("Failed to locate input box")
                return False
            
            # 使用键盘输入消息
            if not self._input_text_via_keyboard(message):
                self.logger.error("Failed to input message via keyboard")
                return False
            
            # 尝试多种发送方式
            send_success = False
            
            # 方式1: Enter键发送
            try:
                pyautogui.press('enter')
                time.sleep(0.8)
                self.logger.info("Attempted send with Enter key")
                send_success = True
            except Exception as e:
                self.logger.warning(f"Enter key send failed: {e}")
            
            # 方式2: 如果Enter失败，尝试Ctrl+Enter
            if not send_success:
                try:
                    pyautogui.hotkey('ctrl', 'enter')
                    time.sleep(0.8)
                    self.logger.info("Attempted send with Ctrl+Enter")
                    send_success = True
                except Exception as e:
                    self.logger.warning(f"Ctrl+Enter send failed: {e}")
            
            if send_success:
                self.logger.info("Message sent successfully using legacy framework")
                return True
            else:
                self.logger.error("All send methods failed in legacy framework")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to send text in legacy version: {e}")
            return False
    
    def _send_text(self, message: str) -> bool:
        """在当前聊天中发送文本消息，自动适配NT框架和传统版本。"""
        if self.is_nt_version:
            return self._send_text_nt(message)
        else:
            return self._send_text_legacy(message)
    
    async def send_text_message(self, contact_name: str, message: str) -> bool:
        """向指定联系人发送文本消息，支持NT框架。"""
        try:
            self.logger.info(f"Sending message to {contact_name}: {message}")
            
            # 检测微信版本
            version = self._detect_wechat_version()
            if version:
                self.logger.info(f"WeChat version detected: {version} (NT framework: {self.is_nt_version})")
            
            # 查找并激活微信窗口
            wechat_hwnd = self._find_wechat_window()
            if not wechat_hwnd:
                return False
            
            if not self._activate_window(wechat_hwnd):
                return False
            
            # 搜索联系人
            if not self._search_contact(contact_name):
                return False
            
            # 发送消息
            if not self._send_text(message):
                return False
            
            framework_type = "NT framework" if self.is_nt_version else "legacy"
            self.logger.info(f"Successfully sent message to {contact_name} using {framework_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return False
    
    async def schedule_message(self, contact_name: str, message: str, delay_seconds: float) -> bool:
        """安排在延迟后发送消息。"""
        try:
            self.logger.info(f"Scheduling message to {contact_name} in {delay_seconds} seconds")
            
            async def delayed_send():
                await asyncio.sleep(delay_seconds)
                # 调用异步函数
                try:
                    result = await self.send_text_message(contact_name, message)
                    self.logger.info(f"Scheduled message sent successfully: {result}")
                except Exception as e:
                    self.logger.error(f"Error in delayed send: {e}")
            
            # 创建异步任务
            asyncio.create_task(delayed_send())
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling message: {e}")
            return False
    
    def get_status(self) -> dict:
        """获取微信控制器的当前状态，包含NT框架信息。"""
        # 检测版本信息
        version = self._detect_wechat_version()
        wechat_hwnd = self._find_wechat_window()
        
        return {
            "wechat_available": wechat_hwnd is not None,
            "window_handle": wechat_hwnd,
            "wechat_version": self.wechat_version,
            "is_nt_framework": self.is_nt_version,
            "nt_framework_support": self.nt_framework_support,
            "framework_type": "NT framework (4.0+)" if self.is_nt_version else "Legacy (<4.0)"
        }