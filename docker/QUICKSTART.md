# NL2Py Docker - Quick Start Guide

Get NL2Py running with all services in 5 minutes!

## Step 1: Prerequisites

✅ Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
✅ Ensure at least 8GB RAM available
✅ Get your [OpenAI API key](https://platform.openai.com/api-keys)

## Step 2: Configure API Key

Edit `docker/config/nl2py.conf`:

```ini
[llm]
API_TOKEN = sk-your-actual-openai-key-here
```

## Step 3: Start Services

### Windows:
```cmd
cd docker
start.bat
```

### Linux/Mac:
```bash
cd docker
chmod +x start.sh
./start.sh
```

**Or using docker-compose directly:**
```bash
cd docker
docker-compose up -d
```

⏳ Wait 30-60 seconds for all services to start

## Step 4: Access NL2Py

```bash
docker exec -it nl2py bash
```

You're now inside the NL2Py container!

## Step 5: Run Your First Program

### Create a simple program:

```bash
cat > /app/test.aib << 'EOF'
10 print "Hello from NL2Py!"
20 set x to 5
30 set y to 10
40 add x to y and store in result
50 print "Result:" and result
EOF
```

### Compile and run:

```bash
python src/nl2py/nl2pyc.py \
  -c /app/config/nl2py.conf \
  -i test.aib \
  -o test.py

python test.py
```

Expected output:
```
Hello from NL2Py!
Result: 15
```

## Step 6: Test Database Integration

### PostgreSQL Example:

```bash
cat > /app/test_postgres.aib << 'EOF'
10 (postgres) connect to database "nl2py_db"
20 (postgres) query "SELECT * FROM users"
30 print "Found users:" and row count
40 (postgres) query "SELECT username, email FROM users WHERE age > 25"
50 print "Users over 25:" and row count
EOF
```

Compile and run:
```bash
python src/nl2py/nl2pyc.py -c /app/config/nl2py.conf -i test_postgres.aib -o test_postgres.py
python test_postgres.py
```

### MongoDB Example:

```bash
cat > /app/test_mongodb.aib << 'EOF'
10 (mongodb) connect to collection "products"
20 (mongodb) find documents where category equals "Electronics"
30 print "Found products:" and document count
EOF
```

Compile and run:
```bash
python src/nl2py/nl2pyc.py -c /app/config/nl2py.conf -i test_mongodb.aib -o test_mongodb.py
python test_mongodb.py
```

### Redis Cache Example:

```bash
cat > /app/test_redis.aib << 'EOF'
10 (redis) set key "greeting" to value "Hello NL2Py!"
20 (redis) get value from key "greeting"
30 print "Redis says:" and value
40 (redis) set key "counter" to value 0
50 (redis) increment counter "counter"
60 (redis) increment counter "counter"
70 (redis) get value from key "counter"
80 print "Counter value:" and value
EOF
```

Compile and run:
```bash
python src/nl2py/nl2pyc.py -c /app/config/nl2py.conf -i test_redis.aib -o test_redis.py
python test_redis.py
```

### S3/MinIO Example:

```bash
cat > /app/test_s3.aib << 'EOF'
10 print "Testing MinIO S3 storage..."
20 (csv) create file "data.csv" with sample data
30 (s3) upload file "data.csv" to bucket "nl2py-bucket"
40 print "File uploaded successfully"
50 (s3) list objects in bucket "nl2py-bucket"
60 print "Files in bucket:" and object count
EOF
```

Compile and run:
```bash
python src/nl2py/nl2pyc.py -c /app/config/nl2py.conf -i test_s3.aib -o test_s3.py
python test_s3.py
```

### Email Test (MailHog):

```bash
cat > /app/test_email.aib << 'EOF'
10 (email) send email to "test@example.com"
20 (email) set subject to "Test from NL2Py"
30 (email) set body to "This is a test email from NL2Py Docker"
40 print "Email sent! Check http://localhost:8025"
EOF
```

Compile and run:
```bash
python src/nl2py/nl2pyc.py -c /app/config/nl2py.conf -i test_email.aib -o test_email.py
python test_email.py
```

Then open http://localhost:8025 in your browser to see the email!

## Step 7: Explore Services

Open these URLs in your browser:

- **RabbitMQ**: http://localhost:15672 (nl2py/nl2py123)
- **MinIO Console**: http://localhost:9001 (nl2py/nl2py123)
- **MailHog**: http://localhost:8025

## Step 8: Try Examples

```bash
# Inside the container
cd /app/examples

# Compile any example
python /app/src/nl2py/nl2pyc.py \
  -c /app/config/nl2py.conf \
  -i example_postgres.aib \
  -o /app/output/example.py

python /app/output/example.py
```

## Common Commands

### View logs:
```bash
docker-compose logs -f nl2py
docker-compose logs -f postgres
```

### Restart a service:
```bash
docker-compose restart nl2py
docker-compose restart postgres
```

### Stop all services:
```bash
cd docker
./stop.sh          # Windows: stop.bat
# Or: docker-compose down
```

### Check service status:
```bash
docker-compose ps
```

### Clean up everything (⚠️ deletes all data):
```bash
docker-compose down -v
```

## Troubleshooting

### Services won't start
```bash
# Check Docker is running
docker info

# Check logs
docker-compose logs

# Restart services
docker-compose restart
```

### Out of memory
Increase Docker memory to 8GB in Docker Desktop settings.

### Port conflicts
Edit `docker-compose.yml` and change port mappings:
```yaml
ports:
  - "15432:5432"  # Change first number
```

### OpenSearch won't start
```bash
# Linux/Mac
sudo sysctl -w vm.max_map_count=262144

# Windows (in WSL)
wsl -d docker-desktop
sysctl -w vm.max_map_count=262144
```

## Next Steps

📖 Read the [full documentation](README.md)
📝 Check [examples directory](../examples/)
🔧 Customize [configuration](config/nl2py.conf)
🌐 Explore [module guides](../MODULES_GUIDE.md)

## Getting Help

- Check logs: `docker-compose logs <service-name>`
- View container status: `docker-compose ps`
- Restart services: `docker-compose restart`
- Full reset: `docker-compose down -v && docker-compose up -d`

---

**You're all set!** Start building with NL2Py 🚀
