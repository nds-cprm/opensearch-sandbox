# Roteiro de testes

Testes manuais da stack, feitos com `curl` contra os serviços em execução. O projeto não tem testes automatizados, e este roteiro não cobre saídas HTML: não entram `f=html` no OGC API nem `text/html` no `GetFeatureInfo`.

As rotas e os resultados consideram a massa padrão de `opensearch/dados/gerar_massa.py`, com 500 documentos, e `PUBLIC_HOST=localhost`.

## Preparação

```bash
docker compose up -d --wait
curl -s 'http://localhost:9200/_cat/indices/litoestratigrafia*?h=index,docs.count'   # esperado: 500
```

Se o índice não existir, rode `python3 opensearch/dados/gerar_massa.py`. Sem ele, o pygeoapi reinicia em ciclo. O WCS também precisa de `gis/mapserver/data/bluemarble.tif`.

Os pedidos abaixo são relativos a `https://localhost`, exceto os que começam com a porta. Com certificado autoassinado, use `curl -k`. Por exemplo:

```bash
curl -sk -o /dev/null -w '%{http_code} %{content_type}\n' 'https://localhost/ogcapi/conformance?f=json'
```

Pedidos com `SUBSET=Long(...)` precisam de aspas simples no shell.

## 1. Estado da stack

```bash
docker compose config --quiet
docker compose ps                                  # todos no ar, healthy onde há healthcheck
docker compose exec nginx nginx -t
docker compose exec opensearch-proxy nginx -t
```

Só devem estar publicadas as portas 80, 443, 5601 e 9200. Conexões em 8080, 8081, 8443 e 9600 no host precisam falhar.

## 2. Rotas e filtros do nginx

| Pedido | Esperado |
| --- | --- |
| `:80/x` | 301 para `https://localhost/x` |
| `/geoserver/wms?request=GetCapabilities` | 301 para `/geoserver/ows`, com `service=wms` e URL completa |
| `/geoserver/wfs?request=GetCapabilities` | 301, com `service=wfs` |
| `/geoserver/wcs?request=GetCapabilities` | 301, com `service=wcs` |
| `/geoserver/wfs?SERVICE=WFS&request=GetCapabilities` | 301, com um único `SERVICE` |
| `/geoserver/ows` | 403 |
| `/geoserver/ows?service=abc` | 403 |
| `/geoserver/ows?service=WMS&service=WFS&request=GetCapabilities` | 403 |
| `/geoserver/ows?%73ervice=WMS&request=GetCapabilities` | 403 |
| `/geoserver/ows?service=WFS&mode=map` | 403 |
| `/geoserver/ows?service=WFS&map=DEFAULT&request=GetCapabilities` | 403 |
| `/geoserver/ows?service=WCS&version=2.0.1&request=GetCoverage&coverageid=bluemarble&format=image/png` | 403 |
| `/geoserver/DEFAULT/ogcapi` | 404 |
| `/mapproxy/demo/` | 404 |
| `/demo/` | 404 |

Pedidos com outros métodos:

```bash
OWS=https://localhost/geoserver
curl -sk -o /dev/null -w '%{http_code}\n' -X PUT -d x "$OWS/ows?service=WFS"                 # 405
curl -sk -o /dev/null -w '%{http_code}\n' -d 'service=WMS&request=GetCapabilities' "$OWS/ows" # 403, formulário
curl -sk -o /dev/null -w '%{http_code}\n' -H 'Content-Type: text/xml' -d '<x/>' "$OWS/ows?service=WFS" # 403, XML com query string
curl -sk -o /dev/null -w '%{http_code} %{redirect_url}\n' -H 'Content-Type: text/xml' -d '<x/>' "$OWS/wfs" # 308 para /geoserver/ows
```

## 3. WFS

