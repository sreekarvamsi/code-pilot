#!/bin/bash

# CodePilot Setup Script
# Automated setup for development and deployment

set -e  # Exit on error

echo "=========================================="
echo "CodePilot Setup Script"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_error "This script is designed for Linux. For other systems, please install dependencies manually."
    exit 1
fi

# Check Python version
print_info "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.8"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    print_error "Python 3.8+ required. Found: $PYTHON_VERSION"
    exit 1
fi
print_success "Python $PYTHON_VERSION found"

# Create virtual environment
print_info "Creating Python virtual environment..."
if [ -d "venv" ]; then
    print_info "Virtual environment already exists"
else
    python3 -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
source venv/bin/activate
print_success "Virtual environment activated"

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
print_success "pip upgraded"

# Install Python dependencies
print_info "Installing Python dependencies..."
pip install -r requirements.txt
print_success "Python dependencies installed"

# Check for CUDA
print_info "Checking for CUDA..."
if command -v nvidia-smi &> /dev/null; then
    CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}')
    print_success "CUDA $CUDA_VERSION detected"
else
    print_error "CUDA not found. GPU acceleration will not be available."
    print_info "For CPU-only inference, that's okay. For training, you'll need a GPU."
fi

# Create necessary directories
print_info "Creating project directories..."
mkdir -p data/raw data/processed
mkdir -p model/checkpoints
mkdir -p logs
mkdir -p evaluation/results
print_success "Directories created"

# Download example data (optional)
read -p "Download example automotive code samples? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Downloading example data..."
    # Clone example repositories
    mkdir -p data/raw/autoware
    mkdir -p data/raw/apollo
    
    # Note: In production, you'd clone actual repositories
    # git clone --depth 1 https://github.com/autowarefoundation/autoware data/raw/autoware
    print_success "Example data prepared"
fi

# Setup VSCode extension
read -p "Setup VSCode extension? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Setting up VSCode extension..."
    cd vscode-extension
    
    # Check for Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js $NODE_VERSION found"
        
        # Install dependencies
        npm install
        print_success "VSCode extension dependencies installed"
        
        # Compile TypeScript
        npm run compile
        print_success "VSCode extension compiled"
    else
        print_error "Node.js not found. Please install Node.js to build the VSCode extension."
    fi
    cd ..
fi

# Create environment file
print_info "Creating .env file..."
cat > .env << EOF
# CodePilot Environment Configuration

# Model settings
MODEL_PATH=./model/codepilot-13b
BASE_MODEL=codellama/CodeLlama-13b-Instruct-hf

# Server settings
API_HOST=0.0.0.0
API_PORT=8000

# Training settings
WANDB_API_KEY=your_wandb_key_here
WANDB_PROJECT=codepilot-automotive

# Evaluation
EVAL_OUTPUT_DIR=./evaluation/results

# GPU settings
CUDA_VISIBLE_DEVICES=0
EOF
print_success ".env file created"

# Create run script
print_info "Creating convenience scripts..."
cat > run_server.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd inference
python server.py
EOF
chmod +x run_server.sh
print_success "run_server.sh created"

cat > run_training.sh << 'EOF'
#!/bin/bash
source venv/bin/activate
cd model
python train_qlora.py \
    --output_dir ./checkpoints/codepilot-13b \
    --num_train_epochs 3 \
    --per_device_train_batch_size 4 \
    --gradient_accumulation_steps 8 \
    --learning_rate 2e-4 \
    --save_steps 500 \
    --logging_steps 10 \
    --evaluation_strategy steps \
    --eval_steps 500
EOF
chmod +x run_training.sh
print_success "run_training.sh created"

# Final instructions
echo ""
echo "=========================================="
print_success "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Activate virtual environment:"
echo "   source venv/bin/activate"
echo ""
echo "2. Add your WandB API key to .env file (for training)"
echo ""
echo "3. To preprocess data:"
echo "   python data/preprocess.py --input data/raw --output data/processed"
echo ""
echo "4. To train the model:"
echo "   ./run_training.sh"
echo ""
echo "5. To start the inference server:"
echo "   ./run_server.sh"
echo ""
echo "6. To install VSCode extension:"
echo "   - Open VSCode"
echo "   - Press F5 in vscode-extension directory"
echo "   - Or: vsce package && code --install-extension *.vsix"
echo ""
echo "For more information, see README.md"
echo ""
