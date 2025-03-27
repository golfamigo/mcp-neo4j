FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY src/ /app/src/
COPY start.py .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "start.py"]
