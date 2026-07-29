# opensearch-sandbox
Laboratório de ensaios para o uso de OpenSearch como fonte de dados GIS


## Versões avaliadas: 
- 2.12.0 [(Versão homologada pela ESRI)](https://doc.esri.com/en/arcgis-pro/latest/help/data/databases/database-reqs-opensearch.html)
- 2.19.6 [(Últiva versão estável de 2.x)](https://opensearch.org/releases/)

## Clientes esperados
- **ArcGIS 12.x**: Exposição de indices como FeatureLayers. 
- **Apache Airflow**, para processamento de pipelines dos bacnos corporativos para o OpenSearch.
- **Mapserver**, para a estilização dos mapas e fonte para WFS (Considerando depreciar para usar OGC API Features)
- **MapProxy**, para disponibilização de serviços cacheados de WMS, WMS-C, WMTS e KML - Lidos a partir do **MapServer**.
- **PyGeoAPI**, para serviços de OGC API Features, Maps, Coverages e Tiles.


## Usar em modo de compatibilidade 
Para funcionar no GDAL, é preciso habilitar o modo de compatibilidade para o ElastiSearch 7.x
Há duas formas de fazer isso:

A primeira é em bash, rodando direto no curl
```bash
curl -X PUT "https://localhost:9200/_cluster/settings" \
     -u "admin:sua_senha_aqui" \
     -k \
     -H 'Content-Type: application/json' \
     -d '{
       "persistent": {
         "compatibility": {
           "override_main_response_version": true
         }
       }
     }'
```

A segunda é usando esta entrada em opensearch.sxml
```yaml
compatibility.override_main_response_version: true
```

Referência: https://aws.amazon.com/pt/blogs/opensource/keeping-clients-of-opensearch-and-elasticsearch-compatible-with-open-source/
