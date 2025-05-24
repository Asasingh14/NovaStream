# NovaStream

[![Build Status](https://github.com/Asasingh14/NovaStream/actions/workflows/build.yml/badge.svg)](https://github.com/Asasingh14/NovaStream/actions)
[![PyPI Version](https://img.shields.io/pypi/v/novastream.svg)](https://pypi.org/project/novastream/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/novastream.svg)](https://pypi.org/project/novastream/)
[![Coverage Status](https://img.shields.io/codecov/c/gh/Asasingh14/NovaStream.svg)](https://codecov.io/gh/Asasingh14/NovaStream)

NovaStream is a powerful HLS streaming downloader for movies, series, and more. It offers:

- A sleek Tkinter-based GUI for interactive downloads
- A programmatic API for scriptable use
- Episode selection by range or full-season download
- Real-time progress bars and instant cancellation
- Multi-threaded downloads with logging and resume support
- Cross-platform compatibility (Windows, macOS, Linux)

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Usage](#usage)
   - [GUI](#gui)
   - [Programmatic API](#programmatic-api)
4. [Contributing](#contributing)
5. [License](#license)
6. [Testing](#testing)

## Features

- Download HLS-based streaming episodes via m3u8 manifests
- Select specific episodes (`1,3-5`) or download all
- Instant cancel & cleanup of partial downloads
- Human-friendly file naming: `Drama Name - Episode XX - Title.mp4`
- Configurable worker threads for parallel downloads
- Graphical interface powered by Tkinter
- Programmatic interface via `run_download`
- Comprehensive logging and verbose mode

## Installation

### From PyPI

```bash
pip install novastream
```

### From GitHub

```bash
pip install git+https://github.com/Asasingh14/NovaStream.git
```

## Usage

### GUI

After installation, launch the GUI:

```bash
novastream
```

1. Enter the stream's homepage URL
2. Provide a drama/series name (optional)
3. Choose an output folder
4. Tick **Download ALL** or enter specific episodes
5. Set the number of **Workers**
6. Click **Start**

### Programmatic API

```python
from src import run_download

run_download(
    url="https://example.com/show",
    name_input="MyDrama",
    base_output="downloads",
    download_all=True,
    episode_list="",
    workers=4
)
```

## Contributing

Contributions, issues, and feature requests are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -am 'Add NewFeature'`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Testing

Use the Makefile to run tests and generate coverage:

```bash
# Run the test suite only
make test

# Generate coverage report (coverage.xml + HTML site)
make coverage
```

---
_End of README for NovaStream_ 