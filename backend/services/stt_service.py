import asyncio
import os
from config import STT_CONFIG

# 模型缓存
model_cache = {}
should_stop = False
current_file = None

def get_faster_whisper_model(model_size: str = None):
    """加载 Faster-Whisper 模型"""
    if model_size is None:
        model_size = STT_CONFIG.get("whisper_model", "tiny")

    if model_size not in model_cache:
        hf_mirror = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
        os.environ["HF_ENDPOINT"] = hf_mirror

        try:
            from faster_whisper import WhisperModel
            # 使用CPU模式，int8量化可以提高CPU推理速度
            model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
            print(f"✅ faster-whisper {model_size} model loaded on CPU with int8!")
        except ImportError:
            import whisper
            model_cache[model_size] = whisper.load_model(model_size)
            print(f"✅ whisper {model_size} model loaded!")

    return model_cache[model_size]

def transcribe_with_faster_whisper(file_path: str, model_size: str = None):
    """使用 Faster-Whisper 进行转录"""
    if model_size is None:
        model_size = STT_CONFIG.get("whisper_model", "large")
    
    whisper_model = get_faster_whisper_model(model_size)
    
    try:
        from faster_whisper import WhisperModel
        segments_generator = whisper_model.transcribe(
            file_path,
            language=STT_CONFIG.get("language", "zh"),
            beam_size=STT_CONFIG.get("beam_size", 5),
            vad_filter=STT_CONFIG.get("vad_filter", True)
        )
        segments, info = segments_generator
        transcription = []
        for segment in segments:
            if should_stop:
                break
            transcription.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
        return transcription
    except ImportError:
        result = whisper_model.transcribe(
            file_path, 
            language=STT_CONFIG.get("language", "zh"), 
            beam_size=STT_CONFIG.get("beam_size", 5)
        )
        transcription = []
        for segment in result["segments"]:
            if should_stop:
                break
            transcription.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"]
            })
        return transcription

def transcribe_with_openai(file_path: str):
    """使用 OpenAI Whisper API 进行转录（质量最高）"""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=STT_CONFIG.get("openai_api_key", ""),
            base_url=STT_CONFIG.get("openai_base_url", "https://api.openai.com/v1")
        )
        
        print(f"🚀 使用 OpenAI Whisper API 进行转录...")
        
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=STT_CONFIG.get("language", "zh"),
                response_format="verbose_json"
            )
        
        # 转换为标准格式
        result = []
        for segment in transcription.segments:
            if should_stop:
                break
            result.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
        
        print(f"✅ OpenAI Whisper API 转录完成！")
        return result
    except ImportError:
        raise Exception("OpenAI SDK 未安装，请运行: pip install openai")
    except Exception as e:
        raise Exception(f"OpenAI API 调用失败: {str(e)}")

def transcribe_with_funasr(file_path: str):
    """使用 FunASR（阿里开源的中文语音识别模型）进行转录"""
    try:
        import torch
        from funasr import AutoModel

        print(f"🚀 使用 FunASR 进行转录...")

        # 使用 FunASR 的中文大模型
        model = AutoModel(model="paraformer-zh", model_revision="v2.0.4")

        # 进行转录
        result = model.generate(input=file_path, batch_size_s=300)

        # 转换为标准格式
        transcription = []
        if result and len(result) > 0:
            result_item = result[0]
            text = result_item.get("text", "").replace(" ", "")  # 去掉分词空格
            timestamp = result_item.get("timestamp")

            # 检查 timestamp 是否包含文本信息 [start, end, text] 格式
            has_text_timestamps = False
            if timestamp and isinstance(timestamp, list) and len(timestamp) > 0:
                first = timestamp[0]
                if isinstance(first, (list, tuple)) and len(first) >= 3:
                    has_text_timestamps = True

            if has_text_timestamps:
                # timestamp 格式为 [[start, end, text], ...]
                for item in timestamp:
                    if should_stop:
                        break
                    if len(item) >= 3:
                        transcription.append({
                            "start": item[0] / 1000,  # 转换为秒
                            "end": item[1] / 1000,
                            "text": item[2]
                        })
            elif text:
                # 没有详细时间戳，只有完整文本
                transcription.append({
                    "start": 0,
                    "end": 0,
                    "text": text
                })

        print(f"✅ FunASR 转录完成！")
        return transcription
    except ImportError:
        raise Exception("FunASR 未安装，请运行: pip install funasr modelscope")
    except Exception as e:
        raise Exception(f"FunASR 调用失败: {str(e)}")

async def transcribe_audio(file_path: str, model_size: str = None) -> list:
    """根据配置选择不同的转录引擎进行转录"""
    global should_stop, current_file
    should_stop = False
    current_file = file_path

    try:
        engine = STT_CONFIG.get("engine", "faster_whisper")
        print(f"🔍 使用转录引擎: {engine}")
        
        # 根据引擎选择不同的转录方法
        if engine == "openai":
            transcription = await asyncio.to_thread(transcribe_with_openai, file_path)
        elif engine == "funasr":
            transcription = await asyncio.to_thread(transcribe_with_funasr, file_path)
        else:  # 默认使用 faster_whisper
            transcription = await asyncio.to_thread(transcribe_with_faster_whisper, file_path, model_size)
        
        if should_stop:
            current_file = None
            raise asyncio.CancelledError("Transcription cancelled")
        
        current_file = None
        return transcription

    except asyncio.CancelledError:
        should_stop = True
        current_file = None
        raise
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        current_file = None
        raise
    finally:
        should_stop = False
        current_file = None

def stop_transcription():
    """停止转录"""
    global should_stop
    should_stop = True

def is_file_being_transcribed(file_path: str) -> bool:
    """检查文件是否正在被转录"""
    return current_file == file_path
