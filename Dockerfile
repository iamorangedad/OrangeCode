FROM dustynv/l4t-pytorch:r36.2.0
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel
COPY requirements_rag.txt .
RUN pip3 install --no-cache-dir -r requirements_rag.txt