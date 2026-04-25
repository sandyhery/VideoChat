import os
import json
from typing import List
from models import ChatMessage
from config import AI_CONFIG
import httpx

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
3. 如有视频文件名，将其作为重要参考信息"""

    if filename:
        import re
        clean_filename = re.sub(r'\.\w+$', '', filename)  # 去除扩展名
        clean_filename = re.sub(r'^\d+[_\-]', '', clean_filename)  # 去除开头的序号
        system_prompt = f"""你是一个专业的视频内容分析助手。请对以下内容进行简洁准确的总结。

视频文件名为 "{clean_filename}"，这个文件名包含了重要的主题信息，请作为总结的重要参考。

要求：
1. 总结应该简洁有力，突出核心内容
2. 保留关键术语和数据
3. 结合文件名理解内容主题
4. 总结长度控制在200字以内"""

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
                                    if content:
                                        yield content
                                elif "message" in choice:
                                    content = choice["message"].get("content", "")
                                    if content:
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
        import re
        root_topic = "主题"
        if filename:
            clean_filename = re.sub(r'\.\w+$', '', filename)
            clean_filename = re.sub(r'^\d+[_\-]', '', clean_filename)
            root_topic = clean_filename
        
        example = {
            "meta": {"name": "思维导图", "author": "AI", "version": "1.0"},
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
        
        system_prompt = f"""你是一个专业的思维导图生成专家。请将视频内容转换为结构化的思维导图 JSON。

## 核心要求：
1. 严格按示例格式生成 JSON
2. 包含 meta、format、data 三个顶级字段
3. data 必须包含 id、topic、children 字段
4. 第一层子节点必须指定 direction（left/right），左右交替
5. 所有节点的 id 必须唯一
6. 只返回 JSON，不要任何额外说明
7. 确保 JSON 格式有效可解析

## 内容理解指导：
- 根节点使用视频文件名 "{root_topic}" 作为主题
- 子节点要提炼核心主题和关键要点
- 思维导图层级控制在3-4层
- 子节点数量适中，每个节点内容简洁

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
            "temperature": 0.6,
            "max_tokens": 4000  # 增加 token 限制以支持更复杂的思维导图
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
            elif "base_resp" in result and result["base_resp"]["status_code"] != 0:
                raise Exception(result["base_resp"]["status_msg"])
            else:
                full_response = str(result)

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
                "meta": {"name": "解析错误", "author": "System", "version": "1.0"},
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
4. 如问题超出上下文范围，请明确告知"""

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

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, headers=headers, json=data) as response:
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
                                if content:
                                    yield content
                            elif "message" in choice:
                                content = choice["message"].get("content", "")
                                if content:
                                    yield content
                    except json.JSONDecodeError:
                        continue

async def generate_detailed_summary(text: str, filename: str = ""):
    print(f"[generate_detailed_summary] 开始生成详细总结，输入文本长度: {len(text)}")
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
        import re
        clean_filename = re.sub(r'\.\w+$', '', filename)
        clean_filename = re.sub(r'^\d+[_\-]', '', clean_filename)
        base_prompt = f"""你是一个专业的视频内容分析助手。请对以下内容进行详细、系统的总结分析。

视频文件名为 "{clean_filename}"，这个文件名包含了重要的主题信息，请作为总结的重要参考。

请严格按照以下Markdown结构输出：
1. 内容概述（约50字）
2. 核心要点（3-5个要点，每个要点用### 小标题）
3. 详细内容（针对每个要点展开说明，保留关键引用和数据）
4. 总结与结论

重要原则：
- 保持原文的核心信息和关键细节
- 结合文件名理解内容主题
- 逻辑清晰，层次分明
- 关键技术术语和概念不要遗漏"""

    data = {
        "model": AI_CONFIG["model"],
        "messages": [
            {"role": "system", "content": base_prompt},
            {"role": "user", "content": text}
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
                                    if content:
                                        yield content
                                elif "message" in choice:
                                    content = choice["message"].get("content", "")
                                    if content:
                                        yield content
                        except json.JSONDecodeError:
                            continue
        print("[generate_detailed_summary] 详细总结生成完成")
    except Exception as e:
        print(f"[generate_detailed_summary] 发生错误: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        yield f"错误: {str(e)}"
