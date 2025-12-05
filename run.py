#!/usr/bin/env python
"""
ZZImage 启动脚本
"""
import uvicorn
from app.config import HOST, PORT, RELOAD


def main():
    """启动服务"""
    print(f"""
    ╔═══════════════════════════════════════════╗
    ║         🎨 ZZImage 文生图服务              ║
    ╠═══════════════════════════════════════════╣
    ║  服务地址: http://{HOST}:{PORT}              ║
    ║  API文档:  http://{HOST}:{PORT}/docs         ║
    ║  管理界面: http://{HOST}:{PORT}              ║
    ╚═══════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD,
        log_level="info"
    )


if __name__ == "__main__":
    main()
