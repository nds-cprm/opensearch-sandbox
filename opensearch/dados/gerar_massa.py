#!/usr/bin/env python3
"""Gera uma massa de teste de litoestratigrafia e carrega no OpenSearch.

Os dados são fictícios: a grade de polígonos cobre o bbox do Brasil, mas nomes,
siglas e geometrias não representam nenhuma unidade real. Sementes iguais geram
exatamente os mesmos documentos.

    python3 opensearch/dados/gerar_massa.py
    python3 opensearch/dados/gerar_massa.py --registros 5000 --recriar
"""
import argparse
import json
import math
import random
import sys
import urllib.error
import urllib.request

# mesmo bbox de gis/pygeoapi/local.config.yml
OESTE, SUL, LESTE, NORTE = -73.9872, -33.7684, -28.6341, 5.2843

# nomes usados por gis/mapserver/default.map e gis/pygeoapi/local.config.yml
INDICE = 'litoestratigrafia_1m_20260728_192458'
ALIAS = 'litoestratigrafia_1m'

# segmentos por lado de cada célula: aumente para geometrias mais pesadas
VERTICES_POR_LADO = 8
# fração do passo: abaixo de 0.5 os vértices não se cruzam
RUIDO = 0.35
# um a cada N documentos vira MultiPolygon
INTERVALO_MULTI = 10
TAMANHO_LOTE = 500

TEXTO = {'type': 'text', 'fields': {'raw': {'type': 'keyword', 'ignore_above': 256}}}
CAMPOS_TEXTO = (
    'sigla', 'hierarquia', 'nome', 'amb_tecto', 'sub_amb_tectonico',
    'sigla_pai', 'nome_pai', 'legenda', 'escala', 'mapa', 'litotipos', 'range',
    'eon_min', 'eon_max', 'era_min', 'era_max', 'sistema_min', 'sistema_max',
    'epoca_min', 'epoca_max', 'siglas_historicas', 'grupo',
)

# (idade mínima, idade máxima, éon, era, sistema, época), da mais nova à mais antiga
PERIODOS = [
    (0.0, 2.58, 'Fanerozoico', 'Cenozoico', 'Quaternário', 'Pleistoceno'),
    (5.33, 23.03, 'Fanerozoico', 'Cenozoico', 'Neógeno', 'Mioceno'),
    (33.9, 56.0, 'Fanerozoico', 'Cenozoico', 'Paleógeno', 'Eoceno'),
    (100.5, 145.0, 'Fanerozoico', 'Mesozoico', 'Cretáceo', 'Inferior'),
    (145.0, 163.5, 'Fanerozoico', 'Mesozoico', 'Jurássico', 'Superior'),
    (272.95, 298.9, 'Fanerozoico', 'Paleozoico', 'Permiano', 'Cisuraliano'),
    (393.3, 419.2, 'Fanerozoico', 'Paleozoico', 'Devoniano', 'Inferior'),
    (538.8, 635.0, 'Proterozoico', 'Neoproterozoico', 'Ediacarano', ''),
    (1200.0, 1400.0, 'Proterozoico', 'Mesoproterozoico', 'Ectasiano', ''),
    (2050.0, 2300.0, 'Proterozoico', 'Paleoproterozoico', 'Riaciano', ''),
    (2500.0, 2800.0, 'Arqueano', 'Neoarqueano', '', ''),
]

HIERARQUIAS = ['Formação', 'Grupo', 'Suíte', 'Complexo', 'Membro']
NOMES = ['Alfa', 'Beta', 'Gama', 'Delta', 'Épsilon', 'Zeta', 'Eta', 'Teta']
AMBIENTES = [
    ('Bacia sedimentar', 'Bacia intracratônica'),
    ('Bacia sedimentar', 'Rifte'),
    ('Orógeno', 'Arco magmático'),
    ('Orógeno', 'Faixa de dobramentos'),
    ('Cráton', 'Greenstone belt'),
    ('Cráton', 'Embasamento'),
]
LITOTIPOS = [
    'Arenito', 'Argilito', 'Basalto', 'Calcário', 'Conglomerado', 'Filito',
    'Folhelho', 'Gnaisse', 'Granito', 'Quartzito', 'Siltito', 'Xisto',
]


