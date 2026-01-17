FROM python:3.11-slim
WORKDIR /app
COPY requirements_no_rag.txt .
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir -r requirements_no_rag.txt
COPY . .
CMD ["python3", "agent_no_rag.py"]