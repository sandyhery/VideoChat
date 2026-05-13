import asyncio
import os
import re
from config import STT_CONFIG

# 模型缓存
model_cache = {}
should_stop = False
current_file = None


def extract_keywords_from_filename(filename: str) -> dict:
    """
    从文件名中提取关键词和信息，用于校准转录结果
    返回包含清理后文件名、关键词列表和主题信息的字典
    """
    # 去除扩展名
    name = re.sub(r'\.\w+$', '', filename)
    # 去除开头的序号（如 01_、02-、第1集 等）
    name = re.sub(r'^\d+[_\-]', '', name)
    name = re.sub(r'^第\d+[集部章节]', '', name)

    # 提取关键词（2字以上的词组）
    keywords = re.findall(r'[\u4e00-\u9fff]{2,}', name)

    # 提取可能的专有名词（括号内的内容）
    brackets_content = re.findall(r'[（(]([^)）]+)[)）]', name)
    special_terms = []
    for content in brackets_content:
        special_terms.extend(re.findall(r'[\u4e00-\u9fff]+', content))

    return {
        "clean_name": name,
        "keywords": keywords,
        "special_terms": special_terms,
        "all_terms": keywords + special_terms
    }


def detect_dialect_from_filename(filename: str) -> str:
    """
    从文件名中自动检测方言类型
    根据文件名关键词匹配方言特征词
    """
    if not filename:
        return "auto"

    file_info = extract_keywords_from_filename(filename)
    keywords = file_info["all_terms"]

    dialect_indicators = {
        "cantonese": ["粤语", "香港", "广东", "广州", "粤方言", "白话"],
        "sichuan": ["四川", "成都", "川普", "川话", "四川话"],
        "shanghai": ["上海", "沪语", "浦东", "上海话", "沪"],
        "taiwan": ["台湾", "闽南", "台语", "Taiwan", "台海"],
        "hongkong": ["香港", "港语", "港话", "HK"],
        "nanjing": ["南京", "江浙", "江苏", "金陵"],
        "shandong": ["山东", "济南", "齐鲁"],
        "henan": ["河南", "中原", "郑州"],
        "dongbei": ["东北", "辽宁", "吉林", "黑龙江"],
    }

    for dialect, indicators in dialect_indicators.items():
        if any(kw in keywords for kw in indicators):
            print(f"🔍 检测到方言特征: {dialect} (关键词: {[kw for kw in indicators if kw in keywords]})")
            return dialect

    return "auto"


def get_dialect_prompt(dialect: str) -> str:
    """
    根据方言类型返回对应的提示词
    """
    dialect_prompts = {
        "auto": "这是一段中文语音，可能包含多种方言口音特征。请结合上下文准确识别。",
        "mandarin": "这是一段中文普通话语音，标准中文发音，识别难度较低。",
        "cantonese": '这是一段粤语语音，注意粤方言特征：入声丰富、倒装句多、常用单字词。如"我食先"表示"我先吃"。同音词注意：时/是、死/洗、行/形等。',
        "sichuan": "这是一段四川话语音，注意川音特征：n/l不分、in/ing不分、ang/an不分。如'牛奶'可能读成'流来'。常用'哈'、'嘛'等语气词。",
        "shanghai": "这是一段上海话语音，注意沪语特征：入声短促、浊音多。如'朋友'可能读成'朋迂'。常用'阿拉'、'侬'等代词。",
        "taiwan": "这是一段台湾国语语音，注意台音特征：轻声多、儿化音特殊。如'这样子'常说成'酱子'。部分词汇受闽南语影响。",
        "hongkong": "这是一段香港普通话语音，注意港音特征：声调偏平、英文词汇多。如'ok'常直接使用。",
        "nanjing": "这是一段南京话语音，注意江浙特征：平翘舌混淆、in/ing不分。如'人民'可能读成'人明'。",
        "shandong": "这是一段山东话语音，注意鲁音特征：翘舌音多、ang/an混淆。如'吃饭'可能读成'吃翻'。",
        "henan": "这是一段河南话语音，注意中原特征：去声多、声调偏高。如'什么'常说成'啥'。",
        "dongbei": "这是一段东北话语音，注意东北特征：儿化音多、声调夸张。常用'嘎'、'咋'等语气词。",
    }

    return dialect_prompts.get(dialect, dialect_prompts["auto"])


