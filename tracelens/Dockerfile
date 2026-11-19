FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e .
COPY . .
EXPOSE 8000
CMD ["python", "-m", "tracelens.main"]
