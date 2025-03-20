# Claude Computer Use Demo - Quick Start Guide

This guide will help you quickly set up and run the Claude Computer Use Demo.

## Prerequisites

- Docker installed and running
- Anthropic API key with computer use capabilities

## 1. Set Up Environment

Create a `.env` file with your API key:

```bash
# Linux/Mac
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env

# Windows (PowerShell)
"ANTHROPIC_API_KEY=your-api-key-here" | Out-File -FilePath .env -Encoding utf8
```

Or just copy the example file and edit it:

```bash
cp .env.example .env
# Edit .env with your favorite text editor
```

## 2. Run the Demo

Using the unified script (simplest option):

```bash
# First time: build and run
python run.py --build

# Subsequent runs
python run.py
```

## 3. Access the Web Interface

Open your browser to:
```
http://localhost:8501
```

You should see the Streamlit interface where you can chat with Claude and ask it to use your computer!

## Common Commands

### Clean Rebuild

If you need to rebuild the Docker image from scratch:

```bash
python run.py --build --clean
```

### Change Port

If port 8501 is already in use:

```bash
python run.py --port 8502
```

### Specify a Different Model

```bash
python run.py --model claude-3-7-sonnet-20250219
```

## Using Docker Compose Directly

You can also use Docker Compose directly:

```bash
# Build and run
docker compose up --build

# Run in background
docker compose up -d

# Stop the container
docker compose down
```

## Asking Claude to Use Your Computer

Once the interface loads, you can ask Claude to:

- Take a screenshot: "Can you take a screenshot of my desktop?"
- Run a command: "Can you list the files in my workspace directory?"
- Create a file: "Can you create a hello world Python script in my workspace?"
- Browse the web: "Can you visit example.com and take a screenshot?"

Enjoy exploring Claude's computer use capabilities!