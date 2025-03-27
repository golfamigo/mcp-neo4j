#!/usr/bin/env python
import os
import sys
import logging
import asyncio

# Add the servers directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'servers/mcp-neo4j-memory/src'))

# Import the server module
from mcp_neo4j_memory.server import main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('start')

# Get Neo4j connection details from environment variables
neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
neo4j_user = os.environ.get('NEO4J_USER', 'neo4j')
neo4j_password = os.environ.get('NEO4J_PASSWORD', 'password')

logger.info(f"Starting Neo4j Memory MCP Server with URI: {neo4j_uri}")

if __name__ == "__main__":
    try:
        # Run the main function
        asyncio.run(main(neo4j_uri, neo4j_user, neo4j_password))
    except KeyboardInterrupt:
        logger.info("Server interrupted, shutting down...")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)
