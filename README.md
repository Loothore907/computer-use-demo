# Claude Computer Use Demo

A demonstration of Claude's computer use capabilities using a Docker container with Streamlit UI.

## Overview

This project provides a web interface for interacting with Claude that can access and control various aspects of your computer through tools:

- **Computer Tool**: Get screenshots and system information
- **Bash Tool**: Run shell commands
- **Edit Tool**: Read, write, and modify files
- **Browser Tool**: Navigate websites and capture screenshots
- **Search Tool**: Find files and content within files
- **Docker Tool**: Manage Docker containers and images

## Prerequisites

- Docker installed and running
- Python 3.9+ (for development outside the container)
- Anthropic API key with Claude computer use capabilities

## Quick Setup

1. **Clone the repository**

```bash
git clone https://your-repository-url.git
cd computer_use_demo
```

2. **Create an environment file**

Copy the example environment file and add your Anthropic API key:

```bash
cp .env.example .env
# Edit .env with your API key and any other settings
```

3. **Build and run the container**

Using the run script (recommended):

```bash
python run.py --build
```

OR using Docker Compose:

```bash
docker compose up --build
```

4. **Access the interface**

Open your browser to:
```
http://localhost:8501
```

## Configuration

The following environment variables can be configured in your `.env` file:

- `ANTHROPIC_API_KEY` (required): Your Anthropic API key
- `MODEL`: The Claude model to use (default: `claude-3-5-sonnet-20241022`)
- `BETA_FLAG`: The beta flag for computer use capabilities (default: `computer-use-2024-10-22`)
- `PORT`: Port for the Streamlit UI (default: `8501`)

## Usage

### Starting with a Clean Build

To rebuild the Docker image with a clean cache:

```bash
# Using run.py
python run.py --build --clean

# Using Docker directly
docker build --no-cache -t claude-computer-use .
python run.py
```

### Command Line Options

The `run.py` script supports several options:

```
usage: run.py [-h] [--api-key API_KEY] [--model MODEL] [--beta-flag BETA_FLAG] [--port PORT] [--build] [--clean]

Claude Computer Use Demo

options:
  -h, --help            show this help message and exit
  --api-key API_KEY     Anthropic API key (if not set in .env file)
  --model MODEL         Claude model to use (default: claude-3-5-sonnet-20241022)
  --beta-flag BETA_FLAG
                        Beta flag for computer use capabilities (default: computer-use-2024-10-22)
  --port PORT           Port to run Streamlit on (default: 8501)
  --build               Build the Docker image before running
  --clean               Clean Docker cache when building
```

## Project Structure

```
.
├── .env.example        # Example environment file
├── .streamlit/         # Streamlit configuration
├── Dockerfile          # Docker image definition
├── app.py              # Streamlit user interface
├── container_entry.py  # Container startup script
├── docker-compose.yml  # Docker Compose configuration
├── loop.py             # Agent loop implementation
├── run.py              # Unified entry point script
├── tools/              # Tool implementations
│   ├── __init__.py
│   ├── base.py         # Base tool class
│   ├── bash.py         # Shell command tool
│   ├── browser.py      # Web browser tool
│   ├── computer.py     # Computer info tool
│   ├── docker.py       # Docker management tool
│   ├── edit.py         # File editing tool
│   └── search.py       # File searching tool
├── data/               # Data directory (mounted into container)
└── workspace/          # Workspace directory (mounted into container)
```

## Architecture

The system consists of the following components:

1. **Docker Container**: Provides an isolated environment with all dependencies
2. **Streamlit UI**: Web interface for interacting with Claude
3. **Agent Loop**: Manages communication with the Claude API and tool calls
4. **Tools**: Python classes that provide access to system capabilities

### Tools Architecture

All tools extend the base `Tool` class and implement the following methods:

- `_run()`: Executes the tool's functionality
- `to_dict()`: Converts the tool definition to the format expected by Claude

### Security Considerations

The Docker container has access to:
- The host's Docker daemon (via the Docker socket)
- Files in the mounted volumes (`workspace/` and `data/`)

**Note**: The container can execute commands on your system and has significant privileges. Only use this demo in trusted environments.

## Troubleshooting

### API Key Issues

If you see errors about invalid API keys:
1. Check that your `.env` file contains a valid key
2. Ensure the key has computer use capabilities
3. Try entering the key directly in the Streamlit UI

### Docker Socket Issues

If Docker-in-Docker functionality fails:
1. Ensure Docker is running on your host
2. Check that the socket path is correct for your OS
3. For Windows, use `//./pipe/docker_engine://./pipe/docker_engine`
4. For Linux/Mac, use `/var/run/docker.sock:/var/run/docker.sock`

### Streamlit UI Issues

If the UI doesn't load:
1. Check the Docker logs: `docker logs claude-computer-use`
2. Ensure port 8501 is not in use by another application
3. Try accessing with a different browser

## License

[Include your license information here]