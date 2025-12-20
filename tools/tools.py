#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片替换工具
可视化界面，可以读取JSON文件，查看项目信息，并从剪切板替换图片
"""

import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import List, Dict, Optional

try:
    from PIL import Image, ImageTk
    from PIL import ImageGrab
except ImportError:
    print("错误：需要安装Pillow库")
    print("请运行: pip install Pillow")
    sys.exit(1)

# 导入MP3生成模块
try:
    # 添加tools目录到路径
    tools_dir = Path(__file__).parent
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from batch_generate_mp3 import MP3BatchGenerator
except ImportError as e:
    MP3BatchGenerator = None
    print(f"警告：无法导入MP3生成模块: {e}")


class ImageReplacerApp:
    """图片替换工具主应用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("图片替换工具")
        self.root.geometry("900x700")
        
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.json_file = self.data_dir / "fruits.json"
        self.data: List[Dict] = []
        self.current_item: Optional[Dict] = None
        self.current_index: Optional[int] = None
        
        # 设置中文字体
        self.setup_fonts()
        
        # 创建界面
        self.create_widgets()
        
        # 加载数据
        self.load_json()
    
    def setup_fonts(self):
        """设置支持中文的字体"""
        import platform
        
        # 根据操作系统选择合适的中文字体
        system = platform.system()
        if system == "Windows":
            # Windows系统使用微软雅黑
            self.font_normal = ("Microsoft YaHei", 10)
            self.font_bold = ("Microsoft YaHei", 12, "bold")
            self.font_large = ("Microsoft YaHei", 11)
            self.font_code = ("Consolas", 9)
        elif system == "Darwin":  # macOS
            # macOS使用PingFang SC
            self.font_normal = ("PingFang SC", 10)
            self.font_bold = ("PingFang SC", 12, "bold")
            self.font_large = ("PingFang SC", 11)
            self.font_code = ("Menlo", 9)
        else:  # Linux
            # Linux使用文泉驿或系统默认字体
            self.font_normal = ("WenQuanYi Micro Hei", 10)
            self.font_bold = ("WenQuanYi Micro Hei", 12, "bold")
            self.font_large = ("WenQuanYi Micro Hei", 11)
            self.font_code = ("DejaVu Sans Mono", 9)
        
        # 如果字体不存在，使用系统默认字体
        try:
            # 测试字体是否可用
            test_font = tk.Font(font=self.font_normal)
            test_font.actual()
        except:
            # 使用系统默认字体
            self.font_normal = ("TkDefaultFont", 10)
            self.font_bold = ("TkDefaultFont", 12, "bold")
            self.font_large = ("TkDefaultFont", 11)
            self.font_code = ("TkFixedFont", 9)
            self.font_code = ("TkFixedFont", 9)
    
    def create_widgets(self):
        """创建界面组件"""
        # 顶部：文件选择
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="JSON文件:").pack(side=tk.LEFT, padx=5)
        self.file_var = tk.StringVar(value=str(self.json_file))
        file_entry = ttk.Entry(top_frame, textvariable=self.file_var, width=50)
        file_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="浏览", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="重新加载", command=self.load_json).pack(side=tk.LEFT, padx=5)
        
        # 主内容区域：左右分栏
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：项目列表
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        ttk.Label(left_frame, text="项目列表", font=self.font_bold).pack(anchor=tk.W, pady=(0, 5))
        
        # 列表框架
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 列表和滚动条
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=self.font_large)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        scrollbar.config(command=self.listbox.yview)
        
        # 右侧：详细信息（可编辑）
        right_frame = ttk.Frame(main_frame, width=400)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False)
        right_frame.pack_propagate(False)
        
        # 标题和添加按钮
        title_frame = ttk.Frame(right_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(title_frame, text="详细信息", font=self.font_bold).pack(side=tk.LEFT)
        ttk.Button(title_frame, text="添加新项目", command=self.add_new_item).pack(side=tk.RIGHT, padx=5)
        
        # 详细信息编辑区域
        info_frame = ttk.Frame(right_frame)
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        # ID（只读）
        ttk.Label(info_frame, text="ID:").pack(anchor=tk.W, pady=(0, 2))
        self.id_var = tk.StringVar()
        id_entry = ttk.Entry(info_frame, textvariable=self.id_var, state=tk.DISABLED)
        id_entry.pack(fill=tk.X, pady=(0, 10))
        
        # 名字（可编辑）
        ttk.Label(info_frame, text="名字:").pack(anchor=tk.W, pady=(0, 2))
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(info_frame, textvariable=self.name_var)
        name_entry.pack(fill=tk.X, pady=(0, 10))
        name_entry.bind('<KeyRelease>', self.on_field_change)
        
        # 英文名字（可编辑）
        ttk.Label(info_frame, text="英文名字:").pack(anchor=tk.W, pady=(0, 2))
        self.name_english_var = tk.StringVar()
        name_english_entry = ttk.Entry(info_frame, textvariable=self.name_english_var)
        name_english_entry.pack(fill=tk.X, pady=(0, 10))
        name_english_entry.bind('<KeyRelease>', self.on_field_change)
        
        # 描述（可编辑，多行）
        ttk.Label(info_frame, text="描述:").pack(anchor=tk.W, pady=(0, 2))
        desc_frame = ttk.Frame(info_frame)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        desc_scrollbar = ttk.Scrollbar(desc_frame)
        desc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.desc_text = tk.Text(desc_frame, yscrollcommand=desc_scrollbar.set,
                                 font=self.font_normal, wrap=tk.WORD, height=6)
        self.desc_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.desc_text.bind('<KeyRelease>', self.on_field_change)
        desc_scrollbar.config(command=self.desc_text.yview)
        
        # 图片路径（只读）
        ttk.Label(info_frame, text="图片路径:").pack(anchor=tk.W, pady=(0, 2))
        self.image_path_var = tk.StringVar()
        image_entry = ttk.Entry(info_frame, textvariable=self.image_path_var, state=tk.DISABLED)
        image_entry.pack(fill=tk.X, pady=(0, 5))
        
        # 音频路径（只读）
        ttk.Label(info_frame, text="音频路径:").pack(anchor=tk.W, pady=(0, 2))
        self.audio_path_var = tk.StringVar()
        audio_entry = ttk.Entry(info_frame, textvariable=self.audio_path_var, state=tk.DISABLED)
        audio_entry.pack(fill=tk.X, pady=(0, 10))
        
        # MP3文本生成按钮
        ttk.Button(info_frame, text="生成MP3文本（复制到剪切板）", 
                   command=self.generate_mp3_text).pack(fill=tk.X, pady=(0, 5))
        
        # 生成当前项目MP3按钮
        ttk.Button(info_frame, text="生成当前项目MP3", 
                   command=self.generate_current_item_mp3).pack(fill=tk.X, pady=(0, 5))
        
        # 保存当前项目按钮
        ttk.Button(info_frame, text="保存当前项目", command=self.save_current_item).pack(fill=tk.X, pady=(0, 5))
        
        # 图片预览区域
        image_frame = ttk.LabelFrame(right_frame, text="图片预览", padding="10")
        image_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.image_label = ttk.Label(image_frame, text="无图片", anchor=tk.CENTER)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # 底部：操作按钮
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)
        
        ttk.Button(bottom_frame, text="从剪切板替换图片", 
                   command=self.replace_from_clipboard, 
                   style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="从文件选择图片", 
                   command=self.replace_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="保存JSON", 
                   command=self.save_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="批量生成MP3", 
                   command=self.batch_generate_mp3).pack(side=tk.LEFT, padx=5)
    
    def browse_file(self):
        """浏览选择JSON文件"""
        # 先保存当前项目的修改
        self.save_current_item(silent=True)
        
        file_path = filedialog.askopenfilename(
            title="选择JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialdir=str(self.data_dir)
        )
        if file_path:
            self.file_var.set(file_path)
            self.json_file = Path(file_path)
            self.load_json()
    
    def load_json(self):
        """加载JSON文件"""
        # 先保存当前项目的修改
        self.save_current_item(silent=True)
        
        json_path = Path(self.file_var.get())
        if not json_path.exists():
            messagebox.showerror("错误", f"文件不存在: {json_path}")
            return
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            self.json_file = json_path
            self.current_item = None
            self.current_index = None
            self.update_list()
            self.update_info()
            self.update_image_preview()
            #messagebox.showinfo("成功", f"已加载 {len(self.data)} 个项目")
        except Exception as e:
            messagebox.showerror("错误", f"加载JSON文件失败:\n{e}")
    
    def update_list(self):
        """更新列表显示"""
        self.listbox.delete(0, tk.END)
        for item in self.data:
            display_text = f"ID {item.get('id', 'N/A')}: {item.get('name', '未知')}"
            self.listbox.insert(tk.END, display_text)
    
    def on_select(self, event):
        """列表项选择事件"""
        # 先保存当前项目的修改
        self.save_current_item(silent=True)
        
        selection = self.listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        self.current_index = index
        self.current_item = self.data[index]
        self.update_info()
        self.update_image_preview()
    
    def on_field_change(self, event=None):
        """字段修改事件（用于实时更新列表显示）"""
        if self.current_item and self.current_index is not None:
            # 更新名字显示
            name = self.name_var.get()
            display_text = f"ID {self.current_item.get('id', 'N/A')}: {name or '未知'}"
            self.listbox.delete(self.current_index)
            self.listbox.insert(self.current_index, display_text)
            self.listbox.selection_set(self.current_index)
    
    def update_info(self):
        """更新详细信息显示"""
        if not self.current_item:
            self.id_var.set("")
            self.name_var.set("")
            self.name_english_var.set("")
            self.desc_text.delete(1.0, tk.END)
            self.image_path_var.set("")
            self.audio_path_var.set("")
            return
        
        item = self.current_item
        self.id_var.set(str(item.get('id', 'N/A')))
        self.name_var.set(item.get('name', ''))
        self.name_english_var.set(item.get('name_english', ''))
        
        self.desc_text.delete(1.0, tk.END)
        self.desc_text.insert(1.0, item.get('description', ''))
        
        self.image_path_var.set(item.get('image', 'N/A'))
        self.audio_path_var.set(item.get('audio', 'N/A'))
    
    def _get_assets_path(self):
        """根据当前JSON文件名确定assets路径"""
        json_filename = self.json_file.stem  # 获取不带扩展名的文件名
        
        # 特殊处理：music.json 使用 assets/mp3/
        if json_filename == "music":
            return "assets/mp3"
        
        # 其他图包：直接使用文件名作为assets子目录
        return f"assets/{json_filename}"
    
    def update_image_preview(self):
        """更新图片预览"""
        if not self.current_item or not self.current_item.get('image'):
            self.image_label.config(image='', text="无图片")
            return
        
        image_path = self.base_dir / self.current_item['image']
        if not image_path.exists():
            self.image_label.config(image='', text="图片文件不存在")
            return
        
        try:
            # 加载并缩放图片以适应预览区域
            img = Image.open(image_path)
            # 计算缩放比例，保持宽高比
            max_size = 300
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(img)
            self.image_label.config(image=photo, text='')
            self.image_label.image = photo  # 保持引用
        except Exception as e:
            self.image_label.config(image='', text=f"加载图片失败:\n{e}")
    
    def replace_from_clipboard(self):
        """从剪切板替换图片"""
        if not self.current_item:
            messagebox.showwarning("警告", "请先选择一个项目")
            return
        
        # 如果是新项目，确保有图片路径
        if not self.current_item.get('image'):
            item_id = self.current_item.get('id', 1)
            assets_path = self._get_assets_path()
            self.current_item['image'] = f"{assets_path}/{item_id}.JPG"
            self.image_path_var.set(self.current_item['image'])
        
        try:
            # 从剪切板获取图片
            clipboard_content = ImageGrab.grabclipboard()
            if clipboard_content is None:
                messagebox.showwarning("警告", "剪切板中没有图片")
                return
            
            # 检查返回类型：可能是 Image 对象或文件路径列表
            if isinstance(clipboard_content, list):
                # 如果是列表，尝试从第一个文件路径加载图片
                if not clipboard_content:
                    messagebox.showwarning("警告", "剪切板中的文件列表为空")
                    return
                file_path = clipboard_content[0]
                if not os.path.exists(file_path):
                    messagebox.showwarning("警告", f"剪切板中的文件路径不存在: {file_path}")
                    return
                img = Image.open(file_path)
            elif hasattr(clipboard_content, 'mode'):
                # 如果是 Image 对象，直接使用
                img = clipboard_content
            else:
                messagebox.showwarning("警告", "剪切板中的内容不是有效的图片")
                return
            
            # 确保是RGB模式
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 获取目标路径
            image_path = self.base_dir / self.current_item['image']
            image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 确保是1:1比例（如果需要）
            width, height = img.size
            if width != height:
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                img = img.crop((left, top, left + size, top + size))
                img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
            
            # 保存图片
            img.save(image_path, "JPEG", quality=70)
            
            messagebox.showinfo("成功", f"图片已替换:\n{image_path}")
            self.update_image_preview()
        except Exception as e:
            messagebox.showerror("错误", f"替换图片失败:\n{e}")
    
    def replace_from_file(self):
        """从文件选择图片替换"""
        if not self.current_item:
            messagebox.showwarning("警告", "请先选择一个项目")
            return
        
        # 如果是新项目，确保有图片路径
        if not self.current_item.get('image'):
            item_id = self.current_item.get('id', 1)
            assets_path = self._get_assets_path()
            self.current_item['image'] = f"{assets_path}/{item_id}.JPG"
            self.image_path_var.set(self.current_item['image'])
        
        file_path = filedialog.askopenfilename(
            title="选择图片文件",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp *.gif"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 打开图片
            img = Image.open(file_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 获取目标路径
            image_path = self.base_dir / self.current_item['image']
            image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 确保是1:1比例
            width, height = img.size
            if width != height:
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                img = img.crop((left, top, left + size, top + size))
                img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
            
            # 保存图片
            img.save(image_path, "JPEG", quality=95)
            
            messagebox.showinfo("成功", f"图片已替换:\n{image_path}")
            self.update_image_preview()
        except Exception as e:
            messagebox.showerror("错误", f"替换图片失败:\n{e}")
    
    def save_current_item(self, silent=False):
        """保存当前项目的修改"""
        if not self.current_item or self.current_index is None:
            return
        
        # 更新当前项目数据
        self.current_item['name'] = self.name_var.get()
        self.current_item['name_english'] = self.name_english_var.get()
        self.current_item['description'] = self.desc_text.get(1.0, tk.END).strip()
        
        # 更新列表中的数据
        self.data[self.current_index] = self.current_item
        
        # 保存整个JSON文件
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            if not silent:
                messagebox.showinfo("成功", "当前项目已保存，JSON文件已更新")
        except Exception as e:
            if not silent:
                messagebox.showerror("错误", f"保存JSON文件失败:\n{e}")
    
    def add_new_item(self):
        """添加新项目"""
        # 先保存当前项目的修改
        self.save_current_item(silent=True)
        
        # 计算新ID
        max_id = max((item.get('id', 0) for item in self.data), default=0)
        new_id = max_id + 1
        
        # 根据当前JSON文件确定assets路径
        assets_path = self._get_assets_path()
        
        # 创建新项目
        new_item = {
            "id": new_id,
            "name": "",
            "name_english": "",
            "description": "",
            "image": f"{assets_path}/{new_id}.JPG",
            "audio": f"{assets_path}/{new_id}.MP3"
        }
        
        # 添加到数据列表
        self.data.append(new_item)
        
        # 更新列表显示
        self.update_list()
        
        # 选择新项目
        new_index = len(self.data) - 1
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(new_index)
        self.listbox.see(new_index)
        
        # 更新当前项目
        self.current_index = new_index
        self.current_item = new_item
        self.update_info()
        self.update_image_preview()
        
        #messagebox.showinfo("成功", f"已添加新项目，ID: {new_id}")
    
    def generate_mp3_text(self):
        """生成MP3文本并复制到剪切板"""
        if not self.current_item:
            messagebox.showwarning("警告", "请先选择一个项目")
            return
        
        name = self.name_var.get().strip()
        name_english = self.name_english_var.get().strip()
        
        if not name:
            messagebox.showwarning("警告", "名字不能为空")
            return
        
        if not name_english:
            messagebox.showwarning("警告", "英文名字不能为空")
            return
        
        # 生成文本：name，name_english,name,name_english
        mp3_text = f"{name}，{name_english},{name},{name_english}"
        
        # 复制到剪切板
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(mp3_text)
            self.root.update()  # 确保剪切板更新
            #messagebox.showinfo("成功", f"MP3文本已复制到剪切板:\n{mp3_text}")
        except Exception as e:
            messagebox.showerror("错误", f"复制到剪切板失败:\n{e}")
    
    def generate_current_item_mp3(self):
        """生成当前项目的MP3"""
        if not self.current_item:
            messagebox.showwarning("警告", "请先选择一个项目")
            return
        
        # 先保存当前项目的修改
        self.save_current_item(silent=True)
        
        # 检查必要字段
        name = self.name_var.get().strip()
        name_english = self.name_english_var.get().strip()
        audio_path = self.current_item.get('audio', '')
        
        if not name:
            messagebox.showwarning("警告", "名字不能为空")
            return
        
        if not name_english:
            messagebox.showwarning("警告", "英文名字不能为空")
            return
        
        if not audio_path:
            messagebox.showwarning("警告", "音频路径为空")
            return
        
        # 检查MP3BatchGenerator是否可用
        if MP3BatchGenerator is None:
            messagebox.showerror("错误", "无法导入MP3生成模块，请检查依赖是否已安装")
            return
        

        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("生成MP3")
        progress_window.geometry("500x300")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # 进度显示
        progress_frame = ttk.Frame(progress_window, padding="20")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(progress_frame, text="正在生成MP3...", font=self.font_bold).pack(pady=(0, 10))
        
        status_label = ttk.Label(progress_frame, text="准备中...", font=self.font_normal)
        status_label.pack(pady=5)
        
        # 日志区域
        log_frame = ttk.Frame(progress_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        log_scrollbar = ttk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        log_text = tk.Text(log_frame, yscrollcommand=log_scrollbar.set, 
                          font=self.font_code, height=10, wrap=tk.WORD)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=log_text.yview)
        
        def log_message(message):
            """添加日志消息"""
            log_text.insert(tk.END, message + "\n")
            log_text.see(tk.END)
            progress_window.update()
        
        # 停止和关闭按钮
        button_frame = ttk.Frame(progress_frame)
        button_frame.pack(pady=(10, 0))
        
        stop_button = ttk.Button(button_frame, text="停止", 
                                state=tk.NORMAL)
        stop_button.pack(side=tk.LEFT, padx=5)
        
        close_button = ttk.Button(button_frame, text="关闭", 
                                 command=progress_window.destroy, state=tk.DISABLED)
        close_button.pack(side=tk.LEFT, padx=5)
        
        # 在后台线程中运行MP3生成
        import threading
        
        # 创建生成器实例（用于停止控制）
        generator = None
        
        def stop_generate():
            """停止生成"""
            if generator:
                generator.stop()
                log_message("\n正在停止...")
                status_label.config(text="正在停止...")
                stop_button.config(state=tk.DISABLED)
        
        stop_button.config(command=stop_generate)
        
        def run_generate():
            nonlocal generator
            try:
                config_path = self.base_dir / "tools" / "config.json"
                
                # 创建生成器
                generator = MP3BatchGenerator(str(config_path))
                
                # 准备项目数据
                item = {
                    "id": self.current_item.get('id', 0),
                    "name": name,
                    "name_english": name_english,
                    "audio": audio_path
                }
                
                log_message(f"开始处理项目 ID {item['id']}: {name} ({name_english})")
                log_message("=" * 50)
                
                # 处理单个项目
                success, message = generator.process_single_item(item, 1, 1)
                
                log_message("=" * 50)
                if generator._check_stop():
                    log_message("已停止")
                    status_label.config(text="已停止")
                    messagebox.showinfo("提示", "生成已停止")
                elif success:
                    log_message(f"✓ 生成成功: {message}")
                    status_label.config(text="生成成功！")
                    messagebox.showinfo("成功", f"MP3文件已生成:\n{audio_path}")
                else:
                    log_message(f"✗ 生成失败: {message}")
                    status_label.config(text=f"生成失败: {message}")
                    messagebox.showerror("失败", f"MP3生成失败:\n{message}")
                
            except Exception as e:
                log_message(f"错误: {e}")
                status_label.config(text=f"错误: {e}")
                import traceback
                log_message(traceback.format_exc())
                messagebox.showerror("错误", f"生成MP3时发生错误:\n{e}")
            finally:
                # 启用关闭按钮，禁用停止按钮
                close_button.config(state=tk.NORMAL)
                stop_button.config(state=tk.DISABLED)
        
        # 启动后台线程
        thread = threading.Thread(target=run_generate, daemon=True)
        thread.start()
    
    def save_json(self):
        """保存JSON文件"""
        # 先保存当前项目的修改
        self.save_current_item(silent=True)
        
        if not self.data:
            messagebox.showwarning("警告", "没有数据可保存")
            return
        
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"JSON文件已保存:\n{self.json_file}")
        except Exception as e:
            messagebox.showerror("错误", f"保存JSON文件失败:\n{e}")
    
    def batch_generate_mp3(self):
        """批量生成MP3"""
        # 先保存当前项目的修改
        self.save_current_item(silent=True)
        
        if not self.data:
            messagebox.showwarning("警告", "没有数据可处理")
            return
        
        # 确认操作
        response = messagebox.askyesno(
            "确认",
            f"将批量生成 {len(self.data)} 个项目的MP3文件。\n\n"
            "请确保：\n"
            "1. 目标TTS应用程序已打开\n"
            "2. 已正确配置 config.json 中的 mp3_generation 设置\n\n"
            "是否继续？"
        )
        if not response:
            return
        
        # 获取JSON文件名（相对于data目录）
        json_filename = self.json_file.name
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("批量生成MP3")
        progress_window.geometry("500x300")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # 进度显示
        progress_frame = ttk.Frame(progress_window, padding="20")
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(progress_frame, text="正在批量生成MP3...", font=self.font_bold).pack(pady=(0, 10))
        
        status_label = ttk.Label(progress_frame, text="准备中...", font=self.font_normal)
        status_label.pack(pady=5)
        
        progress_var = tk.StringVar(value="0/0")
        progress_label = ttk.Label(progress_frame, textvariable=progress_var, font=self.font_normal)
        progress_label.pack(pady=5)
        
        # 日志区域
        log_frame = ttk.Frame(progress_frame)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        log_scrollbar = ttk.Scrollbar(log_frame)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        log_text = tk.Text(log_frame, yscrollcommand=log_scrollbar.set, 
                          font=self.font_code, height=10, wrap=tk.WORD)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=log_text.yview)
        
        def log_message(message):
            """添加日志消息"""
            log_text.insert(tk.END, message + "\n")
            log_text.see(tk.END)
            progress_window.update()
        
        # 停止和关闭按钮
        button_frame = ttk.Frame(progress_frame)
        button_frame.pack(pady=(10, 0))
        
        stop_button = ttk.Button(button_frame, text="停止", 
                                state=tk.NORMAL)
        stop_button.pack(side=tk.LEFT, padx=5)
        
        close_button = ttk.Button(button_frame, text="关闭", 
                                 command=progress_window.destroy, state=tk.DISABLED)
        close_button.pack(side=tk.LEFT, padx=5)
        
        # 在后台线程中运行批量生成
        import threading
        
        # 创建生成器实例（用于停止控制）
        generator = None
        
        def stop_generation():
            """停止生成"""
            if generator:
                generator.stop()
                log_message("\n正在停止...")
                status_label.config(text="正在停止...")
                stop_button.config(state=tk.DISABLED)
        
        stop_button.config(command=stop_generation)
        
        def run_batch_generate():
            nonlocal generator
            try:
                config_path = self.base_dir / "tools" / "config.json"
                
                # 创建生成器
                generator = MP3BatchGenerator(str(config_path))
                
                log_message(f"开始批量生成 {len(self.data)} 个项目")
                log_message("=" * 50)
                
                # 直接调用批量生成方法
                result = generator.batch_generate(json_filename, 0, None)
                
                log_message("=" * 50)
                if generator._check_stop():
                    log_message("已停止")
                    status_label.config(text="已停止")
                elif result["failed"] == 0:
                    log_message(f"批量生成完成！成功: {result['success']}")
                    status_label.config(text="批量生成完成！")
                else:
                    log_message(f"批量生成完成！成功: {result['success']}, 失败: {result['failed']}")
                    status_label.config(text=f"完成（成功: {result['success']}, 失败: {result['failed']}）")
                
            except Exception as e:
                log_message(f"错误: {e}")
                status_label.config(text=f"错误: {e}")
                import traceback
                log_message(traceback.format_exc())
            finally:
                # 启用关闭按钮，禁用停止按钮
                close_button.config(state=tk.NORMAL)
                stop_button.config(state=tk.DISABLED)
                progress_var.set(f"完成 ({len(self.data)}/{len(self.data)})")
        
        # 启动后台线程
        thread = threading.Thread(target=run_batch_generate, daemon=True)
        thread.start()


def main():
    """主函数"""
    root = tk.Tk()
    app = ImageReplacerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

