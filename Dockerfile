# ScienceClaw Agent - Docker Image
# Run autonomous science agents in isolated containers
#
# Usage:
#   docker build -t scienceclaw/agent .
#   docker run -it scienceclaw/agent
#   docker run -it -e AGENT_NAME="MyBot-7" scienceclaw/agent

FROM ubuntu:22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm-256color

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22 (required for OpenClaw)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for running agent
RUN useradd -m -s /bin/bash sciencebot \
    && echo "sciencebot ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER sciencebot
WORKDIR /home/sciencebot

# Install OpenClaw globally
# Note: This requires interactive onboarding, so we'll do it at runtime
# For now, just install the package
RUN sudo npm install -g openclaw@latest

# Clone ScienceClaw repository
RUN git clone https://github.com/lamm-mit/scienceclaw.git /home/sciencebot/scienceclaw

# Set up Python virtual environment and install dependencies
WORKDIR /home/sciencebot/scienceclaw
RUN python3 -m venv .venv \
    && .venv/bin/pip install --upgrade pip \
    && .venv/bin/pip install -r requirements.txt

# Create OpenClaw workspace directory
RUN mkdir -p /home/sciencebot/.openclaw/workspace

# Environment variables (can be overridden at runtime)
ENV SCIENCECLAW_DIR=/home/sciencebot/scienceclaw
ENV AGENT_NAME=""
ENV AGENT_INTERESTS=""

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN sudo chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose any ports if needed (none for now)
# EXPOSE 8080

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command: start agent
CMD ["start"]
