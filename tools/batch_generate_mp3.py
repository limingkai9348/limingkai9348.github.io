#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量生成MP3工具
通过GUI自动化操作桌面应用程序，批量生成MP3音频文件

操作步骤配置说明：
在 config.json 的 mp3_generation.steps 中定义操作步骤，支持的步骤类型：

1. generate_text - 生成MP3文本（格式：name，name_english,name,name_english）
2. copy_to_clipboard - 复制MP3文本到剪切板
3. copy_id_to_clipboard - 复制ID到剪切板
4. activate_window - 激活目标应用程序窗口
5. click - 点击指定位置
   params: {"position": [x, y], "wait_after": 0.5}
6. paste - 粘贴文本
   params: {"wait_after": 0.5}
7. select_all - 全选（Ctrl+A）
   params: {"wait_after": 0.1}
8. delete - 删除（Delete键）
   params: {"wait_after": 0.1}
9. wait - 等待指定时间
   params: {"duration": 3}
10. hotkey - 按下快捷键
    params: {"keys": ["ctrl", "v"], "wait_after": 0.5}
11. type - 输入文本
    params: {"text": "文本内容", "wait_after": 0.5}
12. press - 按下单个键
    params: {"key": "enter", "wait_after": 0.5}
13. save_file - 保存文件
    params: {"method": "button|hotkey", "button_position": [x, y], "wait_after": 1}
14. conditional - 条件步骤（如：文件已存在时跳过）
    params: {"condition": "skip_if_exists", "steps": [...]}

