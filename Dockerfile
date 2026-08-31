FROM python:3.12-bookworm

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium and all required Linux dependencies
RUN python -m playwright install --with-deps chromium

COPY . .

CMD ["python", "main.py"]