def calibrate_transcription_with_filename(transcription: list, filename: str) -> list:
    """
    基于文件名校准转录结果
    利用文件名中的主题信息来修正转录中的错误
    """
    if not transcription or not filename:
        return transcription

    file_info = extract_keywords_from_filename(filename)
    clean_name = file_info["clean_name"]
    all_terms = file_info["all_terms"]

    if not all_terms:
        return transcription

    # 基于文件名的常见修正规则
    corrections = []

    # 如果文件名包含特定主题，添加相关修正
    if '小篆' in clean_name or '篆' in clean_name:
        corrections.extend([
            (r'转篆', '小篆'),
            (r'象形', '象形'),
            (r'绳形', '绳形'),
        ])

    if '道德经' in clean_name or '德经' in clean_name:
        corrections.extend([
            (r'道(\w+)经', r'道德经'),
        ])

    # 处理同音异字问题（基于主题上下文）
    theme_corrections = {
        '行为': ['行为', '行为', '形为'],
        '无为': ['无为', '无违'],
        '道德': ['道德', '道得'],
        '汉字': ['汉字', '汉子', '汉 字'],
        '小篆': ['小篆', '小传', '小篆'],
        '甲骨': ['甲骨', '甲古'],
        '金文': ['金文', '今文'],
        '隶书': ['隶书', '隶書'],
        '楷书': ['楷书', '楷書', '开书'],
        '草书': ['草书', '草書'],
        '行书': ['行书', '行書'],
    }

    for term in all_terms:
        if term in theme_corrections:
            for wrong in theme_corrections[term]:
                if wrong != term:
                    corrections.append((wrong, term))

    # 应用修正
    for segment in transcription:
        if 'text' in segment:
            text = segment['text']

            # 应用修正规则
            for pattern, replacement in corrections:
                text = re.sub(pattern, replacement, text)

            segment['text'] = text.strip()

    return transcription


def post_process_transcription(transcription: list, filename: str = "") -> list:
    """
    后处理转录结果，修复方言、口音带来的常见问题
    可选地基于文件名进行校准
    """
    if not transcription:
        return transcription

    # 如果有文件名，先进行基于文件名的校准
    if filename and STT_CONFIG.get("post_processing", {}).get("fix_common_errors", True):
        transcription = calibrate_transcription_with_filename(transcription, filename)

    if not STT_CONFIG.get("post_processing", {}).get("fix_common_errors", True):
        return transcription

    # 常见的方言错误模式及修正
    corrections = [
        # "的"、"地"、"得" 混用修正（基于上下文）
        (r'\s+的\s+', '的'),
        (r'\s+地\s+', '地'),
        (r'\s+得\s+', '得'),
        # 常见错别字修正常见方言口音问题
        (r'那吗', '那么'),
        (r'这个', '这个'),
        (r'什么', '什么'),
        (r'怎么', '怎么'),
        (r'这样', '这样'),
        (r'那样', '那样'),
    ]

    # 移除填充词
    fillers = ['呃', '嗯', '啊', '哦', '呢', '嘛', '哈', '呀', '哟']
    filler_pattern = re.compile(rf'\s*([{"".join(fillers)}])\s*')

    for segment in transcription:
        if 'text' in segment:
            text = segment['text']

            # 移除填充词
            if STT_CONFIG.get("post_processing", {}).get("remove_fillers", True):
                text = filler_pattern.sub('', text)

            # 修正常见错误
            for pattern, replacement in corrections:
                text = re.sub(pattern, replacement, text)

            segment['text'] = text.strip()

    return transcription

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

def transcribe_with_faster_whisper(file_path: str, model_size: str = None, filename: str = ""):
    """使用 Faster-Whisper 进行转录（方言/口音优化）"""
    if model_size is None:
        model_size = STT_CONFIG.get("whisper_model", "large")

    whisper_model = get_faster_whisper_model(model_size)

    try:
        from faster_whisper import WhisperModel

        # 构建转录参数
        vad_params = STT_CONFIG.get("vad_params", {})
        vad_filter = STT_CONFIG.get("vad_filter", True)

        transcribe_kwargs = {
            "language": STT_CONFIG.get("language", "zh"),
            "beam_size": STT_CONFIG.get("beam_size", 5),
            "vad_filter": vad_filter,
        }

        # 添加 VAD 参数优化
        if vad_params and vad_filter:
            transcribe_kwargs["vad_parameters"] = {
                "threshold": vad_params.get("threshold", 0.5),
                "min_speech_duration_ms": int(vad_params.get("min_speech_duration", 0.3) * 1000),
                "min_silence_duration_ms": int(vad_params.get("min_silence_duration", 0.5) * 1000),
            }

        # 使用 initial_prompt 帮助识别方言/口音
        # 自动从文件名检测方言，然后获取对应的方言提示词
        detected_dialect = detect_dialect_from_filename(filename) if filename else "auto"
        dialect_prompt = get_dialect_prompt(detected_dialect)

        if filename:
            file_info = extract_keywords_from_filename(filename)
            context_hint = f"视频主题关键词：{', '.join(file_info['all_terms'][:5])}"
            transcribe_kwargs["initial_prompt"] = f"{dialect_prompt}\n{context_hint}"
        else:
            transcribe_kwargs["initial_prompt"] = dialect_prompt

        if detected_dialect != "auto":
            print(f"🔍 检测到方言: {detected_dialect}, 使用提示词: {dialect_prompt[:50]}...")

        print(f"🚀 使用 Faster-Whisper 进行转录（beam_size={transcribe_kwargs['beam_size']}, vad={vad_filter}）...")

        segments_generator = whisper_model.transcribe(
            file_path,
            **transcribe_kwargs
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

        # 后处理（传递文件名用于校准）
        if transcription and STT_CONFIG.get("post_processing", {}).get("fix_common_errors", True):
            transcription = post_process_transcription(transcription, filename)

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

def transcribe_with_openai(file_path: str, filename: str = ""):
    """使用 OpenAI Whisper API 进行转录（质量最高）"""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=STT_CONFIG.get("openai_api_key", ""),
            base_url=STT_CONFIG.get("openai_base_url", "https://api.openai.com/v1")
        )

        print(f"🚀 使用 OpenAI Whisper API 进行转录...")

        # 构建 prompt 参数（方言+文件名提示）
        prompt = None
        detected_dialect = detect_dialect_from_filename(filename) if filename else "auto"
        dialect_prompt = get_dialect_prompt(detected_dialect)

        if filename:
            file_info = extract_keywords_from_filename(filename)
            keywords = file_info["all_terms"]
            context_hint = f"视频主题关键词：{', '.join(keywords[:5])}" if keywords else ""
            if context_hint:
                prompt = f"{dialect_prompt}\n{context_hint}"
            else:
                prompt = dialect_prompt
        elif detected_dialect != "auto":
            prompt = dialect_prompt

        if prompt:
            print(f"📝 使用提示词: {prompt[:80]}...")

        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=STT_CONFIG.get("language", "zh"),
                response_format="verbose_json",
                prompt=prompt if prompt else None
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

