#!/usr/bin/env python
import os
import sys
import logging
import asyncio
import subprocess
import threading
import time
import multiprocessing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('start-services')

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

def run_memory_service():
    """Run the mcp-neo4j-memory service"""
    logger.info("Starting mcp-neo4j-memory service")
    # Set PORT environment variable for the memory service
    memory_port = 5000
    
    sys.path.insert(0, os.path.join(os.getcwd(), 'servers/mcp-neo4j-memory/src'))
    
    try:
        from mcp_neo4j_memory.server import main, app, memory, Neo4jMemory
        from neo4j import GraphDatabase
        
        # Get Neo4j connection details from environment variables
        neo4j_uri = os.environ.get('NEO4J_URI')
        neo4j_user = os.environ.get('NEO4J_USER')
        neo4j_password = os.environ.get('NEO4J_PASSWORD')
        
        logger.info(f"Memory service connecting to Neo4j at {neo4j_uri}")
        
        # Connect to Neo4j
        neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        # Verify connection
        neo4j_driver.verify_connectivity()
        logger.info(f"Memory service connected to Neo4j at {neo4j_uri}")
        
        # Initialize memory
        globals()['memory'] = Neo4jMemory(neo4j_driver)
        
        # Run the Flask app with Gunicorn
        logger.info(f"Starting Memory Flask web server with Gunicorn on port {memory_port}")
        
        # Create a temporary WSGI file for the memory service
        wsgi_path = os.path.join(os.getcwd(), 'memory_wsgi.py')
        with open(wsgi_path, 'w') as f:
            f.write("""
import sys
import os

# Add the servers directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'servers/mcp-neo4j-memory/src'))

from mcp_neo4j_memory.server import app as application
""")
        
        # Start Gunicorn
        cmd = [
            "gunicorn",
            "--bind", f"0.0.0.0:{memory_port}",
            "--workers", "2",
            "--timeout", "120",
            "memory_wsgi:application"
        ]
        subprocess.run(cmd)
        
    except Exception as e:
        logger.error(f"Error running memory service: {e}")
        
        # Create a simple error response app
        from flask import Flask, jsonify
        error_app = Flask("memory-error")
        
        @error_app.route('/', methods=['GET'])
        def error_response():
            return jsonify({
                "status": "error",
                "service": "mcp-neo4j-memory",
                "error": str(e),
                "neo4j_uri": neo4j_uri,
                "neo4j_user": neo4j_user,
                "neo4j_password": "***" if neo4j_password else None
            })
        
        error_app.run(host='0.0.0.0', port=memory_port)

def run_cypher_service():
    """Run the mcp-neo4j-cypher service"""
    logger.info("Starting mcp-neo4j-cypher service")
    # Set PORT environment variable for the cypher service
    cypher_port = 5001
    
    sys.path.insert(0, os.path.join(os.getcwd(), 'servers/mcp-neo4j-cypher/src'))
    
    try:
        from mcp_neo4j_cypher.server import main, app, db, neo4jDatabase
        
        # Get Neo4j connection details from environment variables
        neo4j_uri = os.environ.get('NEO4J_URI')
        neo4j_username = os.environ.get('NEO4J_USER')
        neo4j_password = os.environ.get('NEO4J_PASSWORD')
        
        logger.info(f"Cypher service connecting to Neo4j at {neo4j_uri}")
        
        # Connect to Neo4j
        globals()['db'] = neo4jDatabase(neo4j_uri, neo4j_username, neo4j_password)
        logger.info(f"Cypher service connected to Neo4j at {neo4j_uri}")
        
        # Run the Flask app with Gunicorn
        logger.info(f"Starting Cypher Flask web server with Gunicorn on port {cypher_port}")
        
        # Create a temporary WSGI file for the cypher service
        wsgi_path = os.path.join(os.getcwd(), 'cypher_wsgi.py')
        with open(wsgi_path, 'w') as f:
            f.write("""
import sys
import os

# Add the servers directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'servers/mcp-neo4j-cypher/src'))

from mcp_neo4j_cypher.server import app as application
""")
        
        # Start Gunicorn
        cmd = [
            "gunicorn",
            "--bind", f"0.0.0.0:{cypher_port}",
            "--workers", "2",
            "--timeout", "120",
            "cypher_wsgi:application"
        ]
        subprocess.run(cmd)
        
    except Exception as e:
        logger.error(f"Error running cypher service: {e}")
        
        # Create a simple error response app
        from flask import Flask, jsonify
        error_app = Flask("cypher-error")
        
        @error_app.route('/', methods=['GET'])
        def error_response():
            return jsonify({
                "status": "error",
                "service": "mcp-neo4j-cypher",
                "error": str(e),
                "neo4j_uri": neo4j_uri,
                "neo4j_user": neo4j_username,
                "neo4j_password": "***" if neo4j_password else None
            })
        
        error_app.run(host='0.0.0.0', port=cypher_port)

if __name__ == "__main__":
    # Log environment variables for debugging
    logger.info(f"NEO4J_URI: {os.environ.get('NEO4J_URI')}")
    logger.info(f"NEO4J_USER: {os.environ.get('NEO4J_USER')}")
    
    # Get the service to run from environment variable
    service = os.environ.get('SERVICE', 'all')
    
    if service == 'memory':
        # Run only the memory service
        run_memory_service()
    elif service == 'cypher':
        # Run only the cypher service
        run_cypher_service()
    else:
        # Run both services in separate processes
        logger.info("Starting both services")
        
        # Start cypher service in a separate process
        cypher_process = multiprocessing.Process(target=run_cypher_service)
        cypher_process.start()
        
        # Wait a bit to ensure cypher service is up
        time.sleep(2)
        
        # Start memory service in the main process
        run_memory_service()
