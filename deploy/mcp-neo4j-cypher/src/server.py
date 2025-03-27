#!/usr/bin/env python
"""
Neo4j Cypher MCP Server - 使用FastAPI和FastMCP实现
"""
import os
import sys
import logging
import uvicorn
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
import re
from neo4j import GraphDatabase

# 加载.env文件
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            "neo4j_cypher_server.log", 
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
    ]
)
logger = logging.getLogger('mcp_neo4j_cypher')
logger.info("Starting Neo4j Cypher MCP Server")

# 获取环境变量
NEO4J_URI = os.environ.get('NEO4J_URI') or os.environ.get('NEO4J_URL', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'

# 设置日志级别
if DEBUG:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.debug("Debug mode enabled")

def is_write_query(query: str) -> bool:
    """判断是否为写入查询"""
    return re.search(r"\b(MERGE|CREATE|SET|DELETE|REMOVE|ADD)\b", query, re.IGNORECASE) is not None

class Neo4jDatabase:
    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str):
        """初始化Neo4j数据库连接"""
        logger.debug(f"Initializing database connection to {neo4j_uri}")
        d = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        d.verify_connectivity()
        self.driver = d

    def _execute_query(self, query: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """执行Cypher查询并返回结果"""
        logger.debug(f"Executing query: {query}")
        try:
            result = self.driver.execute_query(query, params)
            counters = vars(result.summary.counters)
            if is_write_query(query):
                logger.debug(f"Write query affected {counters}")
                return [counters]
            else:
                results = [dict(r) for r in result.records]
                logger.debug(f"Read query returned {len(results)} rows")
                return results
        except Exception as e:
            logger.error(f"Database error executing query: {e}\n{query}")
            raise

# 初始化Neo4j数据库连接
try:
    logger.info(f"Connecting to Neo4j at {NEO4J_URI}")
    db = Neo4jDatabase(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    logger.info(f"Connected to Neo4j at {NEO4J_URI}")
except Exception as e:
    logger.error(f"Failed to connect to Neo4j: {e}")
    if not DEBUG:
        sys.exit(1)
    else:
        logger.warning("Using mock database for local development")
        db = None

# 创建FastMCP实例
mcp = FastMCP("neo4j-cypher")

# 注册工具
@mcp.tool("read-neo4j-cypher", "Execute a Cypher query on the neo4j database")
async def read_neo4j_cypher(ctx: Context, query: str):
    """执行只读Cypher查询"""
    logger.info(f"Executing read query: {query}")
    
    if is_write_query(query):
        return {"error": "Only MATCH queries are allowed for read-query"}
    
    try:
        results = db._execute_query(query)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error executing read query: {e}")
        return {"error": str(e)}

@mcp.tool("write-neo4j-cypher", "Execute a write Cypher query on the neo4j database")
async def write_neo4j_cypher(ctx: Context, query: str):
    """执行写入Cypher查询"""
    logger.info(f"Executing write query: {query}")
    
    if not is_write_query(query):
        return {"error": "Only write queries are allowed for write-query"}
    
    try:
        results = db._execute_query(query)
        return {"results": results}
    except Exception as e:
        logger.error(f"Error executing write query: {e}")
        return {"error": str(e)}

@mcp.tool("get-neo4j-schema", "List all node types, their attributes and their relationships TO other node-types in the neo4j database")
async def get_neo4j_schema(ctx: Context):
    """获取Neo4j数据库模式"""
    logger.info("Getting Neo4j schema")
    
    try:
        results = db._execute_query(
            """
            call apoc.meta.data() yield label, property, type, other, unique, index, elementType
            where elementType = 'node' and not label starts with '_'
            with label, 
                collect(case when type <> 'RELATIONSHIP' then [property, type + case when unique then " unique" else "" end + case when index then " indexed" else "" end] end) as attributes,
                collect(case when type = 'RELATIONSHIP' then [property, head(other)] end) as relationships
            RETURN label, apoc.map.fromPairs(attributes) as attributes, apoc.map.fromPairs(relationships) as relationships
            """
        )
        return {"schema": results}
    except Exception as e:
        logger.error(f"Error getting Neo4j schema: {e}")
        return {"error": str(e)}

# 创建FastAPI应用
app = FastAPI(title="Neo4j Cypher MCP Server")

# 主页路由
@app.get("/")
def index():
    """健康检查端点"""
    return {
        "status": "ok",
        "service": "mcp-neo4j-cypher",
        "version": "1.0.0"
    }

# 挂载MCP服务器
app.mount("/", mcp.sse_app())

# 启动服务器
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
