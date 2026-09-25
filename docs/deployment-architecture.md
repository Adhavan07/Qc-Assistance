# Deployment & Cloud Infrastructure Architecture
**Project**: Wiring Diagram QC Assistant  
**Client / Product Owner**: Spandsons Horizon Engineering Pvt. Ltd.  
**Version**: 1.0.0 | **Date**: 2026-09-25

---

## 1. Cloud Provider & Compute Target
* **Target Cloud**: AWS (Production region: Asia Pacific - Mumbai `ap-south-1` or US East `us-east-1`).
* **Container Orchestration**: AWS ECS (Elastic Container Service) with AWS Fargate (Serverless container execution, eliminating EC2 management overhead).
* **Load Balancing & CDN**: AWS Application Load Balancer (ALB) behind CloudFront CDN with AWS WAF for DDoS, rate limiting, and SQL injection protection.

## 2. Infrastructure as Code (Terraform)
All infrastructure is declared via modular Terraform under `infra/`:
```
infra/
├── modules/
│   ├── vpc/             # 3-tier VPC (Public, Private App, Private Data)
│   ├── ecs/             # ECS Cluster, Task Definitions, Fargate Services
│   ├── rds/             # Aurora / RDS PostgreSQL Multi-AZ with pgvector
│   ├── elasticache/     # Redis Cluster for caching & job queuing
│   ├── s3/              # Encrypted private document buckets & lifecycle rules
│   ├── sqs/             # Background job queues & Dead Letter Queues (DLQ)
│   ├── iam/             # Least-privilege IAM roles and task execution policies
│   └── monitoring/      # CloudWatch alarms, Log Groups, OpenSearch / Grafana
└── environments/
    ├── dev/
    ├── staging/
    └── prod/
```

## 3. Container Images & Multi-Stage Builds
* **`frontend`**: Node.js 20 multi-stage build producing a standalone Next.js production server.
* **`api`**: Python 3.11-slim multi-stage build running Uvicorn with Gunicorn workers.
* **`worker`**: Python 3.11-slim container with Poppler (`pdftoppm`) and Tesseract OCR installed, running Celery/ARQ workers under an unprivileged user (`qcuser:1001`).
