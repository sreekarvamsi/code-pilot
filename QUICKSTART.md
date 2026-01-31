# CodePilot Quick Start Guide

Get CodePilot up and running in 15 minutes!

## 🚀 Quick Installation

### Prerequisites Check
```bash
# Check Python version (need 3.8+)
python3 --version

# Check if CUDA is available (optional, for GPU)
nvidia-smi

# Check Node.js (for VSCode extension)
node --version
```

### Step 1: Clone and Setup (5 minutes)

```bash
# Clone repository
git clone https://github.com/sreekar-gajula/code-pilot.git
cd code-pilot

# Run automated setup
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- Create Python virtual environment
- Install all dependencies
- Check for CUDA/GPU
- Create necessary directories
- Setup VSCode extension (optional)

### Step 2: Start Inference Server (5 minutes)

**Option A: Use Base CodeLlama (No training required)**
```bash
# Activate environment
source venv/bin/activate

# Start server (will auto-download model)
cd inference
python server.py --model-path codellama/CodeLlama-13b-Instruct-hf
```

**Option B: Use Fine-tuned Model (After training)**
```bash
source venv/bin/activate
cd inference
python server.py --model-path ../model/checkpoints/codepilot-13b
```

Server will start on `http://localhost:8000`

### Step 3: Test the Server (2 minutes)

```bash
# Health check
curl http://localhost:8000/health

# Test completion
curl -X POST http://localhost:8000/complete \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "void can_transmit_message(can_msg_t* msg) {\n    // Check if message is valid\n    if",
    "max_tokens": 100,
    "temperature": 0.2
  }'
```

### Step 4: Install VSCode Extension (3 minutes)

```bash
cd vscode-extension
npm install
npm run compile

# Open in VSCode
code .

# Press F5 to launch extension development host
```

Or package and install:
```bash
npm install -g vsce
vsce package
code --install-extension codepilot-automotive-1.0.0.vsix
```

Configure in VSCode settings:
```json
{
  "codepilot.apiEndpoint": "http://localhost:8000",
  "codepilot.enableAutoComplete": true,
  "codepilot.maxTokens": 150,
  "codepilot.temperature": 0.2
}
```

---

## 📝 Usage Examples

### In VSCode

1. **Auto-completion**
   - Open any `.c` or `.cpp` file
   - Start typing automotive code
   - CodePilot suggestions appear automatically
   - Press `Tab` to accept

2. **Explain Code**
   - Select code block
   - Right-click → "CodePilot: Explain Code"
   - Or use command palette (`Ctrl+Shift+P`)

3. **Detect Bugs**
   - Select code block
   - Command: "CodePilot: Detect Bugs"
   - View safety analysis

4. **Generate Tests**
   - Select function
   - Command: "CodePilot: Generate Unit Tests"
   - Choose test framework (Unity, GTest)

### Via API

```python
import requests

# Complete code
response = requests.post('http://localhost:8000/complete', json={
    'prompt': 'uint32_t can_extract_signal(uint8_t* data, uint8_t start_bit, uint8_t length) {\n',
    'max_tokens': 150
})
print(response.json()['completion'])

# Explain code
response = requests.post('http://localhost:8000/explain', json={
    'code': 'void Rte_Write_Signal(uint16_t value) { ... }',
    'language': 'c'
})
print(response.json()['explanation'])
```

---

## 🎯 Common Use Cases

### 1. CAN Message Handler
```c
// Type this in VSCode:
void can_receive_handler(can_msg_t* msg) {
    // Parse vehicle speed from CAN message
    
// CodePilot completes:
    if (msg == NULL) {
        return;
    }
    
    if (msg->id == VEHICLE_SPEED_MSG_ID) {
        uint16_t raw_speed = (msg->data[0]) | (msg->data[1] << 8);
        float speed_kmh = raw_speed * 0.01f;
        
        // Update vehicle speed signal
        Rte_Write_VehicleSpeed(speed_kmh);
    }
}
```

