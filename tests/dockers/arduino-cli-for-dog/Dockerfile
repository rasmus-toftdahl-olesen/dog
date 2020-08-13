FROM zoobab/arduino-cli
LABEL maintainer=rasmus.toftdahl.olesen@gmail.com
RUN apt install -y sudo

ADD entrypoint.sh /
RUN chmod a+x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
