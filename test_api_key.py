import httpx
import json

# 测试 API 密钥
api_key = "sk-cp-GAyfdBUfd2_CGBhrqLrmgq2W-s37XhvOTAk8FSzuNuuzxTgiFrp7mR0xRkw8lk0koVT-dg40n9eygtjxuw_OTPG8pakHOhiMWfVMsES-qJWAtx7E9zw9AYg"
base_url = "https://api.minimax.chat/v1"

async def test_api_key():
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "minimax-m2.7",
        "messages": [
            {"role": "system", "content": "请简单回答：你好"},
            {"role": "user", "content": "你好"}
        ],
        "stream": False
    }

    print(f"测试 API 密钥...")
    print(f"URL: {url}")
    print(f"API Key: {api_key[:20]}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=data)
            print(f"响应状态码: {resp.status_code}")
            if resp.status_code != 200:
                print(f"错误响应: {resp.text}")
            else:
                result = resp.json()
                print(f"成功！响应: {result}")
    except Exception as e:
        print(f"发生错误: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_api_key())
