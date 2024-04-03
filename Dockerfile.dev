
FROM python:3.8-alpine3.13 AS builder

RUN apk add --no-cache build-base gcc python3-dev jpeg-dev zlib-dev libressl-dev musl-dev libffi-dev sqlite git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN pip install .

FROM python:3.8-alpine3.13 as production

RUN apk add --no-cache libressl-dev musl-dev libffi-dev gcc

ARG COMMIT_HASH
ARG COMMIT_HASH_SHORT
ENV COMMIT_HASH=$COMMIT_HASH
ENV COMMIT_HASH_SHORT=$COMMIT_HASH_SHORT


ENV MUSL_LOCALE_DEPS cmake make musl-dev gcc gettext-dev libintl
ENV MUSL_LOCPATH /usr/share/i18n/locales/musl

RUN apk add --no-cache \
    $MUSL_LOCALE_DEPS \
    && wget https://gitlab.com/rilian-la-te/musl-locales/-/archive/master/musl-locales-master.zip \
    && unzip musl-locales-master.zip \
      && cd musl-locales-master \
      && cmake -DLOCALE_PROFILE=OFF -D CMAKE_INSTALL_PREFIX:PATH=/usr . && make && make install \
      && cd .. && rm -r musl-locales-master

WORKDIR /app

COPY --from=builder /usr/local /usr/local
COPY --from=builder /app /app

CMD ["python", "./app.py"]