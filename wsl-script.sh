#!/bin/bash
set -e # Exit script if any command fails

echo "--- AGGRESSIVE CLEANUP ---"
minikube delete --all --purge || true
docker system prune -af || true
sudo rm -rf /var/lib/minikube || true
sudo rm -rf /root/.minikube || true
sudo rm -rf ~/.minikube || true
echo "Cleanup complete."

echo "--- Installing required tools inside WSL ---"
sudo apt-get update && sudo apt-get install -y curl
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

echo "--- Starting Minikube cluster with Docker driver ---"
minikube start --driver=docker --memory=7000 --cpus=6 --force --kubernetes-version=v1.28.3

echo "--- Building Docker image ---"
docker build -t codybias9/reo-airflow:0.1.0 -f infra/images/airflow/Dockerfile .

echo "--- Loading image into Minikube ---"
minikube image load codybias9/reo-airflow:0.1.0

echo "--- Setting up Helm repository ---"
helm repo add apache-airflow https://airflow.apache.org
helm repo update

echo "--- Installing or Upgrading Airflow Helm release (with increased timeout) ---"
helm upgrade --install airflow apache-airflow/airflow --namespace airflow --create-namespace -f infra/charts/overrides/values-airflow.yaml --timeout 15m

echo "--- Deployment script completed successfully! ---"
echo "--- Monitor the pod rollout with: kubectl get pods -n airflow -w ---"
