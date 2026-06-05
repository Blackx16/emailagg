FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir aiogram==3.15.0 httpx==0.28.0 python-dotenv==1.0.1

COPY . ./bot

CMD ["python", "-m", "bot.main"]
