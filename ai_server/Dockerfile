FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV DJANGO_SETTINGS_MODULE=ai_server.settings
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security
RUN useradd -m appuser
USER appuser

# Expose the port Django runs on
EXPOSE 8000

# Start the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
