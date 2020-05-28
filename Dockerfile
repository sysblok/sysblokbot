FROM python:3.7-alpine

RUN apk add --no-cache gcc libressl-dev musl-dev libffi-dev sqlite; rm -rf /var/lib/apt/lists/*

WORKDIR /app
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt
COPY . /app

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

RUN pip install .

RUN apk del libressl-dev musl-dev libffi-dev gcc

CMD python ./app.py
