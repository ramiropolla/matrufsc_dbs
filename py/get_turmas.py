#!/usr/bin/python
# -*- coding: utf-8 -*-

from BeautifulSoup import BeautifulSoup
from xml.etree import cElementTree
from StringIO import StringIO
import cookielib
import urllib2
import urllib
import gzip
import sys
import os

if len(sys.argv) < 2:
    print('usage: %s [semestre]' % sys.argv[0])
    sys.exit(1)

try:
    semestre = sys.argv[1]
except IndexError:
    semestre = '20251'

#opener
jar = cookielib.CookieJar()
opener = urllib2.build_opener(
    urllib2.HTTPCookieProcessor(jar),
    urllib2.HTTPSHandler(debuglevel=0)
)

def add_cookie(name, value, domain):
    jar.set_cookie(cookielib.Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=False,
        path='/',
        path_specified=True,
        secure=True,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={}
    ))


#cole aqui seus cookies
JSESSIONID = 'adicione aqui sua sessão ID cookie'
INGRESSCOOKIE = "adicione aqui sua sessão ID cookie"


add_cookie('JSESSIONID', JSESSIONID, 'cagr.sistemas.ufsc.br')
add_cookie('INGRESSCOOKIE', INGRESSCOOKIE, 'cagr.sistemas.ufsc.br')
add_cookie('JSESSIONID', JSESSIONID, 'sistemas.ufsc.br')
add_cookie('INGRESSCOOKIE', INGRESSCOOKIE, 'sistemas.ufsc.br')

print('Semestre: %s' % semestre)

print('- Acessando Cadastro de Turmas')
resp = opener.open('https://cagr.sistemas.ufsc.br/modules/aluno/cadastroTurmas/')
html = resp.read()

print(html[:500]) 

soup = BeautifulSoup(html)

#checa se o input existe
vs_input = soup.find('input', {'name':'javax.faces.ViewState'})
if vs_input is None:
    print('ERRO: Não foi possível encontrar ViewState. Cheque seus cookies.')
    sys.exit(1)

viewState = vs_input['value']

print('- Pegando banco de dados')

request = urllib2.Request(
    'https://cagr.sistemas.ufsc.br/modules/aluno/cadastroTurmas/index.xhtml'
)
request.add_header('Accept-encoding', 'gzip')

page_form = {
    'AJAXREQUEST': '_viewRoot',
    'formBusca:selectSemestre': semestre,
    'formBusca:selectDepartamento': '',
    'formBusca:selectCampus': '1',
    'formBusca:selectCursosGraduacao': '0',
    'formBusca:codigoDisciplina': '',
    'formBusca:j_id135_selection': '',
    'formBusca:filterDisciplina': '',
    'formBusca:j_id139': '',
    'formBusca:j_id143_selection': '',
    'formBusca:filterProfessor': '',
    'formBusca:selectDiaSemana': '0',
    'formBusca:selectHorarioSemana': '',
    'formBusca': 'formBusca',
    'autoScroll': '',
    'javax.faces.ViewState': viewState,
    'formBusca:dataScroller1': '1',
    'AJAX:EVENTS_COUNT': '1',
}

def find_id(xml, id):
    for x in xml:
        if x.get('id') == id:
            return x
        else:
            y = find_id(x, id)
            if y is not None:
                return y
    return None

def go_on(xml):
    scroller = find_id(xml, 'formBusca:dataScroller1_table')
    if scroller is None:
        return False
    for x in scroller[0][0]:
        onclick = x.get('onclick')
        if onclick is not None and 'next' in onclick:
            return True
    return False

campus_str = ['EaD', 'FLO', 'JOI', 'CBS', 'ARA']
if semestre >= '20141':
    campus_str.append('BLN')

#cria pasta db
if not os.path.exists('db'):
    os.makedirs('db')

for campus in range(1, len(campus_str)):
    print('Campus: ' + campus_str[campus])
    outfile = open('db/{}_{}.xml'.format(semestre, campus_str[campus]), 'w')
    page_form['formBusca:selectCampus'] = campus
    pagina = 1
    while True:
        print('  Página %02d' % pagina)
        page_form['formBusca:dataScroller1'] = pagina
        resp = opener.open(request, urllib.urlencode(page_form))
        if resp.info().get('Content-Encoding') == 'gzip':
            buf = StringIO(resp.read())
            f = gzip.GzipFile(fileobj=buf)
            data = f.read()
        else:
            data = resp.read()
        outfile.write(data)
        xml = cElementTree.fromstring(data)
        if not go_on(xml):
            break
        pagina += 1
    outfile.close()

print('Banco de dados salvo na pasta db')