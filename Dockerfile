FROM python:3.11-slim

# System deps (optional, helpful for numpy/pandas)
RUN apt-get update && apt-get install -y build-essential libffi-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Default to polling run; override CMD to run webhook mode
CMD ["python", "run_bot.py"]
