FROM centos:7.5.1804
LABEL maintainer=KBN_Project_Team_Continuous@dgs.com
RUN yum install -y sudo \
    && groupadd -g 1000 oticon

ADD entrypoint.sh /
RUN chmod a+x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
