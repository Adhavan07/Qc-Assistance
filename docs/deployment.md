# Deployment & Infrastructure Architecture Document

**Project**: Wiring Diagram QC Assistant  
**Client**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 2.0.0 (Phase 0 Architecture Release)  
**Date**: 2026-09-25  

---

## 1. AWS Production Architecture

The production cloud infrastructure is provisioned on **Amazon Web Services (AWS)** using **Terraform** Infrastructure as Code (IaC). To maximize reliability and minimize operational complexity, the architecture utilizes managed serverless containers (**AWS ECS Fargate**) and managed datastores (**Amazon RDS** and **Amazon ElastiCache**).

```mermaid
graph TD
    subgraph "Public Edge (Global)"
        R53["Amazon Route 53 (DNS / Anycast)"]
        CF["Amazon CloudFront CDN (Static Frontend Assets & Caching)"]
        WAF["AWS WAF (Layer 7 Anti-DDoS, Rate Limiting & OWASP Rules)"]
    end

    subgraph "VPC: 10.0.0.0/16 (ap-south-1 / us-east-1)"
        subgraph "Public Subnets (AZ-A, AZ-B)"
            ALB["Application Load Balancer (ALB) - TLS 1.3 ACM"]
            NAT["NAT Gateways (Egress Only)"]
        end

        subgraph "Private Application Subnets (AZ-A, AZ-B)"
            ECS_Web["ECS Fargate: Next.js Frontend"]
            ECS_API["ECS Fargate: FastAPI Backend"]
            ECS_Worker["ECS Fargate: Background QC Workers"]
        end

        subgraph "Private Isolated Data Subnets (AZ-A, AZ-B)"
            RDS[("Amazon RDS PostgreSQL 16 (Multi-AZ Standby)")]
            Redis[("Amazon ElastiCache Redis (In-Memory Queue)")]
        end
    end

    subgraph "Managed Cloud Services"
        S3[("Amazon S3 (Encrypted Buckets: Uploads, Reports, Evidence)")]
        KMS["AWS KMS (Envelope Encryption Keys)"]
        SM["AWS Secrets Manager (DB Passwords, JWT Keys, API Keys)"]
        CW["Amazon CloudWatch (Logs, Metrics, Alarms)"]
        SES["Amazon SES (Transactional Notifications)"]
    end

    R53 --> CF
    CF --> WAF
    WAF --> ALB
    ALB -->|/*| ECS_Web
    ALB -->|/api/v1/*| ECS_API

    ECS_API --> RDS
    ECS_API --> Redis
    ECS_API --> S3
    ECS_API --> SM

    ECS_Worker --> Redis
    ECS_Worker --> RDS
    ECS_Worker --> S3
    ECS_Worker --> NAT
    NAT -->|Outbound HTTPS| AI_Providers["External AI Endpoints (OpenAI / Anthropic / Gemini)"]

    ECS_API --> CW
    ECS_Worker --> CW
```

---

## 2. VPC Subnetting & Network Isolation Rules

1. **Zero Public Ingress to Data**:
   - The PostgreSQL database (`RDS`) and Redis cluster (`ElastiCache`) are placed in **Private Isolated Subnets** with zero internet gateways or public IP assignments.
   - Worker containers live in **Private Application Subnets** with outbound internet access strictly mediated through NAT Gateways for calling external AI model APIs.
2. **Security Groups Least Privilege**:
   - `ALB Security Group`: Inbound 443 from CloudFront origin prefix-list or public internet; outbound to ECS API security group on port 8000 and ECS Web on port 3000.
   - `ECS API Security Group`: Inbound 8000 strictly from ALB Security Group; outbound to RDS on port 5432, Redis on port 6379, and S3 VPC Endpoint.
   - `RDS Security Group`: Inbound 5432 strictly from ECS API and ECS Worker security groups; zero internet access.

---

## 3. Terraform Module Hierarchy

Infrastructure is modularized into reusable, version-controlled Terraform modules:

```
infrastructure/terraform/
├── environments/
│   ├── staging/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── production/
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
├── modules/
│   ├── vpc/                    # Multi-AZ VPC, subnets, route tables, NAT gateways
│   ├── security_groups/        # Least-privilege ingress/egress firewalls
│   ├── alb/                    # HTTPS listeners, target groups, health probes
│   ├── ecs/                    # Fargate clusters, task definitions, autoscaling
│   ├── rds/                    # PostgreSQL Multi-AZ, automated backups, KMS
│   ├── redis/                  # ElastiCache Redis replication group
│   ├── s3/                     # Private buckets, lifecycle rules, KMS SSE
│   ├── iam/                    # Task execution roles with least-privilege policies
│   ├── secrets/                # Secrets Manager integration
│   └── cloudwatch/             # Log groups, error rate alarms, latency metrics
```

---

## 4. Local Development Environment (Docker Compose)

For local development and testing, all required services are containerized to run seamlessly on a developer workstation with single-command startup:

```yaml
# docker-compose.yml
version: "3.8"

services:
  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
    depends_on:
      - api

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/qc_assistant
      - REDIS_URL=redis://redis:6379/0
      - S3_ENDPOINT_URL=http://minio:9000
      - S3_BUCKET_NAME=qc-assistant-documents
      - S3_ACCESS_KEY=minioadmin
      - S3_SECRET_KEY=minioadmin
    depends_on:
      - postgres
      - redis
      - minio

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    command: python -m backend.src.services.qc_worker
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/qc_assistant
      - REDIS_URL=redis://redis:6379/0
      - S3_ENDPOINT_URL=http://minio:9000
    depends_on:
      - postgres
      - redis
      - minio

  postgres:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=qc_assistant
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - miniodata:/data

  mailpit:
    image: axllent/mailpit:latest
    ports:
      - "8025:8025" # Web UI
      - "1025:1025" # SMTP

volumes:
  pgdata:
  miniodata:
```
