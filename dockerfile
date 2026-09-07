# Base image with GCC and Python
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    git \
    curl \
    make \
    vim \
    gcc \
    ca-certificates \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Clone and build TinyCC
RUN git clone https://github.com/TinyCC/tinycc.git /opt/tcc && \
    cd /opt/tcc && \
    ./configure && \
    make -j"$(nproc)" && \
    make install

# Install Python Tree-sitter bindings
RUN pip3 install tree_sitter

# Get Tree-sitter C grammar for Python
RUN pip3 install tree-sitter-c

# Add TinyCC to PATH
ENV PATH="/usr/local/bin:${PATH}"

# Create and set working directory
WORKDIR /spe

# Default command when container starts
CMD [ "bash" ]
