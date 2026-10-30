# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

Laboratório (`opensearch-sandbox`) para avaliar o OpenSearch como fonte de dados GIS. O repositório só contém configuração: não há código de aplicação, build, testes automatizados nem lint. Toda a validação é feita subindo a stack e consultando os serviços.

Versões avaliadas: 2.12.0 (homologada pela ESRI) e 2.19.6 (última 2.x estável). A versão em uso é `OPENSEARCH_VERSION` no `.env`.

Clientes previstos: ArcGIS 12.x (índices como FeatureLayers), Apache Airflow (carga dos bancos corporativos), MapServer (estilo e WFS, com possível troca do WFS por OGC API Features), MapProxy (WMS, WMS-C, WMTS e KML em cache, lendo do MapServer) e pygeoapi (OGC API Features, Maps, Coverages e Tiles). O Airflow não faz parte desta stack.

A documentação e os comentários do projeto são em português.

## Comandos

```bash
docker compose up -d                       # sobe a stack (cada nó OpenSearch reserva 3 GB de heap)
docker compose config --quiet              # valida o compose
docker compose ps                          # estado e healthchecks
docker compose logs -f <serviço>

docker compose exec nginx nginx -t         # valida o nginx
docker compose restart nginx               # aplica mudanças no default.conf
```

`./nginx/default.conf` é montado como arquivo único. Editores que substituem o arquivo deixam o container com a versão antiga, por isso prefira `restart` a `nginx -s reload`.

Verificações pela stack em execução:

```bash
curl -s 'http://localhost:9200/_cluster/health?pretty'     # esperado: green, 2 nós
curl -s 'http://localhost:9200/_cat/indices?v'
curl -s 'http://localhost/mapserver?map=TESTE&SERVICE=WMS&REQUEST=GetCapabilities'
```

## Arquitetura

O nginx é a entrada única. A porta 80 do host vai para o `:8080` do nginx, e a 9200 do host para o `:9200` do nginx. Os nós OpenSearch não publicam a 9200; o `9600` do node1 (Performance Analyzer) e o `5601` do Dashboards são os únicos acessos diretos.

| Rota | Upstream | Protocolo |
| --- | --- | --- |
| `/ogcapi/` | `pygeoapi:8000` | uwsgi |
| `/mapproxy/` | `mapproxy:8000` | uwsgi |
| `/mapserver` | `mapserver:8080` | FastCGI |
| `:9200/` | `opensearch-node1` e `opensearch-node2` | HTTP |

Fluxo de dados pretendido: `MapProxy → MapServer → OpenSearch`, e `pygeoapi → OpenSearch` em paralelo.

Pontos que atravessam vários arquivos:

- **MapServer e pygeoapi acessam o OpenSearch por `nginx:9200`, não pelos nós.** O GDAL não aceita múltiplos hosts, então o balanceamento fica no upstream `opensearch-cluster`. A mesma porta tem `proxy_buffering off` e timeouts de 300 s para geometrias pesadas.
- **Modo de compatibilidade ES 7.x.** O driver ES do GDAL exige `compatibility.override_main_response_version=true`, definido no compose para os dois nós. Por isso `GET /` responde `7.10.2`, e não a versão real do OpenSearch. As instruções do README com `https` e `-u admin` valem para um cluster com segurança ativa, que não é o caso daqui.
- **Segurança desativada.** `DISABLE_SECURITY_PLUGIN=true` deixa o cluster em HTTP sem autenticação, embora as credenciais ainda apareçam na URL do pygeoapi e em `dashboards/opensearch_dashboards.yml`. Nesse arquivo, `opensearch.hosts` aponta para `https://localhost:9200`, mas o valor efetivo vem de `OPENSEARCH_HOSTS` no compose.
- **Imagens pré-construídas.** MapServer, MapProxy e pygeoapi usam imagens `docker.io/ndscprm/*`, e os Dockerfiles locais foram removidos. Comentários como `conf/uwsgi.conf of the image` e `examples/` se referem ao repositório dessas imagens, não a este.
- **Timeouts acoplados.** O `harakiri` de 60 s do uWSGI anda junto com `uwsgi_read_timeout 65s` no nginx. Ao mudar um, mude o outro. O MapServer não tem timeout próprio e depende de `fastcgi_read_timeout 60s`.
- **Porta real do pygeoapi.** O `server.bind.port` da configuração não define onde o serviço escuta. Com `pygeoapi/uwsgi.conf`, a porta vem de `PYGEOAPI_LISTEN_PORT` (8000 por padrão na imagem), usando o protocolo uwsgi, não HTTP.
- **Prefixo do pygeoapi.** `/ogcapi` aparece em `SCRIPT_NAME` e `PYGEOAPI_SERVER_URL` no compose, em `mount` no `uwsgi.conf` e no `uwsgi_param` do nginx. Mudanças de prefixo precisam tocar os três.

