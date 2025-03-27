#!/usr/bin/env python
import os
import sys
import logging
import asyncio
import subprocess
import threading
import time

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
    os.environ['PORT'] = '5000'
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
        
        # Run the Flask app
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Memory Flask web server on port {port}")
        app.run(host='0.0.0.0', port=port, threaded=True)
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
        
        port = int(os.environ.get('PORT', 5000))
        error_app.run(host='0.0.0.0', port=port)

def run_cypher_service():
    """Run the mcp-neo4j-cypher service"""
    logger.info("Starting mcp-neo4j-cypher service")
    os.environ['PORT'] = '5001'
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
        
        # Run the Flask app
        port = int(os.environ.get('PORT', 5001))
        logger.info(f"Starting Cypher Flask web server on port {port}")
        app.run(host='0.0.0.0', port=port, threaded=True)
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
        
        port = int(os.environ.get('PORT', 5001))
        error_app.run(host='0.0.0.0', port=port)

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
        # Run both services in separate threads
        logger.info("Starting both services")
        
        memory_thread = threading.Thread(target=run_memory_service)
        cypher_thread = threading.Thread(target=run_cypher_service)
        
        memory_thread.daemon = True
        cypher_thread.daemon = True
        
        memory_thread.start()
        cypher_thread.start()
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            sys.exit(0)
