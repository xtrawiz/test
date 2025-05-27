# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install TA-Lib dependencies
RUN apt-get update && apt-get install -y --no-install-recommends build-essential wget libatlas-base-dev libgomp1 && rm -rf /var/lib/apt/lists/*

# Download and install TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Copy the requirements file into the container at /usr/src/app
COPY ./bot/requirements.txt /usr/src/app/requirements.txt

# Install any needed packages specified in requirements.txt
# TA-Lib will be installed from pip after its C libraries are available
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot application code into the container
COPY ./bot /usr/src/app/bot
COPY ./web /usr/src/app/web # For models and schemas
COPY .env /usr/src/app/.env

# Make port 80 available to the world outside this container (if needed by the bot, though usually not)
# EXPOSE 80 

# Define environment variable
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /usr/src/app

# Run main.py when the container launches
# The command will be overridden by docker-compose.yml for bot, celery_worker, celery_beat
CMD ["python", "bot/main.py"]
