import uvicorn
import os

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        reload_dirs=["backend"],  # 只监视 backend 目录
        reload_excludes=["node_modules", "uploads"]  # 排除这些目录
    ) 