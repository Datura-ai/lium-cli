FROM ubuntu

RUN apt-get update && \
    apt-get install -y wget && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y openssh-server

# Ensure SSH host keys are generated
RUN ssh-keygen -A

RUN mkdir -p /run/sshd && \
    mkdir -p /root/.ssh && \
    chmod 700 /root/.ssh

RUN echo USER_PUBLIC_KEY > /root/.ssh/authorized_keys && \
    chmod 600 /root/.ssh/authorized_keys

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
