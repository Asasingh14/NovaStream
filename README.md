# NovaStream

[![Build & Release](https://github.com/Asasingh14/NovaStream/actions/workflows/release-build.yml/badge.svg)](https://github.com/Asasingh14/NovaStream/actions/workflows/release-build.yml)
[![codecov](https://codecov.io/gh/Asasingh14/NovaStream/branch/main/graph/badge.svg?token=8PBXU7ND63)](https://codecov.io/gh/Asasingh14/NovaStream)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/Asasingh14/NovaStream)](https://github.com/Asasingh14/NovaStream/commits/main)
[![Release](https://img.shields.io/github/v/release/Asasingh14/NovaStream)](https://github.com/Asasingh14/NovaStream/releases)
[![Platforms](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](#)
[![Open Issues](https://img.shields.io/github/issues/Asasingh14/NovaStream)](https://github.com/Asasingh14/NovaStream/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/Asasingh14/NovaStream)](https://github.com/Asasingh14/NovaStream/pulls)

---

**NovaStream** is a cross-platform HLS streaming downloader for movies, series, and more. Whether you're a developer or an end user, NovaStream simplifies the process of downloading media via `.m3u8` manifests with ease.

---

## 🔥 Key Features

- ✅ GUI powered by Tkinter for non-technical users  
- 🧠 Programmatic API for developers and automation  
- 🔄 Range-based or full-season episode selection  
- 💡 Smart file naming: `Drama Name - Episode XX - Title.mp4`  
- 🚀 Multi-threaded downloading with resume support  
- 🧹 Automatic cleanup on interruption or cancel  
- 🔒 Works offline once streaming URLs are obtained  

---

## 📚 Table of Contents

1. [Installation](#installation)  
2. [Usage](#usage)  
   - [Graphical User Interface](#graphical-user-interface)  
   - [Programmatic API](#programmatic-api)  
   - [Example Script](#example-script)  
3. [Development](#development)  
4. [Testing](#testing)  
5. [Contributing](#contributing)  
6. [License](#license)  
7. [CI/CD & Workflow](#cicd--workflow)  
8. [Roadmap](#roadmap)  

---

## 📦 Installation

> **Note:** NovaStream is not yet on PyPI. Please install via GitHub.

### Install via GitHub

```bash
pip install git+https://github.com/Asasingh14/NovaStream.git
```

### Manual Clone

```bash
git clone https://github.com/Asasingh14/NovaStream.git
cd NovaStream
pip install .
```

---

## 🖥️ Usage

### Graphical User Interface

```bash
novastream
```

Then:
1. Paste the stream homepage or episode URL  
2. Optionally enter a drama/series name  
3. Choose output folder  
4. Select specific episodes (e.g., 1,3-5) or download all  
5. Set number of workers (e.g., 4)  
6. Click Start  

---

### Programmatic API

Use the `run_download` function to programmatically download streams. For a full example script, see [examples/basic_usage.py](examples/basic_usage.py).

### Example Script

A standalone example script demonstrating programmatic usage is available at [examples/basic_usage.py](examples/basic_usage.py). You can execute it with:

```bash
python examples/basic_usage.py
```

---

## 🛠️ Development

### Requirements
- Python 3.8+  
- ffmpeg installed and in system PATH  

### Setup Dev Environment
```bash
python -m venv venv
source venv/bin/activate  # or venv\\Scripts\\activate on Windows
pip install -r requirements-dev.txt
```

---

## ✅ Testing

### Run all tests:
```bash
pytest
```

### With coverage:
```bash
pytest --cov --cov-branch --cov-report=xml
```

### Linting (optional):
```bash
ruff check src tests
```

---

## 🤝 Contributing

We welcome contributions! Follow these steps:
1. Fork the repo  
2. Create your branch: `git checkout -b feature/awesome`  
3. Commit changes: `git commit -am 'feat: awesome new feature'`  
4. Push: `git push origin feature/awesome`  
5. Open a PR  

See CONTRIBUTING.md for detailed guidelines.

---

## 📄 License

---

This project is licensed under the MIT License. See LICENSE for details.

---

## 🚦 CI/CD & Workflow

---

NovaStream uses GitHub Actions:
- Test Workflow: Runs on every push & PR  
- pytest with coverage  
- Uploads to Codecov  
- Build Workflow:  
  - Runs only on main branch pushes  
  - Builds standalone binaries for Windows, macOS, Linux  
- Auto-cancel: Concurrent runs on same branch auto-cancelled  
- Fail fast: Workflows fail on test failure  

---

## 🛣️ Roadmap

| Status        | Feature                                                         |
|---------------|-----------------------------------------------------------------|
| ✅ Completed  | Programmatic download interface                                 |
| ✅ Completed  | Basic GUI for stream selection                                  |
| ✅ Completed  | Multi-threaded engine                                           |
| ✅ Completed  | Auto-update mechanism via GitHub Releases                       |
| ⏳ Planned     | Subtitle (.vtt) merging                                         |
| ⏳ Planned     | Full settings GUI                                               |
| 🤖 Planned    | Discord bot integration (keyword extraction & API-driven download) |

---

_Built by [d4rkw3bd31ty](https://github.com/Asasingh14)_