def transcribe_with_funasr(file_path: str, filename: str = ""):
    """使用 FunASR（阿里开源的中文语音识别模型）进行转录"""
    try:
        import torch
        from funasr import AutoModel

        print(f"🚀 使用 FunASR 进行转录（方言/口音优化）...")

        # 获取配置参数
        enable_itn = STT_CONFIG.get("enable_itn", True)  # 逆文本正则化
        enable_punc = STT_CONFIG.get("enable_punc", True)  # 标点恢复
        vad_params = STT_CONFIG.get("vad_params", {})

        # 使用 FunASR 的中文大模型，带方言/口音优化参数
        # paraformer-zh 支持中文普通话及多种方言
        model_kwargs = {
            "model": "paraformer-zh",
            "model_revision": "v2.0.4",
        }

        # 添加 VAD 参数优化（对方言口音更鲁棒）
        if vad_params:
            model_kwargs["vad_model"] = "fsmn-vad"
            model_kwargs["vad_model_revision"] = "v2.0.4"
            model_kwargs["vad_kwargs"] = vad_params

        # 添加热词文件（如果有配置）
        hotwords_file = STT_CONFIG.get("hotwords_file", "")
        if hotwords_file and os.path.exists(hotwords_file):
            model_kwargs["hotword_file"] = hotwords_file
            print(f"📝 使用热词文件: {hotwords_file}")

        # 从文件名提取关键词作为内置热词
        filename_hotwords = ""
        if filename:
            file_info = extract_keywords_from_filename(filename)
            if file_info["all_terms"]:
                filename_hotwords = ",".join(file_info["all_terms"][:10])
                print(f"📝 使用文件主题关键词: {file_info['all_terms'][:5]} -> 热词: {filename_hotwords}")

        model = AutoModel(**model_kwargs)

        # 构建生成参数
        generate_kwargs = {
            "input": file_path,
            "batch_size_s": 300,
            "merge_vad": True,  # 合并 VAD 分段，提高连续性
            "merge_length_s": 15,  # 合并段落长度（秒），适合长音频
        }

        # 添加文件名关键词热词
        if filename_hotwords:
            generate_kwargs["hotword"] = filename_hotwords

        # 启用逆文本正则化（阿拉伯数字/日期等转换为中文）
        if enable_itn:
            generate_kwargs["text_norm"] = True
            print(f"✅ 启用逆文本正则化 (ITN)")

        # 启用标点恢复
        if enable_punc:
            generate_kwargs["punc"] = True
            print(f"✅ 启用标点恢复")

        # 进行转录
        result = model.generate(**generate_kwargs)

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

        # 后处理：传递文件名用于基于主题的校准
        if transcription and STT_CONFIG.get("post_processing", {}).get("fix_common_errors", True):
            transcription = post_process_transcription(transcription, filename)

        print(f"✅ FunASR 转录完成！共 {len(transcription)} 个片段")
        return transcription
    except ImportError:
        raise Exception("FunASR 未安装，请运行: pip install funasr modelscope")
    except Exception as e:
        raise Exception(f"FunASR 调用失败: {str(e)}")

async def transcribe_audio(file_path: str, model_size: str = None, filename: str = "") -> list:
    """根据配置选择不同的转录引擎进行转录"""
    global should_stop, current_file
    should_stop = False
    current_file = file_path

    try:
        engine = STT_CONFIG.get("engine", "faster_whisper")
        print(f"🔍 使用转录引擎: {engine}")

        # 根据引擎选择不同的转录方法
        if engine == "openai":
            transcription = await asyncio.to_thread(transcribe_with_openai, file_path, filename)
        elif engine == "funasr":
            transcription = await asyncio.to_thread(transcribe_with_funasr, file_path, filename)
        else:  # 默认使用 faster_whisper
            transcription = await asyncio.to_thread(transcribe_with_faster_whisper, file_path, model_size, filename)

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
