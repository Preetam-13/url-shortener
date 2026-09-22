# URL Shortener & Analytics Platform

A production-style URL shortening service built with FastAPI, PostgreSQL, Redis, Docker, Kubernetes, Helm, GitHub Actions, Prometheus, and Grafana.

The project demonstrates backend development, authentication, caching, containerization, Kubernetes deployment, CI/CD, and application monitoring.

---

## Architecture

```text
                         GitHub
                            |
                            v
                    GitHub Actions
                 +-------------------+
                 | Run Tests         |
                 | Build Docker      |
                 | Push Image        |
                 +---------+---------+
                           |
                           v
                       Docker Hub
                           |
                           v
                    Kubernetes Cluster
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
      FastAPI          PostgreSQL         Redis
          |                |                |
          |                v                |
          |              PVC                 |
          |                                 |
          +---------------+-----------------+
                          |
                          v
                      Prometheus
                          |
                          v
                       Grafana



---

## Features

- Create shortened URLs
- Redirect users using short codes
- Track URL click counts
- User registration and JWT-based authentication
- User-specific URL management
- URL analytics
- Redis caching for faster URL lookups
- PostgreSQL database for persistent storage
- Docker containerization
- Kubernetes deployment
- Helm-based deployment and rollback
- GitHub Actions CI/CD pipeline
- Prometheus and Grafana monitoring
- Kubernetes readiness and liveness probes

---

## Technology Stack

| Category | Technology |
|---|---|
| Backend | FastAPI |
| Language | Python 3.10 |
| Database | PostgreSQL |
| Cache | Redis |
| Authentication | JWT + Argon2 |
| Containerization | Docker |
| Orchestration | Kubernetes |
| Package Management | Helm |
| CI/CD | GitHub Actions |
| Container Registry | Docker Hub |
| Monitoring | Prometheus |
| Visualization | Grafana |
| Testing | Pytest |
| Database Migrations | Alembic |

---

## Project Structure

```text
url shortener/
│
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── user_models.py
│   └── redis_client.py
│
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_urls.py
│
├── k8s/
│   ├── api.yaml
│   ├── configmap.yaml
│   ├── postgres.yaml
│   ├── postgres-pvc.yaml
│   ├── redis.yaml
│   └── secret.yaml
│
├── helm/
│   └── url-shortener/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│
├── alembic/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── README.md