| Pedido | Esperado |
| --- | --- |
| `/geoserver/ows?SERVICE=WFS&VERSION=1.0.0&REQUEST=GetCapabilities` | 200, XML, com `SHAPE-ZIP`, `KML`, `GPKG` e `csv` |
| `/geoserver/ows?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetCapabilities` | 200, XML |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities` | 200, XML, com os formatos por MIME e URL `https://localhost/geoserver/ows` |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=DescribeFeatureType&TYPENAMES=ms:poligonos_opensearch` | 200, XML |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=2` | 200, GML |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&RESULTTYPE=hits` | 200, `numberMatched="500"` |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=3&OUTPUTFORMAT=json` | 200, GeoJSON com 3 feições |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=3&OUTPUTFORMAT=application/json` | 200, GeoJSON com 3 feições |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=2&STARTINDEX=2&SORTBY=fid&OUTPUTFORMAT=json` | 200, 2 feições diferentes das de `STARTINDEX=0` |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&FEATUREID=poligonos_opensearch.1&OUTPUTFORMAT=json` | 200, 1 feição |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&OUTPUTFORMAT=json&FILTER=%3CFilter%3E%3CPropertyIsEqualTo%3E%3CPropertyName%3Esigla%3C/PropertyName%3E%3CLiteral%3ET22pa%3C/Literal%3E%3C/PropertyIsEqualTo%3E%3C/Filter%3E` | 200, ao menos 1 feição, todas com `sigla` igual a `T22pa` |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&BBOX=-74,-34,-29,6,urn:ogc:def:crs:OGC:1.3:CRS84&COUNT=5&OUTPUTFORMAT=json` | 200, ao menos 1 feição |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=5&OUTPUTFORMAT=SHAPE-ZIP` | 200, ZIP com `.shp` |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=3&OUTPUTFORMAT=KML&SRSNAME=EPSG:4326` | 200, KML em lon,lat |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=3&OUTPUTFORMAT=KML&SRSNAME=EPSG:4674` | 200, KML em lon,lat |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=5&OUTPUTFORMAT=GPKG` | 200, arquivo SQLite |
| `/geoserver/ows?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature&TYPENAMES=ms:poligonos_opensearch&COUNT=5&OUTPUTFORMAT=csv` | 200, CSV com WKT na geometria |

No GeoJSON, confira também:

- As propriedades não têm `_id`, `id`, `type` nem o prefixo `properties.`.
- O identificador sai só em `properties.fid`, sem `id` na feição.

`GetFeature` por `POST`, com `Content-Type` `text/xml` e, depois, `application/xml; charset=utf-8`:

```bash
curl -sk -H 'Content-Type: text/xml' 'https://localhost/geoserver/ows' -d \
  '<wfs:GetFeature service="WFS" version="2.0.0" outputFormat="application/json" count="2" xmlns:wfs="http://www.opengis.net/wfs/2.0"><wfs:Query typeNames="ms:poligonos_opensearch" xmlns:ms="http://mapserver.gis.umn.edu/mapserver"/></wfs:GetFeature>'
```

Esperado: 200, GeoJSON com 2 feições.

## 4. WMS

