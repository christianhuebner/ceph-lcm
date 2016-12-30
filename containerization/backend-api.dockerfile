# vi: set ft=dockerfile :


FROM decapod/base-plugins
MAINTAINER Sergey Arkhipov <sarkhipov@mirantis.com>


LABEL version="0.2.0" description="API service for Decapod" vendor="Mirantis"
ARG pip_index_url=
ARG npm_registry_url=


COPY .git /project/.git


RUN set -x \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    gcc \
    git \
    libffi-dev \
    libpcre3 \
    libpcre3-dev \
    python3-dev \
    python3-pip \
    \
    # workaround for https://github.com/pypa/pip/issues/4180
  && ln -s /project/.git /tmp/.git && ln -s /project/.git /.git \
  && cd /project \
  && git reset --hard \
  && scd -v \
  && pip3 install --no-cache-dir -c /project/constraints.txt uwsgi \
  && pip3 install --no-cache-dir /project/backend/api \
  && rm -r /project /.git /tmp/.git \
  && apt-get clean \
  && apt-get purge -y git libffi-dev libpcre3-dev python3-dev python3-pip gcc \
  && apt-get autoremove -y \
  && rm -r /var/lib/apt/lists/*


EXPOSE 8000

ENTRYPOINT ["/usr/bin/dumb-init", "-c", "--"]
CMD ["dockerize", "-wait", "tcp://database:27017", "--", "uwsgi", "/etc/decapod-api-uwsgi.ini"]
