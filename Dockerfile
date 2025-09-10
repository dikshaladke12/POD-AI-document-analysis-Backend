# Base image
FROM python:3.10-slim

# Install necessary tools including pdftotext
RUN apt-get update && apt-get install -y netcat-openbsd poppler-utils tesseract-ocr && apt-get clean

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Expose the application port
EXPOSE 9076

# Wait for PostgreSQL to be ready, apply migrations, and start the application
CMD ["bash", "-c", "while ! nc -z db 5432; do sleep 1; done; python manage.py migrate && gunicorn FAX_POD.wsgi:application --bind 0.0.0.0:8000"]


# # Base image
# FROM python:3.10-slim

# # Install necessary tools
# RUN apt-get update && apt-get install -y netcat-openbsd

# # Set environment variables
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # Set the working directory
# WORKDIR /app

# # Install dependencies
# COPY requirements.txt /app/
# RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# # Copy project files
# COPY . /app/

# # Expose the application port
# EXPOSE 9076

# # Wait for PostgreSQL to be ready, apply migrations, and start the application
# CMD ["bash", "-c", "while ! nc -z db 5432; do sleep 1; done; python manage.py migrate && gunicorn FAX_POD.wsgi:application --bind 0.0.0.0:8000"]
