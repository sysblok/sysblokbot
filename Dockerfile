FROM python:3.8-alpine3.13

RUN apk add --no-cache build-base gcc python3-dev jpeg-dev zlib-dev libressl-dev musl-dev libffi-dev sqlite git; rm -rf /var/lib/apt/lists/*

WORKDIR /app
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . /app

ARG COMMIT_HASH
ARG COMMIT_HASH_SHORT
ARG UPTRACE_DSN
ENV COMMIT_HASH=$COMMIT_HASH
ENV COMMIT_HASH_SHORT=$COMMIT_HASH_SHORT
ENV UPTRACE_DSN=$UPTRACE_DSN


ENV MUSL_LOCALE_DEPS cmake make musl-dev gcc gettext-dev libintl
ENV MUSL_LOCPATH /usr/share/i18n/locales/musl
# Last musl-locales commit before upstream switched to -std=c23, which Alpine 3.13 GCC does not support.
ARG MUSL_LOCALES_VERSION=e3c3bef8df744ae9c09382a11e10831168d82311

RUN apk add --no-cache \
    $MUSL_LOCALE_DEPS \
    && wget -O musl-locales.zip https://gitlab.com/rilian-la-te/musl-locales/-/archive/${MUSL_LOCALES_VERSION}/musl-locales-${MUSL_LOCALES_VERSION}.zip \
    && unzip musl-locales.zip \
      && cd musl-locales-${MUSL_LOCALES_VERSION} \
      && cmake -DLOCALE_PROFILE=OFF -DCMAKE_INSTALL_PREFIX:PATH=/usr . && make && make install \
      && cd .. && rm -rf musl-locales-${MUSL_LOCALES_VERSION} musl-locales.zip

RUN pip install .

RUN apk del libressl-dev musl-dev libffi-dev gcc git

CMD python ./app.py
