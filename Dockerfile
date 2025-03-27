FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Install the mcp-neo4j-memory and mcp-neo4j-cypher packages
RUN cd servers/mcp-neo4j-memory && pip install -e .
RUN cd servers/mcp-neo4j-cypher && pip install -e .

# Set default environment variables
ENV NEO4J_URI="bolt://localhost:7687"
ENV NEO4J_USER="neo4j"
ENV NEO4J_PASSWORD="password"

# Expose ports
EXPOSE 5000 5001

# Make the start script executable
RUN chmod +x start-services.py

# Run the services
CMD ["python", "start-services.py"]
