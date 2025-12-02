#!/bin/bash
# Elasticsearch Initialization Script for NL2Py
# This script creates sample indexes and data for testing

echo "Waiting for Elasticsearch to be ready..."
until curl -s http://localhost:9200/_cluster/health | grep -q '"status":"green"\|"status":"yellow"'; do
    sleep 2
done
echo "Elasticsearch is ready!"

# Create products index with mappings
echo "Creating products index..."
curl -X PUT "localhost:9200/products" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "properties": {
      "name": {"type": "text"},
      "description": {"type": "text"},
      "category": {"type": "keyword"},
      "price": {"type": "float"},
      "stock": {"type": "integer"},
      "tags": {"type": "keyword"},
      "rating": {"type": "float"},
      "created_at": {"type": "date"}
    }
  }
}
'

# Index sample products
echo "Indexing sample products..."
curl -X POST "localhost:9200/products/_bulk" -H 'Content-Type: application/json' -d'
{"index":{"_id":"1"}}
{"name":"Laptop Pro 15","description":"High-performance laptop for professionals with 16GB RAM","category":"Electronics","price":1299.99,"stock":50,"tags":["laptop","computer","professional"],"rating":4.5,"created_at":"2025-01-15T10:00:00Z"}
{"index":{"_id":"2"}}
{"name":"Wireless Mouse","description":"Ergonomic wireless mouse with precision tracking","category":"Electronics","price":29.99,"stock":200,"tags":["mouse","wireless","ergonomic"],"rating":4.2,"created_at":"2025-01-15T11:00:00Z"}
{"index":{"_id":"3"}}
{"name":"Mechanical Keyboard","description":"RGB mechanical keyboard with blue switches","category":"Electronics","price":89.99,"stock":150,"tags":["keyboard","mechanical","rgb"],"rating":4.7,"created_at":"2025-01-15T12:00:00Z"}
{"index":{"_id":"4"}}
{"name":"USB-C Hub","description":"7-in-1 USB-C hub with HDMI and ethernet","category":"Electronics","price":49.99,"stock":100,"tags":["hub","usb-c","adapter"],"rating":4.3,"created_at":"2025-01-15T13:00:00Z"}
{"index":{"_id":"5"}}
{"name":"Webcam HD","description":"1080p HD webcam with autofocus","category":"Electronics","price":79.99,"stock":75,"tags":["webcam","camera","hd"],"rating":4.4,"created_at":"2025-01-15T14:00:00Z"}
{"index":{"_id":"6"}}
{"name":"27\" 4K Monitor","description":"Professional 4K monitor with IPS panel","category":"Electronics","price":399.99,"stock":30,"tags":["monitor","4k","display"],"rating":4.8,"created_at":"2025-01-15T15:00:00Z"}
{"index":{"_id":"7"}}
{"name":"Noise-Canceling Headphones","description":"Premium headphones with active noise cancellation","category":"Electronics","price":249.99,"stock":60,"tags":["headphones","audio","noise-canceling"],"rating":4.6,"created_at":"2025-01-15T16:00:00Z"}
{"index":{"_id":"8"}}
{"name":"External SSD 1TB","description":"Fast portable SSD with USB-C connection","category":"Electronics","price":129.99,"stock":120,"tags":["ssd","storage","portable"],"rating":4.5,"created_at":"2025-01-15T17:00:00Z"}
{"index":{"_id":"9"}}
{"name":"Desk Lamp LED","description":"Adjustable LED desk lamp with touch control","category":"Office","price":39.99,"stock":80,"tags":["lamp","led","office"],"rating":4.1,"created_at":"2025-01-15T18:00:00Z"}
{"index":{"_id":"10"}}
{"name":"Ergonomic Chair","description":"Office chair with lumbar support and adjustable height","category":"Office","price":299.99,"stock":25,"tags":["chair","ergonomic","office"],"rating":4.7,"created_at":"2025-01-15T19:00:00Z"}
'

# Create logs index for analytics
echo "Creating logs index..."
curl -X PUT "localhost:9200/logs" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "properties": {
      "timestamp": {"type": "date"},
      "level": {"type": "keyword"},
      "message": {"type": "text"},
      "service": {"type": "keyword"},
      "host": {"type": "keyword"},
      "user": {"type": "keyword"},
      "ip_address": {"type": "ip"},
      "response_time": {"type": "integer"},
      "status_code": {"type": "integer"}
    }
  }
}
'