| Pedido | Esperado |
| --- | --- |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities` | 200, XML, com `litoestratigrafia`, `/geoserver/ows` e `application/vnd.ogc.gml` |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities` | 200, XML, com `text/plain`, `application/json` e `text/xml` |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:4326&BBOX=-60,-20,-40,0&WIDTH=256&HEIGHT=256&FORMAT=image/png` | 200, PNG |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:4326&BBOX=-60,-20,-40,0&WIDTH=256&HEIGHT=256&FORMAT=image/jpeg` | 200, JPEG |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:4326&BBOX=-60,-20,-40,0&WIDTH=256&HEIGHT=256&FORMAT=image/gif` | 200, GIF |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:3857&BBOX=-6000000,-3000000,-4000000,-1000000&WIDTH=256&HEIGHT=256&FORMAT=image/png` | 200, PNG |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:900913&BBOX=-6000000,-3000000,-4000000,-1000000&WIDTH=256&HEIGHT=256&FORMAT=image/png` | 200, PNG |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:4674&BBOX=-60,-20,-40,0&WIDTH=256&HEIGHT=256&FORMAT=image/png` | 200, PNG |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS=litoestratigrafia&STYLES=&CRS=EPSG:4326&BBOX=-20,-60,0,-40&WIDTH=256&HEIGHT=256&FORMAT=image/png` | 200, PNG |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:4326&BBOX=-60,-20,-40,0&WIDTH=256&HEIGHT=256&FORMAT=image/tiff` | 500, TIFF recusado |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&LAYERS=litoestratigrafia&QUERY_LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:4326&BBOX=-74,-34,-29,6&WIDTH=256&HEIGHT=256&X=128&Y=128&FORMAT=image/png&FEATURE_COUNT=5&INFO_FORMAT=text/plain` | 200, texto |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&LAYERS=litoestratigrafia&QUERY_LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:4326&BBOX=-74,-34,-29,6&WIDTH=256&HEIGHT=256&X=128&Y=128&FORMAT=image/png&FEATURE_COUNT=5&INFO_FORMAT=application/json` | 200, JSON |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&LAYERS=litoestratigrafia&QUERY_LAYERS=litoestratigrafia&STYLES=&SRS=EPSG:4326&BBOX=-74,-34,-29,6&WIDTH=256&HEIGHT=256&X=128&Y=128&FORMAT=image/png&FEATURE_COUNT=5&INFO_FORMAT=application/vnd.ogc.gml` | 200, GML 2 |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=litoestratigrafia&QUERY_LAYERS=litoestratigrafia&STYLES=&CRS=EPSG:4326&BBOX=-34,-74,6,-29&WIDTH=256&HEIGHT=256&I=128&J=128&FORMAT=image/png&FEATURE_COUNT=5&INFO_FORMAT=application/json` | 200, JSON |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo&LAYERS=litoestratigrafia&QUERY_LAYERS=litoestratigrafia&STYLES=&CRS=EPSG:4326&BBOX=-34,-74,6,-29&WIDTH=256&HEIGHT=256&I=128&J=128&FORMAT=image/png&FEATURE_COUNT=5&INFO_FORMAT=text/xml` | 200, XML |
| `/geoserver/ows?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetLegendGraphic&LAYER=litoestratigrafia&FORMAT=image/png` | 200, PNG |

O `GetCapabilities` não pode anunciar `text/html`, TIFF no `GetMap` nem, na 1.3.0, `application/vnd.ogc.gml`.

## 5. WCS

| Pedido | Esperado |
| --- | --- |
| `/geoserver/ows?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCapabilities` | 200, XML, com `bluemarble` |
| `/geoserver/ows?SERVICE=WCS&VERSION=1.1.1&REQUEST=GetCapabilities` | 200, XML, com `bluemarble` |
| `/geoserver/ows?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities` | 200, XML, com `bluemarble` |
| `/geoserver/ows?SERVICE=WCS&VERSION=1.0.0&REQUEST=DescribeCoverage&COVERAGE=bluemarble` | 200, XML |
| `/geoserver/ows?SERVICE=WCS&VERSION=2.0.1&REQUEST=DescribeCoverage&COVERAGEID=bluemarble` | 200, XML |
| `/geoserver/ows?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&COVERAGE=bluemarble&CRS=EPSG:4326&BBOX=-50,-20,-49,-19&WIDTH=30&HEIGHT=30&FORMAT=GEOTIFF` | 200, TIFF |
| `/geoserver/ows?SERVICE=WCS&VERSION=1.1.1&REQUEST=GetCoverage&IDENTIFIER=bluemarble&BOUNDINGBOX=-20,-50,-19,-49,urn:ogc:def:crs:EPSG::4326&FORMAT=image/tiff` | 200, resposta multipart com TIFF |
| `/geoserver/ows?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=bluemarble&FORMAT=image/tiff&SUBSET=Long(-50,-49)&SUBSET=Lat(-20,-19)` | 200, TIFF |
| `/geoserver/ows?SERVICE=WCS&VERSION=2.0.1&REQUEST=DescribeCoverage&COVERAGEID=poligonos_opensearch` | 404, exceção OGC em XML |

`GetCoverage` por `POST`, que devolve a cobertura inteira:

```bash
curl -sk -o /dev/null -w '%{http_code} %{content_type}\n' -H 'Content-Type: text/xml' 'https://localhost/geoserver/ows' -d \
  '<wcs:GetCoverage xmlns:wcs="http://www.opengis.net/wcs/2.0" service="WCS" version="2.0.1"><wcs:CoverageId>bluemarble</wcs:CoverageId><wcs:format>image/tiff</wcs:format></wcs:GetCoverage>'
```

Esperado: 200, `image/tiff`.

## 6. OGC API

| Pedido | Esperado |
| --- | --- |
| `/ogcapi?f=json` | 200, JSON, com links em `https://localhost/ogcapi` |
| `/ogcapi/conformance?f=json` | 200, JSON |
| `/ogcapi/openapi?f=json` | 200, JSON |
| `/ogcapi/collections?f=json` | 200, JSON, com `opensearch_demo` |
| `/ogcapi/collections/opensearch_demo?f=json` | 200, JSON |
| `/ogcapi/collections/opensearch_demo/queryables?f=json` | 200, JSON |
| `/ogcapi/collections/opensearch_demo/items?f=json&limit=2` | 200, 2 feições e `numberMatched` 500 |
| `/ogcapi/collections/opensearch_demo/items?f=json&limit=2&offset=2` | 200, 2 feições |
| `/ogcapi/collections/opensearch_demo/items?f=json&limit=2&bbox=-74,-34,-29,6` | 200, ao menos 1 feição |
| `/ogcapi/collections/opensearch_demo/items/1?f=json` | 200, feição de id 1 |
| `/ogcapi/collections/opensearch_demo/items?f=json&limit=3&sortby=nome` | 200, 3 feições |
| `/ogcapi/collections/opensearch_demo/items?f=csv&limit=2` | 200, CSV |
| `/ogcapi/collections/opensearch_demo/items?f=jsonld&limit=2` | 200, JSON-LD |
| `/ogcapi/collections/opensearch_demo/items/nao-existe?f=json` | 404 |

