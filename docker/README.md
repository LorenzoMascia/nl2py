# NL2Py Docker Setup

Complete Docker environment for NL2Py with all integrated modules and services.

## 📦 What's Included

This Docker setup includes:

- **NL2Py Application** - Main application container
- **PostgreSQL 16** - Relational database
- **MySQL 8.0** - Relational database
- **MongoDB 7** - NoSQL document database
- **ClickHouse 23.12** - High-performance analytics database (OLAP)
- **Neo4j 5.15** - Native graph database
- **Elasticsearch 8.11** - Distributed search and analytics engine
- **TimescaleDB (PG 16)** - Time-series database (PostgreSQL extension)
- **LocalStack** - AWS services emulator for local development
- **Redis 7** - In-memory cache
- **RabbitMQ 3** - Message queue with management UI
- **Apache Kafka** - Distributed streaming platform (with Zookeeper)
- **Cassandra 4.1** - Wide-column distributed database
- **OpenSearch 2.11** - Search and analytics engine
- **HashiCorp Vault** - Secrets management
- **MinIO** - S3-compatible object storage
- **MailHog** - SMTP testing server

## 🚀 Quick Start

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 8GB RAM available
- 20GB free disk space

### 1. Set Your OpenAI API Key

Edit `docker/config/nl2py.conf` and replace:
```ini
API_TOKEN = your-openai-api-key-here
```

### 2. Start All Services

```bash
cd docker
docker-compose up -d
```

This will:
- Build the NL2Py image
- Start all 17 services
- Initialize databases with sample data
- Create necessary volumes and networks

### 3. Check Service Health

```bash
docker-compose ps
```

All services should show "healthy" or "running" status.

### 4. Access NL2Py Container

```bash
docker exec -it nl2py bash
```

### 5. Compile and Run NL2Py Programs

```bash
# Inside the container
cd /app
python src/nl2py/nl2pyc.py \
  -c /app/config/nl2py.conf \
  -i examples/example_postgres.aib \
  -o /app/output/program.py

python /app/output/program.py
```

## 🌐 Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| RabbitMQ Management | http://localhost:15672 | nl2py / nl2py123 |
| MinIO Console | http://localhost:9001 | nl2py / nl2py123 |
| OpenSearch | https://localhost:9200 | admin / Aibasic123! |
| Elasticsearch | http://localhost:9200 | - |
| ClickHouse HTTP | http://localhost:8123 | nl2py / nl2py123 |
| Neo4j Browser | http://localhost:7474 | neo4j / nl2py123 |
| TimescaleDB | localhost:5433 | nl2py / nl2py123 |
| LocalStack | http://localhost:4566 | test / test |
| MailHog Web UI | http://localhost:8025 | - |
| PostgreSQL | localhost:5432 | nl2py / nl2py123 |
| MySQL | localhost:3306 | nl2py / nl2py123 |
| MongoDB | localhost:27017 | nl2py / nl2py123 |
| Redis | localhost:6379 | Password: nl2py123 |
| Kafka | localhost:9092 | - |
| Cassandra | localhost:9042 | - |
| Neo4j Bolt | bolt://localhost:7687 | neo4j / nl2py123 |
| Vault | http://localhost:8200 | Token: nl2py-root-token |

## 📁 Directory Structure

```
docker/
├── Dockerfile                  # NL2Py image definition
├── docker-compose.yml          # Services orchestration
├── config/
│   └── nl2py.conf           # Pre-configured for Docker
├── init-scripts/
│   ├── postgres/
│   │   └── 01-init.sql        # PostgreSQL sample data
│   ├── mysql/
│   │   └── 01-init.sql        # MySQL sample data
│   ├── mongodb/
│   │   └── 01-init.js         # MongoDB sample data
│   ├── clickhouse/
│   │   └── 01-init.sql        # ClickHouse sample data
│   ├── neo4j/
│   │   └── 01-init.cypher     # Neo4j sample graph
│   └── elasticsearch/
│       └── init.sh            # Elasticsearch sample indexes
└── data/                       # Shared data directory
```

## 🔧 Common Operations

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Stop Services and Remove Volumes (⚠️ Deletes all data)
```bash
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f nl2py
docker-compose logs -f postgres
```

### Rebuild NL2Py Image
```bash
docker-compose build --no-cache nl2py
docker-compose up -d nl2py
```

### Execute Commands in Container
```bash
# Interactive shell
docker exec -it nl2py bash

# Single command
docker exec nl2py python --version
```

