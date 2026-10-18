FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN DJANGO_DEBUG=1 python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && uvicorn api.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