示例配置请参考 config.json.example
"""

import json
import os
import sys
import time
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    import pyautogui
    import pyperclip
except ImportError:
    print("错误：缺少必要的依赖包。请运行: pip install -r requirements.txt")
    print("缺失的包: pyautogui, pyperclip")
    sys.exit(1)


class MP3BatchGenerator:
    """批量MP3生成器"""
    
    def __init__(self, config_path: str = "tools/config.json"):
        """初始化生成器"""
        self.config = self._load_config(config_path)
        self.mp3_config = self.config.get("mp3_generation", {})
        self.base_dir = Path(__file__).parent.parent
        
        # 设置pyautogui安全设置
        pyautogui.FAILSAFE = True  # 鼠标移到屏幕角落可中断
        pyautogui.PAUSE = 0.5  # 每次操作后暂停0.5秒
        
        # 获取DPI缩放比例
        self.dpi_scale = self._get_dpi_scale()
        
        # 获取坐标偏移量（如果有配置）
        self.coord_offset = self.mp3_config.get("coordinate_offset", [0, 0])
        
        # 获取坐标缩放比例（如果有配置）
        self.coord_scale = self.mp3_config.get("coordinate_scale", 1.0)
        
        # 停止标志
        self.should_stop = False
        
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"错误：配置文件 {config_path} 不存在")
            print(f"请复制 config.json.example 为 config.json 并填入配置")
            sys.exit(1)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_dpi_scale(self) -> float:
        """获取DPI缩放比例"""
        try:
            import platform
            if platform.system() == "Windows":
                try:
                    import ctypes
                    # 获取DPI感知
                    user32 = ctypes.windll.user32
                    # 获取系统DPI
                    dc = user32.GetDC(0)
                    dpi = user32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
                    user32.ReleaseDC(0, dc)
                    # 标准DPI是96，计算缩放比例
                    scale = dpi / 96.0
                    return scale
                except:
                    return 1.0
            else:
                return 1.0
        except:
            return 1.0
    
    def stop(self):
        """停止执行"""
        self.should_stop = True
        print("\n收到停止信号，将在当前步骤完成后停止...")
    
    def _check_stop(self) -> bool:
        """检查是否应该停止"""
        return self.should_stop
    
    def _adjust_coordinate(self, x: float, y: float) -> Tuple[int, int]:
        """调整坐标（处理DPI缩放和偏移）"""
        # 应用缩放
        x_scaled = x * self.coord_scale
        y_scaled = y * self.coord_scale
        
        # 应用DPI缩放（如果需要）
        use_dpi_scale = self.mp3_config.get("use_dpi_scaling", False)
        if use_dpi_scale:
            x_scaled = x_scaled * self.dpi_scale
            y_scaled = y_scaled * self.dpi_scale
        
        # 应用偏移
        x_final = int(x_scaled + self.coord_offset[0])
        y_final = int(y_scaled + self.coord_offset[1])
        
        return x_final, y_final
    
    def load_json_data(self, json_file: str) -> List[Dict]:
        """加载JSON数据"""
        json_path = self.base_dir / "data" / json_file
        if not json_path.exists():
            print(f"错误：JSON文件不存在: {json_path}")
            return []
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"错误：读取JSON文件失败: {e}")
            return []
    
    def find_app_window(self) -> bool:
        """查找并激活目标应用程序窗口"""
        window_title = self.mp3_config.get("app_window_title", "")
        if not window_title:
            print("警告：配置文件中未设置 app_window_title")
            print("将尝试手动激活窗口...")
            print("等待5秒，请手动切换到目标应用程序...")
            time.sleep(5)
            return True
        
        try:
            # 在Windows上，尝试使用pywinauto（如果可用）
            try:
                from pywinauto import Application
                app = Application(backend="win32").connect(title_re=f".*{window_title}.*")
                app.top_window().set_focus()
                time.sleep(1)
                return True
            except ImportError:
                # pywinauto未安装，使用pyautogui的方法
                pass
            except Exception:
                # 连接失败，继续尝试其他方法
                pass
            
            # 尝试使用pyautogui（在某些系统上可能可用）
            try:
                if hasattr(pyautogui, 'getWindowsWithTitle'):
                    windows = pyautogui.getWindowsWithTitle(window_title)
                    if windows:
                        window = windows[0]
                        window.activate()
                        time.sleep(1)
                        return True
            except Exception:
                pass
            
            # 如果自动定位失败，提示用户手动切换
            print(f"警告：无法自动定位窗口 '{window_title}'")
            print("请手动切换到目标应用程序")
            print("等待5秒后继续...")
            time.sleep(5)
            return True
            
        except Exception as e:
            print(f"警告：无法自动定位窗口: {e}")
            print("请手动切换到目标应用程序")
            print("等待5秒后继续...")
            time.sleep(5)
            return True
    
    def generate_mp3_text(self, name: str, name_english: str) -> str:
        """生成MP3文本格式"""
        return f"{name}{name}{name_english},{name_english} {name_english} {name_english}。"
    
    def copy_to_clipboard(self, text: str):
        """复制文本到剪切板"""
        try:
            pyperclip.copy(text)
            time.sleep(0.2)  # 等待剪切板更新
        except Exception as e:
            print(f"  错误：复制到剪切板失败 - {e}")
            raise
    
    def paste_text(self):
        """粘贴文本"""
        try:
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
        except Exception as e:
            print(f"  错误：粘贴失败 - {e}")
            raise
    
    def click_button(self, position: List[int], description: str = "按钮"):
        """点击指定位置的按钮"""
        if not position or len(position) < 2:
            print(f"  警告：{description}位置未配置")
            return False
        
        try:
            x, y = position[0], position[1]
            pyautogui.click(x, y)
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"  错误：点击{description}失败 - {e}")
            return False
    
    def wait_for_completion(self, wait_time: float):
        """等待操作完成"""
        time.sleep(wait_time)
    
    def save_file(self, item_id: int, audio_path: str) -> bool:
        """保存文件"""
        # 从audio_path提取目录和文件名
        # audio_path格式如: "assets/fruits/200.mp3"
        target_path = self.base_dir / audio_path
        target_dir = target_path.parent
        
        # 确保目录存在
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查文件是否已存在
        if target_path.exists():
            print(f"  提示：文件已存在，将被覆盖: {target_path}")
        
        # 获取保存方式配置
        save_method = self.mp3_config.get("save_method", "button")  # "button" 或 "dialog"
        
        if save_method == "button":
            # 方式1：点击保存按钮，然后处理保存对话框
            save_button_pos = self.mp3_config.get("save_button_position")
            if save_button_pos:
                if not self.click_button(save_button_pos, "保存按钮"):
                    return False
                
                # 等待保存对话框出现
                time.sleep(1)
                
                # 在保存对话框中输入文件路径
                # 先清空输入框
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                
                # 输入完整路径
                full_path = str(target_path.absolute())
                pyperclip.copy(full_path)
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                
                # 按回车确认保存
                pyautogui.press('enter')
                time.sleep(self.mp3_config.get("wait_time_after_save", 1))
            else:
                print("  警告：保存按钮位置未配置")
                return False
        elif save_method == "hotkey":
            # 方式2：使用快捷键保存（Ctrl+S）
            pyautogui.hotkey('ctrl', 's')
            time.sleep(1)
            
            # 在保存对话框中输入文件路径
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            
            full_path = str(target_path.absolute())
            pyperclip.copy(full_path)
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            
            pyautogui.press('enter')
            time.sleep(self.mp3_config.get("wait_time_after_save", 1))
        else:
            print(f"  警告：未知的保存方式: {save_method}")
            return False
        
        # 验证文件是否已保存
        # 等待一段时间让文件系统更新
        time.sleep(0.5)
        if target_path.exists():
            print(f"  ✓ 文件已保存: {target_path}")
            return True
        else:
            print(f"  ✗ 文件保存失败或路径不正确: {target_path}")
            print(f"     请检查应用程序的保存行为，可能需要调整配置")
            return False
    
    def execute_step(self, step: Dict, context: Dict) -> Tuple[bool, str]:
        """执行单个操作步骤"""
        # 在执行前检查是否应该停止
        if self._check_stop():
            return False, "用户中断"
        
        step_type = step.get("type", "")
        params = step.get("params", {})
        description = step.get("description", step_type)
        
        try:
            if step_type == "generate_text":
                # 生成文本并存储到上下文
                name = context.get("name", "")
                name_english = context.get("name_english", "")
                mp3_text = self.generate_mp3_text(name, name_english)
                context["mp3_text"] = mp3_text
                print(f"  [{description}] 生成文本: {mp3_text}")
                return True, ""
                
            elif step_type == "copy_to_clipboard":
                # 复制文本到剪切板
                text = context.get("mp3_text", "")
                if not text:
                    return False, "上下文中没有文本可复制"
                self.copy_to_clipboard(text)
                print(f"  [{description}] 已复制到剪切板")
                return True, ""
                
            elif step_type == "copy_id_to_clipboard":
                # 复制ID到剪切板
                item_id = context.get("item_id", "")
                if not item_id:
                    return False, "上下文中没有ID可复制"
                self.copy_to_clipboard(str(item_id))
                print(f"  [{description}] 已复制ID到剪切板: {item_id}")
                return True, ""
                
            elif step_type == "select_all":
                # 全选（Ctrl+A）
                pyautogui.hotkey('ctrl', 'a')
                wait_time = params.get("wait_after", 0.1)
                time.sleep(wait_time)
                print(f"  [{description}] 已全选")
                return True, ""
                
            elif step_type == "delete":
                # 删除（Delete键）
                pyautogui.press('delete')
                wait_time = params.get("wait_after", 0.1)
                time.sleep(wait_time)
                print(f"  [{description}] 已删除")
                return True, ""
                
            elif step_type == "activate_window":
                # 激活窗口
                if not self.find_app_window():
                    return False, "无法找到或激活目标应用程序窗口"
                print(f"  [{description}] 窗口已激活")
                return True, ""
                
            elif step_type == "click":
                # 点击指定位置
                position = params.get("position")
                if not position or len(position) < 2:
                    return False, f"点击位置未配置: {description}"
                x, y = position[0], position[1]
                
                # 调整坐标（处理DPI缩放和偏移）
                x_adjusted, y_adjusted = self._adjust_coordinate(x, y)
                
                pyautogui.click(x_adjusted, y_adjusted)
                wait_time = params.get("wait_after", 0.5)
                time.sleep(wait_time)
                print(f"  [{description}] 已点击位置 ({x}, {y}) -> ({x_adjusted}, {y_adjusted})")
                return True, ""
                
            elif step_type == "paste":
                # 粘贴文本
                self.paste_text()
                wait_time = params.get("wait_after", 0.5)
                time.sleep(wait_time)
                print(f"  [{description}] 已粘贴")
                return True, ""
                
            elif step_type == "wait":
                # 等待指定时间（支持中断）
                wait_time = params.get("duration", 1)
                print(f"  [{description}] 等待 {wait_time} 秒...")
                
                # 分段等待，每0.5秒检查一次是否应该停止
                elapsed = 0
                check_interval = 0.5
                while elapsed < wait_time:
                    if self._check_stop():
                        return False, "用户中断"
                    sleep_time = min(check_interval, wait_time - elapsed)
                    time.sleep(sleep_time)
                    elapsed += sleep_time
                
                return True, ""
                
            elif step_type == "hotkey":
                # 按下快捷键
                keys = params.get("keys", [])
                if not keys:
                    return False, "快捷键未配置"
                pyautogui.hotkey(*keys)
                wait_time = params.get("wait_after", 0.5)
                time.sleep(wait_time)
                print(f"  [{description}] 已按下快捷键: {'+'.join(keys)}")
                return True, ""
                
            elif step_type == "type":
                # 输入文本
                text = params.get("text", "")
                if not text:
                    # 尝试从上下文获取
                    text = context.get("mp3_text", "")
                if not text:
                    return False, "没有文本可输入"
                pyautogui.write(text, interval=0.1)
                wait_time = params.get("wait_after", 0.5)
                time.sleep(wait_time)
                print(f"  [{description}] 已输入文本")
                return True, ""
                
            elif step_type == "press":
                # 按下单个键
                key = params.get("key", "")
                if not key:
                    return False, "按键未配置"
                pyautogui.press(key)
                wait_time = params.get("wait_after", 0.5)
                time.sleep(wait_time)
                print(f"  [{description}] 已按下键: {key}")
                return True, ""
                
            elif step_type == "save_file":
                # 保存文件
                item_id = context.get("item_id", 0)
                audio_path = context.get("audio_path", "")
                if not audio_path:
                    return False, "音频路径为空"
                
                target_path = self.base_dir / audio_path
                target_dir = target_path.parent
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # 获取保存方式
                save_method = params.get("method", "dialog")  # "dialog" 或 "hotkey"
                
                if save_method == "hotkey":
                    # 使用快捷键打开保存对话框
                    pyautogui.hotkey('ctrl', 's')
                    time.sleep(1)
                elif save_method == "button":
                    # 点击保存按钮
                    save_button_pos = params.get("button_position")
                    if save_button_pos:
                        x, y = save_button_pos[0], save_button_pos[1]
                        x_adjusted, y_adjusted = self._adjust_coordinate(x, y)
                        pyautogui.click(x_adjusted, y_adjusted)
                        time.sleep(1)
                    else:
                        return False, "保存按钮位置未配置"
                
                # 在保存对话框中输入文件路径
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.2)
                
                full_path = str(target_path.absolute())
                pyperclip.copy(full_path)
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                
                # 按回车确认保存
                pyautogui.press('enter')
                wait_time = params.get("wait_after", 1)
                time.sleep(wait_time)
                
                # 验证文件是否已保存
                time.sleep(0.5)
                if target_path.exists():
                    print(f"  [{description}] ✓ 文件已保存: {target_path}")
                    return True, ""
                else:
                    print(f"  [{description}] ✗ 文件保存失败: {target_path}")
                    return False, "文件保存失败或路径不正确"
                
            elif step_type == "conditional":
                # 条件步骤：根据条件决定是否执行
                condition = params.get("condition", "always")
                if condition == "skip_if_exists":
                    audio_path = context.get("audio_path", "")
                    if audio_path:
                        target_path = self.base_dir / audio_path
                        if target_path.exists():
                            print(f"  [{description}] 跳过：文件已存在")
                            return True, "文件已存在，已跳过"
                
                # 执行子步骤
                sub_steps = params.get("steps", [])
                for sub_step in sub_steps:
                    success, msg = self.execute_step(sub_step, context)
                    if not success:
                        return False, msg
                return True, ""
                
            else:
                return False, f"未知的步骤类型: {step_type}"
                
        except Exception as e:
            return False, f"执行步骤失败: {str(e)}"
    
    def process_single_item(self, item: Dict, index: int, total: int) -> Tuple[bool, str]:
        """处理单个项目"""
        item_id = item.get('id', 'N/A')
        name = item.get('name', '').strip()
        name_english = item.get('name_english', '').strip()
        audio_path = item.get('audio', '')
        
        print(f"\n[{index}/{total}] 处理项目 ID {item_id}: {name} ({name_english})")
        
        # 检查必要字段
        if not name:
            return False, "名字为空"
        if not name_english:
            return False, "英文名字为空"
        if not audio_path:
            return False, "音频路径为空"
        
        # 检查文件是否已存在（可选：跳过已存在的文件）
        target_path = self.base_dir / audio_path
        skip_existing = self.mp3_config.get("skip_existing", False)
        if skip_existing and target_path.exists():
            print(f"  跳过：文件已存在")
            return True, "文件已存在，已跳过"
        
        # 准备上下文数据
        context = {
            "item_id": item_id,
            "name": name,
            "name_english": name_english,
            "audio_path": audio_path,
            "mp3_text": ""
        }
        
        # 获取操作步骤配置
        steps = self.mp3_config.get("steps", [])
        
        # 如果没有配置步骤，使用默认步骤（向后兼容）
        if not steps:
            print("  警告：未配置操作步骤，使用默认步骤")
            return self._process_with_default_steps(context)
        
        # 按配置的步骤顺序执行
        try:
            for step in steps:
                # 检查是否应该停止
                if self._check_stop():
                    return False, "用户中断"
                
                success, message = self.execute_step(step, context)
                if not success:
                    return False, message
            
            # 最后检查一次
            if self._check_stop():
                return False, "用户中断"
            
            return True, "成功"
            
        except Exception as e:
            if self._check_stop():
                return False, "用户中断"
            return False, f"处理失败: {str(e)}"
    
    def _process_with_default_steps(self, context: Dict) -> Tuple[bool, str]:
        """使用默认步骤处理（向后兼容）"""
        try:
            # 1. 生成文本
            mp3_text = self.generate_mp3_text(context["name"], context["name_english"])
            context["mp3_text"] = mp3_text
            print(f"  生成文本: {mp3_text}")
            
            # 2. 复制到剪切板
            self.copy_to_clipboard(mp3_text)
            
            # 3. 确保窗口激活
            if not self.find_app_window():
                return False, "无法找到或激活目标应用程序窗口"
            
            # 4. 定位输入框并粘贴
            input_pos = self.mp3_config.get("input_field_position")
            if input_pos:
                pyautogui.click(input_pos[0], input_pos[1])
                time.sleep(0.3)
            
            self.paste_text()
            
            # 5. 点击生成按钮
            generate_pos = self.mp3_config.get("generate_button_position")
            if not generate_pos:
                return False, "生成按钮位置未配置"
            
            if not self.click_button(generate_pos, "生成按钮"):
                return False, "点击生成按钮失败"
            
            # 6. 等待生成完成
            wait_time = self.mp3_config.get("wait_time_after_generate", 3)
            print(f"  等待生成完成 ({wait_time}秒)...")
            self.wait_for_completion(wait_time)
            
            # 7. 保存文件
            if not self.save_file(context["item_id"], context["audio_path"]):
                return False, "保存文件失败"
            
            return True, "成功"
            
        except Exception as e:
            return False, f"处理失败: {str(e)}"
    
    def batch_generate(self, json_file: str, start_index: int = 0, end_index: Optional[int] = None) -> Dict:
        """批量生成MP3"""
        print("=" * 60)
        print("批量生成MP3工具")
        print("=" * 60)
        
        # 加载JSON数据
        data = self.load_json_data(json_file)
        if not data:
            return {"success": 0, "failed": 0, "errors": []}
        
        # 确定处理范围
        total = len(data)
        if end_index is None:
            end_index = total
        else:
            end_index = min(end_index, total)
        
        items_to_process = data[start_index:end_index]
        actual_total = len(items_to_process)
        
        print(f"\n将处理 {actual_total} 个项目 (索引 {start_index} 到 {end_index-1})")
        print(f"目标应用程序: {self.mp3_config.get('app_window_title', '未配置')}")
        print("\n提示：请确保目标TTS应用程序已打开并准备好")
        print("5秒后开始处理...")
        time.sleep(5)
        
        # 统计结果
        success_count = 0
        failed_count = 0
        errors = []
        
        # 处理每个项目
        for i, item in enumerate(items_to_process, start=1):
            # 检查是否应该停止
            if self._check_stop():
                print("\n用户中断，停止处理")
                break
            
            success, message = self.process_single_item(item, start_index + i, total)
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                item_id = item.get('id', 'N/A')
                errors.append(f"ID {item_id}: {message}")
                
                # 如果用户中断，停止处理
                if self._check_stop() or message == "用户中断":
                    print("\n用户中断，停止处理")
                    break
            
            # 项目之间的延迟
            if i < actual_total and not self._check_stop():
                delay = self.mp3_config.get("delay_between_items", 1)
                if delay > 0:
                    time.sleep(delay)
        
        # 输出结果
        print("\n" + "=" * 60)
        print("处理完成！")
        print(f"成功: {success_count}")
        print(f"失败: {failed_count}")
        if errors:
            print("\n错误详情:")
            for error in errors:
                print(f"  - {error}")
        print("=" * 60)
        
        return {
            "success": success_count,
            "failed": failed_count,
            "errors": errors
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量生成MP3工具")
    parser.add_argument("json_file", help="JSON文件名（如: fruits.json）")
    parser.add_argument("--start", "-s", type=int, default=0, help="起始索引（默认: 0）")
    parser.add_argument("--end", "-e", type=int, help="结束索引（默认: 全部）")
    parser.add_argument("--config", "-c", default="tools/config.json", help="配置文件路径")
    
    args = parser.parse_args()
    
    try:
        generator = MP3BatchGenerator(args.config)
        result = generator.batch_generate(args.json_file, args.start, args.end)
        
        if result["failed"] > 0:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n已中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

