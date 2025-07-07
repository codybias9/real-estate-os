<#
.SYNOPSIS
    Adds and updates the required Helm chart repositories for the project.
    This script is idempotent and can be run safely multiple times.
.DESCRIPTION
    Adds Bitnami for core services like Postgres and RabbitMQ, and Qdrant for the vector database.
#>
Write-Host "Adding and updating Helm repositories..."
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add qdrant https://qdrant.github.io/qdrant-helm
helm repo update
Write-Host "Helm repositories are up to date."
