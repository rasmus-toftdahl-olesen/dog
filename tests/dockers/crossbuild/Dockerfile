FROM multiarch/crossbuild
LABEL maintainer=rasmus.toftdahl.olesen@gmail.com

ENV CROSS_TRIPLE=aarch64-linux-gnu

RUN apt-get update; apt-get install -y sudo

ADD entrypoint.sh /
RUN chmod a+x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
