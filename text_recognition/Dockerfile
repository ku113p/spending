FROM python:3.11-slim

# Set working directory
WORKDIR /app
# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
# Upgrade pip & setuptools
RUN pip install --upgrade pip setuptools wheel

RUN python -m pip install paddlepaddle==3.0.0 \
  --index-url https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
  --extra-index-url https://pypi.org/simple
RUN pip install paddleocr==3.0.0

# Warm up PaddleOCR with a sample image
COPY example.png ./general_ocr_002.png
RUN paddleocr ocr -i ./general_ocr_002.png  --use_doc_orientation_classify False --use_doc_unwarping False --use_textline_orientation False

# Install pip requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py example.png ./

# Expose FastAPI default port
EXPOSE 8000

# Run the app using uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
