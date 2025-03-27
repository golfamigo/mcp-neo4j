#!/usr/bin/env python
import os
import sys
import logging
import asyncio

# Add the servers directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, os.path.join(project_root, 'servers/mcp-neo4j-cypher/src'))

# Import the server module
from mcp_neo4j_cypher.server import main, app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('start')

# Get Neo4j connection details from environment variables
neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
neo4j_username = os.environ.get('NEO4J_USER', 'neo4j')
neo4j_password = os.environ.get('NEO4J_PASSWORD', 'password')

logger.info(f"Starting Neo4j Cypher MCP Server with URI: {neo4j_uri}")

# Check if we're running in Railway (PORT environment variable is set)
is_railway = 'PORT' in os.environ

if __name__ == "__main__":
    try:
        if is_railway:
            # Initialize the database instance
            from mcp_neo4j_cypher.server import db, neo4jDatabase
            
            # Connect to Neo4j
            globals()['db'] = neo4jDatabase(neo4j_uri, neo4j_username, neo4j_password)
            logger.info(f"Connected to Neo4j at {neo4j_uri}")
            
            # Run the Flask app
            port = int(os.environ.get('PORT', 5000))
            logger.info(f"Starting Flask web server on port {port}")
            app.run(host='0.0.0.0', port=port)
        else:
            # Run the MCP server over stdio
            asyncio.run(main(neo4j_uri, neo4j_username, neo4j_password))
    except KeyboardInterrupt:
        logger.info("Server interrupted, shutting down...")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)
