#!/usr/bin/env python
"""
启动脚本 - 启动Neo4j Memory MCP服务器
"""
import os
import sys
import logging
import uvicorn
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mcp-neo4j-memory')

# 加载.env文件
load_dotenv()

# 添加src目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'src'))

# 处理不同的环境变量名称
neo4j_uri = os.environ.get('NEO4J_URI') or os.environ.get('NEO4J_URL')
neo4j_user = os.environ.get('NEO4J_USER')
neo4j_password = os.environ.get('NEO4J_PASSWORD')

# 设置环境变量以保持一致性
if neo4j_uri:
    os.environ['NEO4J_URI'] = neo4j_uri
else:
    os.environ['NEO4J_URI'] = 'bolt://localhost:7687'
    
if neo4j_user:
    os.environ['NEO4J_USER'] = neo4j_user
else:
    os.environ['NEO4J_USER'] = 'neo4j'
    
if neo4j_password:
    os.environ['NEO4J_PASSWORD'] = neo4j_password
else:
    os.environ['NEO4J_PASSWORD'] = 'password'

if __name__ == "__main__":
    # 记录环境变量以进行调试
    logger.info(f"NEO4J_URI: {os.environ.get('NEO4J_URI')}")
    logger.info(f"NEO4J_USER: {os.environ.get('NEO4J_USER')}")
    
    # 导入服务器模块
    from server import app
    
    # 获取端口
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting server on port {port}")
    
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
