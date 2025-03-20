FROM python:3.10-slim

# Set environment variable for better Docker logs
ENV PYTHONUNBUFFERED=1 

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    openssl \
    vim \
    ca-certificates \
    wget \
    xvfb \
    xdotool \
    scrot \
    gnome-screenshot \
    imagemagick \
    firefox-esr \
    dbus-x11 \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Set up X11 virtual display
ENV DISPLAY=:1
ENV WIDTH=1366
ENV HEIGHT=768
ENV DEPTH=24
ENV DISPLAY_NUM=1

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY tools/ ./tools/
COPY loop.py app.py container_entry.py run.py ./
COPY .streamlit/ /root/.streamlit/

# Create directories
RUN mkdir -p /tmp/outputs /app/workspace /app/data /var/log/claude-agent

# Create X11 startup script
RUN echo '#!/bin/bash\nXvfb :1 -screen 0 ${WIDTH}x${HEIGHT}x${DEPTH} &\nsleep 2\nexport DISPLAY=:1\nexec "$@"' > /app/start-xvfb.sh && \
    chmod +x /app/start-xvfb.sh

# Container startup script
RUN echo '#!/bin/bash\n/app/start-xvfb.sh python /app/container_entry.py' > /app/start.sh && \
    chmod +x /app/start.sh

# Create user
RUN useradd -m appuser
RUN chown -R appuser:appuser /app /var/log/claude-agent /tmp/outputs

# Switch to non-root user for better security
USER appuser

# Add a healthcheck
HEALTHCHECK --interval=5s --timeout=3s --retries=3 \
  CMD python -c "import os, sys; sys.exit(0 if os.path.exists('/app/loop.py') else 1)"

# Default command
ENTRYPOINT ["/app/start.sh"]