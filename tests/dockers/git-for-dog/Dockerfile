FROM alpine/git
LABEL maintainer=rasmus.toftdahl.olesen@gmail.com

RUN apk add sudo

ADD entrypoint.sh /
RUN chmod a+x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
