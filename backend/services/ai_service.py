import os
import json
from typing import List, Dict
from models import ChatMessage
from config import AI_CONFIG
import httpx

def clean_think_tags(text: str) -> str:
    """清理 AI 输出中的 think 标签和思考内容"""
    if not text:
        return text
    # 移除 <think>... 标签及其内容
    import re
    # 匹配 <think>...</think> 形式的标签（包括多行）
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text)
    # 清理可能残留的空白
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

async def add_punctuation_and_segmentation(text: str, _from_long: bool = False) -> str:
    """使用 AI 为转录文本添加标点符号和分段"""
    if not text or len(text.strip()) < 5:
        return text

    # 对于超长文本（超过8000字符），分块处理
    # _from_long 标志防止递归调用
    MAX_CHUNK_SIZE = 6000
    if len(text) > MAX_CHUNK_SIZE and not _from_long:
        return await add_punctuation_and_segmentation_long(text)

    url = f"{AI_CONFIG['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }

    system_prompt = """你是一个专业的中文文本处理助手。你的任务是对转录文本进行润色和格式化。

要求：
1. 为文本添加适当的标点符号（，。！？；：""等）
2. 根据语义适当分段（用空行分隔）
3. 保持原意不变，不要添加或删除内容
4. 对于长段落，可以根据语义分成2-3段
5. 输出格式：直接输出处理后的文本，不要添加任何解释

注意：这是一段语音转录的文字，可能存在一些口语化表达，请在保持原意的前提下进行规范化处理。

古文字处理：如果内容涉及古文字（特别是用双引号""标注的单字或词语，如"手"、"又"、"巾"等），或是提到"篆"相关的字（如篆书、小篆等），或是黑板上写的古文字，请单独标记这些字，用[seal]标签包裹，如：[seal]手[/seal]、[seal]篆[/seal]。注意：只标记单个字或词语，不要标记整句话。"""

    data = {
        "model": AI_CONFIG["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下转录文本添加标点符号和分段：\n\n{text}"}
        ],
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 8000
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"[add_punctuation_and_segmentation] 发送请求...")
            resp = await client.post(url, headers=headers, json=data)
            print(f"[add_punctuation_and_segmentation] 响应状态: {resp.status_code}")
            if resp.status_code != 200:
                print(f"[add_punctuation_and_segmentation] 错误: {resp.text}")
                return text

            result = resp.json()
            print(f"[add_punctuation_and_segmentation] 响应内容: {result.keys() if isinstance(result, dict) else type(result)}")
            if "choices" in result and result["choices"]:
                punctuated_text = result["choices"][0]["message"]["content"].strip()
                # 清理 think 标签
                punctuated_text = clean_think_tags(punctuated_text)
                print(f"[add_punctuation_and_segmentation] 成功，结果长度: {len(punctuated_text)}")
                return punctuated_text
            elif "base_resp" in result and result["base_resp"]["status_code"] != 0:
                print(f"[add_punctuation_and_segmentation] API错误: {result['base_resp']['status_msg']}")
            return text
    except Exception as e:
        print(f"[add_punctuation_and_segmentation] 异常: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return text

async def add_punctuation_and_segmentation_long(text: str) -> str:
    """处理超长文本的分段标点恢复"""
    import httpx

    print(f"[add_punctuation_and_segmentation_long] 文本长度: {len(text)}，开始分段处理...")

    # 直接按固定字数分割，不依赖换行符
    MAX_CHUNK_SIZE = 4000  # 每块最大字符数
    text_len = len(text)

    if text_len <= MAX_CHUNK_SIZE:
        # 文本本身不长，直接处理
        return await add_punctuation_and_segmentation(text, _from_long=True)

    # 分割成多个块
    results = []
    for i in range(0, text_len, MAX_CHUNK_SIZE):
        chunk = text[i:i + MAX_CHUNK_SIZE]
        results.append(chunk)

    print(f"[add_punctuation_and_segmentation_long] 分割成 {len(results)} 块进行处理")

    # 逐块处理并合并结果
    punctuated_parts = []
    for i, chunk in enumerate(results):
        print(f"[add_punctuation_and_segmentation_long] 处理第 {i+1}/{len(results)} 块，长度: {len(chunk)}")
        punctuated = await add_punctuation_and_segmentation(chunk, _from_long=True)
        punctuated_parts.append(punctuated)

    final_result = "\n\n".join(punctuated_parts)
    print(f"[add_punctuation_and_segmentation_long] 处理完成，总长度: {len(final_result)}")
    return final_result

def extract_filename_info(filename: str) -> dict:
    """从文件名中提取关键信息"""
    import re
    if not filename:
        return {"clean_name": "", "keywords": [], "special_terms": []}

    name = re.sub(r'\.\w+$', '', filename)
    name = re.sub(r'^\d+[_\-]', '', name)
    name = re.sub(r'^第\d+[集部章节]', '', name)

    keywords = re.findall(r'[\u4e00-\u9fff]{2,}', name)
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


async def generate_summary(text: str, filename: str = ""):
    print(f"[generate_summary] 开始生成总结，输入文本长度: {len(text)}")
    url = f"{AI_CONFIG['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }

    # 增强的系统提示词，提供更清晰的指导
    system_prompt = """你是一个专业的视频内容分析助手。请对以下内容进行简洁准确的总结。

要求：
1. 总结应该简洁有力，突出核心内容
2. 保留关键术语和数据
3. 结合视频主题理解内容"""

    if filename:
        file_info = extract_filename_info(filename)
        clean_name = file_info["clean_name"]
        keywords = ", ".join(file_info["all_terms"][:5]) if file_info["all_terms"] else "未知主题"

        system_prompt = f"""你是一个专业的视频内容分析助手。请根据以下视频信息进行总结。

【视频文件名】: {clean_name}
【主题关键词】: {keywords}

文件名和关键词包含了视频的核心主题信息，请作为总结的最重要参考。

要求：
1. 总结必须紧扣视频主题（{clean_name}）
2. 突出与主题相关的核心内容
3. 保留关键术语和数据
4. 如发现内容与主题不匹配，以主题为准进行校正
5. 总结长度控制在200字以内
6. 如果内容涉及古文字（特别是用双引号""标注的单字或词语，如"手"、"又"、"巾"等），或是提到"篆"相关的字（如篆书、小篆等），或是黑板上写的古文字，请单独标记这些字，用[seal]标签包裹，如：[seal]手[/seal]、[seal]篆[/seal]
7. 注意：只标记单个字或词语，不要标记整句话"""

    data = {
        "model": AI_CONFIG["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "stream": True,
        "temperature": 0.3,  # 降低随机性，提高一致性
        "max_tokens": 500    # 限制输出长度
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"[generate_summary] 发送请求到 {url}")
            async with client.stream("POST", url, headers=headers, json=data) as response:
                print(f"[generate_summary] 响应状态码: {response.status_code}")
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[generate_summary] 错误响应: {error_text}")
                    yield f"API错误: {response.status_code}"
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        try:
                            chunk_data = json.loads(line[6:])
                            if "choices" in chunk_data and chunk_data["choices"]:
                                choice = chunk_data["choices"][0]
                                if "delta" in choice:
                                    delta = choice["delta"]
                                    content = delta.get("content", "")
                                    if content and content not in ["<think>", ""]:
                                        yield content
                                elif "message" in choice:
                                    content = choice["message"].get("content", "")
                                    if content and content not in ["<think>", ""]:
                                        yield content
                        except json.JSONDecodeError:
                            continue
        print("[generate_summary] 总结生成完成")
    except Exception as e:
        print(f"[generate_summary] 发生错误: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        yield f"错误: {str(e)}"

async def generate_mindmap(text: str, filename: str = "") -> str:
    print(f"[generate_mindmap] 开始生成思维导图，输入文本长度: {len(text)}")
    try:
        # 从文件名中提取有意义的信息
        root_topic = "主题"
        keywords = []
        if filename:
            file_info = extract_filename_info(filename)
            root_topic = file_info["clean_name"]
            keywords = file_info["all_terms"][:5]

        example = {
            "meta": {"name": "思维导图", "author": "AI", "version": "0.2"},
            "format": "node_tree",
            "data": {
                "id": "root",
                "topic": root_topic,
                "children": [
                    {"id": "sub1", "topic": "子主题1", "direction": "left", "children": []},
                    {"id": "sub2", "topic": "子主题2", "direction": "right", "children": []}
                ]
            }
        }

        url = f"{AI_CONFIG['base_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {AI_CONFIG['api_key']}",
            "Content-Type": "application/json"
        }

        # 根据文件名获取方言提示
        dialect_hint = ""
        if filename:
            from services.stt_service import detect_dialect_from_filename, get_dialect_prompt
            dialect = detect_dialect_from_filename(filename)
            if dialect != "auto":
                dialect_hint = f"\n注意：音频包含{dialect}口音特征，识别时注意对应方言特征。"
                dialect_prompt = get_dialect_prompt(dialect)
                dialect_hint = f"\n{dialect_prompt}"

        keywords_str = ", ".join(keywords) if keywords else "未知主题"

        system_prompt = f"""你是一个专业的思维导图生成专家。请将视频内容转换为结构化的思维导图 JSON。

【视频文件名】: {root_topic}
【主题关键词】: {keywords_str}
{dialect_hint}

## 核心要求：
1. 严格按示例格式生成 JSON
2. 包含 meta、format、data 三个顶级字段
3. data 必须包含 id、topic、children 字段（jsMind 使用 topic 不是 text）
4. 第一层子节点必须指定 direction（left/right），左右交替
5. 所有节点的 id 必须唯一
6. 只返回 JSON，不要任何额外说明
7. 确保 JSON 格式有效可解析

## 内容理解指导：
- 根节点使用视频文件名 "{root_topic}" 作为主题
- 子节点要提炼核心主题和关键要点
- 思维导图层级控制在3-4层
- 子节点数量适中，每个节点内容简洁
- 主题关键词 {keywords_str} 包含视频的核心概念，请确保相关内容被正确提取

## 古文字处理：
- 如果内容涉及古文字（特别是用双引号""标注的单字或词语，如"手"、"又"、"巾"等），或是提到"篆"相关的字（如篆书、小篆等），或是黑板上写的古文字，请单独标记这些字，用[seal]标签包裹，如：[seal]手[/seal]、[seal]篆[/seal]
- 注意：只标记单个字或词语，不要标记整句话

## jsMind 格式说明：
- 根节点 id 为 "root"，topic 为根主题（不是 text）
- 每个节点必须有 id、topic、children 字段
- 第一层子节点需要 direction 字段（left 或 right）

## 示例结构：
{json.dumps(example, ensure_ascii=False, indent=2)}

请严格按照上述格式生成有效的思维导图 JSON。"""

        data = {
            "model": AI_CONFIG["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "stream": False,
            "temperature": 0.3,  # 降低温度提高 JSON 一致性
            "max_tokens": 4000
        }

        print(f"[generate_mindmap] 发送请求到 {url}")
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, headers=headers, json=data)
            print(f"[generate_mindmap] 响应状态码: {resp.status_code}")
            
            if resp.status_code != 200:
                error_text = resp.text
                print(f"[generate_mindmap] 错误响应: {error_text}")
                raise Exception(f"API请求失败: {resp.status_code} - {error_text}")
            
            result = resp.json()
            print(f"[generate_mindmap] API响应结果: {result.keys() if isinstance(result, dict) else type(result)}")

            if "choices" in result and result["choices"]:
                full_response = result["choices"][0]["message"]["content"].strip()
                # 清理 think 标签
                full_response = clean_think_tags(full_response)
            elif "base_resp" in result and result["base_resp"]["status_code"] != 0:
                raise Exception(result["base_resp"]["status_msg"])
            else:
                full_response = str(result)
                full_response = clean_think_tags(full_response)

        def clean_response(response_text: str) -> str:
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            return response_text.strip()

        cleaned_response = clean_response(full_response)

        try:
            mindmap_data = json.loads(cleaned_response)
            if not all(key in mindmap_data for key in ['meta', 'format', 'data']):
                raise ValueError("Missing required fields")
            if not all(key in mindmap_data['data'] for key in ['id', 'topic']):
                raise ValueError("Missing required fields in data.data")
            print("[generate_mindmap] 思维导图生成成功")
            return json.dumps(mindmap_data, ensure_ascii=False)
        except json.JSONDecodeError:
            print("[generate_mindmap] JSON解析失败，返回错误思维导图")
            error_mindmap = {
                "meta": {"name": "解析错误", "author": "System", "version": "0.2"},
                "format": "node_tree",
                "data": {
                    "id": "root",
                    "topic": "无法生成思维导图",
                    "children": [{"id": "error", "topic": "生成失败，请重试", "direction": "right"}]
                }
            }
            return json.dumps(error_mindmap, ensure_ascii=False)

    except Exception as e:
        print(f"[generate_mindmap] 错误类型: {type(e).__name__}")
        print(f"[generate_mindmap] 错误信息: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

async def chat_with_model(messages: List[ChatMessage], context: str):
    url = f"{AI_CONFIG['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }

    system_prompt = """你是一个专业的视频内容问答助手。请基于以下上下文信息，准确回答用户的问题。

要求：
1. 回答要紧扣上下文，不要偏离主题
2. 如有必要，可引用上下文中的具体内容
3. 回答要清晰、有条理
4. 如问题超出上下文范围，请明确告知
5. 回答使用中文

古文字处理：如果内容涉及古文字（特别是用双引号""标注的单字或词语，如"手"、"又"、"巾"等），或是提到"篆"相关的字（如篆书、小篆等），或是黑板上写的古文字，请单独标记这些字，用[seal]标签包裹，如：[seal]手[/seal]、[seal]篆[/seal]。注意：只标记单个字或词语，不要标记整句话。"""

    full_messages = [
        {"role": "system", "content": f"{system_prompt}\n\n以下是上下文信息：\n{context}"}
    ]

    for message in messages:
        full_messages.append({
            "role": message.role,
            "content": message.content
        })

    data = {
        "model": AI_CONFIG["model"],
        "messages": full_messages,
        "stream": True,
        "temperature": 0.5,
        "max_tokens": 1500
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, headers=headers, json=data) as response:
                print(f"[chat_with_model] Response status: {response.status_code}")
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[chat_with_model] Error response: {error_text}")
                    yield f"API错误: {response.status_code}"
                    return

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    if line == "data: [DONE]":
                        break
                    try:
                        line_content = line[6:]  # Remove "data: " prefix
                        if not line_content.strip():
                            continue
                        chunk_data = json.loads(line_content)
                        print(f"[chat_with_model] Chunk keys: {chunk_data.keys() if isinstance(chunk_data, dict) else 'not dict'}")
                        if "choices" in chunk_data and chunk_data["choices"]:
                            choice = chunk_data["choices"][0]
                            if "delta" in choice:
                                delta = choice["delta"]
                                content = delta.get("content", "")
                                if content:
                                    # 跳过 think 标签内容
                                    if content in ["<think>", ""]:
                                        continue
                                    # 解码 Unicode 转义序列
                                    if isinstance(content, str):
                                        # 处理 Unicode 转义
                                        try:
                                            # 先尝试解码 \uXXXX 格式
                                            if '\\u' in content:
                                                decoded_content = content.encode('utf-8').decode('unicode_escape', errors='replace')
                                                # 再次检查是否包含 think 标签解码后的内容
                                                if '<think>' in decoded_content:
                                                    decoded_content = clean_think_tags(decoded_content)
                                                if decoded_content.strip():
                                                    yield decoded_content
                                            else:
                                                # 如果没有 Unicode 转义，直接输出
                                                yield content
                                        except Exception as e:
                                            print(f"[chat_with_model] Decode error: {e}")
                                            yield content
                                    else:
                                        yield str(content)
                            elif "message" in choice:
                                content = choice["message"].get("content", "")
                                if content:
                                    if isinstance(content, str):
                                        try:
                                            if '\\u' in content:
                                                decoded_content = content.encode('utf-8').decode('unicode_escape', errors='replace')
                                                if '<think>' in decoded_content:
                                                    decoded_content = clean_think_tags(decoded_content)
                                                if decoded_content.strip():
                                                    yield decoded_content
                                            else:
                                                yield content
                                        except Exception as e:
                                            print(f"[chat_with_model] Decode error: {e}")
                                            yield content
                                    else:
                                        yield str(content)
                        elif "base_resp" in chunk_data:
                            # 处理错误响应
                            status_code = chunk_data["base_resp"].get("status_code", 0)
                            if status_code != 0:
                                yield f"API错误: {chunk_data['base_resp'].get('status_msg', 'Unknown error')}"
                                break
                    except json.JSONDecodeError as e:
                        print(f"[chat_with_model] JSON decode error: {e}, line: {line[:100]}")
                        continue
    except Exception as e:
        print(f"[chat_with_model] Error: {e}")
        import traceback
        traceback.print_exc()
        yield f"抱歉，发生了错误：{str(e)}"

async def generate_detailed_summary(text: str, filename: str = "", chat_context: str = ""):
    print(f"[generate_detailed_summary] 开始生成详细总结，输入文本长度: {len(text)}, chat_context长度: {len(chat_context)}")
    url = f"{AI_CONFIG['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }

    # 增强的系统提示词，提供更详细的结构化指导
    base_prompt = """你是一个专业的视频内容分析助手。请对以下内容进行详细、系统的总结分析。

请严格按照以下Markdown结构输出：
1. 内容概述（约50字）
2. 核心要点（3-5个要点，每个要点用### 小标题）
3. 详细内容（针对每个要点展开说明，保留关键引用和数据）
4. 总结与结论

重要原则：
- 保持原文的核心信息和关键细节
- 逻辑清晰，层次分明
- 关键技术术语和概念不要遗漏"""

    if filename:
        file_info = extract_filename_info(filename)
        clean_name = file_info["clean_name"]
        keywords = ", ".join(file_info["all_terms"][:5]) if file_info["all_terms"] else "未知主题"

        base_prompt = f"""你是一个专业的视频内容分析助手。请根据以下视频信息进行详细、系统的总结分析。

【视频文件名】: {clean_name}
【主题关键词】: {keywords}

文件名和关键词包含了视频的核心主题信息，请作为总结的最重要参考。

请严格按照以下Markdown结构输出：
1. 内容概述（约50字）- 必须紧扣主题"{clean_name}"
2. 核心要点（3-5个要点，每个要点用### 小标题）
3. 详细内容（针对每个要点展开说明，保留关键引用和数据）
4. 总结与结论

重要原则：
- 总结必须围绕视频主题（{clean_name}）展开
- 如发现内容偏离主题，以主题为准进行校正
- 保持原文的核心信息和关键细节
- 逻辑清晰，层次分明
- 关键技术术语和概念不要遗漏

古文字处理：如果内容涉及古文字（特别是用双引号""标注的单字或词语，如"手"、"又"、"巾"等），或是提到"篆"相关的字（如篆书、小篆等），或是黑板上写的古文字，请单独标记这些字，用[seal]标签包裹，如：[seal]手[/seal]、[seal]篆[/seal]。注意：只标记单个字或词语，不要标记整句话。"""

    # 如果有对话上下文，添加到提示词
    if chat_context:
        base_prompt += f"\n\n用户对话讨论摘要（供参考）：\n{chat_context}\n\n请结合上述对话讨论要点，在总结中反映用户关注的问题和讨论内容。"

    user_content = text
    if chat_context:
        user_content = f"转录文本：\n{text}\n\n---\n用户对话讨论摘要：\n{chat_context}\n\n请基于以上内容生成详细总结。"

    data = {
        "model": AI_CONFIG["model"],
        "messages": [
            {"role": "system", "content": base_prompt},
            {"role": "user", "content": user_content}
        ],
        "stream": True,
        "temperature": 0.5,  # 适中随机性，平衡创造性和准确性
        "max_tokens": 3000   # 允许更长的详细总结
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"[generate_detailed_summary] 发送请求到 {url}")
            async with client.stream("POST", url, headers=headers, json=data) as response:
                print(f"[generate_detailed_summary] 响应状态码: {response.status_code}")
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"[generate_detailed_summary] 错误响应: {error_text}")
                    yield f"API错误: {response.status_code}"
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        if line == "data: [DONE]":
                            break
                        try:
                            chunk_data = json.loads(line[6:])
                            if "choices" in chunk_data and chunk_data["choices"]:
                                choice = chunk_data["choices"][0]
                                if "delta" in choice:
                                    delta = choice["delta"]
                                    content = delta.get("content", "")
                                    if content and content not in ["<think>", ""]:
                                        # 解码 Unicode 转义
                                        if '\\u' in content:
                                            try:
                                                content = content.encode('utf-8').decode('unicode_escape', errors='replace')
                                            except:
                                                pass
                                        if '<think>' in content:
                                            content = clean_think_tags(content)
                                        if content.strip():
                                            yield content
                                elif "message" in choice:
                                    content = choice["message"].get("content", "")
                                    if content and content not in ["<think>", ""]:
                                        if '\\u' in content:
                                            try:
                                                content = content.encode('utf-8').decode('unicode_escape', errors='replace')
                                            except:
                                                pass
                                        if '<think>' in content:
                                            content = clean_think_tags(content)
                                        if content.strip():
                                            yield content
                        except json.JSONDecodeError:
                            continue
        print("[generate_detailed_summary] 详细总结生成完成")
    except Exception as e:
        print(f"[generate_detailed_summary] 发生错误: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        yield f"错误: {str(e)}"

async def correct_transcription_with_ocr(transcription: List[Dict], ocr_results: List[Dict],
                                         subtitle_results: List[Dict] = None) -> List[Dict]:
    """
    使用 OCR 识别结果和字幕来修正转录结果

    Args:
        transcription: 原始转录结果
        ocr_results: OCR 识别结果列表，每个包含 image_path, text, time 等
        subtitle_results: 字幕识别结果列表

    Returns:
        修正后的转录结果
    """
    if not transcription or len(transcription) == 0:
        return transcription

    url = f"{AI_CONFIG['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }

    # 构建输入数据
    ocr_texts = []
    for ocr in ocr_results:
        if ocr.get('text') and ocr['text'].strip():
            time_str = ""
            if 'time' in ocr:
                time_str = f"[{ocr['time']:.1f}秒]"
            elif 'image_path' in ocr:
                # 从 image_path 提取时间
                import re
                match = re.search(r'_(\d+\.?\d*)s', ocr['image_path'])
                if match:
                    time_str = f"[{match.group(1)}秒]"
            ocr_texts.append(f"{time_str}: {ocr['text'].strip()}")

    subtitle_texts = []
    if subtitle_results:
        for sub in subtitle_results:
            if sub.get('text') and sub['text'].strip():
                # 确保字幕文本是简体
                from services.paddleocr_service import normalize_chinese_text
                text = normalize_chinese_text(sub['text'].strip(), 'simplified')
                subtitle_texts.append(f"[{sub['time']:.1f}秒]: {text}")

    # 构建转录文本
    transcription_text = "\n".join([
        f"[{seg['start']:.1f}s-{seg['end']:.1f}s] {seg['text']}"
        for seg in transcription
    ])

    system_prompt = """你是一个专业的文字校对准。任务是将视频截图中的文字（OCR识别结果、字幕）与音频转录进行对比，找出转录中的错误并进行修正。

修正原则：
1. OCR 识别可能存在误差，如果 OCR 结果与转录高度相似（80%以上匹配），说明转录可能正确
2. 如果 OCR 或字幕中的文字与转录内容有明显差异，优先以 OCR/字幕为准（来自视频画面，更可能是正确的）
3. 重点关注：
   - 同音异字错误：如"无违"vs"无为"，"道德"vs"道得"，"行为"vs"形为"
   - 方言发音导致的常见错误
   - 专业术语错误
   - 文字顺序颠倒或遗漏
4. 保持转录的时间轴不变，只修正文字内容
5. 如果无法确定或差异太大，不做修改

输出要求：
- 输出 JSON 格式，包含修正后的 transcription 数组
- 每个元素包含 start, end, text 三个字段
- 不要输出任何解释，只输出 JSON

重要：只修正明显的错误，不要过度修正。转录中可能包含方言特征，这是正常的。

古文字处理：如果内容涉及古文字（特别是用双引号""标注的单字或词语，如"手"、"又"、"巾"等），或是提到"篆"相关的字（如篆书、小篆等），或是黑板上写的古文字，请单独标记这些字，用[seal]标签包裹，如：[seal]手[/seal]、[seal]篆[/seal]。注意：只标记单个字或词语，不要标记整句话。"""

    user_prompt = f"""【转录文本】
{transcription_text}

【OCR 识别结果】（来自视频截图的文字识别）
{chr(10).join(ocr_texts) if ocr_texts else '（无OCR结果）'}

【字幕识别结果】（来自视频画面检测的字幕）
{chr(10).join(subtitle_texts) if subtitle_texts else '（无字幕）'}

请对比上述内容，找出转录中的错误并修正。输出 JSON 格式的修正结果。

修正示例：
- 如果转录是"无为"但OCR显示"无违"，且语义上"无违"更合理，则修正为"无违"
- 如果转录是"道可道"但OCR显示"道可道，非常道"，应该补全
- 如果不确定，保留原转录内容"""

    data = {
        "model": AI_CONFIG["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "temperature": 0.3,
        "max_tokens": 8000
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"[correct_transcription_with_ocr] 发送请求，OCR条目数: {len(ocr_texts)}, 字幕条目数: {len(subtitle_texts)}")
            resp = await client.post(url, headers=headers, json=data)
            print(f"[correct_transcription_with_ocr] 响应状态: {resp.status_code}")

            if resp.status_code != 200:
                print(f"[correct_transcription_with_ocr] 错误: {resp.text}")
                return transcription

            result = resp.json()
            if "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"].strip()
                # 清理 think 标签
                content = clean_think_tags(content)

                # 提取 JSON
                import re
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    corrected = json.loads(json_match.group(0))
                    print(f"[correct_transcription_with_ocr] 成功，修正 {len(corrected)} 条")
                    return corrected
                else:
                    print(f"[correct_transcription_with_ocr] 无法解析 JSON: {content[:200]}")
            elif "base_resp" in result and result["base_resp"]["status_code"] != 0:
                print(f"[correct_transcription_with_ocr] API错误: {result['base_resp']['status_msg']}")
            return transcription
    except Exception as e:
        print(f"[correct_transcription_with_ocr] 异常: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return transcription