### 2. AUTOSAR RTE Callback
```c
// Type this:
FUNC(void, RTE_CODE) Rte_Runnable_

// CodePilot suggests:
FUNC(void, RTE_CODE) Rte_Runnable_SpeedMonitor_100ms(void)
{
    Std_ReturnType ret;
    uint16_t speed;
    
    ret = Rte_Read_PpSpeed_DeSpeed(&speed);
    if (ret == E_OK) {
        // Process speed value
        if (speed > SPEED_THRESHOLD) {
            Rte_Write_PpWarning_DeWarning(TRUE);
        }
    }
}
```

### 3. UDS Diagnostic Service
```c
// Type:
uint8_t UDS_Service_0x22_

// Completes:
uint8_t UDS_Service_0x22_ReadDataByID(uint16_t did, uint8_t* response, uint16_t* length)
{
    switch (did) {
        case DID_VIN:
            response[0] = 0x62;
            response[1] = (did >> 8) & 0xFF;
            response[2] = did & 0xFF;
            memcpy(&response[3], vehicle_vin, 17);
            *length = 20;
            return 0x00;
        
        default:
            return NRC_REQUEST_OUT_OF_RANGE;
    }
}
```

---

## 🔧 Training Your Own Model (Optional)

### Prepare Dataset (2 hours)

```bash
# Collect automotive code samples
mkdir -p data/raw/automotive_repos

# Clone example repositories
git clone --depth 1 https://github.com/autowarefoundation/autoware data/raw/autoware

# Preprocess data
python data/preprocess.py --input data/raw --output data/processed
```

### Train Model (48 hours on A100)

```bash
# Configure training
edit model/config.yaml

# Start training
python model/train_qlora.py \
    --config model/config.yaml \
    --output_dir model/checkpoints/codepilot-13b
```

Training will:
- Fine-tune CodeLlama-13B with QLoRA
- Use 4-bit quantization
- Save checkpoints every 500 steps
- Log to WandB

### Evaluate Model

```bash
# Run HumanEval-Automotive benchmark
python evaluation/humaneval_automotive.py \
    --model model/checkpoints/codepilot-13b
```

---

## 🐛 Troubleshooting

### Server won't start
```bash
# Check port availability
lsof -ti:8000 | xargs kill -9

# Try different port
python server.py --port 8001
```

### CUDA out of memory
```bash
# Use smaller batch size
export CUDA_VISIBLE_DEVICES=0
python server.py --max-batch-size 1
```

### Model download slow
```bash
# Use local cache
export TRANSFORMERS_CACHE=/path/to/cache
export HF_HOME=/path/to/cache
```

### VSCode extension not working
```bash
# Check server is running
curl http://localhost:8000/health

# Check extension logs
View → Output → CodePilot
```

---

## 📚 Next Steps

- **Read [Documentation](docs/)** for detailed guides
- **Check [Examples](examples/)** for more code samples
- **Review [Applications](APPLICATIONS.md)** for use cases
- **Join Community** (GitHub Discussions)
- **Contribute** (see [CONTRIBUTING.md](CONTRIBUTING.md))

---

## 💡 Tips & Tricks

### Optimize Completions
- Use descriptive comments as prompts
- Provide context (function signature, variable names)
- Set temperature lower (0.1-0.3) for deterministic code

### Safety-Critical Code
- Always enable ISO 26262 checks
- Review generated code carefully
- Add defensive programming patterns

### Performance
- Keep server running (don't restart frequently)
- Use local model for faster inference
- Enable caching for repeated prompts

---

## 🆘 Getting Help

- **Issues:** Report bugs on [GitHub Issues](https://github.com/sreekar-gajula/code-pilot/issues)
- **Questions:** Ask in [Discussions](https://github.com/sreekar-gajula/code-pilot/discussions)
- **Email:** sreekar.gajula@example.com

---

## ⭐ Star the Project!

If you find CodePilot useful, please star the repository on GitHub!

[⭐ Star CodePilot](https://github.com/sreekar-gajula/code-pilot)
