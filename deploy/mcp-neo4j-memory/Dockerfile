FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Install the mcp-neo4j-memory package
RUN cd servers/mcp-neo4j-memory && pip install -e .

# Expose port
EXPOSE 5000

# Make the start script executable
RUN chmod +x deploy/mcp-neo4j-memory/start.py

# Run the service with Gunicorn (default)
ENV RUN_MODE=gunicorn

# Run the application
CMD ["python", "deploy/mcp-neo4j-memory/start.py"]