# Index sample logs
echo "Indexing sample logs..."
curl -X POST "localhost:9200/logs/_bulk" -H 'Content-Type: application/json' -d'
{"index":{}}
{"timestamp":"2025-01-15T10:00:00Z","level":"INFO","message":"Service started successfully","service":"api","host":"server1","user":"admin","ip_address":"192.168.1.100","response_time":150,"status_code":200}
{"index":{}}
{"timestamp":"2025-01-15T10:01:00Z","level":"ERROR","message":"Connection timeout to database","service":"api","host":"server1","user":"user123","ip_address":"192.168.1.101","response_time":5000,"status_code":500}
{"index":{}}
{"timestamp":"2025-01-15T10:02:00Z","level":"INFO","message":"Request processed successfully","service":"web","host":"server2","user":"user456","ip_address":"192.168.1.102","response_time":200,"status_code":200}
{"index":{}}
{"timestamp":"2025-01-15T10:03:00Z","level":"WARN","message":"High memory usage detected","service":"api","host":"server1","user":"system","ip_address":"192.168.1.100","response_time":300,"status_code":200}
{"index":{}}
{"timestamp":"2025-01-15T10:04:00Z","level":"INFO","message":"User logged in","service":"auth","host":"server3","user":"user789","ip_address":"192.168.1.103","response_time":100,"status_code":200}
{"index":{}}
{"timestamp":"2025-01-15T10:05:00Z","level":"ERROR","message":"Authentication failed","service":"auth","host":"server3","user":"hacker","ip_address":"192.168.1.200","response_time":50,"status_code":401}
{"index":{}}
{"timestamp":"2025-01-15T10:06:00Z","level":"INFO","message":"Data backup completed","service":"backup","host":"server4","user":"system","ip_address":"192.168.1.104","response_time":30000,"status_code":200}
{"index":{}}
{"timestamp":"2025-01-15T10:07:00Z","level":"WARN","message":"Slow query detected","service":"db","host":"server5","user":"api_user","ip_address":"192.168.1.105","response_time":2500,"status_code":200}
{"index":{}}
{"timestamp":"2025-01-15T10:08:00Z","level":"INFO","message":"Cache cleared successfully","service":"cache","host":"server6","user":"admin","ip_address":"192.168.1.106","response_time":20,"status_code":200}
{"index":{}}
{"timestamp":"2025-01-15T10:09:00Z","level":"ERROR","message":"Disk space critical","service":"monitoring","host":"server1","user":"system","ip_address":"192.168.1.100","response_time":10,"status_code":500}
'

# Create articles index for full-text search
echo "Creating articles index..."
curl -X PUT "localhost:9200/articles" -H 'Content-Type: application/json' -d'
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "custom_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "stop", "snowball"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title": {"type": "text", "analyzer": "custom_analyzer"},
      "content": {"type": "text", "analyzer": "custom_analyzer"},
      "author": {"type": "keyword"},
      "category": {"type": "keyword"},
      "tags": {"type": "keyword"},
      "published_date": {"type": "date"},
      "views": {"type": "integer"},
      "likes": {"type": "integer"}
    }
  }
}
'

# Index sample articles
echo "Indexing sample articles..."
curl -X POST "localhost:9200/articles/_bulk" -H 'Content-Type: application/json' -d'
{"index":{"_id":"1"}}
{"title":"Getting Started with Elasticsearch","content":"Elasticsearch is a distributed, RESTful search and analytics engine. It provides real-time search and analytics for all types of data.","author":"John Doe","category":"Technology","tags":["elasticsearch","search","tutorial"],"published_date":"2025-01-10T00:00:00Z","views":1500,"likes":120}
{"index":{"_id":"2"}}
{"title":"Machine Learning Basics","content":"Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed.","author":"Jane Smith","category":"AI","tags":["machine-learning","ai","tutorial"],"published_date":"2025-01-12T00:00:00Z","views":2300,"likes":180}
{"index":{"_id":"3"}}
{"title":"Docker Best Practices","content":"Docker containers provide a lightweight way to package and deploy applications. Learn the best practices for using Docker in production.","author":"Bob Johnson","category":"DevOps","tags":["docker","containers","devops"],"published_date":"2025-01-13T00:00:00Z","views":1800,"likes":150}
{"index":{"_id":"4"}}
{"title":"Python for Data Science","content":"Python has become the de facto language for data science. This guide covers essential libraries like NumPy, Pandas, and Matplotlib.","author":"Alice Brown","category":"Data Science","tags":["python","data-science","tutorial"],"published_date":"2025-01-14T00:00:00Z","views":3200,"likes":250}
{"index":{"_id":"5"}}
{"title":"Kubernetes Architecture","content":"Kubernetes is an open-source container orchestration platform. Understanding its architecture is crucial for managing containerized applications.","author":"Charlie Davis","category":"DevOps","tags":["kubernetes","containers","architecture"],"published_date":"2025-01-15T00:00:00Z","views":2100,"likes":175}
'

# Refresh indexes
echo "Refreshing indexes..."
curl -X POST "localhost:9200/_refresh"

echo ""
echo "Elasticsearch initialization complete!"
echo "Indexes created: products, logs, articles"
echo "Sample data loaded successfully"
