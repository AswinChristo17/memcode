# memcode

A memory layer wrapper for OpenCode CLI. Gives OpenCode persistent memory across sessions using vector search.

## How it works

```
User message → Memory Engine → Prompt Augmentation → OpenCode CLI → LLM → Store Conversation
```

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git (for version control)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/AswinChristo17/memcode.git
cd memcode
```

### 2. Create a virtual environment (recommended)

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -e .
```

This installs memcode in development mode along with all required dependencies:
- `chromadb>=0.5.0` - Vector database for memory storage
- `click>=8.1` - CLI framework
- `sentence-transformers>=3.0` - Text embedding model
- `rich>=13.0` - Beautiful terminal output
- `python-dotenv>=1.0` - Environment variable management
- `groq>=0.9.0` - Groq API client

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Groq API Key (required for LLM functionality)
GROQ_API_KEY=your_api_key_here

# Optional: OpenCode CLI path (if not in PATH)
# OPENCODE_PATH=/path/to/opencode

# Optional: Memory database location
# MEMORY_DB_PATH=./chroma_data
```

## Usage

### Basic Commands

```bash
# Run memcode with a question (searches memory and augments prompt)
memcode run "What project was I working on yesterday?"

# Continue work on a specific topic
memcode run "Continue the FastAPI work"

# View stored sessions in memory
memcode history

# Search memory manually for specific topics
memcode search "FastAPI"

# Get help on available commands
memcode --help

# Clear all stored memory
memcode clear
```

### Workflow Example

```bash
# First session - work on a project
memcode run "Build a REST API with FastAPI"

# Later - memcode remembers the context
memcode run "What were we doing with the authentication?"

# Search for specific work
memcode search "authentication"
```

## Project Structure

```
memcode/
├── memcode/
│   ├── __init__.py      — Package initialization
│   ├── cli.py           — Click CLI entry point
│   ├── memory.py        — ChromaDB vector store, session storage/retrieval
│   ├── wrapper.py       — OpenCode CLI wrapper, output capture
│   ├── prompt.py        — Augmented prompt builder with memory context
│   └── config.py        — Configuration settings and paths
├── build/               — Distribution build artifacts
├── memcode.egg-info/    — Package metadata
├── pyproject.toml       — Project configuration and dependencies
├── .gitignore           — Git ignore rules
├── README.md            — This file
└── fix_path.py          — Utility script
```

## Architecture

- `memcode/memory.py` — ChromaDB vector store for persistent session storage and semantic search
- `memcode/wrapper.py` — Calls OpenCode CLI and captures command output
- `memcode/prompt.py` — Builds augmented prompts enriched with relevant memory context
- `memcode/cli.py` — Entry point with Click CLI framework
- `memcode/config.py` — Centralized configuration (model, memory count, paths)

## Development

### Running tests

```bash
python -m pytest
```

### Code style

The project uses standard Python formatting. For linting:

```bash
pip install ruff
ruff check .
```

## Troubleshooting

### OpenCode CLI not found

Ensure OpenCode CLI is installed and in your PATH, or set the `OPENCODE_PATH` environment variable:

```bash
export OPENCODE_PATH=/path/to/opencode
# On Windows:
set OPENCODE_PATH=C:\path\to\opencode
```

### Memory database issues

If you encounter issues with the ChromaDB database, clear it:

```bash
memcode clear
```

### Missing API key

Ensure your `.env` file contains a valid `GROQ_API_KEY`:

```bash
echo "GROQ_API_KEY=your_key_here" > .env
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
