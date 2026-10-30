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

Massa de teste (dados fictícios, usa só a biblioteca padrão do Python):

```bash
python3 dados/gerar_massa.py                            # 500 documentos
python3 dados/gerar_massa.py --registros 5000 --recriar # apaga o índice e recarrega
```

O script cria `litoestratigrafia_1m_20260728_192458` (lido pelo MapServer) com o alias `litoestratigrafia_1m` (lido pelo pygeoapi). O índice fica nos volumes `opensearch-data*`. Documentos precisam seguir o formato GeoJSON (`type`, `geometry`, `properties.*`), com `geometry` como `geo_shape` e textos com subcampo `.raw`, usado pelo pygeoapi para ordenar.

## Arquitetura

O nginx é a entrada única. A porta 80 do host vai para o `:8080` do nginx, e a 9200 do host para o `:9200` do nginx. Os nós OpenSearch não publicam portas, e o `5601` do Dashboards é o único acesso direto. A porta 9600 do Performance Analyzer está comentada no compose, porque não respondia.

| Rota | Upstream | Protocolo |
| --- | --- | --- |
| `/ogcapi` | `pygeoapi:8000` | uwsgi |
| `/mapproxy` | `mapproxy:8000` | uwsgi |
| `/mapserver` | `mapserver:8080` | FastCGI |
| `:9200/` | `opensearch-node1` e `opensearch-node2` | HTTP |

Fluxo de dados pretendido: `MapProxy → MapServer → OpenSearch`, e `pygeoapi → OpenSearch` em paralelo.

Pontos que atravessam vários arquivos:

- **MapServer e pygeoapi acessam o OpenSearch por `nginx:9200`, não pelos nós.** O GDAL não aceita múltiplos hosts, então o balanceamento fica no upstream `opensearch-cluster`. A mesma porta tem `proxy_buffering off` e timeouts de 300 s para geometrias pesadas.
- **Modo de compatibilidade ES 7.x.** O driver ES do GDAL exige `compatibility.override_main_response_version=true`, definido no compose para os dois nós. Por isso `GET /` responde `7.10.2`, e não a versão real do OpenSearch. As instruções do README com `https` e `-u admin` valem para um cluster com segurança ativa, que não é o caso daqui.
- **Segurança desativada.** `DISABLE_SECURITY_PLUGIN=true` deixa o cluster em HTTP sem autenticação, embora as credenciais ainda apareçam na URL do pygeoapi e em `dashboards/opensearch_dashboards.yml`. Nesse arquivo, `opensearch.hosts` aponta para `https://localhost:9200`, mas o valor efetivo vem de `OPENSEARCH_HOSTS` no compose.
- **Imagens pré-construídas.** MapServer, MapProxy e pygeoapi usam imagens `docker.io/ndscprm/*`, e os Dockerfiles locais foram removidos. Comentários como `conf/uwsgi.conf of the image` e `examples/` se referem ao repositório dessas imagens, não a este.
- **Ordem de subida.** Primeiro os nós OpenSearch, com healthcheck de `_cluster/health`; depois os serviços; por último o nginx, que não inicia sem resolver os upstreams. O pygeoapi não pode depender do nginx, porque isso cria um ciclo, e o nginx usa `service_started` para ele: o pygeoapi só fica `healthy` depois de gerar o OpenAPI, o que passa pelo nginx. Trocar para `service_healthy` trava a subida.
- **Timeouts acoplados.** O `harakiri` de 60 s do uWSGI anda junto com `uwsgi_read_timeout 65s` no nginx. Ao mudar um, mude o outro. O MapServer não tem timeout próprio e depende de `fastcgi_read_timeout 60s`.
- **Configuração do pygeoapi.** O serviço lê `PYGEOAPI_CONFIG`, e `pygeoapi/local.config.yml` é montado nesse caminho (`/run/pygeoapi/config.yml`). Sem a variável, a imagem lê `/etc/pygeoapi/config.yml`, um exemplo com `resources: {}`. O uWSGI só lê `pygeoapi/uwsgi.conf` ao iniciar: depois de editá-lo, reinicie o serviço.
- **Prefixo do MapProxy.** `mapproxy/uwsgi.conf` não tem `mount`, então quem remove `/mapproxy` é o `location` do nginx, definindo `SCRIPT_NAME` e `PATH_INFO` depois de `include uwsgi_params`. A ordem importa: o último `PATH_INFO` vence.
- **Porta real do pygeoapi.** O `server.bind.port` da configuração não define onde o serviço escuta. Com `pygeoapi/uwsgi.conf`, a porta vem de `PYGEOAPI_LISTEN_PORT` (8000 por padrão na imagem), usando o protocolo uwsgi, não HTTP.
- **Prefixo do pygeoapi.** `/ogcapi` aparece em `SCRIPT_NAME` e `PYGEOAPI_SERVER_URL` no compose, em `mount` no `uwsgi.conf` e no `uwsgi_param` do nginx. Mudanças de prefixo precisam tocar os três.