## 7. OpenSearch e Dashboards

| Pedido | Esperado |
| --- | --- |
| `:9200/` | 200, versão `7.10.2`, do modo de compatibilidade |
| `:9200/_cluster/health` | 200, `green`, 2 nós |
| `:9200/_cat/aliases/litoestratigrafia_1m?h=index` | 200, `litoestratigrafia_1m_20260728_192458` |
| `:9200/litoestratigrafia_1m/_count` | 200, `"count":500` |
| `:9200/litoestratigrafia_1m/_mapping` | 200, `geometry` como `geo_shape` |
| `:9200/litoestratigrafia_1m/_mapping/properties` | 200, igual ao anterior |
| `:5601/api/status` | 200, estado `green` |
| `:5601/api/saved_objects/_find?type=index-pattern` | 200, sem login |

Busca espacial pelo proxy:

```bash
curl -s -H 'Content-Type: application/json' 'http://localhost:9200/litoestratigrafia_1m/_search' -d \
  '{"size":1,"query":{"geo_shape":{"geometry":{"shape":{"type":"envelope","coordinates":[[-74,6],[-29,-34]]},"relation":"intersects"}}}}'
```

Esperado: 200, com `hits` preenchido.

## 8. Operação

### Limite de feições do WFS

Este teste apaga e recria o índice. Os dados são fictícios, e a mesma semente gera os mesmos documentos.

```bash
python3 opensearch/dados/gerar_massa.py --registros 5100 --recriar
```

Com `OUTPUTFORMAT=json`, `KML` ou `csv`, sem `COUNT`, cada resposta traz 5.000 feições. `RESULTTYPE=hits` mostra `numberMatched="5100"`, e `COUNT=5000&STARTINDEX=5000` devolve as outras 100. Não faça pedidos WMS nesta etapa, para não gravar tiles com a massa maior.

Ao terminar, volte à massa padrão:

```bash
python3 opensearch/dados/gerar_massa.py --recriar
```

### Massa em índice temporário

```bash
python3 opensearch/dados/gerar_massa.py --registros 20 --indice lab_teste_massa --alias lab_teste_massa_a
curl -s 'http://localhost:9200/lab_teste_massa_a/_count'       # "count":20
curl -s -X DELETE 'http://localhost:9200/lab_teste_massa'
```

### Seed do MapProxy

```bash
docker compose exec mapproxy sh -c 'cd /var/lib/mapproxy/config && mapproxy-seed --dry-run -f mapproxy.yaml -s seed.yaml'
```

Esperado: sem erros e sem mudança na quantidade de arquivos em `gis/mapproxy/cache/`. As linhas `removing old tiles` também aparecem no `--dry-run`, sem apagar nada.

## 9. Falhas

Estes testes derrubam partes da stack.

### Queda do proxy do OpenSearch

```bash
docker compose stop opensearch-proxy
```

| Serviço | Esperado |
| --- | --- |
| WFS `GetCapabilities` | 200 |
| WFS `GetFeature` | 400 |
| WMS `GetMap` em área já em cache | 200 |
| WCS `GetCoverage` | 200 |
| Itens do `/ogcapi`, com o pygeoapi em execução | 500 |

Depois, reinicie o pygeoapi com `docker compose restart pygeoapi`. Ele entra em ciclo de reinício, e `/ogcapi` passa a responder 502, enquanto o WMS e o WFS seguem normais.

Volte o proxy com `docker compose start opensearch-proxy` e aguarde cerca de 1 minuto. Tudo precisa se recuperar sem reiniciar o nginx dos mapas.

### Reinício dos nós

Reinicie um nó por vez e, em outro terminal, repita `curl 'http://localhost:9200/litoestratigrafia_1m/_count'` enquanto isso:

```bash
docker compose restart opensearch-node2
docker compose restart opensearch-node1
```

Esperado: a API segue respondendo 200, e o cluster volta a `green` com 2 nós.

### Subida do zero

```bash
docker compose down        # sem -v, para preservar os volumes
docker compose up -d --wait
```

Aguarde o Dashboards terminar de subir, porque ele responde 503 nos primeiros segundos, e repita as seções 2 a 7.

## Fora do roteiro

- Saídas HTML.
- ArcGIS, QGIS e OpenSearch 2.12.0.
- Reboot do host. Se o nginx e o MapServer subirem ao mesmo tempo, as rotas do MapServer podem responder 502 por 25 a 40 s e se recuperam sozinhas.
