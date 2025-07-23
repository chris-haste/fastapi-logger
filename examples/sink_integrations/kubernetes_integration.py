# Example Kubernetes manifest for deploying a FastAPI app with fapilog sinks

KUBERNETES_MANIFEST = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-logger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fastapi-logger
  template:
    metadata:
      labels:
        app: fastapi-logger
    spec:
      containers:
      - name: fastapi-logger
        image: your-docker-repo/fastapi-logger:latest
        env:
        - name: FAPILOG_SINKS
          value: (
            "postgres://postgres:5432/logs,"
            "elasticsearch://elasticsearch:9200/logs"
          )
        - name: FAPILOG_LEVEL
          value: "INFO"
        ports:
        - containerPort: 8000
"""

# Save this manifest as deployment.yaml and apply with:
# kubectl apply -f deployment.yaml
