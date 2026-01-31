#!/bin/bash

# GitHub Repository Setup Script
# Initializes git repository and prepares for first push

set -e

echo "=========================================="
echo "CodePilot GitHub Setup"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed. Please install git first."
    exit 1
fi

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    print_info "Initializing git repository..."
    git init
    print_success "Git repository initialized"
else
    print_info "Git repository already initialized"
fi

# Configure git user (if not set)
if [ -z "$(git config user.name)" ]; then
    read -p "Enter your name for git commits: " git_name
    git config user.name "$git_name"
    print_success "Git user name set to: $git_name"
fi

if [ -z "$(git config user.email)" ]; then
    read -p "Enter your email for git commits: " git_email
    git config user.email "$git_email"
    print_success "Git user email set to: $git_email"
fi

# Create initial commit if no commits exist
if [ -z "$(git log 2>/dev/null)" ]; then
    print_info "Creating initial commit..."
    
    # Add all files
    git add .
    
    # Create initial commit
    git commit -m "Initial commit: CodePilot - Automotive Embedded Code Assistant

- Fine-tuned CodeLlama-13B for automotive C/C++ development
- QLoRA training pipeline with automotive dataset
- vLLM inference server with FastAPI
- VSCode extension for IDE integration
- HumanEval-Automotive benchmark
- Complete documentation and examples

Features:
- Code completion for AUTOSAR, CAN protocols
- ISO 26262 safety violation detection
- Unit test generation
- Bug detection and code explanation
"
    
    print_success "Initial commit created"
fi

# Create GitHub repository
echo ""
print_info "Setting up GitHub remote..."
echo ""
echo "Please create a repository on GitHub:"
echo "1. Go to https://github.com/new"
echo "2. Repository name: code-pilot"
echo "3. Description: Automotive Embedded Code Assistant - AI-powered code completion for automotive C/C++"
echo "4. Keep it public (for portfolio)"
echo "5. Do NOT initialize with README, .gitignore, or license (we have them)"
echo ""
read -p "Press Enter once you've created the repository..."

# Get repository URL
echo ""
read -p "Enter your GitHub username: " github_username
repo_url="https://github.com/${github_username}/code-pilot.git"

# Add remote
if git remote | grep -q "origin"; then
    print_info "Removing existing origin..."
    git remote remove origin
fi

git remote add origin "$repo_url"
print_success "Remote 'origin' added: $repo_url"

# Set main as default branch
git branch -M main
print_success "Default branch set to 'main'"

# Create and push to develop branch (optional)
read -p "Create 'develop' branch for development? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git checkout -b develop
    print_success "Created and switched to 'develop' branch"
    git checkout main
fi

# Push to GitHub
echo ""
print_info "Pushing to GitHub..."
git push -u origin main

if git branch | grep -q "develop"; then
    git push -u origin develop
    print_success "Pushed 'main' and 'develop' branches"
else
    print_success "Pushed 'main' branch"
fi

# Create topics/tags on GitHub
echo ""
echo "=========================================="
print_success "Repository Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Add repository topics on GitHub:"
echo "   - automotive, embedded-systems, c, cpp"
echo "   - machine-learning, code-completion, autosar"
echo "   - iso26262, can-protocol, code-generation"
echo ""
echo "2. Update repository settings:"
echo "   - Add description"
echo "   - Add website (if you have a demo)"
echo "   - Enable GitHub Actions"
echo "   - Enable GitHub Pages (for documentation)"
echo ""
echo "3. Add repository badges to README:"
echo "   - Build status"
echo "   - License"
echo "   - Version"
echo ""
echo "4. Create first release:"
echo "   - Go to Releases on GitHub"
echo "   - Create a new release (v1.0.0)"
echo "   - Add release notes"
echo ""
echo "5. Share your project:"
echo "   - Add to your LinkedIn"
echo "   - Share on Twitter/X"
echo "   - Submit to awesome lists"
echo ""
echo "Repository URL: $repo_url"
echo ""

# Optional: Create GitHub CLI configuration
if command -v gh &> /dev/null; then
    read -p "Configure repository with GitHub CLI? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Configuring with GitHub CLI..."
        
        # Set repository topics
        gh repo edit --add-topic automotive,embedded-systems,c,cpp,machine-learning,code-completion,autosar,iso26262,can-protocol
        
        # Enable features
        gh repo edit --enable-issues --enable-wiki
        
        print_success "Repository configured with GitHub CLI"
    fi
fi

echo ""
print_success "All done! Your CodePilot repository is ready on GitHub!"
