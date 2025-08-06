FROM python:3.12-alpine3.22

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./

RUN pip install --upgrade pip


RUN pip install --no-cache-dir -r requirements.txt

COPY . .