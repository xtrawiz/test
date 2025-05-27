# 1. Use the official python:3.10-slim image as the base.
FROM python:3.10-slim

# 2. Set the working directory to /app.
WORKDIR /app

# 3. Create a non-root user `appuser` and switch to it.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# 4. Copy the requirements.txt file into the /app directory.
COPY requirements.txt .

# 5. Install dependencies from requirements.txt using pip. Ensure pip is upgraded first.
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the web application code from the crypto_bot/web directory into the /app directory in the container.
COPY . .

# 7. Copy the shared core module code from crypto_bot/core into /app/core in the container.
COPY ../core ./core

# 8. Copy the static directory from crypto_bot/static into /app/static in the container.
COPY ../static ./static

# 9. Copy the templates directory from crypto_bot/templates into /app/templates in the container.
COPY ../templates ./templates

# 10. Make the /app directory owned by appuser.
# This step is implicitly handled as files copied are owned by the current USER (appuser)
# and WORKDIR /app is also created with appuser ownership if it doesn't exist.
# However, to be explicit, especially if any previous operations were done as root:
USER root
RUN chown -R appuser:appgroup /app
USER appuser

# 11. Expose port 8000 for the FastAPI application.
EXPOSE 8000

# 12. Specify the command to run the FastAPI server using Uvicorn.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
