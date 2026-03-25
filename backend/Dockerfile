FROM python:3.11-alpine

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip --no-cache-dir

# Copy requirements
COPY requirements.txt .

# Install dependencies with timeout
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

# Run Flask
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]