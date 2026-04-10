FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Start server
CMD ["./entrypoint.sh"]
