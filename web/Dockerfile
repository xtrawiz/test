# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY ./web/requirements.txt /usr/src/app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the web application code into the container
COPY ./web /usr/src/app/web
COPY .env /usr/src/app/.env # If web service needs .env directly

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /usr/src/app

# Run uvicorn server when the container launches
# The command will be overridden by docker-compose.yml
CMD ["uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "8000"]
