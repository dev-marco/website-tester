# -*- coding: utf-8 -*-
import os, re, sys, socket, unicodedata
import http.client
import urllib.robotparser
import itertools as it


class URLException (Exception):

    def __init__ (self, value):
        self.value = value

    def __str__ (self):
        return str(self.value)

    def __repr__ (self):
        return str(self)

def fetch_robots (url):
    robots = urllib.robotparser.RobotFileParser(url.hyperlink('/robots.txt').encoded)

    try:
        robots.read()
    except ( urllib.error.URLError, ConnectionError ):
        robots = None

    return robots

def parse_headers (headers):
    result = {}

    for key, val in headers:
        key = key.lower()
        result.setdefault(key, []).append(val)

    return result

def make_request (conn, method, url, max_attempts = 0, attempt = 0, **kwargs):

    try:
        conn.request(method, url, **kwargs)
        rep = conn.getresponse()
    except ( socket.error, ConnectionError, ValueError, http.client.BadStatusLine ) as exc:

        if sys.version_info < ( 3, 5 ) or not isinstance(exc, ConnectionError):
            conn.close()

            try:
                conn.connect()
            except socket.error:
                pass

        if attempt >= max_attempts:
            return ( None, str(exc) )

        return make_request(conn, method, url, max_attempts, attempt + 1, **kwargs)

    return rep, rep.read()

def content_split (content):
    return dict(
        it.islice(it.chain(val.strip().lower().split('=', 1), it.repeat('')), 0, 2)
        for val in filter(bool, content.split(';'))
    )

def make_gnu_error (message):

    text = ''

    if 'firstLine' not in message and 'lastLine' in message:
        message['firstLine'] = message['lastLine']
        message.pop('lastLine', None)

    if 'firstColumn' not in message and 'lastColumn' in message:
        message['firstColumn'] = message['lastColumn']
        message.pop('lastColumn', None)

    if 'firstLine' in message:
        text += '{0}'.format(message['firstLine'])
        if 'firstColumn' in message:
            text += '.'
        elif 'lastLine' in message or 'lastColumn' in message:
            text += '-'

    if 'firstColumn' in message:
        text += '{0}'.format(message['firstColumn'])
        if 'lastLine' in message or 'lastColumn' in message:
            text += '-'

    if 'lastLine' in message:
        text += '{0}'.format(message['lastLine'])
        if 'lastColumn' in message:
            text += '.'

    if 'lastColumn' in message:
        text += '{0}'.format(message['lastColumn'])
    return text

def normalize_filename (name):
    return normalize_filename.non_word.sub('_', unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')).strip()

normalize_filename.non_word = re.compile(r'[^\w_.,-]')

def normalize_filepath (name):
    return os.path.normpath('/'.join(normalize_filename(p) for p in name.split('/')))

def compile_rule (rule, urls = []):
    if '[%url%]' in rule:
        return [ re.compile(rule.replace('[%url%]', re.escape(url.netloc))) for url in urls ]
    return [ re.compile(rule) ]

def read_rules (name, urls = []):

    rules = []

    with open(name, 'r', encoding = 'utf-8') as rules_file:
        for line in rules_file:
            line = line.rstrip('\n\r')
            if line[0] != '#':
                rules.extend(compile_rule(line, urls))

    return rules
