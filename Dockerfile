FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "vai.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