def gerar_vertices(colunas, linhas, semente):
    """Ruído por vértice da grade fina, compartilhado entre células vizinhas."""
    rng = random.Random(semente)
    largura = (LESTE - OESTE) / (colunas * VERTICES_POR_LADO)
    altura = (NORTE - SUL) / (linhas * VERTICES_POR_LADO)
    vertices = {}
    for i in range(colunas * VERTICES_POR_LADO + 1):
        for j in range(linhas * VERTICES_POR_LADO + 1):
            x = OESTE + i * largura + rng.uniform(-RUIDO, RUIDO) * largura
            y = SUL + j * altura + rng.uniform(-RUIDO, RUIDO) * altura
            vertices[i, j] = [round(x, 6), round(y, 6)]
    return vertices


def anel(vertices, coluna, linha):
    """Contorno da célula em sentido anti-horário, fechado no primeiro vértice."""
    i, j = coluna * VERTICES_POR_LADO, linha * VERTICES_POR_LADO
    n = VERTICES_POR_LADO
    indices = (
        [(i + k, j) for k in range(n)]
        + [(i + n, j + k) for k in range(n)]
        + [(i + n - k, j + n) for k in range(n)]
        + [(i, j + n - k) for k in range(n)]
    )
    pontos = [vertices[v] for v in indices]
    return pontos + [pontos[0]]


def gerar_unidades(rng, total=40):
    unidades = []
    for numero in range(1, total + 1):
        hierarquia = rng.choice(HIERARQUIAS)
        nome = f'{hierarquia} {rng.choice(NOMES)} {numero} (teste)'
        indice = rng.randrange(len(PERIODOS))
        minimo = PERIODOS[indice]
        maximo = PERIODOS[min(indice + rng.randint(0, 1), len(PERIODOS) - 1)]
        ambiente, sub_ambiente = rng.choice(AMBIENTES)
        sigla = f'T{numero:02d}{minimo[3][:2].lower()}'
        pai = rng.randint(1, 8)
        unidades.append({
            'id_uni_estratigrafica': 9000 + numero,
            'sigla': sigla,
            'hierarquia': hierarquia,
            'nome': nome,
            'amb_tecto': ambiente,
            'sub_amb_tectonico': sub_ambiente,
            'sigla_pai': f'TP{pai}',
            'nome_pai': f'Supergrupo Teste {pai}',
            'legenda': f'{sigla} - {nome}',
            'escala': '1:1.000.000',
            'mapa': 'Massa de teste (dados fictícios)',
            'litotipos': ', '.join(sorted(rng.sample(LITOTIPOS, 3))),
            'range': f'{minimo[0]} - {maximo[1]} Ma',
            'idade_min': minimo[0],
            'idade_max': maximo[1],
            'eon_min': minimo[2],
            'eon_max': maximo[2],
            'era_min': minimo[3],
            'era_max': maximo[3],
            'sistema_min': minimo[4],
            'sistema_max': maximo[4],
            'epoca_min': minimo[5],
            'epoca_max': maximo[5],
            'siglas_historicas': f'T{numero:02d}a, T{numero:02d}b',
            'grupo': f'Grupo Teste {pai}',
        })
    return unidades


def gerar_documentos(registros, semente):
    rng = random.Random(semente)
    unidades = gerar_unidades(rng)

    # células a mais para compensar as consumidas pelos MultiPolygons
    celulas = max(math.ceil(registros * (1 + 1.5 / INTERVALO_MULTI)), 9)
    lado = math.sqrt((LESTE - OESTE) * (NORTE - SUL) / celulas)
    colunas = max(math.ceil((LESTE - OESTE) / lado), 3)
    linhas = max(math.ceil((NORTE - SUL) / lado), 1)
    vertices = gerar_vertices(colunas, linhas, semente)

    usadas = set()
    fid = 0
    for linha in range(linhas):
        for coluna in range(colunas):
            if (coluna, linha) in usadas:
                continue
            if fid == registros:
                return
            fid += 1
            parceira = (coluna + 2, linha)
            if (fid % INTERVALO_MULTI == 0 and coluna + 2 < colunas
                    and parceira not in usadas):
                usadas.add(parceira)
                geometria = {
                    'type': 'MultiPolygon',
                    'coordinates': [
                        [anel(vertices, coluna, linha)],
                        [anel(vertices, *parceira)],
                    ],
                }
            else:
                geometria = {
                    'type': 'Polygon',
                    'coordinates': [anel(vertices, coluna, linha)],
                }
            yield {
                'type': 'Feature',
                'id': fid,
                'geometry': geometria,
                'properties': {'fid': fid, **rng.choice(unidades)},
            }


