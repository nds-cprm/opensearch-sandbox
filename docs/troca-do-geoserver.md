# Troca do GeoServer

Comparação entre os serviços atuais, `https://geoservicos.sgb.gov.br/geoserver` e `https://geoservicos.sgb.gov.br/ogcapi`, e esta stack, que vai substituí-los. Os dados atuais vêm dos `GetCapabilities` e das respostas públicas, e os da stack, de testes em `https://localhost`. Levantamento feito em 2026-10-30.

A comparação mostra o que está publicado, não o que é usado. Os logs de acesso de produção dizem quais lacunas pesam de fato.

**Foco atual:** serviços e metadados. As camadas ficam para outro momento, na última seção.

## Serviços

| Item | GeoServer atual | Esta stack | Situação |
| --- | --- | --- | --- |
| Ponto único | `/ows` | `/geoserver/ows` | Atendido |
| Rotas por serviço | `/wms`, `/wfs`, `/wcs` | Não existem | Falta |
| Rotas por workspace | `/geosgb/wms`, `/geosgb/wfs`, `/geosgb/ows` e iguais para `gestao-territorial` e `hidrogeologia` | Não existem | Falta |
| WMTS | `/gwc/service/wmts`, 23 camadas | Ativo no MapProxy, sem rota no nginx | Falta a rota |
| WMS em cache | `/gwc/service/wms` | Não existe, mas o WMS já passa pelo cache do MapProxy | Falta a rota |
| Grades do WMTS | `EPSG:4326`, `EPSG:4326x2`, `WebMercatorQuad`, `WebMercatorQuadx2` | `webmercator` | Divergente |
| Projeções | `CRS:84`, `EPSG:4326`, `EPSG:4674`, `EPSG:3857`, `EPSG:900913` | `EPSG:3857`, `EPSG:4326`, `EPSG:4674` | Falta `EPSG:900913` |
| OGC API | Fora do GeoServer, em `/ogcapi` (ver [OGC API](#ogc-api)) | `/ogcapi` | Atendido |
| WCS | Sem coberturas listadas | `bluemarble`, de exemplo | Sem impacto |
| `/web` e `/rest` | Fechados ao público | Não existem | Sem impacto |

### Formatos

| Operação | GeoServer atual | Esta stack | Situação |
| --- | --- | --- | --- |
| `GetMap` | PNG, JPEG, GIF, GeoTIFF, PDF, KML, KMZ, OpenLayers | PNG, JPEG, GIF, TIFF, GeoTIFF | Falta PDF, KML, KMZ e OpenLayers |
| `GetFeatureInfo` | Texto, GML 2 e 3.1.1, `text/xml`, HTML, JSON | Texto e JSON anunciados, e GML responde sem ser anunciado | HTML removido de propósito |
| `GetFeature` (WFS) | GML 2, 3.1.1 e 3.2, JSON, SHAPE-ZIP, KML, CSV | GML 2, 3.1.1 e 3.2, JSON | Falta SHAPE-ZIP, KML e CSV |

Pontos de atenção:

- `image/geotiff`, em minúsculas como no GeoServer, responde 500 aqui. A stack anuncia `image/GeoTIFF`.
- Um cliente que peça HTML no `GetFeatureInfo` recebe uma exceção. Os visualizadores que consomem o serviço atual precisam ser checados.
- As operações `CreateStoredQuery` e `DropStoredQuery` do WFS não são anunciadas aqui.

## OGC API

O serviço atual é um pygeoapi 0.21.0 em `https://geoservicos.sgb.gov.br/ogcapi`, separado do GeoServer. A stack usa o pygeoapi 0.24.0.

O endereço fica o mesmo, `/ogcapi`, na raiz do domínio.

| Item | Serviço atual | Esta stack | Situação |
| --- | --- | --- | --- |
| Caminho | `/ogcapi` | `/ogcapi` | Atendido |
| Tipo de coleção | Feature, 23 coleções | Feature, 1 coleção | Tratar com as camadas |
| Formatos de `items` | GeoJSON, JSON-LD, HTML, CSV | GeoJSON, JSON-LD, HTML, CSV | Atendido |
| `bbox`, `sortby`, `properties` | Respondem | Respondem | Atendido |
| CRS de saída | CRS84, EPSG:4326, EPSG:4674 | CRS84 | Falta: `crs=` com EPSG:4674 responde 400 |
| Filtro CQL2 | Não declarado na conformidade | Declarado, e `filter=` responde | A stack oferece mais |
| Idiomas | Português (`pt-BR`) e inglês, por `lang=` | Só `en-US`, e `lang=` não muda o texto | Falta |
| Link `canonical` na coleção | Presente | Ausente | Falta |
| Extensão temporal na coleção | Presente | Ausente | Tratar com as camadas |
| Processos e `/jobs` | Sem processos, e `/jobs` responde | Sem processos, e `/jobs` responde, sem link na página inicial | Atendido |
| Grades de tiles | `WorldCRS84Quad`, `WebMercatorQuad` | `WorldCRS84Quad`, `WebMercatorQuad` | Atendido |

## Metadados dos serviços

Na stack, o WMS público é o do MapProxy, e o WFS e o WCS são os do MapServer. Por isso, os metadados ficam em arquivos diferentes.

| Campo | GeoServer atual | WMS (MapProxy) | WFS (MapServer) | WCS (MapServer) |
| --- | --- | --- | --- | --- |
| Título | `SGB/CPRM WMS Server`, `WFS Server`, `WCS Server`, `WMTS Server` | Exemplo do MapProxy | Texto de teste | Vazio em 2.0.1 |
| Resumo | `SGB/CPRM Web Map Service` e equivalentes | Exemplo do MapProxy | Texto de teste | Vazio em 2.0.1 |
| Palavras-chave | Preenchidas | Ausentes | Ausentes | Ausentes |
| Organização | `CPRM - Geological Survey of Brazil` | Ausente | Ausente | Ausente |
| Contato | Nome, cargo e e-mail | Ausente | Ausente | Ausente |
| Endereço | Rio de Janeiro, RJ, CEP 22290240, Brazil | Ausente | Ausente | Ausente |
| Taxas | `NONE` | `none` | Ausente | Ausente |
| Restrições de acesso | `NONE` | `none` | Ausente | Ausente |

### Metadados do OGC API

Na stack, `pygeoapi/local.config.yml` ainda traz os textos de exemplo. O serviço atual serve de referência, por ser o único com textos em dois idiomas.

| Campo | Serviço atual | Esta stack |
| --- | --- | --- |
| Título | `Servidor de OGC-API do SGB/CPRM`; em inglês, `SGB/CPRM OGC-API Server` | `My Local Geospatial API` |
| Descrição | `API para disponibilização de dados geológicos do Serviço Geológico do Brasil` | `A pygeoapi instance serving local geospatial data.` |
| Palavras-chave | `geoespacial`, `dados`, `api` | `geospatial`, `api`, `OGC` |
| Provedor | `Divisão de Geoprocessamento`, `https://www.sgb.gov.br/` | `My Organization`, `https://example.org` |
| Endereço | `Av Pasteur, 404, Urca`, Rio de Janeiro | Ausente |
| Contato | Com instruções de horário, em dois idiomas | `geoteam@example.org` |
| Licença | CC-BY 4.0 | CC-BY 4.0 |

### Onde configurar

| Serviço | Arquivo | Chaves |
| --- | --- | --- |
| WMS, e WMTS quando tiver rota | `mapproxy/data/mapproxy.yaml` | `services.wms.md`: `title`, `abstract`, `contact`, `fees`, `access_constraints`, `keyword_list` |
| WFS e WCS | `mapserver/default.map` | `ows_*` no `METADATA` do `WEB`, ainda a validar nesta versão, em especial o título e o resumo do WCS 2.0.1 |
| OGC API | `pygeoapi/local.config.yml` | `metadata.identification`, `metadata.provider`, `metadata.contact` e `server.languages`, com textos por idioma |

### Conferir antes de copiar

O GeoServer atual tem inconsistências que não valem a pena levar para a stack:

- O endereço varia entre os serviços: `Pasteur` no WMS, WCS e WMTS, e `404, Urca` no WFS. O OGC API tem a forma completa, `Av Pasteur, 404, Urca`.
- O provedor varia: `CPRM - Geological Survey of Brazil` no GeoServer, `SGB/CPRM Geoprocessing Division` no WMTS e `Divisão de Geoprocessamento` no OGC API.
- O WCS anuncia `http://geoserver.org` como site do provedor.
- As palavras-chave são genéricas (`WFS`, `WMS`) e misturam serviços: o WCS traz `WMS`.
- O contato é uma pessoa. Um e-mail institucional dura mais.
- Os textos do GeoServer estão em inglês, e os do OGC API, em português e inglês. A organização aparece como CPRM e SGB/CPRM. Vale definir o nome oficial antes de reescrever.

## Antes da virada

- Trocar `PUBLIC_HOST` no `.env` e as quatro chaves `*_onlineresource` em `mapserver/default.map` para `geoservicos.sgb.gov.br`, e instalar o certificado real.
- Avisar quem usa o QGIS: depois de uma troca de formatos ou rotas, ele pode manter o `GetCapabilities` anterior por até 24 horas.

## Para outro momento: camadas

- **Quantidade:** o GeoServer publica 22 camadas em 3 workspaces: `geosgb` (14), `gestao-territorial` (6) e `hidrogeologia` (2). O OGC API publica 23 coleções. A stack serve 1, com dados fictícios.
- **Nomes:** lá, `geosgb:litoestratigrafia_1m` no WMS e no WFS, e `geologia/litoestratigrafia/1000000` no OGC API, com barras no id. Aqui, `litoestratigrafia` no WMS, `poligonos_opensearch` no WFS e `opensearch_demo` no OGC API.
- **Metadados:** a camada do GeoServer tem resumo e palavras-chave. A do MapProxy tem só título, e `md` em cada camada aceita `abstract`, `keyword_list` e `attribution`.
- **Estilo:** cada camada lá tem o próprio SLD. A stack tem um estilo único no mapfile.
- **Campos da litoestratigrafia 1:1M:**
  - Lá são `ambiente_tectonico` e `sub_ambiente_tectonico`; aqui, `amb_tecto` e `sub_amb_tectonico`.
  - Só a stack tem `fid`, `grupo` e `id_uni_estratigrafica`.
  - `idade_min` e `idade_max` são inteiros lá e `double` aqui.
  - A geometria se chama `geom` lá e `msGeometry` aqui.
- **Volume:** a camada 1:1M tem 46.715 feições, contra 500 da massa de teste. O desempenho com esse volume ainda não foi medido.
- **Publicação:** cada camada precisa da própria fonte no `mapproxy.yaml`, por causa do limite do GeoJSON com várias camadas. Essa regra está no `CLAUDE.md` e ainda não foi testada.
