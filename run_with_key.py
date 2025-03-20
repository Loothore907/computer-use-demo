import os
import subprocess
import re
import sys

# Read API key from .env file
api_key = None
try:
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith('ANTHROPIC_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
                # Remove quotes if present
                api_key = re.sub(r'^["\']|["\']$', '', api_key)
                break
except Exception as e:
    print(f"Error reading .env file: {e}")

if not api_key:
    print("Could not find ANTHROPIC_API_KEY in .env file")
    exit(1)

# Print first and last 5 characters of API key
print(f"Using API key: {api_key[:5]}...{api_key[-5:]}")

# Build docker command
cmd = [
    "docker", "run", "-it", "--rm", 
    "-p", "8501:8501", 
    "-v", f"{os.getcwd()}/workspace:/app/workspace",
    "-v", f"{os.getcwd()}/data:/app/data",
    "-e", f"ANTHROPIC_API_KEY={api_key}",
    "-e", "MODEL=claude-3-5-sonnet-20241022",
    "-e", "BETA_FLAG=computer-use-2024-10-22",
    "claude-computer-use", 
    "python", "container_entry.py"
]

# Run docker command
print("Running docker container...")
try:
    # Use check=True to raise an exception if the command fails
    subprocess.run(cmd, check=True)
except subprocess.CalledProcessError as e:
    print(f"Docker command failed with return code {e.returncode}")
    sys.exit(1)
except Exception as e:
    print(f"Error running docker command: {e}")
    sys.exit(1) 