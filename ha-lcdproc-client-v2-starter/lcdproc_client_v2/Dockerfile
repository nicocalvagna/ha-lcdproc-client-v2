FROM ghcr.io/home-assistant/amd64-base:latest
RUN apk add --no-cache python3 py3-requests
WORKDIR /app
COPY run.sh /run.sh
COPY main.py /app/main.py
RUN chmod a+x /run.sh
CMD ["/run.sh"]