def requisitar(url, metodo='GET', corpo=None, tipo='application/json'):
    requisicao = urllib.request.Request(url, data=corpo, method=metodo)
    if corpo is not None:
        requisicao.add_header('Content-Type', tipo)
    try:
        with urllib.request.urlopen(requisicao, timeout=120) as resposta:
            return json.load(resposta)
    except urllib.error.HTTPError as erro:
        sys.exit(f'{metodo} {url}: {erro.code} {erro.read().decode()[:500]}')


def indice_existe(url):
    requisicao = urllib.request.Request(url, method='HEAD')
    try:
        urllib.request.urlopen(requisicao, timeout=30)
    except urllib.error.HTTPError as erro:
        if erro.code == 404:
            return False
        raise
    return True


def criar_indice(base, indice, alias):
    propriedades = {campo: TEXTO for campo in CAMPOS_TEXTO}
    propriedades.update({
        'fid': {'type': 'long'},
        'id_uni_estratigrafica': {'type': 'long'},
        'idade_min': {'type': 'float'},
        'idade_max': {'type': 'float'},
    })
    corpo = {
        'mappings': {'properties': {
            'type': {'type': 'keyword'},
            'id': {'type': 'long'},
            'geometry': {'type': 'geo_shape'},
            'properties': {'properties': propriedades},
        }},
        'aliases': {alias: {}},
    }
    requisitar(f'{base}/{indice}', 'PUT', json.dumps(corpo).encode())


def enviar_lote(base, indice, lote):
    linhas = []
    for documento in lote:
        linhas.append(json.dumps({'index': {'_id': documento['id']}}))
        linhas.append(json.dumps(documento, ensure_ascii=False))
    corpo = ('\n'.join(linhas) + '\n').encode()
    resposta = requisitar(f'{base}/{indice}/_bulk', 'POST', corpo, 'application/x-ndjson')
    if resposta['errors']:
        falhas = [i['index']['error'] for i in resposta['items'] if 'error' in i['index']]
        sys.exit(f'{len(falhas)} documentos rejeitados, primeiro erro: {falhas[0]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--url', default='http://localhost:9200')
    parser.add_argument('--registros', type=int, default=500)
    parser.add_argument('--semente', type=int, default=42)
    parser.add_argument('--indice', default=INDICE)
    parser.add_argument('--alias', default=ALIAS)
    parser.add_argument('--recriar', action='store_true',
                        help='apaga o índice antes de carregar')
    args = parser.parse_args()

    base = args.url.rstrip('/')
    if indice_existe(f'{base}/{args.indice}'):
        if not args.recriar:
            sys.exit(f'{args.indice} já existe: use --recriar para substituí-lo')
        requisitar(f'{base}/{args.indice}', 'DELETE')
    criar_indice(base, args.indice, args.alias)

    lote = []
    enviados = 0
    for documento in gerar_documentos(args.registros, args.semente):
        lote.append(documento)
        if len(lote) == TAMANHO_LOTE:
            enviar_lote(base, args.indice, lote)
            enviados += len(lote)
            lote = []
    if lote:
        enviar_lote(base, args.indice, lote)
        enviados += len(lote)

    requisitar(f'{base}/{args.indice}/_refresh', 'POST')
    total = requisitar(f'{base}/{args.indice}/_count')['count']
    print(f'{enviados} enviados, {total} no índice {args.indice} (alias {args.alias})')


if __name__ == '__main__':
    main()
