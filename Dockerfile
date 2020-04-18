FROM python:3.7-alpine

RUN apk add --no-cache gcc libressl-dev musl-dev libffi-dev; rm -rf /var/lib/apt/lists/*

COPY . /app
WORKDIR /app

RUN pip install .
RUN pip install -r requirements.txt

RUN apk del libressl-dev musl-dev libffi-dev gcc

CMD python ./app.py
