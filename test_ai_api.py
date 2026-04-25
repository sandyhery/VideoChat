import os
import json
import httpx
from backend.config import AI_CONFIG

async def test_ai_api():
    print("Testing AI API connection...")
    print(f"API Base URL: {AI_CONFIG['base_url']}")
    print(f"Model: {AI_CONFIG['model']}")
    
    url = f"{AI_CONFIG['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AI_CONFIG['api_key']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": AI_CONFIG["model"],
        "messages": [
            {"role": "system", "content": "请简要总结以下内容："},
            {"role": "user", "content": "这是一个测试消息，用于验证AI API是否正常工作。"}
        ],
        "stream": True
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("Sending request to AI API...")
            async with client.stream("POST", url, headers=headers, json=data) as response:
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        print(f"Received: {line}")
                        if line == "data: [DONE]":
                            break
                        try:
                            chunk_data = json.loads(line[6:])
                            print(f"Parsed data: {chunk_data}")
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ai_api())