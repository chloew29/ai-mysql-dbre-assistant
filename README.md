# AI-Assisted MySQL DBRE Platform

A hands-on Database Reliability Engineering (DBRE) platform that provisions a production-style **MySQL 8 primary–replica topology** in Docker, loads it with realistic data at scale, and demonstrates the core DBRE workflow: **replication, query optimization, health monitoring, and backup/restore** — with an AI assistant layer on the roadmap.

Built to mirror the day-to-day work of keeping a relational data tier fast, observable, and recoverable.

---

## Why this project

Most demo databases are toy-sized and single-node, which hides the problems that actually matter in production. This platform is built around the failure modes and performance work a DBRE deals with: replication topology and lag, slow queries on multi-million-row tables, monitoring via `performance_schema`, and tested backup/restore paths.

Everything is reproducible from a single `docker compose up` — no manual setup.

---

## Architecture

```
                 ┌──────────────────────────────┐
   writes ─────► │   MySQL 8  (PRIMARY)          │
                 │   GTID enabled                │
                 └──────────────┬───────────────┘
                                │  GTID-based replication
                                ▼
                 ┌──────────────────────────────┐
   reads  ◄───── │   MySQL 8  (REPLICA)          │
                 │   super_read_only = ON        │
                 └──────────────────────────────┘
                                ▲
                                │  performance_schema metrics
                 ┌──────────────┴───────────────┐
                 │   Python health monitor       │
                 │   + backup / restore scripts  │
                 └──────────────────────────────┘
```

- **GTID-based replication** between primary and replica for consistent, position-free failover.
- **`super_read_only`** enforced on the replica to prevent accidental writes and replication drift.
- Orchestrated entirely with **Docker Compose** so the whole topology comes up identically every time.

---

## Tech stack

| Layer | Tools |
|---|---|
| Database | MySQL 8 (primary–replica, GTID) |
| Orchestration | Docker, Docker Compose |
| Data generation | Python, Faker |
| Monitoring / scripting | Python, `performance_schema` |
| Analysis | `EXPLAIN`, `EXPLAIN ANALYZE` |

---

## What it demonstrates

- **Replication setup** — primary–replica with GTID and `super_read_only`, provisioned from scratch in containers.
- **Realistic scale** — a 10-table e-commerce schema seeded with ~1.2M synthetic rows via Python/Faker, so query plans behave like they would in production.
- **Query optimization case studies** — five slow queries profiled with `EXPLAIN` / `EXPLAIN ANALYZE`, then tuned (indexing, rewrites, join order) with measured before/after results — up to ~22x faster. *(See `docs/` for the per-query writeups.)*
- **Health monitoring** — a Python monitor that reads `performance_schema` to surface replication lag, slow queries, and connection/throughput signals.
- **Backup & restore** — scripted logical backup and restore, validating the recovery path rather than assuming it works.

---

## Query optimization highlights

Each case study documents the original query, its plan, the bottleneck, the fix, and the measured improvement.

| Case | Bottleneck | Fix | Result |
|---|---|---|---|
| 1 | Full table scan on filtered lookup | Composite index | ~22x faster |
| 2 | Inefficient join order on large tables | Index + rewrite | ~19x faster |
| 3 | _[add]_ | _[add]_ | _[add]_ |
| 4 | _[add]_ | _[add]_ | _[add]_ |
| 5 | _[add]_ | _[add]_ | _[add]_ |

> Replace the `[add]` rows with your actual case studies and confirm the exact multipliers from your `EXPLAIN ANALYZE` runs.

---

## Quickstart

```bash
# 1. Clone
git clone https://github.com/chloew29/ai-mysql-dbre-assistant.git
cd ai-mysql-dbre-assistant

# 2. Bring up the primary + replica
docker compose up -d

# 3. Seed the schema and ~1.2M rows
python scripts/seed_data.py        # adjust to your actual script name

# 4. Run the health monitor
python scripts/health_monitor.py   # adjust to your actual script name
```

> Confirm the script paths/names match your repo — placeholders above.

---

## Repository structure

```
ai-mysql-dbre-assistant/
├── docker-compose.yml        # primary + replica topology
├── primary/                  # primary config (my.cnf, init SQL)
├── replica/                  # replica config
├── schema/                   # 10-table e-commerce schema
├── scripts/                  # seed data, health monitor, backup/restore
├── docs/                     # query optimization case studies
└── README.md
```

> This is a conventional layout — swap in your real tree (paste `git ls-files` and I'll match it exactly).

---

## Roadmap

- [ ] **Disaster-recovery drill** — scripted primary failure + replica promotion, with documented RTO/RPO.
- [ ] **AI/RAG DBRE assistant** — natural-language layer over the monitoring data and runbooks: explain slow-query plans, suggest indexes, and answer "why is replication lagging?" grounded in live `performance_schema` output.

---

## About

Built by Chloe Wong as a hands-on DBRE portfolio project.

- GitHub: [chloew29](https://github.com/chloew29)
- _[add LinkedIn / portfolio link]_