#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Parser dos XMLs do CAGR-UFSC para JSON. Python 2.7

Uso (na pasta onde está a pasta db/):
    py -2.7-32 parse_turmas.py db/20251_FLO.xml db/20251_JOI.xml db/20251_CBS.xml db/20251_ARA.xml db/20251_BLN.xml 20251_turmas.json

Ou para um campus só:
    py -2.7-32 parse_turmas.py db/20251_FLO.xml saida_FLO.json
"""

from xml.etree import cElementTree
import unicodedata
import datetime
import codecs
import json
import sys
import os
import re

if len(sys.argv) < 3:
    print('uso: %s <arquivo1.xml> [arquivo2.xml ...] <saida.json>' % sys.argv[0])
    sys.exit(1)

NS = '{http://www.w3.org/1999/xhtml}'

def strip_ns(tag):
    return tag.replace(NS, '') if isinstance(tag, basestring) else ''

def get_text(el):
    return (el.text or '').strip()

def get_text_with_br(el):
    partes = []
    t = (el.text or '').strip()
    if t:
        partes.append(t)
    for sub in el:
        tail = (sub.tail or '').strip()
        if tail:
            partes.append(tail)
    return partes

def get_professores(el):
    professores = []
    filhos = list(el)
    if not filhos:
        t = (el.text or '').strip()
        if t:
            professores.append(t)
    for sub in filhos:
        if sub.text and sub.text.strip():
            professores.append(sub.text.strip())
        tail = (sub.tail or '').strip()
        if tail:
            professores.append(tail)
    if not professores:
        t = (el.text or '').strip()
        if t:
            professores.append(t)
    return professores

def find_table_rows(xml):
    rows = []
    _collect_rows(xml, rows)
    return rows

def _collect_rows(el, rows):
    tag = strip_ns(el.tag)
    if tag == 'tr':
        tds = [c for c in el if strip_ns(c.tag) == 'td']
        if len(tds) >= 14:
            rows.append(tds)
            return
    for child in el:
        _collect_rows(child, rows)

def normalize_nome(nome):
    try:
        if isinstance(nome, unicode):
            return unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').upper()
        else:
            return unicodedata.normalize('NFKD', nome.decode('utf-8', 'ignore')).encode('ascii', 'ignore').upper()
    except Exception:
        return (nome or '').upper()

data_str = datetime.datetime.now().strftime('%d/%m/%y - %H:%M')
arquivos_entrada = sys.argv[1:-1]
arquivo_saida    = sys.argv[-1]

outf = codecs.open(arquivo_saida, 'w', encoding='utf-8')
outf.write(u'{\n')
outf.write(u'"DATA":"%s"' % data_str)

for idx, caminho in enumerate(arquivos_entrada):
    if not os.path.exists(caminho):
        print('AVISO: arquivo nao encontrado: %s' % caminho)
        continue

    basename = os.path.splitext(os.path.basename(caminho))[0]
    partes   = basename.split('_')
    campus   = partes[-1] if len(partes) > 1 else basename

    print('Processando campus: %s (%s)' % (campus, caminho))

    with open(caminho, 'r') as inf:
        conteudo = inf.read()

    paginas = re.split(r'<\?xml version="1\.0"\?>', conteudo)

    prev_codigo = None
    cur_materia = None
    materias    = []
    erros       = 0

    for pagina in paginas:
        pagina = pagina.strip()
        if not pagina:
            continue

        xml_str = '<?xml version="1.0"?>' + pagina

        try:
            xml = cElementTree.fromstring(xml_str)
        except Exception as e:
            erros += 1
            if erros <= 3:
                print('  AVISO: erro ao parsear XML: %s' % e)
            continue

        rows = find_table_rows(xml)

        for tds in rows:
            try:
                codigo_disciplina = get_text(tds[3])
                nome_turma        = get_text(tds[4])
                nome_disciplina   = get_text(tds[5])
                for sub in tds[5]:
                    tail = (sub.tail or '').strip()
                    if tail:
                        nome_disciplina = nome_disciplina + ' ' + tail

                def safe_int(el):
                    try:
                        return int(get_text(el))
                    except (ValueError, TypeError):
                        return 0

                horas_aula       = safe_int(tds[6])
                vagas_ofertadas  = safe_int(tds[7])
                vagas_ocupadas   = safe_int(tds[8])
                alunos_especiais = safe_int(tds[9])
                saldo_vagas      = safe_int(tds[10])
                pedidos_sem_vaga = safe_int(tds[11])

                horarios    = get_text_with_br(tds[12])
                professores = get_professores(tds[13])

                if not codigo_disciplina:
                    continue

                if codigo_disciplina != prev_codigo:
                    nome_ascii = normalize_nome(nome_disciplina)
                    if isinstance(nome_disciplina, str):
                        nome_disciplina = nome_disciplina.decode('utf-8', 'ignore')
                    cur_materia = [codigo_disciplina, nome_ascii, nome_disciplina, []]
                    materias.append(cur_materia)
                    prev_codigo = codigo_disciplina

                turma = [nome_turma, horas_aula, vagas_ofertadas, vagas_ocupadas,
                         alunos_especiais, saldo_vagas, pedidos_sem_vaga,
                         horarios, professores]
                cur_materia[3].append(turma)

            except Exception as e:
                erros += 1
                if erros <= 5:
                    print('  AVISO: erro numa linha: %s' % e)

    print('  -> %d disciplinas encontradas' % len(materias))

    outf.write(u',\n')
    outf.write(u'"%s":[\n' % campus)

    for i, materia in enumerate(materias):
        outf.write(json.dumps(materia, ensure_ascii=False, separators=(',', ':')))
        if i < len(materias) - 1:
            outf.write(u',')
        outf.write(u'\n')

    outf.write(u']')

outf.write(u'\n}')
outf.close()

print('\nArquivo salvo em: %s' % arquivo_saida)