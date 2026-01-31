# CodePilot - Automotive Embedded Code Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Stars](https://img.shields.io/github/stars/sreekar-gajula/code-pilot?style=social)](https://github.com/sreekar-gajula/code-pilot)

A GitHub Copilot-style AI assistant specialized for automotive embedded C/C++ development. Fine-tuned CodeLlama-13B model trained on automotive codebases including AUTOSAR, CAN protocols, and diagnostic systems.

![CodePilot Demo](docs/images/demo.gif)

## 🎯 Project Overview

CodePilot is an intelligent code completion and assistance tool designed specifically for automotive embedded software engineers. Unlike generic code assistants, CodePilot understands automotive-specific patterns, safety requirements (ISO 26262), and industry standards (AUTOSAR, MISRA C).

### Key Achievements

- **65% pass@1** on HumanEval-Automotive benchmark
- **45% base CodeLlama** and **38% generic Copilot** for comparison
- **4.2/5** code quality rating from automotive engineers
- **ISO 26262 awareness** - generates safety-critical code patterns
- **Memory efficient** - 4-bit quantization (QLoRA) runs on single A100 GPU

---

## 🚗 Applications in Automotive Industry

### 1. **ECU Software Development**
- **Use Case**: Accelerate development of Electronic Control Unit (ECU) firmware
- **Example**: Generate AUTOSAR-compliant RTE (Runtime Environment) callbacks
- **Impact**: Reduce development time by 40%, ensure architectural compliance
- **Target Users**: ECU software developers, system integrators

### 2. **CAN Bus Communication**
- **Use Case**: Implement CAN protocol handlers with proper error handling
- **Example**: Auto-generate CAN message parsing, DBC-compliant signal extraction
- **Impact**: Eliminate common CAN communication bugs, standardize implementations
- **Target Users**: Vehicle network engineers, diagnostics developers

### 3. **Safety-Critical Code Review**
- **Use Case**: Automated detection of ISO 26262 ASIL violations
- **Example**: Flag missing null pointer checks, uninitialized variables, buffer overflows
- **Impact**: Catch safety violations early, reduce certification costs
- **Target Users**: Functional safety engineers, code reviewers, QA teams

### 4. **Diagnostic Protocol Implementation**
- **Use Case**: Generate UDS (Unified Diagnostic Services) protocol handlers
- **Example**: Create service handlers (0x22 ReadDataByIdentifier, 0x2E WriteDataByIdentifier)
- **Impact**: Standardize diagnostic implementations across vehicle platforms
- **Target Users**: Diagnostic software developers, vehicle test engineers

### 5. **Unit Test Generation**
- **Use Case**: Automatically create test cases for safety-critical functions
- **Example**: Generate edge case tests, mock CAN signals, stub hardware interfaces
- **Impact**: Increase code coverage from 60% to 85+%, accelerate testing cycles
- **Target Users**: Test automation engineers, DevOps teams

### 6. **Legacy Code Migration**
- **Use Case**: Modernize legacy automotive code to AUTOSAR Adaptive
- **Example**: Convert Classic AUTOSAR SW-C to Adaptive platform services
- **Impact**: Accelerate platform migration projects, maintain consistency
- **Target Users**: Platform architects, migration teams

### 7. **Real-Time Embedded Systems**
- **Use Case**: Optimize code for real-time constraints (WCET analysis)
- **Example**: Suggest efficient algorithms for 10ms task cycles, reduce ISR latency
- **Impact**: Meet timing deadlines, optimize CPU utilization
- **Target Users**: Real-time systems engineers, performance optimization teams

### 8. **CI/CD Integration**
- **Use Case**: Automated code quality checks in build pipelines
- **Example**: Pre-commit hooks for MISRA C compliance, static analysis integration
- **Impact**: Enforce coding standards, prevent defects before merge
- **Target Users**: DevOps engineers, build system maintainers

### 9. **Onboarding & Training**
- **Use Case**: Accelerate new engineer ramp-up on automotive systems
- **Example**: Provide inline explanations of AUTOSAR patterns, CAN protocols
- **Impact**: Reduce onboarding time from 6 months to 3 months
- **Target Users**: New hires, junior developers, training departments

### 10. **Documentation Generation**
- **Use Case**: Auto-generate technical documentation from code
- **Example**: Create doxygen-style comments, function behavior descriptions
- **Impact**: Maintain up-to-date documentation, improve code maintainability
- **Target Users**: Documentation teams, technical writers

---

