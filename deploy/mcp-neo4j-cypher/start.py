#!/usr/bin/env python
import os
import sys
import logging
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mcp-neo4j-cypher')

# Add the servers directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '../..'))
sys.path.insert(0, os.path.join(project_root, 'servers/mcp-neo4j-cypher/src'))

# Handle different environment variable names
neo4j_uri = os.environ.get('NEO4J_URI') or os.environ.get('NEO4J_URL')
neo4j_user = os.environ.get('NEO4J_USER')
neo4j_password = os.environ.get('NEO4J_PASSWORD')

# Set environment variables for consistency
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

def run_with_flask():
    """Run the service with Flask development server"""
    from mcp_neo4j_cypher.server import app, db, neo4jDatabase
    
    # Get Neo4j connection details from environment variables
    neo4j_uri = os.environ.get('NEO4J_URI')
    neo4j_username = os.environ.get('NEO4J_USER')
    neo4j_password = os.environ.get('NEO4J_PASSWORD')
    
    logger.info(f"Connecting to Neo4j at {neo4j_uri}")
    
    # Connect to Neo4j
    globals()['db'] = neo4jDatabase(neo4j_uri, neo4j_username, neo4j_password)
    logger.info(f"Connected to Neo4j at {neo4j_uri}")
    
    # Run the Flask app
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask web server on port {port}")
    app.run(host='0.0.0.0', port=port)

def run_with_gunicorn():
    """Run the service with Gunicorn"""
    # Create a temporary WSGI file
    wsgi_path = os.path.join(os.getcwd(), 'wsgi.py')
    with open(wsgi_path, 'w') as f:
        f.write("""
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('wsgi')

# Add the servers directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir))
sys.path.insert(0, os.path.join(project_root, 'servers/mcp-neo4j-cypher/src'))

# Handle different environment variable names
neo4j_uri = os.environ.get('NEO4J_URI') or os.environ.get('NEO4J_URL')
neo4j_user = os.environ.get('NEO4J_USER')
neo4j_password = os.environ.get('NEO4J_PASSWORD')

# Set environment variables for consistency
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

from mcp_neo4j_cypher.server import app, db, neo4jDatabase

try:
    # Get Neo4j connection details from environment variables
    neo4j_uri = os.environ.get('NEO4J_URI')
    neo4j_username = os.environ.get('NEO4J_USER')
    neo4j_password = os.environ.get('NEO4J_PASSWORD')
    
    logger.info(f"Connecting to Neo4j at {neo4j_uri}")
    
    # Connect to Neo4j
    globals()['db'] = neo4jDatabase(neo4j_uri, neo4j_username, neo4j_password)
    logger.info(f"Connected to Neo4j at {neo4j_uri}")
except Exception as e:
    logger.error(f"Error connecting to Neo4j: {e}")
    # We'll let the application handle the error

# Export the Flask app as 'application' for WSGI
application = app
""")
    
    # Start Gunicorn
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Gunicorn on port {port}")
    
    import subprocess
    cmd = [
        "gunicorn",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "2",
        "--timeout", "120",
        "wsgi:application"
    ]
    subprocess.run(cmd)

async def run_with_mcp():
    """Run the service with MCP over stdio"""
    from mcp_neo4j_cypher.server import main
    
    # Get Neo4j connection details from environment variables
    neo4j_uri = os.environ.get('NEO4J_URI')
    neo4j_username = os.environ.get('NEO4J_USER')
    neo4j_password = os.environ.get('NEO4J_PASSWORD')
    
    logger.info(f"Starting MCP server with Neo4j at {neo4j_uri}")
    
    # Run the MCP server
    await main(neo4j_uri, neo4j_username, neo4j_password)

if __name__ == "__main__":
    # Log environment variables for debugging
    logger.info(f"NEO4J_URI: {os.environ.get('NEO4J_URI')}")
    logger.info(f"NEO4J_USER: {os.environ.get('NEO4J_USER')}")
    
    # Determine the run mode
    run_mode = os.environ.get('RUN_MODE', 'gunicorn').lower()
    
    if run_mode == 'flask':
        # Run with Flask development server
        run_with_flask()
    elif run_mode == 'mcp':
        # Run with MCP over stdio
        asyncio.run(run_with_mcp())
    else:
        # Default to Gunicorn for production
        run_with_gunicorn()
