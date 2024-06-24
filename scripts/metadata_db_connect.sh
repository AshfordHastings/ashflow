#!/bin/bash

# Define the namespace where PostgreSQL is running
NAMESPACE="default"

# Define the name of the Kubernetes secret containing the PostgreSQL credentials
SECRET_NAME="ashflow-metadata"
SECRET_KEY="connection"

# Fetch the PostgreSQL credentials from the Kubernetes secret
CONNECTION_STRING=$(kubectl get secret --namespace $NAMESPACE $SECRET_NAME -o jsonpath="{.data.$SECRET_KEY}" | base64 --decode)


# Find the PostgreSQL pod
POD_NAME=$(kubectl get pods --namespace $NAMESPACE -l "app.kubernetes.io/name=postgresql" -o jsonpath="{.items[0].metadata.name}")
echo $POSTGRES_PASSWORD
# Log into the PostgreSQL pod and start a psql session
kubectl exec -it --namespace $NAMESPACE $POD_NAME -- psql "$CONNECTION_STRING"
