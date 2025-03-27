#!/usr/bin/env python
"""
Neo4j Memory MCP Server - 使用FastAPI和FastMCP实现
"""
import os
import sys
import logging
import uvicorn
import json
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP, Context
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

import neo4j
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
            "neo4j_memory_server.log", 
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
    ]
)
logger = logging.getLogger('mcp_neo4j_memory')
logger.info("Starting Neo4j Memory MCP Server")

# 获取环境变量
NEO4J_URI = os.environ.get('NEO4J_URI') or os.environ.get('NEO4J_URL', 'bolt://localhost:7687')
NEO4J_USER = os.environ.get('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', 'password')
DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'

# 设置日志级别
if DEBUG:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.debug("Debug mode enabled")

# 知识图谱模型
class Entity(BaseModel):
    name: str
    type: str
    observations: List[str]

class Relation(BaseModel):
    source: str
    target: str
    relationType: str

class KnowledgeGraph(BaseModel):
    entities: List[Entity]
    relations: List[Relation]

class ObservationAddition(BaseModel):
    entityName: str
    contents: List[str]

class ObservationDeletion(BaseModel):
    entityName: str
    observations: List[str]

class Neo4jMemory:
    def __init__(self, neo4j_driver):
        self.neo4j_driver = neo4j_driver
        self.create_fulltext_index()

    def create_fulltext_index(self):
        try:
            # 创建全文搜索索引
            query = """
            CREATE FULLTEXT INDEX search IF NOT EXISTS FOR (m:Memory) ON EACH [m.name, m.type, m.observations];
            """
            self.neo4j_driver.execute_query(query)
            logger.info("Created fulltext search index")
        except neo4j.exceptions.ClientError as e:
            if "An index with this name already exists" in str(e):
                logger.info("Fulltext search index already exists")
            else:
                raise e

    async def load_graph(self, filter_query="*"):
        query = """
            CALL db.index.fulltext.queryNodes('search', $filter) yield node as entity, score
            OPTIONAL MATCH (entity)-[r]-(other)
            RETURN collect(distinct {
                name: entity.name, 
                type: entity.type, 
                observations: entity.observations
            }) as nodes,
            collect({
                source: startNode(r).name, 
                target: endNode(r).name, 
                relationType: type(r)
            }) as relations
        """
        
        result = self.neo4j_driver.execute_query(query, {"filter": filter_query})
        
        if not result.records:
            return KnowledgeGraph(entities=[], relations=[])
        
        record = result.records[0]
        nodes = record.get('nodes')
        rels = record.get('relations')
        
        entities = [
            Entity(
                name=node.get('name'),
                type=node.get('type'),
                observations=node.get('observations', [])
            )
            for node in nodes if node.get('name')
        ]
        
        relations = [
            Relation(
                source=rel.get('source'),
                target=rel.get('target'),
                relationType=rel.get('relationType')
            )
            for rel in rels if rel.get('source') and rel.get('target') and rel.get('relationType')
        ]
        
        logger.debug(f"Loaded entities: {entities}")
        logger.debug(f"Loaded relations: {relations}")
        
        return KnowledgeGraph(entities=entities, relations=relations)

    async def create_entities(self, entities: List[Entity]) -> List[Entity]:
        query = """
        UNWIND $entities as entity
        MERGE (e:Memory { name: entity.name })
        SET e += entity {.type, .observations}
        SET e:$(entity.type)
        """
        
        entities_data = [entity.model_dump() for entity in entities]
        self.neo4j_driver.execute_query(query, {"entities": entities_data})
        return entities

    async def create_relations(self, relations: List[Relation]) -> List[Relation]:
        for relation in relations:
            query = """
            UNWIND $relations as relation
            MATCH (from:Memory),(to:Memory)
            WHERE from.name = relation.source
            AND  to.name = relation.target
            MERGE (from)-[r:$(relation.relationType)]->(to)
            """
            
            self.neo4j_driver.execute_query(
                query, 
                {"relations": [relation.model_dump() for relation in relations]}
            )
        
        return relations

    async def add_observations(self, observations: List[ObservationAddition]) -> List[Dict[str, Any]]:
        query = """
        UNWIND $observations as obs  
        MATCH (e:Memory { name: obs.entityName })
        WITH e, [o in obs.contents WHERE NOT o IN e.observations] as new
        SET e.observations = coalesce(e.observations,[]) + new
        RETURN e.name as name, new
        """
            
        result = self.neo4j_driver.execute_query(
            query, 
            {"observations": [obs.model_dump() for obs in observations]}
        )

        results = [{"entityName": record.get("name"), "addedObservations": record.get("new")} for record in result.records]
        return results

    async def delete_entities(self, entity_names: List[str]) -> None:
        query = """
        UNWIND $entities as name
        MATCH (e:Memory { name: name })
        DETACH DELETE e
        """
        
        self.neo4j_driver.execute_query(query, {"entities": entity_names})

    async def delete_observations(self, deletions: List[ObservationDeletion]) -> None:
        query = """
        UNWIND $deletions as d  
        MATCH (e:Memory { name: d.entityName })
        SET e.observations = [o in coalesce(e.observations,[]) WHERE NOT o IN d.observations]
        """
        self.neo4j_driver.execute_query(
            query, 
            {
                "deletions": [deletion.model_dump() for deletion in deletions]
            }
        )

    async def delete_relations(self, relations: List[Relation]) -> None:
        query = """
        UNWIND $relations as relation
        MATCH (source:Memory)-[r:$(relation.relationType)]->(target:Memory)
        WHERE source.name = relation.source
        AND target.name = relation.target
        DELETE r
        """
        self.neo4j_driver.execute_query(
            query, 
            {"relations": [relation.model_dump() for relation in relations]}
        )

    async def read_graph(self) -> KnowledgeGraph:
        return await self.load_graph()

    async def search_nodes(self, query: str) -> KnowledgeGraph:
        return await self.load_graph(query)

    async def find_nodes(self, names: List[str]) -> KnowledgeGraph:
        return await self.load_graph("name: (" + " ".join(names) + ")")

