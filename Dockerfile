FROM ubuntu:16.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
	   git wget python3-pip apt-utils \
	&& rm -rf /var/lib/apt/lists/*

ENV DOCKERIZE_VERSION v0.6.1
RUN wget -q https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
    && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

RUN pip3 install --upgrade pip
RUN pip3 install setuptools
RUN ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /workspace
ADD . .
RUN pip3 install -r requirements.txt

ENV LANG en_US.UTF-8

ENV DJANGO_SUPERUSER_USERNAME root
ENV DJANGO_SUPERUSER_EMAIL none@none.com
ENV DJANGO_SUPERUSER_PASSWORD password

RUN chmod -R a+w /workspace

EXPOSE 8000
