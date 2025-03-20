FROM python:3.10-slim

# Set environment variable for better Docker logs
ENV PYTHONUNBUFFERED=1 

# Install basic utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    openssl \
    vim \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and Xvfb for Selenium
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chrome and Selenium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
ENV DISPLAY=:99

# Set up Selenium
RUN pip install --no-cache-dir webdriver-manager

# Set working directory
WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create log directory
RUN mkdir -p /var/log/claude-agent

# Copy source code
COPY loop.py .
COPY tools/ ./tools/
COPY docker_demo.py .
COPY simple_docker_demo.py .
COPY run_container_demo.py .
COPY app.py .
COPY container_entry.py .

# Make entry script executable
RUN chmod +x /app/container_entry.py

# Copy Streamlit configuration to disable welcome screen
COPY .streamlit/ /root/.streamlit/

# Create a debug script
RUN echo "#!/bin/bash\nls -la /app\nls -la /app/tools\ncat /app/tools/__init__.py\necho 'Python version:'\npython --version\necho 'Done!'" > /app/debug.sh && chmod +x /app/debug.sh

# Create app user
RUN useradd -m appuser
RUN chown -R appuser:appuser /app /var/log/claude-agent

# Create dirs for mounting
RUN mkdir -p /app/workspace /app/data
RUN chown -R appuser:appuser /app/workspace /app/data

# Switch to non-root user
USER appuser

# Add a healthcheck
HEALTHCHECK --interval=5s --timeout=3s --retries=3 \
  CMD python -c "import os, sys; sys.exit(0 if os.path.exists('/app/loop.py') else 1)"

# Default command
CMD ["python", "-c", "import os; print('Container started successfully'); print('Environment:'); [print(f\"{k}={v[:5]}...{v[-5:]}\" if k == \"ANTHROPIC_API_KEY\" and v else f\"{k}={v}\") for k, v in os.environ.items() if k in [\"ANTHROPIC_API_KEY\", \"MODEL\", \"BETA_FLAG\"]]"]

# Usage:
# Build: docker build -t claude-computer-use .
# Run (Docker-in-Docker): 
#   docker run -it --rm \
#     -v //./pipe/docker_engine://./pipe/docker_engine \
#     -v C:/Dev2025/computer_use_demo/workspace:/app/workspace \
#     -v C:/Dev2025/computer_use_demo/data:/app/data \
#     -e ANTHROPIC_API_KEY=your_api_key \
#     claude-computer-use
#
# Security notes:
# 1. The container has access to the host's Docker daemon via the Docker socket
# 2. The container can only access files in the mounted volumes
# 3. The container runs as a non-root user for better security
# 4. For production, consider further restrictions:
#    - Use capabilities (cap_drop, cap_add) to limit privileges
#    - Use seccomp profiles to restrict syscalls
#    - Set network and CPU/memory limits
#    - Implement SELinux or AppArmor profiles 