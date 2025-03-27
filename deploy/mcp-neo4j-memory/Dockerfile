FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Install the mcp-neo4j-memory package
RUN cd servers/mcp-neo4j-memory && pip install -e .

# Set environment variables
ENV NEO4J_URI=${NEO4J_URI}
ENV NEO4J_USER=${NEO4J_USER}
ENV NEO4J_PASSWORD=${NEO4J_PASSWORD}
ENV PORT=5000

# Expose the port
EXPOSE ${PORT}

# Run the application
CMD ["python", "deploy/mcp-neo4j-memory/start.py"]
