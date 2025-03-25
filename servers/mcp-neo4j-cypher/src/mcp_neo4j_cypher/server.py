import neo4j
import logging
from logging.handlers import RotatingFileHandler
from contextlib import closing
from pathlib import Path
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from pydantic import AnyUrl
from typing import Any, Dict, List
from neo4j import GraphDatabase
import re
import os
from flask import Flask, request, jsonify

logger = logging.getLogger('mcp_neo4j_cypher')
logger.setLevel(logging.INFO)
logger.info("Starting MCP neo4j Server")

def is_write_query(query: str) -> bool:
    return re.search(r"\b(MERGE|CREATE|SET|DELETE|REMOVE|ADD)\b", query, re.IGNORECASE) is not None

class neo4jDatabase:
    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str):
        """Initialize connection to the neo4j database"""
        logger.debug(f"Initializing database connection to {neo4j_uri}")
        d = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        d.verify_connectivity()
        self.driver = d

    def _execute_query(self, query: str, params: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results as a list of dictionaries"""
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

# Flask app initialization
app = Flask(__name__)
server = Server("neo4j-manager")

# Register handlers
@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="read-neo4j-cypher",
            description="Execute a Cypher query on the neo4j database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Cypher read query to execute"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="write-neo4j-cypher",
            description="Execute a write Cypher query on the neo4j database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Cypher write query to execute"},
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get-neo4j-schema",
            description="List all node types, their attributes and their relationships TO other node-types in the neo4j database",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any] | None
) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""
    try:
        if name == "get-neo4j-schema":
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
            return [types.TextContent(type="text", text=str(results))]

        elif name == "read-neo4j-cypher":
            if is_write_query(arguments["query"]):
                raise ValueError("Only MATCH queries are allowed for read-query")
            results = db._execute_query(arguments["query"])
            return [types.TextContent(type="text", text=str(results))]

        elif name == "write-neo4j-cypher":
            if not is_write_query(arguments["query"]):
                raise ValueError("Only write queries are allowed for write-query")
            results = db._execute_query(arguments["query"])
            return [types.TextContent(type="text", text=str(results))]
        
        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# MCP endpoint
@app.route("/mcp", methods=["POST"])
async def mcp_endpoint():
    """Handle MCP requests"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    try:
        # Simulate the stdio environment
        # In a real implementation, you would parse the request and call the appropriate handler
        if data["method"] == "list_tools":
            result = await handle_list_tools()
            return jsonify({"result": result})
        elif data["method"] == "call_tool":
            result = await handle_call_tool(data["params"]["name"], data["params"]["arguments"])
            return jsonify({"result": result})
        else:
            return jsonify({"error": f"Unknown method: {data['method']}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Global database instance
db = None

# Main function to be called from __init__.py
async def main(neo4j_uri, neo4j_username, neo4j_password):
    """Main entry point for the server."""
    global db
    
    logger.info(f"Starting Neo4j Cypher MCP Server with URI: {neo4j_uri}")
    
    # Connect to Neo4j
    try:
        db = neo4jDatabase(neo4j_uri, neo4j_username, neo4j_password)
        logger.info(f"Connected to Neo4j at {neo4j_uri}")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        raise

    # Start the server
    try:
        transport = mcp.server.stdio.StdioServerTransport()
        await server.connect(transport)
        
        # Keep the server running
        await server.wait_until_disconnected()
    except KeyboardInterrupt:
        logger.info("Server interrupted, shutting down...")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        raise
    finally:
        if db and hasattr(db, 'driver'):
            db.driver.close()
        logger.info("Server shut down")

# For running the Flask app directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
