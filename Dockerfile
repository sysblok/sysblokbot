FROM python:3.8-alpine3.13

RUN apk add --no-cache build-base gcc python3-dev jpeg-dev zlib-dev libressl-dev musl-dev libffi-dev sqlite git; rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.21
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
COPY pyproject.toml uv.lock /app/
RUN uv sync --locked --no-dev
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

RUN apk del libressl-dev musl-dev libffi-dev gcc git

CMD ["/app/.venv/bin/python", "./app.py"]
