FROM python:3.11-slim

WORKDIR /app

# Install optional Gemini dependency.
RUN pip install --no-cache-dir google-genai

COPY . /app

# Auto-run the test runner with default setting/env.
CMD ["python", "main.py", "--setting", "retailing-benchmark", "--env", ".env"]