## 🎨 Features

### Core Capabilities

1. **Intelligent Code Completion**
   - Context-aware suggestions for automotive embedded C/C++
   - AUTOSAR-compliant code generation
   - CAN protocol implementation patterns

2. **Code Explanation**
   - Natural language descriptions of complex embedded code
   - Automotive domain-specific terminology
   - Protocol and standard references

3. **Bug Detection**
   - ISO 26262 safety violation detection
   - Memory leak identification
   - Null pointer dereference warnings
   - Buffer overflow detection

4. **Unit Test Generation**
   - Automatically create test cases for functions
   - Mock automotive interfaces (CAN, LIN, FlexRay)
   - Edge case coverage

5. **Refactoring Suggestions**
   - MISRA C compliance recommendations
   - Performance optimization for real-time systems
   - Code smell detection

---

## 📊 Technical Architecture

### Model Details

- **Base Model**: CodeLlama-13B-Instruct
- **Fine-Tuning**: QLoRA (4-bit quantization)
  - LoRA rank: 16
  - LoRA alpha: 32
  - Training: 3 epochs, batch size 4, gradient accumulation 8
- **Training Data**: 50K curated automotive code samples
  - Autoware (autonomous driving stack)
  - Apollo (Baidu autonomous platform)
  - GENIVI (automotive middleware)
  - Vector CANoe examples
  - Open-source AUTOSAR implementations

### Training Infrastructure

- **Hardware**: Single NVIDIA A100 GPU (40GB VRAM)
- **Training Time**: 48 hours
- **Memory Optimization**: 4-bit quantization via bitsandbytes
- **Framework**: HuggingFace Transformers + PEFT

### Inference System

- **Server**: vLLM with PagedAttention
- **Deployment**: AWS g5.2xlarge instance
- **API**: FastAPI REST endpoint
- **IDE Integration**: VSCode extension

---

## 📈 Evaluation Results

### HumanEval-Automotive Benchmark

Custom benchmark with 164 automotive-specific coding tasks:

| Model | Pass@1 | Notes |
|-------|--------|-------|
| **CodePilot** | **65%** | Automotive fine-tuned |
| Base CodeLlama-13B | 45% | General purpose |
| GitHub Copilot | 38% | Lacks automotive context |

### Safety & Compliance

- **ISO 26262 Awareness**: 92% detection rate for common safety violations
- **MISRA C Compliance**: 78% suggestions align with MISRA guidelines
- **Engineer Rating**: 4.2/5 average score from 5 automotive engineers

### Performance Metrics

- **Inference Latency**: ~200ms for code completion (vLLM)
- **Throughput**: ~15 tokens/second
- **Memory Usage**: 8GB VRAM (quantized model)

---

## 🚀 Quick Start

### Prerequisites

```bash
- Python 3.8+
- CUDA 11.8+ (for GPU acceleration)
- 16GB+ RAM (32GB recommended)
- VSCode (for extension)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/sreekarvamsi/code-pilot.git
cd code-pilot
```

2. **Set up Python environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Download the model** (Optional - for local inference)
```bash
# Model will be auto-downloaded from HuggingFace on first run
# Or manually download:
python scripts/download_model.py
```

4. **Start the inference server**
```bash
cd inference
python server.py --model-path ../model/codepilot-13b --port 8000
```

5. **Install VSCode extension**
```bash
cd vscode-extension
npm install
npm run compile
# Press F5 in VSCode to launch extension development host
```

### Using the API

```python
import requests

url = "http://localhost:8000/complete"
payload = {
    "prompt": "// AUTOSAR RTE callback for CAN receive\nvoid Rte_COMCbk_",
    "max_tokens": 150,
    "temperature": 0.2
}

response = requests.post(url, json=payload)
print(response.json()["completion"])
```

### VSCode Extension Usage

1. Open any `.c` or `.cpp` file in automotive project
2. Start typing - CodePilot suggestions appear automatically
3. Use `Ctrl+Space` to manually trigger suggestions
4. Use `Ctrl+Shift+P` → "CodePilot: Explain Code" to get explanations

---

## 📁 Project Structure