### MapServer

`mapserver/` é montado somente leitura em `/var/lib/mapserver`, e a configuração global é `mapserver/mapserver.conf`:

- Mapfiles são chamados pelo alias da seção `MAPS` (`map=TESTE`). Mapfile novo precisa ser adicionado ali.
- Também é possível usar o caminho, desde que case com `MS_MAP_PATTERN` (`^/var/lib/mapserver/`).
- Sem `map=`, a requisição falha de propósito (`MS_MAPFILE ""`).
- `wms_onlineresource` em `teste.map` não inclui `map=TESTE`.

### Nomes de índice

Os nomes estão fixos nos arquivos e não coincidem entre si:

- `mapserver/teste.map`: `litoestratigrafia_1m_20260728_192458`, nas cláusulas `DATA`/`FROM`
- `mapproxy/teste.xml`: `litoestratigrafia_1m_20260727_222038`
- `pygeoapi/local.config.yml`: `litoestratigrafia_1m`, sem timestamp

O SQL de `teste.map` projeta os campos `properties.*` com aliases, pois os documentos seguem a estrutura GeoJSON. Ao mudar o índice, atualize a query inteira.

### Regra temporária

O `location` de `/_mapping/properties` no nginx existe só para o GeoServer e está marcado como "Excluir depois".

## Problemas conhecidos (verificado em 2026-10-30)

Com a stack em execução, os nós estavam `green`, e o `GetCapabilities` do MapServer respondeu 200. O restante estava assim:

- **Sem dados:** nenhum índice `litoestratigrafia*` existe no cluster, apenas índices de sistema e `top_queries-*`.
- **pygeoapi, rotas:** `/ogcapi/` retornava 404 porque o uWSGI em execução subiu antes da edição de `pygeoapi/uwsgi.conf` e não tinha o mount `/ogcapi`, logo `PATH_INFO` chegava ao Flask com o prefixo. O uWSGI só lê o arquivo ao iniciar: use `docker compose restart pygeoapi`. Testado em instância temporária com o arquivo atual: responde 200.
- **pygeoapi, configuração:** a imagem lê `PYGEOAPI_CONFIG=/etc/pygeoapi/config.yml`, que vem com `resources: {}`, mas o compose monta `pygeoapi/local.config.yml` em `/pygeoapi/local.config.yml`. Por isso a coleção `opensearch_demo` não existe no serviço. Testado com `PYGEOAPI_CONFIG` apontando para o arquivo montado: a coleção aparece, e `/items` retorna 500 até o índice `litoestratigrafia_1m` existir.
- **MapProxy, rotas:** tudo em `/mapproxy/...` retorna 404 porque o `uwsgi.conf` da imagem não tem `mount` nem `manage-script-name`, e o nginx envia `PATH_INFO` com o prefixo. A correção é no `location` do nginx: capturar o caminho por regex e definir `SCRIPT_NAME` e `PATH_INFO` depois de `include uwsgi_params` (a ordem importa: o último `PATH_INFO` vence). Testado em nginx descartável: `/demo/`, WMS e WMTS respondem 200.
- **MapProxy, configuração:** o `app.py` da imagem lê `$HOME/mapproxy.yaml`, ou seja, `/var/lib/mapproxy/config/mapproxy.yaml`, mas o compose monta `./mapproxy` em `/mapproxy`. Sem arquivo em `$HOME`, o entrypoint gera um exemplo a cada subida, com `${server}` e `$layer` sem valor. Editar `mapproxy/mapproxy.yaml` não altera o serviço em execução. O destino da montagem deve ser `/var/lib/mapproxy/config`.
- **MapProxy, fonte:** `mapproxy/mapproxy.yaml` e `seed.yaml` ainda são os exemplos padrão, com fonte em `example.org` em vez do MapServer. Como `mapserver:8080` fala FastCGI e não HTTP, a fonte precisa passar pelo nginx: `http://nginx:8080/mapserver?map=TESTE`, camada `poligonos_opensearch`.
- **Mapnik:** `mapproxy/test_mapnik.py` não roda na imagem atual, que não tem o módulo `mapnik`. Ele também depende de `/mapproxy/teste.vrt`, que não existe no repositório.
- **Dashboards:** `/api/status` retorna 503. O log mostra a migração de saved objects parada, aguardando o índice `.kibana_1`.
