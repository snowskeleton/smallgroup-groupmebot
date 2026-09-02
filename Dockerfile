# Use an official Python runtime
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port if needed (adjust based on your Flask app)
EXPOSE 5001

# Run the bot
# One worker, many threads. The scheduled-post loop is a thread inside the
# app, so a second *worker* would be a second scheduler posting duplicates.
# Threads give concurrency for the blocking Sheets and GroupMe calls without
# that, which is the right trade for an I/O-bound app.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "-w", "1", "--threads", "8", "main:app"]