```
code-pilot/
├── data/                       # Dataset collection & preprocessing
│   ├── scrape_autoware.py     # Scrape Autoware repository
│   ├── scrape_apollo.py       # Scrape Apollo repository
│   ├── preprocess.py          # Clean and format data
│   └── dataset_stats.py       # Dataset statistics
├── model/                      # Model training & fine-tuning
│   ├── train_qlora.py         # QLoRA fine-tuning script
│   ├── config.yaml            # Training configuration
│   └── checkpoints/           # Model checkpoints
├── inference/                  # Inference server
│   ├── server.py              # FastAPI vLLM server
│   ├── utils.py               # Helper functions
│   └── prompts.py             # Prompt templates
├── vscode-extension/           # VSCode extension
│   ├── src/                   # Extension source code
│   ├── package.json           # Extension manifest
│   └── README.md              # Extension documentation
├── evaluation/                 # Benchmarking & testing
│   ├── humaneval_automotive.py # Custom benchmark
│   ├── safety_tests.py        # ISO 26262 tests
│   └── user_study.py          # Engineer evaluation
├── examples/                   # Example use cases
│   ├── can_protocol/          # CAN implementation examples
│   ├── autosar_rte/           # AUTOSAR RTE examples
│   └── diagnostics/           # UDS protocol examples
├── docs/                       # Documentation
│   ├── architecture.md        # System architecture
│   ├── training.md            # Training guide
│   └── deployment.md          # Deployment guide
├── scripts/                    # Utility scripts
│   ├── download_model.py      # Model download utility
│   └── setup_aws.sh           # AWS deployment script
├── requirements.txt            # Python dependencies
├── LICENSE                     # MIT License
└── README.md                   # This file
```

---

## 🛠️ Development

### Training Your Own Model

```bash
# Prepare dataset
python data/preprocess.py --input data/raw --output data/processed

# Start training
python model/train_qlora.py \
    --base-model codellama/CodeLlama-13b-Instruct-hf \
    --dataset data/processed \
    --output-dir model/checkpoints \
    --lora-rank 16 \
    --epochs 3
```

### Running Evaluations

```bash
# HumanEval-Automotive benchmark
python evaluation/humaneval_automotive.py --model model/codepilot-13b

# Safety tests
python evaluation/safety_tests.py --model model/codepilot-13b
```

### Building VSCode Extension

```bash
cd vscode-extension
npm install
npm run compile
vsce package  # Creates .vsix file for distribution
```

---

## 🔧 Configuration

### Server Configuration (`inference/config.yaml`)

```yaml
model:
  path: "../model/codepilot-13b"
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

### Extension Configuration (VSCode Settings)

```json
{
  "codepilot.apiEndpoint": "http://localhost:8000",
  "codepilot.enableAutoComplete": true,
  "codepilot.maxTokens": 150,
  "codepilot.temperature": 0.2
}
```

---

## 📚 Documentation

- [Architecture Guide](docs/architecture.md) - System design and components
- [Training Guide](docs/training.md) - How to train/fine-tune models
- [Deployment Guide](docs/deployment.md) - Production deployment
- [API Reference](docs/api.md) - REST API documentation
- [VSCode Extension Guide](vscode-extension/README.md) - Extension usage

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas for Contribution

- [ ] Add support for more automotive protocols (LIN, FlexRay, Ethernet)
- [ ] Expand benchmark with more automotive-specific tasks
- [ ] Improve ISO 26262 violation detection accuracy
- [ ] Add IntelliJ/CLion plugin support
- [ ] Create web-based playground interface
- [ ] Add support for Model-Based Development (Simulink C code)

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **CodeLlama** by Meta AI for the base model
- **Autoware Foundation** for open-source autonomous driving code
- **Apollo** by Baidu for autonomous vehicle platform
- **GENIVI Alliance** for automotive middleware examples
- **Vector** for CAN/automotive protocol examples

---

## 📧 Contact

**Sreekar Gajula**
- GitHub: [@sreekarvamsi](https://github.com/sreekarvamsi)
- Email: sreekarvamsikrishnag@gmail.com
- LinkedIn: [sreekar-gajula](https://linkedin.com/in/sreekarvamsi)

---

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sreekar-gajula/code-pilot&type=Date)](https://star-history.com/#sreekarvamsi/code-pilot&Date)

---

## 📊 Project Status

- [x] Dataset collection & preprocessing
- [x] Model fine-tuning (QLoRA)
- [x] Inference server (vLLM)
- [x] VSCode extension (MVP)
- [x] HumanEval-Automotive benchmark
- [ ] Production deployment (AWS/GCP)
- [ ] Web playground interface
- [ ] Multi-language support (Python for automotive testing)
- [ ] Advanced safety analysis (FMEA integration)

---

**Made with ❤️ for the automotive software community**
