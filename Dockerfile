# Use a slim version of Python for a smaller image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED="1"
ENV DJANGO_SETTINGS_MODULE="movie_tracker.settings"

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (needed for packages like psycopg2)
# If using SQLite, you can often skip this.
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    # Clean up to keep the image small
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies first (for better Docker caching)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Expose the port Django will run on
EXPOSE 9000

# Default command to run the development server
# NOTE: This will be overridden by docker-compose for migrations/static files.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
