import os
import json
import httpx
from backend.config import AI_CONFIG

async def test_detailed_summary_api():
    print("Testing detailed summary API...")
    
    # 模拟前端发送的请求
    test_text = "这是一个测试视频的转录内容。视频讲述了人工智能的发展历史和未来趋势。首先介绍了人工智能的起源，然后讨论了机器学习和深度学习的发展，最后展望了AI在各个领域的应用前景。"
    
    # 直接调用AI服务的函数
    from backend.services.ai_service import generate_detailed_summary
    
    try:
        print("Calling generate_detailed_summary function...")
        summary_chunks = []
        async for chunk in generate_detailed_summary(test_text):
            print(f"Received chunk: {chunk}")
            summary_chunks.append(chunk)
        
        full_summary = "".join(summary_chunks)
        print(f"\nFull summary generated: {full_summary}")
        print("\n✅ Detailed summary API test passed!")
        
    except Exception as e:
        print(f"\n❌ Detailed summary API test failed: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_detailed_summary_api())