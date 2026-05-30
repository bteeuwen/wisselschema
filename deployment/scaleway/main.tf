# ============================================================================
# Wisselschema - Scaleway Deployment
# ============================================================================
# This creates:
# 1. Container registry - stores Docker images
# 2. Container namespace - groups containers
# 3. Serverless container - runs the Django app (scale-to-zero, ~€0 idle)
# 4. Database + user on the existing shared RDB instance (blind-typen)
#
# Estimated cost: ~€0 idle, ~€1-2/million requests
# ============================================================================

terraform {
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.38"
    }
  }
  required_version = ">= 1.0"
}

# ============================================================================
# Variables
# ============================================================================

variable "region" {
  description = "Scaleway region"
  type        = string
  default     = "fr-par"
}

variable "zone" {
  description = "Scaleway availability zone"
  type        = string
  default     = "fr-par-1"
}

variable "django_secret_key" {
  description = "Django SECRET_KEY for production"
  type        = string
  sensitive   = true
}

variable "create_app_container" {
  description = "Create the container after the first image has been pushed"
  type        = bool
  default     = false
}

variable "mysql_instance_id" {
  description = "Existing RDB instance ID (shared with blind-typen)"
  type        = string
  default     = "6ec7756c-d3c0-4f8a-bdfa-bde47f13cf78"
}

variable "mysql_password" {
  description = "Password for the wisselschema DB user"
  type        = string
  sensitive   = true
}

variable "django_allowed_hosts" {
  description = "Space-separated list of allowed hosts (set after first deploy)"
  type        = string
  default     = ""
}

# ============================================================================
# Provider
# ============================================================================

provider "scaleway" {
  region = var.region
  zone   = var.zone
}

# ============================================================================
# Existing RDB instance (blind-typen shared MySQL)
# ============================================================================

data "scaleway_rdb_instance" "shared" {
  instance_id = var.mysql_instance_id
  region      = var.region
}

locals {
  mysql_host = data.scaleway_rdb_instance.shared.load_balancer[0].ip
  mysql_port = data.scaleway_rdb_instance.shared.load_balancer[0].port
}

resource "scaleway_rdb_database" "wisselschema" {
  instance_id = "${var.region}/${var.mysql_instance_id}"
  name        = "wisselschema"
  region      = var.region
}

resource "scaleway_rdb_user" "wisselschema" {
  instance_id = "${var.region}/${var.mysql_instance_id}"
  name        = "wisselschema"
  password    = var.mysql_password
  is_admin    = false
  region      = var.region
}

resource "scaleway_rdb_privilege" "wisselschema" {
  instance_id   = "${var.region}/${var.mysql_instance_id}"
  user_name     = scaleway_rdb_user.wisselschema.name
  database_name = scaleway_rdb_database.wisselschema.name
  permission    = "all"
  region        = var.region
}

# ============================================================================
# Container Registry
# ============================================================================

resource "scaleway_registry_namespace" "main" {
  name        = "wisselschema"
  description = "Docker images for wisselschema"
  is_public   = false
}

# ============================================================================
# Container Namespace
# ============================================================================

resource "scaleway_container_namespace" "main" {
  name        = "wisselschema"
  description = "Serverless containers for wisselschema"
}

# ============================================================================
# Serverless Container - scale-to-zero (costs ~€0 when idle)
# ============================================================================

resource "scaleway_container" "app" {
  count = var.create_app_container ? 1 : 0

  name         = "wisselschema-app"
  namespace_id = scaleway_container_namespace.main.id

  registry_image = "${scaleway_registry_namespace.main.endpoint}/wisselschema-app:latest"

  min_scale = 0 # Scale to zero when not in use
  max_scale = 1

  memory_limit = 512
  cpu_limit    = 280

  port                   = 8000
  timeout                = 60
  http_option = "redirected"

  environment_variables = {
    DJANGO_DEBUG         = "False"
    DJANGO_ALLOWED_HOSTS = var.django_allowed_hosts
  }

  secret_environment_variables = {
    DJANGO_SECRET_KEY = var.django_secret_key
    DATABASE_URL      = "mysql://wisselschema:${var.mysql_password}@${local.mysql_host}:${local.mysql_port}/wisselschema"
  }

  deploy = true

  depends_on = [scaleway_rdb_privilege.wisselschema]
}

# ============================================================================
# Outputs
# ============================================================================

output "app_url" {
  description = "Public URL of the app"
  value       = length(scaleway_container.app) > 0 ? "https://${scaleway_container.app[0].domain_name}" : null
}

output "registry_endpoint" {
  description = "Docker registry endpoint"
  value       = scaleway_registry_namespace.main.endpoint
}

output "container_id" {
  description = "Container ID for deployment"
  value       = length(scaleway_container.app) > 0 ? scaleway_container.app[0].id : null
}

output "domain_name" {
  description = "Container domain name (set django_allowed_hosts to this after first deploy)"
  value       = length(scaleway_container.app) > 0 ? scaleway_container.app[0].domain_name : null
}

output "mysql_host" {
  description = "MySQL host"
  value       = local.mysql_host
}
