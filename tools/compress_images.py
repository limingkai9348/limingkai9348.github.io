#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片压缩工具
批量压缩图片，减少文件体积，保持原始分辨率不变
"""

import os
import sys
from pathlib import Path
from PIL import Image
import argparse


def compress_image(input_path, output_path, quality=85, optimize=True):
    """
    压缩单张图片
    
    Args:
        input_path: 输入图片路径
        output_path: 输出图片路径
        quality: JPEG质量 (1-100，数值越小文件越小，但质量越低)
        optimize: 是否优化压缩
    """
    try:
        # 打开图片
        img = Image.open(input_path)
        
        # 如果是RGBA模式，转换为RGB（JPEG不支持透明度）
        if img.mode in ('RGBA', 'LA', 'P'):
            # 创建白色背景
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 保存压缩后的图片
        img.save(
            output_path,
            'JPEG',
            quality=quality,
            optimize=optimize
        )
        
        # 获取文件大小
        original_size = os.path.getsize(input_path)
        compressed_size = os.path.getsize(output_path)
        reduction = (1 - compressed_size / original_size) * 100
        
        return {
            'success': True,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'reduction': reduction
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def compress_directory(directory, quality=85, optimize=True, backup=True, output_dir=None):
    """
    批量压缩目录中的所有图片
    
    Args:
        directory: 图片目录路径
        quality: JPEG质量 (1-100)
        optimize: 是否优化压缩
        backup: 是否备份原文件
        output_dir: 输出目录（如果为None，则覆盖原文件）
    """
    directory = Path(directory)
    if not directory.exists():
        print(f"错误：目录不存在: {directory}")
        return
    
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.JPG', '.JPEG', '.PNG', '.BMP', '.GIF'}
    
    # 获取所有图片文件
    image_files = [f for f in directory.iterdir() if f.suffix in image_extensions and f.is_file()]
    
    if not image_files:
        print(f"在目录 {directory} 中未找到图片文件")
        return
    
    print(f"找到 {len(image_files)} 张图片")
    print(f"压缩质量: {quality}")
    print(f"优化压缩: {optimize}")
    print("-" * 60)
    
    # 创建备份目录
    backup_dir = None
    if backup and output_dir is None:
        backup_dir = directory / 'backup_original'
        backup_dir.mkdir(exist_ok=True)
        print(f"原文件将备份到: {backup_dir}")
    
    # 创建输出目录
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        print(f"压缩后的图片将保存到: {output_path}")
    
    total_original = 0
    total_compressed = 0
    success_count = 0
    failed_count = 0
    
    for img_file in image_files:
        try:
            # 备份原文件
            if backup and backup_dir:
                backup_file = backup_dir / img_file.name
                import shutil
                shutil.copy2(img_file, backup_file)
            
            # 确定输出路径
            if output_dir:
                output_file = Path(output_dir) / img_file.name
            else:
                output_file = img_file
            
            # 压缩图片
            result = compress_image(img_file, output_file, quality, optimize)
            
            if result['success']:
                original_size = result['original_size']
                compressed_size = result['compressed_size']
                reduction = result['reduction']
                
                total_original += original_size
                total_compressed += compressed_size
                success_count += 1
                
                # 格式化文件大小
                def format_size(size):
                    for unit in ['B', 'KB', 'MB']:
                        if size < 1024.0:
                            return f"{size:.2f} {unit}"
                        size /= 1024.0
                    return f"{size:.2f} GB"
                
                print(f"✓ {img_file.name}")
                print(f"  原始: {format_size(original_size)} → 压缩后: {format_size(compressed_size)}")
                print(f"  减少: {reduction:.1f}%")
            else:
                failed_count += 1
                print(f"✗ {img_file.name}: {result.get('error', '未知错误')}")
        except Exception as e:
            failed_count += 1
            print(f"✗ {img_file.name}: {str(e)}")
    
    # 打印统计信息
    print("-" * 60)
    print(f"处理完成！")
    print(f"成功: {success_count} 张")
    print(f"失败: {failed_count} 张")
    if success_count > 0:
        total_reduction = (1 - total_compressed / total_original) * 100
        def format_size(size):
            for unit in ['B', 'KB', 'MB']:
                if size < 1024.0:
                    return f"{size:.2f} {unit}"
                size /= 1024.0
            return f"{size:.2f} GB"
        print(f"总大小: {format_size(total_original)} → {format_size(total_compressed)}")
        print(f"总减少: {total_reduction:.1f}%")


def main():
    parser = argparse.ArgumentParser(description='批量压缩图片，保持分辨率不变')
    parser.add_argument('directory', help='图片目录路径（例如: assets/fruits 或 assets/vegetables）')
    parser.add_argument('-q', '--quality', type=int, default=85, 
                       help='JPEG质量 (1-100，默认85，数值越小文件越小)')
    parser.add_argument('--no-optimize', action='store_true',
                       help='禁用优化压缩')
    parser.add_argument('--no-backup', action='store_true',
                       help='不备份原文件（如果指定了输出目录，则自动不备份）')
    parser.add_argument('-o', '--output', 
                       help='输出目录（如果指定，压缩后的图片将保存到此目录，原文件不变）')
    
    args = parser.parse_args()
    
    # 如果指定了输出目录，则不备份
    backup = not args.no_backup and args.output is None
    
    compress_directory(
        directory=args.directory,
        quality=args.quality,
        optimize=not args.no_optimize,
        backup=backup,
        output_dir=args.output
    )


if __name__ == "__main__":
    main()

