print("Testing Python environment...")

try:
    import os
    import sys
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    # 测试导入模块
    from backend.config import AI_CONFIG
    print(f"AI_CONFIG: {AI_CONFIG}")
    
    print("Test successful!")
except Exception as e:
    print(f"Test failed: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
