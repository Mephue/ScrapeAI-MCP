FROM mcr.microsoft.com/playwright/python:v1.54.0-noble

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY scraper-service/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY scraper-service /app
COPY shared /app/shared

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
