FROM python:3.13.2-alpine3.21

WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 y otras librerías
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev libffi-dev

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
CMD [ "gunicorn", "-b", "0.0.0.0:5000", "app:app" ]
