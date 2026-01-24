FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY templates/ ./templates/
COPY webui.py .
COPY tournament_config.json .
COPY .env .

# Create volume mount point for persistent data
VOLUME ["/app/data"]

# Expose ports
EXPOSE 5000

# Default command (can be overridden in docker-compose)
CMD ["python", "webui.py"]
