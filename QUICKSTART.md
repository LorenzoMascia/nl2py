# NL2Py Quick Start Guide

Get started with NL2Py in 5 minutes!

## 📦 Installation

```bash
# 1. Clone or navigate to the project
cd nl2py

# 2. Install the package
pip install -e .

# 3. Install GUI (optional but recommended)
pip install gradio>=4.0.0
```

## 🚀 Launch the GUI

```bash
nl2py-gui
```

The GUI will open at `http://localhost:7860`

## 💡 Try Your First Translation

In the GUI, try these commands:

### Cloud Storage
```
create s3 bucket my-data-store
upload file report.pdf to s3 bucket backups
```

### Databases
```
connect to postgres database production
execute query SELECT * FROM users
set redis key session:123 to active
```

### Containers
```
list all docker containers
deploy kubernetes deployment nginx with 3 replicas
```

### Messaging
```
send message to slack channel devops with text Deploy completed
publish message to kafka topic events
```

## 🎯 What Gets Generated

For: `create s3 bucket my-data-store`

You get:
```python
from nl2py import modules

s3_create_bucket(name='my-data-store')
```

## 📚 More Examples

Check `examples/quick_examples.txt` for 25+ ready-to-use commands!

## ⚙️ Configuration (Optional)

Most modules work without configuration. For database/API modules, copy the example config:

```bash
cp nl2py.conf.example nl2py.conf
# Edit nl2py.conf with your credentials
```

## 🐳 Docker Testing Environment (Optional)

Want to test database modules? Start all services with Docker:

```bash
cd docker
docker-compose up -d
```

This gives you instant access to:
- PostgreSQL, MySQL, MongoDB, Redis
- Kafka, RabbitMQ, Elasticsearch
- And 10+ more services!

## 🆘 Troubleshooting

### GUI won't start
```bash
# Make sure you installed it
pip install -e .
pip install gradio
```

### No modules loading
```bash
# This should show 1300+ examples
python -c "from nl2py import create_interpreter; create_interpreter()"
```

### Need help?
- Check the full README.md
- See examples/ folder
- Check docs/ website

## 🎓 Next Steps

1. **Explore the GUI tabs:**
   - Quick Translate: Single commands
   - Batch Translation: Multiple commands
   - Explore Options: See alternative matches
   - Module Reference: Browse all 35+ modules

2. **Try the CLI:**
   ```bash
   python -m nl2py.nlp_interpreter --interactive
   ```

3. **Use in your Python code:**
   ```python
   from nl2py import create_interpreter

   interpreter = create_interpreter()
   result = interpreter.interpret("create s3 bucket my-data")
   print(result.generated_code)
   ```

## 🌟 Tips for Best Results

- Be specific: ❌ "create bucket" → ✅ "create s3 bucket my-data"
- Include parameters: ❌ "send slack message" → ✅ "send slack message to channel devops"
- Use full names: ❌ "connect db" → ✅ "connect to postgres database production"
- Try alternatives: Use "Explore Options" tab to see other matching methods

---

**Ready to go!** Start translating natural language to Python! 🚀
