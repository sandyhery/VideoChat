# 🎤 语音转文字 (STT) 配置指南

## 🚀 **好消息！我已经为您添加了多种高质量的转录方案！

## 您现在可以在 `backend/config.py` 中配置不同的转录引擎：

## 📋 方案对比

### 1. **Faster-Whisper (本地模型)

- **优点**: 完全免费，无需联网，速度较快
- **缺点**: 精度相对较低，需要下载模型（首次使用时）

### 2. **OpenAI Whisper API (推荐，质量最高)**

- **优点**: 转录质量最高，支持多种语言，特别是中文识别效果优秀
- **缺点**: 需要 API Key，需要联网，有成本（相对来说还是挺便宜）
- **配置**: 在 `STT_CONFIG` 中设置 `engine = "openai"` 并设置 `openai_api_key`

### 3. **FunASR (阿里开源中文模型)**

- **优点**: 中文识别效果很好，完全免费，针对中文优化
- **缺点**: 需要安装较复杂，首次使用需要下载大模型

## 🔧 配置方法

### 方案一：使用 OpenAI Whisper API（推荐使用）

```python
# backend/config.py
STT_CONFIG = {
    "engine": "openai",  # 改为 openai
    "whisper_model": "large",
    "beam_size": 5,
    "language": "zh",
    "vad_filter": True,
    "openai_api_key": "sk-your-api-key-here",  # 填入您的 API Key
    "openai_base_url": "https://api.openai.com/v1"
}
```

**可选：**如果您有国内的 API 代理，可以修改 `openai_base_url`

### 方案二：升级本地大型号模型（免费但质量好）

```python
# backend/config.py
STT_CONFIG = {
    "engine": "faster_whisper",  # 保持默认
    "whisper_model": "large",  # 改为 large！这是最关键的
    "beam_size": 5,
    "language": "zh",
    "vad_filter": True
}
```

### 方案三：使用 FunASR（中文专用）

```python
# backend/config.py
STT_CONFIG = {
    "engine": "funasr",  # 改为 funasr
    # ...其他配置
}
```

## 📥 安装依赖

**方案一（OpenAI）：
- 已在 requirements.txt 中已有 `openai` 已安装

方案二（FunASR）：
```bash
pip install funasr modelscope torch
```

## 💡 推荐选择建议

1. **如果追求最佳效果第一优先：
   使用 OpenAI Whisper API
2. **如果想免费但好效果：
   升级到 "large" 模型
3. **如果主要处理中文：
   尝试 FunASR

## 🔄 使用步骤

1. 修改 `backend/config.py` 中的配置
2. 重启后端服务
3. 重新上传视频进行转录

## ⚠️ 注意事项

- **large 模型首次使用时：
  - 首次运行需要下载约 3GB 的模型文件
  - 需要更多内存（建议至少 8GB）
  - 转录速度会比 tiny 慢一些，但质量会好很多

祝您转录会明显提升！
