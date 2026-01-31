# Contributing to CodePilot

Thank you for your interest in contributing to CodePilot! We welcome contributions from the automotive software community.

## 🤝 How to Contribute

### Reporting Bugs

1. **Check existing issues** to avoid duplicates
2. **Use the bug report template** when creating a new issue
3. **Include**:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, CUDA version)
   - Relevant code snippets or logs

### Suggesting Features

1. **Open a feature request** with detailed description
2. **Explain the use case** and benefits for automotive developers
3. **Consider implementation complexity** and propose approach if possible

### Code Contributions

#### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/sreekar-gajula/code-pilot.git
cd code-pilot

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Create feature branch
git checkout -b feature/your-feature-name
```

#### Code Style

- **Python**: Follow PEP 8, use Black formatter
  ```bash
  black .
  flake8 .
  mypy model/ inference/
  ```

- **TypeScript** (VSCode extension): Follow TSLint rules
  ```bash
  cd vscode-extension
  npm run lint
  ```

- **C/C++** (examples): Follow MISRA C guidelines where applicable

#### Commit Guidelines

Use conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(inference): add support for FlexRay protocol completion
fix(training): resolve memory leak in QLoRA fine-tuning
docs(readme): update installation instructions
```

#### Pull Request Process

1. **Create feature branch** from `develop`
2. **Write tests** for new features
3. **Update documentation** if needed
4. **Run all tests** locally
   ```bash
   pytest evaluation/ -v
   ```
5. **Submit PR** with clear description:
   - What changes were made
   - Why the changes are needed
   - How to test the changes
6. **Address review comments** promptly
7. **Squash commits** before merge (if requested)

### Adding Automotive Code Samples

We're always looking for more automotive code examples! To contribute:

1. **Ensure open-source license** compatibility
2. **Add to appropriate category**:
   - `examples/can_protocol/` - CAN bus implementations
   - `examples/autosar_rte/` - AUTOSAR RTE examples
   - `examples/diagnostics/` - UDS/OBD examples
   - `examples/safety/` - ISO 26262 compliant code

3. **Include documentation**:
   - Purpose and use case
   - Automotive standard references
   - Safety considerations

4. **Add to dataset** if suitable for training:
   ```bash
   python data/preprocess.py --input examples/ --output data/processed
   ```

### Improving the Benchmark

Help us make HumanEval-Automotive more comprehensive:

1. **Add test cases** in `evaluation/humaneval_automotive.py`
2. **Cover new categories**:
   - LIN protocol
   - FlexRay
   - Ethernet/SOME-IP
   - ADAS functions
   - Battery management systems
3. **Include edge cases** and safety-critical scenarios

### Documentation

- Update README.md for user-facing changes
- Add/update docstrings in Python code
- Create examples for new features
- Update API documentation

## 🏆 Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Recognized in project documentation

## 📜 Code of Conduct

### Our Standards

- **Be respectful** and professional
- **Be constructive** in feedback
- **Focus on the code**, not the person
- **Welcome newcomers** and help them learn

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal attacks
- Spam or off-topic content

## 🔒 Security

If you discover a security vulnerability:

1. **DO NOT** create a public issue
2. **Email** sreekar.gajula@example.com with details
3. **Allow time** for us to address before disclosure

## 📝 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## ❓ Questions?

- Open a discussion in GitHub Discussions
- Join our community chat (if available)
- Email: sreekar.gajula@example.com

## 🙏 Thank You!

Every contribution, no matter how small, helps make CodePilot better for the automotive software community!
