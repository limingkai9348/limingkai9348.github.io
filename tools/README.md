# AI内容生成工具使用说明

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

1. 复制配置文件模板：
```bash
cp config.json.example config.json
```

2. 编辑 `config.json`，填入你的OpenAI API密钥：
```json
{
  "openai_api_key": "sk-your-api-key-here",
  "openai_model": "gpt-4",
  "image_model": "dall-e-3",
  "image_size": "1024x1024",
  "image_quality": "standard"
}
```

## 使用方法

### 方式1：直接输入名字
```bash
python tools/generate_content.py 苹果 香蕉 橙子
```

### 方式2：从文件读取
创建一个文本文件（如 `fruits_list.txt`），每行一个名字：
```
苹果
香蕉
橙子
```

然后运行：
```bash
python tools/generate_content.py --file fruits_list.txt
```

### 方式3：追加到现有JSON
```bash
python tools/generate_content.py --append 葡萄 草莓
```

## 功能说明

- **描述生成**：使用OpenAI GPT生成适合儿童学习的描述（50-100字）
- **图片生成**：使用DALL-E生成图片，水果/蔬菜显示在自然生长环境中
- **音频生成**：生成中英文双语语音，格式为：中文-1秒静音-英文-1秒静音-中文-1秒静音-英文
- **JSON生成**：自动生成符合fruits.json格式的文件

## 注意事项

- 需要有效的OpenAI API密钥
- 图片生成会产生费用（DALL-E 3）
- 工具会自动跳过已存在的物品名称
- 生成过程中会有2秒延迟以避免API限流

---

## 图片压缩工具

### 功能说明

批量压缩图片文件，减少文件体积，**保持原始分辨率不变**。

### 使用方法

#### 基本用法：压缩指定文件夹
```bash
# 压缩 assets/fruits 目录（覆盖原文件，自动备份）
python tools/compress_images.py assets/fruits

# 压缩 assets/vegetables 目录
python tools/compress_images.py assets/vegetables
```

#### 指定压缩质量
```bash
# 使用质量75（更小体积，质量略降）
python tools/compress_images.py assets/fruits -q 75

# 使用质量60（最小体积，质量明显下降）
python tools/compress_images.py assets/fruits -q 60
```

#### 压缩到新目录（保留原文件）
```bash
# 压缩后的图片保存到新目录，原文件不变
python tools/compress_images.py assets/fruits -o assets/fruits_compressed
```

#### 不备份原文件
```bash
# 直接覆盖，不创建备份
python tools/compress_images.py assets/fruits --no-backup
```

### 参数说明

- `directory`: **必需**，要压缩的图片目录路径（例如: `assets/fruits` 或 `assets/vegetables`）
- `-q, --quality`: JPEG质量 (1-100，默认85)
  - 85: 平衡质量和体积（推荐）
  - 75: 更小体积，质量略降
  - 60: 最小体积，质量明显下降
- `--no-optimize`: 禁用优化压缩（一般不推荐）
- `--no-backup`: 不备份原文件
- `-o, --output`: 输出目录（如果指定，压缩后的图片将保存到此目录，原文件不变）

### 注意事项

- 压缩时会自动备份原文件到 `backup_original` 子目录（除非使用 `--no-backup`）
- 支持格式：JPG, JPEG, PNG, BMP, GIF
- PNG等带透明通道的图片会转换为RGB模式（白色背景）
- 压缩过程会显示每张图片的压缩统计信息

