FROM centos:7.5.1804
LABEL maintainer=KBN_Project_Team_Continuous@dgs.com
RUN yum install -y sudo

ADD entrypoint.sh /
RUN chmod a+x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
