#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI内容生成工具
根据输入的水果/物品名字列表，自动生成描述、图片、音频和JSON文件
"""

import json
import os
import sys
import argparse
import time
from pathlib import Path
from typing import List, Dict, Optional

try:
    from openai import OpenAI
    import edge_tts
    from pydub import AudioSegment
    from pydub.effects import normalize
    import requests
    from PIL import Image
except ImportError as e:
    print(f"错误：缺少必要的依赖包。请运行: pip install -r requirements.txt")
    print(f"缺失的包: {e}")
    sys.exit(1)


class ContentGenerator:
    """内容生成器主类"""
    
    def __init__(self, config_path: str = "tools/config.json"):
        """初始化生成器"""
        self.config = self._load_config(config_path)
        self.client = OpenAI(api_key=self.config.get("openai_api_key"))
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.assets_dir = self.base_dir / "assets" / "fruits"
        
        # 确保目录存在
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"错误：配置文件 {config_path} 不存在")
            print(f"请复制 config.json.example 为 config.json 并填入API密钥")
            sys.exit(1)
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_max_id(self, json_file: str = "fruits.json") -> int:
        """获取现有JSON文件中的最大ID"""
        json_path = self.data_dir / json_file
        if not json_path.exists():
            return 0
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not data:
                    return 0
                return max(item.get("id", 0) for item in data)
        except Exception as e:
            print(f"警告：读取现有JSON文件失败: {e}")
            return 0
    
    def load_existing_data(self, json_file: str = "fruits.json") -> List[Dict]:
        """加载现有的JSON数据"""
        json_path = self.data_dir / json_file
        if not json_path.exists():
            return []
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告：读取现有JSON文件失败: {e}")
            return []
    
    def save_json(self, data: List[Dict], json_file: str = "fruits.json"):
        """保存JSON数据"""
        json_path = self.data_dir / json_file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def generate_description(self, name: str) -> Optional[str]:
        """使用OpenAI生成描述"""
        try:
            prompt = f"请为{name}生成一段适合儿童学习的简短描述，50-100字，要求语言简单易懂，生动有趣。"
            response = self.client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {"role": "system", "content": "你是一个专业的儿童教育内容创作者。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  错误：生成描述失败 - {e}")
            return None
    
    def get_english_name(self, chinese_name: str) -> Optional[str]:
        """获取英文名字"""
        try:
            prompt = f"请给出'{chinese_name}'的英文名字，只返回英文单词，不要其他解释。"
            response = self.client.chat.completions.create(
                model=self.config.get("openai_model", "gpt-4"),
                messages=[
                    {"role": "system", "content": "你是一个翻译助手，只返回英文单词。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )
            english_name = response.choices[0].message.content.strip()
            # 清理可能的引号或其他符号
            english_name = english_name.strip('"').strip("'").strip()
            return english_name
        except Exception as e:
            print(f"  错误：获取英文名字失败 - {e}")
            return None
    
    def generate_image(self, name: str, item_id: int) -> Optional[str]:
        """生成图片"""
        try:
            # 判断物品类型，生成环境提示词
            # 简单判断：常见的水果和蔬菜关键词
            fruits_keywords = ["果", "莓", "瓜", "桃", "梨", "橘", "橙", "柚", "柑", "李", "杏", "枣", "榴", "芒", "荔", "龙眼", "枇杷"]
            vegetables_keywords = ["菜", "萝卜", "白菜", "菠菜", "芹菜", "韭菜", "葱", "蒜", "姜", "椒", "茄", "豆", "瓜", "薯", "芋", "莲藕"]
            
            is_fruit_or_vegetable = any(keyword in name for keyword in fruits_keywords + vegetables_keywords)
            
            if is_fruit_or_vegetable:
                prompt = f"一个清晰的{name}图片，显示在它的自然生长环境中（如树上、田间、菜园等），适合儿童识物卡片，真实场景，高质量摄影"
            else:
                prompt = f"一个清晰的{name}图片，显示在实际使用场景中，适合儿童识物卡片，真实场景，高质量摄影"
            
            print(f"  生成图片提示词: {prompt}")
            
            response = self.client.images.generate(
                model=self.config.get("image_model", "dall-e-3"),
                prompt=prompt,
                size=self.config.get("image_size", "1024x1024"),
                quality=self.config.get("image_quality", "standard"),
                n=1
            )
            
            image_url = response.data[0].url
            image_path = self.assets_dir / f"{item_id}.jpg"
            
            # 下载图片
            img_response = requests.get(image_url)
            img_response.raise_for_status()
            
            # 保存图片
            with open(image_path, 'wb') as f:
                f.write(img_response.content)
            
            # 确保是1:1比例，使用PIL处理
            img = Image.open(image_path)
            # 如果是正方形，直接保存；如果不是，裁剪为正方形
            width, height = img.size
            if width != height:
                size = min(width, height)
                left = (width - size) // 2
                top = (height - size) // 2
                img = img.crop((left, top, left + size, top + size))
                img = img.resize((1024, 1024), Image.Resampling.LANCZOS)
            
            img.save(image_path, "JPEG", quality=95)
            
            return f"assets/fruits/{item_id}.jpg"
        except Exception as e:
            print(f"  错误：生成图片失败 - {e}")
            return None
    
    def generate_audio(self, chinese_name: str, english_name: str, item_id: int) -> Optional[str]:
        """生成中英文双语音频"""
        try:
            # 生成1秒静音
            silence = AudioSegment.silent(duration=1000)  # 1000毫秒 = 1秒
            
            # 生成中文语音
            print(f"  生成中文语音: {chinese_name}")
            chinese_audio = self._tts_to_audio(chinese_name, "zh-CN-XiaoxiaoNeural")
            
            # 生成英文语音
            print(f"  生成英文语音: {english_name}")
            english_audio = self._tts_to_audio(english_name, "en-US-AriaNeural")
            
            # 合成音频：中文 -> 1秒静音 -> 英文 -> 1秒静音 -> 中文 -> 1秒静音 -> 英文
            combined = chinese_audio + silence + english_audio + silence + chinese_audio + silence + english_audio
            
            # 标准化音量
            combined = normalize(combined)
            
            # 保存为MP3
            audio_path = self.assets_dir / f"{item_id}.mp3"
            combined.export(str(audio_path), format="mp3", bitrate="128k")
            
            return f"assets/fruits/{item_id}.mp3"
        except Exception as e:
            print(f"  错误：生成音频失败 - {e}")
            return None
    
    def _tts_to_audio(self, text: str, voice: str) -> AudioSegment:
        """使用Edge TTS生成音频并转换为AudioSegment"""
        import tempfile
        import asyncio
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 使用edge_tts生成音频（异步）
            async def generate():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(tmp_path)
            
            # 运行异步函数
            # 尝试获取现有事件循环，如果没有则创建新的
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(generate())
            except RuntimeError:
                # 如果没有事件循环，使用asyncio.run
                asyncio.run(generate())
            
            # 加载为AudioSegment
            audio = AudioSegment.from_mp3(tmp_path)
            return audio
        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def process_item(self, name: str, item_id: int, existing_names: set) -> Optional[Dict]:
        """处理单个物品"""
        print(f"\n处理: {name} (ID: {item_id})")
        
        # 检查是否已存在
        if name in existing_names:
            print(f"  跳过：{name} 已存在")
            return None
        
        # 生成描述
        print(f"  生成描述...")
        description = self.generate_description(name)
        if not description:
            return None
        
        # 获取英文名字
        print(f"  获取英文名字...")
        english_name = self.get_english_name(name)
        if not english_name:
            return None
        print(f"  英文名字: {english_name}")
        
        # 生成图片
        print(f"  生成图片...")
        image_path = self.generate_image(name, item_id)
        if not image_path:
            return None
        
        # 生成音频
        print(f"  生成音频...")
        audio_path = self.generate_audio(name, english_name, item_id)
        if not audio_path:
            # 如果音频生成失败，删除已生成的图片
            img_file = self.assets_dir / f"{item_id}.jpg"
            if img_file.exists():
                img_file.unlink()
            return None
        
        return {
            "id": item_id,
            "name": name,
            "image": image_path,
            "audio": audio_path,
            "description": description
        }
    
    def generate(self, names: List[str], json_file: str = "fruits.json", append: bool = False):
        """生成内容"""
        # 加载现有数据
        existing_data = self.load_existing_data(json_file) if append else []
        existing_names = {item["name"] for item in existing_data}
        
        # 获取起始ID
        start_id = self.get_max_id(json_file) + 1 if append else 1
        
        # 处理每个物品
        new_items = []
        failed_items = []
        
        for i, name in enumerate(names, start=1):
            item_id = start_id + len(new_items)
            
            try:
                item = self.process_item(name, item_id, existing_names)
                if item:
                    new_items.append(item)
                    existing_names.add(name)
                    print(f"  ✓ 完成")
                else:
                    failed_items.append(name)
                    print(f"  ✗ 失败")
            except Exception as e:
                print(f"  ✗ 处理失败: {e}")
                failed_items.append(name)
            
            # 添加延迟避免API限流
            if i < len(names):
                time.sleep(2)
        
        # 合并数据
        if append:
            all_data = existing_data + new_items
        else:
            all_data = new_items
        
        # 保存JSON
        if all_data:
            self.save_json(all_data, json_file)
            print(f"\n✓ 已保存 {len(new_items)} 个新项目到 {json_file}")
        
        # 报告失败的项目
        if failed_items:
            print(f"\n✗ 以下项目生成失败: {', '.join(failed_items)}")
        
        return len(new_items), len(failed_items)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI内容生成工具")
    parser.add_argument("names", nargs="*", help="物品名字列表")
    parser.add_argument("--file", "-f", help="从文件读取名字列表（每行一个）")
    parser.add_argument("--append", "-a", action="store_true", help="追加到现有JSON文件")
    parser.add_argument("--json", "-j", default="fruits.json", help="JSON文件名（默认: fruits.json）")
    parser.add_argument("--config", "-c", default="tools/config.json", help="配置文件路径（默认: tools/config.json）")
    
    args = parser.parse_args()
    
    # 获取名字列表
    names = []
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                names = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"错误：读取文件失败 - {e}")
            sys.exit(1)
    elif args.names:
        names = args.names
    else:
        parser.print_help()
        sys.exit(1)
    
    if not names:
        print("错误：没有提供物品名字")
        sys.exit(1)
    
    # 确认
    print(f"将生成 {len(names)} 个物品的内容:")
    for name in names:
        print(f"  - {name}")
    
    if not args.append:
        response = input("\n这将生成新的JSON文件（如果已存在将被覆盖）。继续？(y/n): ")
        if response.lower() != 'y':
            print("已取消")
            sys.exit(0)
    
    # 创建生成器并执行
    try:
        generator = ContentGenerator(args.config)
        success_count, fail_count = generator.generate(names, args.json, args.append)
        print(f"\n完成！成功: {success_count}, 失败: {fail_count}")
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

