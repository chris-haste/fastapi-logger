FROM python:3.11-slim

# Install fapilog and custom sinks
RUN pip install fapilog fapilog-postgres fapilog-elasticsearch

# Set environment variables
ENV FAPILOG_SINKS=postgres://postgres:5432/logs,elasticsearch://elasticsearch:9200/logs
ENV FAPILOG_LEVEL=INFO

# Your application code
COPY . /app
WORKDIR /app

CMD ["python", "app.py"] 