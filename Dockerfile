FROM python:3.13.2-alpine3.21

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt
EXPOSE 5000
CMD [ "gunicorn", "-b", "0.0.0.0:5000", "app:app" ]