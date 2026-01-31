# CodePilot Deployment Guide

This guide covers different deployment scenarios for CodePilot, from local development to production deployment.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Local Inference Server](#local-inference-server)
3. [AWS Deployment](#aws-deployment)
4. [Docker Deployment](#docker-deployment)
5. [VSCode Extension Installation](#vscode-extension-installation)
6. [Production Considerations](#production-considerations)

---

## Local Development Setup

### Prerequisites

- Ubuntu 20.04+ (or similar Linux distribution)
- Python 3.8+
- CUDA 11.8+ (for GPU support)
- 16GB+ RAM (32GB recommended for training)
- Node.js 16+ (for VSCode extension)

### Quick Start

```bash
# Clone repository
git clone https://github.com/sreekar-gajula/code-pilot.git
cd code-pilot

# Run automated setup
chmod +x scripts/setup.sh
./scripts/setup.sh

# Activate environment
source venv/bin/activate
```

### Manual Setup

If automated setup fails:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data/{raw,processed} model/checkpoints logs evaluation/results
```

---

## Local Inference Server

### Option 1: Using Pre-trained Model

```bash
# Activate environment
source venv/bin/activate

# Set model path (will auto-download from HuggingFace)
export MODEL_PATH="codellama/CodeLlama-13b-Instruct-hf"

# Start server
cd inference
python server.py --model-path $MODEL_PATH --port 8000
```

### Option 2: Using Fine-tuned Model

After training your own model:

```bash
# Set path to your fine-tuned model
export MODEL_PATH="./model/checkpoints/codepilot-13b"

# Start server
cd inference
python server.py --model-path $MODEL_PATH --port 8000
```

### Testing the Server

```bash
# Health check
curl http://localhost:8000/health

# Test completion
curl -X POST http://localhost:8000/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "void can_transmit_message(can_msg_t* msg) {\n",
    "max_tokens": 150,
    "temperature": 0.2
  }'
```

### Server Configuration

Edit `inference/config.yaml`:

```yaml
model:
  path: "./model/codepilot-13b"
  quantization: "4bit"
  
server:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  
vllm:
  max_model_len: 4096
  tensor_parallel_size: 1
  dtype: "float16"
```

---

## AWS Deployment

### EC2 Instance Setup

1. **Launch EC2 Instance**
   - Instance Type: `g5.2xlarge` (NVIDIA A10G GPU)
   - AMI: Deep Learning AMI (Ubuntu)
   - Storage: 100GB EBS
   - Security Group: Open port 8000

2. **Connect and Setup**

```bash
# SSH into instance
ssh -i your-key.pem ubuntu@<instance-ip>

# Clone repository
git clone https://github.com/sreekar-gajula/code-pilot.git
cd code-pilot

# Run setup
./scripts/setup.sh

# Install NVIDIA drivers (if not using DL AMI)
sudo apt-get install -y nvidia-driver-525
```

3. **Start Service**

```bash
# Run as background service with systemd
sudo cp scripts/codepilot.service /etc/systemd/system/
sudo systemctl enable codepilot
sudo systemctl start codepilot

# Check status
sudo systemctl status codepilot
```

### systemd Service File

Create `/etc/systemd/system/codepilot.service`:

```ini
[Unit]
Description=CodePilot Inference Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/code-pilot
Environment="PATH=/home/ubuntu/code-pilot/venv/bin"
ExecStart=/home/ubuntu/code-pilot/venv/bin/python inference/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Load Balancing (Optional)

For high availability, use AWS ELB:

```bash
# Install nginx
sudo apt-get install -y nginx

# Configure reverse proxy
sudo nano /etc/nginx/sites-available/codepilot
```

Nginx config:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Docker Deployment

### Build Image

```bash
# Build production image
docker build -t codepilot:latest .

# Or build development image
docker build --target development -t codepilot:dev .
```

### Run Container

```bash
# Run with GPU support
docker run --gpus all -p 8000:8000 \
  -v $(pwd)/model:/app/model \
  codepilot:latest

# Run with custom configuration
docker run --gpus all -p 8000:8000 \
  -e MODEL_PATH=/app/model/codepilot-13b \
  -e API_PORT=8000 \
  codepilot:latest
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  codepilot:
    image: codepilot:latest
    ports:
      - "8000:8000"
    volumes:
      - ./model:/app/model
      - ./logs:/app/logs
    environment:
      - MODEL_PATH=/app/model/codepilot-13b
      - CUDA_VISIBLE_DEVICES=0
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Run with:
```bash
docker-compose up -d
```

---

## VSCode Extension Installation

### Method 1: From Source (Development)

```bash
cd vscode-extension

# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Open in VSCode and press F5 to launch extension development host
```

### Method 2: Package and Install

```bash
cd vscode-extension

# Install VSCE
npm install -g vsce

# Package extension
vsce package

# Install in VSCode
code --install-extension codepilot-automotive-1.0.0.vsix
```

### Method 3: From Marketplace (Future)

Once published:
1. Open VSCode
2. Go to Extensions (Ctrl+Shift+X)
3. Search "CodePilot Automotive"
4. Click Install

### Configuration

After installation, configure in VSCode settings:

```json
{
  "codepilot.apiEndpoint": "http://localhost:8000",
  "codepilot.enableAutoComplete": true,
  "codepilot.maxTokens": 150,
  "codepilot.temperature": 0.2
}
```

---

## Production Considerations

### Performance Optimization

1. **Model Quantization**
   - Use 4-bit quantization for memory efficiency
   - Trade-off: ~5% accuracy for 4x less memory

2. **Batch Processing**
   - vLLM enables efficient batching
   - Configure `max_num_seqs` based on GPU memory

3. **Caching**
   - Enable KV cache for repeated prefixes
   - Can reduce latency by 30-50%

### Monitoring

1. **Prometheus Metrics**

Add to `inference/server.py`:
```python
from prometheus_client import Counter, Histogram

request_count = Counter('codepilot_requests_total', 'Total requests')
latency = Histogram('codepilot_latency_seconds', 'Request latency')
```

2. **Logging**

Configure structured logging:
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/codepilot.log'),
        logging.StreamHandler()
    ]
)
```

### Security

1. **API Authentication**
   - Add API key validation
   - Use JWT tokens for user auth

2. **Rate Limiting**
   - Implement per-user rate limits
   - Use Redis for distributed rate limiting

3. **HTTPS**
   - Use Let's Encrypt for SSL certificates
   - Configure nginx with HTTPS

### Scalability

1. **Horizontal Scaling**
   - Deploy multiple instances
   - Use load balancer (AWS ELB, nginx)

2. **Model Replication**
   - Tensor parallelism for large models
   - Pipeline parallelism across nodes

3. **Auto-scaling**
   - Configure AWS Auto Scaling groups
   - Scale based on GPU utilization

---

## Troubleshooting

### Common Issues

**Issue: CUDA out of memory**
```bash
# Solution: Reduce batch size or use smaller model
export CUDA_VISIBLE_DEVICES=0
python inference/server.py --max-batch-size 1
```

**Issue: Port already in use**
```bash
# Solution: Change port or kill existing process
lsof -ti:8000 | xargs kill -9
python inference/server.py --port 8001
```

**Issue: Model loading slow**
```bash
# Solution: Use local model cache
export TRANSFORMERS_CACHE=/path/to/cache
```

### Getting Help

- GitHub Issues: Report bugs and feature requests
- Discussions: Ask questions and share ideas
- Email: sreekar.gajula@example.com

---

## Next Steps

- [Training Guide](training.md) - Train your own model
- [API Reference](api.md) - Detailed API documentation
- [Examples](../examples/) - Usage examples