### Check Service Health
```bash
# All services status
docker-compose ps

# Specific service logs
docker-compose logs postgres
```

## 📊 Sample Data

All databases are pre-populated with sample data for testing:

### PostgreSQL
- `users` table - 4 users
- `orders` table - 5 orders
- `products` table - 5 products

### MySQL
- `customers` table - 4 customers
- `sales` table - 5 sales records
- `inventory` table - 4 inventory items

### MongoDB
- `products` collection - 3 products
- `orders` collection - 2 orders
- `logs` collection - 3 log entries

## 🧪 Testing Modules

### Test PostgreSQL
```nl2py
10 (postgres) connect to database "nl2py_db"
20 (postgres) query "SELECT * FROM users"
30 print "Found users:" and row count
```

### Test MongoDB
```nl2py
10 (mongodb) connect to collection "products"
20 (mongodb) find all documents
30 print "Found products:" and document count
```

### Test Redis
```nl2py
10 (redis) set key "test" to value "Hello NL2Py"
20 (redis) get value from key "test"
30 print "Redis value:" and value
```

### Test S3/MinIO
```nl2py
10 (csv) create file "test.csv" with data
20 (s3) upload file "test.csv" to bucket "nl2py-bucket"
30 print "File uploaded successfully"
```

### Test Email (MailHog)
```nl2py
10 (email) send email to "test@example.com"
20 (email) set subject to "Test from NL2Py"
30 (email) set body to "This is a test email"
40 print "Email sent - check http://localhost:8025"
```

## 🔒 Security Notes

**⚠️ This setup is for DEVELOPMENT ONLY**

Default credentials and settings:
- Use strong passwords in production
- Enable SSL/TLS for all services
- Use Docker secrets for sensitive data
- Configure firewalls and network policies
- Use environment variables instead of config files

## 🐛 Troubleshooting

### Services Won't Start

Check Docker resources:
```bash
docker system df
docker system prune  # Clean up unused resources
```

### Out of Memory

Increase Docker memory limit to at least 8GB in Docker Desktop settings.

### Database Connection Errors

Wait for services to be healthy:
```bash
docker-compose ps
docker-compose logs <service-name>
```

Some services (Cassandra, OpenSearch) take 30-60 seconds to start.

### OpenSearch Won't Start

OpenSearch requires vm.max_map_count >= 262144:

**Linux:**
```bash
sudo sysctl -w vm.max_map_count=262144
```

**Windows (WSL2):**
```powershell
wsl -d docker-desktop
sysctl -w vm.max_map_count=262144
```

**macOS:**
```bash
screen ~/Library/Containers/com.docker.docker/Data/vms/0/tty
sysctl -w vm.max_map_count=262144
```

### Port Conflicts

If ports are already in use, modify `docker-compose.yml`:
```yaml
ports:
  - "15432:5432"  # Change first number only
```

## 📚 Example Programs

Check the `/examples` directory for sample NL2Py programs:
- `example_postgres.aib` - PostgreSQL queries
- `example_mongodb.aib` - MongoDB operations
- `example_s3.aib` - S3/MinIO file operations
- `example_email.aib` - Email sending

## 🔄 Updates

### Update NL2Py Code

The `src/` directory is mounted as a volume, so changes are reflected immediately:
```bash
# Edit code on host machine
# Restart container to apply changes
docker-compose restart nl2py
```

### Update Services

```bash
docker-compose pull
docker-compose up -d
```

## 📝 Configuration

Edit `docker/config/nl2py.conf` to customize:
- LLM model and parameters
- Database connections
- Service endpoints
- Authentication credentials

Changes to config require container restart:
```bash
docker-compose restart nl2py
```

## 🎯 Production Deployment

For production use:

1. **Change all default passwords**
2. **Enable SSL/TLS on all services**
3. **Use environment variables** for secrets
4. **Configure persistent volumes** with backups
5. **Set resource limits** in docker-compose.yml
6. **Enable authentication** on all services
7. **Configure monitoring** and logging
8. **Use Docker secrets** instead of config files
9. **Review security settings** for each service
10. **Set up health checks** and restart policies

## 📖 Additional Resources

- [NL2Py Documentation](../docs/)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

## 🤝 Support

For issues or questions:
- Check logs: `docker-compose logs <service>`
- Review configuration: `docker/config/nl2py.conf`
- Rebuild images: `docker-compose build --no-cache`

---

**NL2Py v1.0** - Natural Language Programming with Docker