### MapServer

`mapserver/` é montado somente leitura em `/var/lib/mapserver`, e a configuração global é `mapserver/mapserver.conf`:

- Mapfiles são chamados pelo alias da seção `MAPS` (`map=TESTE`). Mapfile novo precisa ser adicionado ali.
- Também é possível usar o caminho, desde que case com `MS_MAP_PATTERN` (`^/var/lib/mapserver/`).
- Sem `map=`, a requisição falha de propósito (`MS_MAPFILE ""`).

### MapProxy

- `mapproxy/data/` é montado somente leitura em `/var/lib/mapproxy/config`, que é o `$HOME` lido pelo `app.py` da imagem. Sem `mapproxy.yaml` ali, o entrypoint gera um exemplo.
- `mapproxy/cache/` guarda os tiles em layout `tms`, em `<cache>/<camada>/<grade>`, o mesmo do bloco de cache do nginx, hoje comentado.
- `localhost` dentro do container é o próprio MapProxy, e `mapserver:8080` fala FastCGI, não HTTP. Por isso, a fonte passa pelo nginx (`http://nginx:8080/mapserver?...`).
- O serviço só lê o YAML ao iniciar: depois de editar, use `docker compose restart mapproxy`.
- `mapproxy/data/seed.yaml` limita o seed à cobertura `brasil`, o mesmo `EXTENT` de `mapserver/teste.map`. Até o nível 10 são 24.864 tiles, contra 1.398.080 do mundo inteiro. Para conferir antes de rodar, use `mapproxy-seed --dry-run`.

### Nomes de índice

O MapServer e o pygeoapi leem o mesmo alias, `litoestratigrafia_1m`:

- `mapserver/teste.map`: pelo curinga `litoestratigrafia*_1m`
- `pygeoapi/local.config.yml`: pelo nome do alias

O driver ES do GDAL não abre alias pelo nome, mas aceita curingas. Para seguir o alias, use `litoestratigrafia*_1m` em `CONNECTIONOPTIONS "LAYER"` e no `DATA`. Esse padrão casa com o alias e não com os índices datados. Já `litoestratigrafia_1m*` soma todos os índices datados e duplica feições.

### WFS e filtros no MapServer

`teste.map` usa a camada direta no `DATA`, sem `SELECT`. O MapServer anexa filtros de atributo como `WHERE` ao SQL do `DATA`, e o OGR não aceita ali aliases do `SELECT`, o que quebra `FILTER` e `FEATUREID`. Por isso, os campos chegam como `properties.*` e são renomeados por metadados da camada:

- Campo novo precisa de `gml_properties.<campo>_alias` (WFS) e `wms_properties.<campo>_alias` (WMS). `ows_*` não vale para o WFS.
- `gml_exclude_items` e `wms_exclude_items` escondem `_id`, `id` e `type`.
- Requisições com filtro são recortadas pelo `EXTENT` do mapfile, que precisa cobrir todos os dados. Sem isso, as contagens ficam menores, sem erro.

### Regra temporária

O `location` de `/_mapping/properties` no nginx existe só para o GeoServer e está marcado como "Excluir depois".

## Problemas conhecidos (verificado em 2026-10-30)

Com a stack em execução, os nós estavam `green`, e o MapServer, o pygeoapi e o MapProxy serviram os dados carregados por `dados/gerar_massa.py`. O restante estava assim:

- **Dashboards:** `/api/status` retorna 503. A migração de saved objects está parada: `.kibana_1` existe, com 0 documentos, sem o alias `.kibana`.
