FROM ubuntu:26.04 
# debian:trixie-slim

# Instala o MapServer, CGI e o spawn-fcgi
RUN apt-get update && apt-get install -y \
    mapserver-bin \
    cgi-mapserver \
    spawn-fcgi \
    && rm -rf /var/lib/apt/lists/*

VOLUME [ "/maps" ]

# Cria diretório para os Mapfiles e dados de mapas
WORKDIR /maps

# Expõe a porta do FastCGI
EXPOSE 9000

ENV NUM_WORKERS=4

COPY start.sh /usr/local/bin

RUN touch /maps/mapserver.log && ln -sf /dev/stderr /maps/mapserver.log

# Inicia o executável do MapServer via spawn-fcgi em modo foreground
CMD [ "start.sh" ]