# 初始化Neo4j数据库连接
try:
    logger.info(f"Connecting to Neo4j at {NEO4J_URI}")
    neo4j_driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD)
    )
    neo4j_driver.verify_connectivity()
    logger.info(f"Connected to Neo4j at {NEO4J_URI}")
    
    # 初始化内存
    memory = Neo4jMemory(neo4j_driver)
except Exception as e:
    logger.error(f"Failed to connect to Neo4j: {e}")
    if not DEBUG:
        sys.exit(1)
    else:
        logger.warning("Using mock database for local development")
        neo4j_driver = None
        memory = None

# 创建FastMCP实例
mcp = FastMCP("neo4j-memory")

# 注册工具
@mcp.tool("create_entities", "Create multiple new entities in the knowledge graph")
async def create_entities_tool(ctx: Context, entities: List[Dict[str, Any]]):
    """创建多个实体"""
    logger.info(f"Creating {len(entities)} entities")
    
    try:
        entity_objects = [Entity(**entity) for entity in entities]
        result = await memory.create_entities(entity_objects)
        return {"entities": [e.model_dump() for e in result]}
    except Exception as e:
        logger.error(f"Error creating entities: {e}")
        return {"error": str(e)}

@mcp.tool("create_relations", "Create multiple new relations between entities in the knowledge graph")
async def create_relations_tool(ctx: Context, relations: List[Dict[str, Any]]):
    """创建多个关系"""
    logger.info(f"Creating {len(relations)} relations")
    
    try:
        relation_objects = [Relation(**relation) for relation in relations]
        result = await memory.create_relations(relation_objects)
        return {"relations": [r.model_dump() for r in result]}
    except Exception as e:
        logger.error(f"Error creating relations: {e}")
        return {"error": str(e)}

@mcp.tool("add_observations", "Add new observations to existing entities in the knowledge graph")
async def add_observations_tool(ctx: Context, observations: List[Dict[str, Any]]):
    """添加观察内容"""
    logger.info(f"Adding observations to {len(observations)} entities")
    
    try:
        observation_objects = [ObservationAddition(**obs) for obs in observations]
        result = await memory.add_observations(observation_objects)
        return {"results": result}
    except Exception as e:
        logger.error(f"Error adding observations: {e}")
        return {"error": str(e)}

@mcp.tool("delete_entities", "Delete multiple entities and their associated relations from the knowledge graph")
async def delete_entities_tool(ctx: Context, entityNames: List[str]):
    """删除实体"""
    logger.info(f"Deleting {len(entityNames)} entities")
    
    try:
        await memory.delete_entities(entityNames)
        return {"status": "success", "message": "Entities deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting entities: {e}")
        return {"error": str(e)}

@mcp.tool("delete_observations", "Delete specific observations from entities in the knowledge graph")
async def delete_observations_tool(ctx: Context, deletions: List[Dict[str, Any]]):
    """删除观察内容"""
    logger.info(f"Deleting observations from {len(deletions)} entities")
    
    try:
        deletion_objects = [ObservationDeletion(**deletion) for deletion in deletions]
        await memory.delete_observations(deletion_objects)
        return {"status": "success", "message": "Observations deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting observations: {e}")
        return {"error": str(e)}

@mcp.tool("delete_relations", "Delete multiple relations from the knowledge graph")
async def delete_relations_tool(ctx: Context, relations: List[Dict[str, Any]]):
    """删除关系"""
    logger.info(f"Deleting {len(relations)} relations")
    
    try:
        relation_objects = [Relation(**relation) for relation in relations]
        await memory.delete_relations(relation_objects)
        return {"status": "success", "message": "Relations deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting relations: {e}")
        return {"error": str(e)}

@mcp.tool("read_graph", "Read the entire knowledge graph")
async def read_graph_tool(ctx: Context):
    """读取整个知识图谱"""
    logger.info("Reading entire graph")
    
    try:
        result = await memory.read_graph()
        return result.model_dump()
    except Exception as e:
        logger.error(f"Error reading graph: {e}")
        return {"error": str(e)}

@mcp.tool("search_nodes", "Search for nodes in the knowledge graph based on a query")
async def search_nodes_tool(ctx: Context, query: str):
    """搜索节点"""
    logger.info(f"Searching nodes with query: {query}")
    
    try:
        result = await memory.search_nodes(query)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Error searching nodes: {e}")
        return {"error": str(e)}

@mcp.tool("find_nodes", "Open specific nodes in the knowledge graph by their names")
async def find_nodes_tool(ctx: Context, names: List[str]):
    """查找特定节点"""
    logger.info(f"Finding nodes: {names}")
    
    try:
        result = await memory.find_nodes(names)
        return result.model_dump()
    except Exception as e:
        logger.error(f"Error finding nodes: {e}")
        return {"error": str(e)}

# 创建FastAPI应用
app = FastAPI(title="Neo4j Memory MCP Server")

# 主页路由
@app.get("/")
def index():
    """健康检查端点"""
    return {
        "status": "ok",
        "service": "mcp-neo4j-memory",
        "version": "1.0.0"
    }

# 挂载MCP服务器
app.mount("/", mcp.sse_app())

# 启动服务器
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
