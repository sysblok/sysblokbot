FROM python:3.7-alpine

RUN apk add --no-cache gcc libressl-dev musl-dev libffi-dev; rm -rf /var/lib/apt/lists/*

WORKDIR /app
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . /app

RUN pip install .

RUN apk del libressl-dev musl-dev libffi-dev gcc

CMD python ./app.py
