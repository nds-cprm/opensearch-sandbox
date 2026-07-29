import os
import mapnik

# 1. ATIVE O DEBUG para ver o erro real de rede do curl (DNS, timeout, etc)
os.environ['CPL_DEBUG'] = 'ON'

# 2. Force o GDAL a aceitar chamadas HTTP sem travar em validações locais
os.environ['GDAL_HTTP_UNSAFE_TLS'] = 'YES'
os.environ['CPL_ACCUM_ERROR_MSG'] = 'ON'
os.environ['CPL_CURL_VERBOSE'] = 'ON'

# 3. Se sua máquina usa proxy ou alguma rota IPv6/IPv4 confusa no Docker, force IPv4
os.environ['GDAL_HTTP_OPTIONS'] = 'IPRESOLVE=V4'

m = mapnik.Map(800, 600)
mapnik.load_map(m, '/mapproxy/teste.xml')

m.zoom_to_box(mapnik.Box2d(-180.0, -90.0, 180.0, 90.0))
mapnik.render_to_file(m, '/mapproxy/mapa_opensearch.png', 'png')
print("Renderizado!")
