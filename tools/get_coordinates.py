#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐标获取工具
帮助用户获取鼠标位置的坐标，用于配置MP3生成操作
"""

import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import pyautogui
except ImportError:
    print("错误：需要安装pyautogui库")
    print("请运行: pip install pyautogui")
    sys.exit(1)


class CoordinateGetter:
    """坐标获取器"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("坐标获取工具")
        self.root.geometry("400x300")
        self.root.attributes('-topmost', True)  # 置顶
        
        self.coordinates = []
        self.is_capturing = False
        
        self.create_widgets()
        self.start_capture()
    
    def create_widgets(self):
        """创建界面"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 说明
        info_label = ttk.Label(
            main_frame, 
            text="移动鼠标到目标位置，按 F2 键获取坐标\n"
                 "按 ESC 键停止捕获",
            font=("Microsoft YaHei", 10),
            justify=tk.LEFT
        )
        info_label.pack(pady=(0, 20))
        
        # 坐标显示区域
        coord_frame = ttk.LabelFrame(main_frame, text="获取的坐标", padding="10")
        coord_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(coord_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.coord_text = tk.Text(
            coord_frame, 
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            height=8,
            wrap=tk.WORD
        )
        self.coord_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.coord_text.yview)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame, 
            text="复制为JSON格式", 
            command=self.copy_json
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="清空", 
            command=self.clear_coordinates
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="关闭", 
            command=self.root.quit
        ).pack(side=tk.RIGHT, padx=5)
    
    def start_capture(self):
        """开始捕获坐标"""
        self.is_capturing = True
        self.root.bind('<F2>', self.capture_coordinate)
        self.root.bind('<Escape>', self.stop_capture)
        self.root.focus_set()
        print("坐标捕获已启动，按 F1 获取坐标，按 ESC 停止")
    
    def stop_capture(self, event=None):
        """停止捕获"""
        self.is_capturing = False
        self.root.unbind('<F2>')
        self.root.unbind('<Escape>')
        messagebox.showinfo("提示", "坐标捕获已停止")
    
    def capture_coordinate(self, event=None):
        """捕获当前鼠标坐标"""
        if not self.is_capturing:
            return
        
        x, y = pyautogui.position()
        self.coordinates.append((x, y))
        
        # 显示坐标
        coord_str = f"坐标 {len(self.coordinates)}: ({x}, {y})\n"
        self.coord_text.insert(tk.END, coord_str)
        self.coord_text.see(tk.END)
        
        # 更新窗口标题
        self.root.title(f"坐标获取工具 - 已获取 {len(self.coordinates)} 个坐标")
        
        print(f"已获取坐标: ({x}, {y})")
    
    def copy_json(self):
        """复制坐标为JSON格式"""
        if not self.coordinates:
            messagebox.showwarning("警告", "没有坐标可复制")
            return
        
        # 生成JSON格式
        json_lines = []
        for i, (x, y) in enumerate(self.coordinates, 1):
            json_lines.append(f'          "position": [{x}, {y}],')
        
        json_text = "\n".join(json_lines)
        
        # 复制到剪切板
        self.root.clipboard_clear()
        self.root.clipboard_append(json_text)
        self.root.update()
        
        messagebox.showinfo("成功", f"已复制 {len(self.coordinates)} 个坐标到剪切板")
    
    def clear_coordinates(self):
        """清空坐标"""
        if messagebox.askyesno("确认", "确定要清空所有坐标吗？"):
            self.coordinates = []
            self.coord_text.delete(1.0, tk.END)
            self.root.title("坐标获取工具")


def main():
    """主函数"""
    root = tk.Tk()
    app = CoordinateGetter(root)
    root.mainloop()


if __name__ == "__main__":
    main()

