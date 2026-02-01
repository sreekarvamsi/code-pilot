# CodePilot – Automotive Code Assistant (VSCode Extension)

AI-powered code completion, explanation, bug detection and unit-test
generation for automotive embedded C/C++ development.

## Features

* **Inline completion** – context-aware suggestions as you type in `.c` / `.cpp` files.
* **Explain Code** – select any block and get a natural-language explanation with
  automotive-domain context (AUTOSAR, CAN, ISO 26262).
* **Detect Bugs** – automated ISO 26262 safety-violation scanning.
* **Generate Tests** – one-click unit-test scaffolding (Unity / GTest / CppUnit).

## Requirements

A running CodePilot inference server (default `http://localhost:8000`).
See the [main repository](https://github.com/sreekar-gajula/code-pilot) for setup instructions.

## Settings

| Key | Default | Description |
|---|---|---|
| `codepilot.apiEndpoint` | `http://localhost:8000` | Inference server URL |
| `codepilot.enableAutoComplete` | `true` | Toggle inline completions |
| `codepilot.maxTokens` | `150` | Max tokens per completion |
| `codepilot.temperature` | `0.2` | Sampling temperature |
