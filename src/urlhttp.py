# -*- coding: utf-8 -*-
import xarray, collections, urllib.parse, copy, os


class URLHttp (object):

    """ Manages absolute and relative HTTP urls """

    def __init__ (self, url, force_ssl = False, use_fragment = False, use_query = True, force_absolute = True):

        url = url.strip()

        url_data = urllib.parse.urlsplit(url)

        if not url_data.hostname and force_absolute:
            url_data = urllib.parse.urlsplit(('https://' if force_ssl else 'http://') + url)
            if not url_data.hostname and force_absolute:
                raise ValueError('URL without address with force_absolute enabled.')

        scheme = ''

        if url_data.scheme != 'http' and url_data.scheme != 'https':
            if force_absolute or url_data.scheme:
                raise ValueError('Invalid scheme.')
        else:
            scheme = 'https' if (force_ssl and force_absolute) else url_data.scheme

        username = urllib.parse.unquote_plus(url_data.username or '')
        username_encoded = urllib.parse.quote_plus(username)

        password = urllib.parse.unquote_plus(url_data.password or '')
        password_encoded = urllib.parse.quote_plus(password)

        port = str(url_data.port or '')

        hostname = url_data.hostname or ''
        hostname_encoded = '.'.join(x.encode('idna').decode('ascii') for x in hostname.split('.')).lower()

        path = url_data.path or ''
        query = (use_query and url_data.query) or ''

        fragment = urllib.parse.unquote_plus((use_fragment and url_data.fragment) or '')
        fragment_encoded = urllib.parse.quote_plus(fragment)

        netloc = netloc_encoded = ''
        address = address_encoded = ''

        if scheme:
            address = scheme + '://'
            address_encoded = address

        if username:
            netloc += username
            netloc_encoded += username_encoded

            if password:
                netloc += ':' + password
                netloc_encoded += ':' + password_encoded

            netloc += '@'
            netloc_encoded += '@'

        netloc += hostname
        netloc_encoded += hostname_encoded

        if port:
            netloc += ':' + port
            netloc_encoded += ':' + port

        address += netloc
        address_encoded += netloc_encoded

        if address and (path == '' or path[0] != '/'):
            path = '/' + path

        path = os.path.normpath(path) + ('/' if len(path) > 1 and path[-1] == '/' else '')

        path_split = tuple(map(urllib.parse.unquote_plus, path.split('/')))

        path = '/'.join(path_split)
        path_encoded = '/'.join(map(urllib.parse.quote_plus, path_split))

        if path_split[-1] == '':
            path_split = path_split[ : -1 ]

        parent, fname = os.path.split(path)
        parent_encoded, file_encoded = os.path.split(path_encoded)

        if parent == '' or parent[-1] != '/':
            parent += '/'
            parent_encoded += '/'

        request = path
        request_encoded = path_encoded

        self.__query_xarray = xarray.from_query(query)
        query_encoded = self.__query_xarray.query

        if query:
            request += '?' + query
            request_encoded += '?' + query_encoded

        if fragment:
            request += '#' + fragment
            request_encoded += '#' + fragment_encoded

        url = address + request
        url_encoded = address_encoded + request_encoded

        data_tuple = collections.namedtuple('urlhttp_data', [
            'scheme', 'username', 'username_encoded', 'password', 'password_encoded',
            'hostname', 'hostname_encoded', 'netloc', 'netloc_encoded', 'address', 'address_encoded',
            'parent', 'parent_encoded', 'file', 'file_encoded', 'path', 'path_encoded',
            'query', 'query_encoded', 'fragment', 'fragment_encoded', 'request', 'request_encoded',
            'full', 'encoded', 'path_split', 'ssl', 'absolute', 'relative'
        ])

        self.data = data_tuple(
            scheme, username, username_encoded, password, password_encoded,
            hostname, hostname_encoded, netloc, netloc_encoded, address, address_encoded,
            parent, parent_encoded, fname, file_encoded, path, path_encoded,
            query, query_encoded, fragment, fragment_encoded, request, request_encoded,
            url, url_encoded, path_split, scheme == 'https', address != '', address == ''
        )

    def hyperlink (self, link, **kwargs):

        """
            Returns a new url as a result of an hyperlink inside a page of this url

            Example 1:
                self = http://user:pass@www.example.com:80/foo/bar/baz
                link = ../abc/def?foo=bar
                result = http://user:pass@www.example.com:80/foo/abc/def?foo=bar

            Example 2:
                self = https://www.example.com/
                link = //www2.example.com/foo/bar.php
                result = https://www2.example.com/foo/bar.php
        """

        if self.absolute:

            if not 'force_absolute' in kwargs:
                kwargs['force_absolute'] = False

            url_data = urllib.parse.urlsplit(link)

            if url_data.scheme == '':
                if url_data.netloc == '':
                    if url_data.path != '':
                        if url_data.path[0] == '/':
                            url = URLHttp(self.address + url_data.geturl(), **kwargs)
                        else:
                            url = URLHttp(self.address + self.parent + url_data.geturl(), **kwargs)
                    else:
                        url = URLHttp(self.address + self.path + url_data.geturl(), **kwargs)
                else:
                    query = ('?' + url_data.query) if url_data.query else ''
                    fragment = ('#' + url_data.fragment) if url_data.fragment else ''
                    path = url_data.path or '/'
                    url = URLHttp(self.scheme + '://' + url_data.netloc + path + query + fragment, **kwargs)
            else:
                url = URLHttp(url_data.geturl(), **kwargs)

            return url
        else:
            raise TypeError('Only absolute urls can hyperlink.')

    def __getattribute__ (self, attr):
        if attr != 'data':
            try:
                return self.data.__getattribute__(attr)
            except AttributeError:
                pass
        return object.__getattribute__(self, attr)

    @property
    def query_xarray (self):
        return copy.deepcopy(self.__query_xarray)

    def __eq__ (self, other):
        return (
            ( self.relative or other.relative or self.address == other.address ) and
            self.path == other.path and
            self.query_xarray == other.query_xarray and
            self.fragment == other.fragment
        )

    def __bool__ (self):
        return str(self) != ''

    def __hash__ (self):
        return hash(( self.address, self.path, self.query_xarray ))

    def __str__ (self):
        return self.full

    def __repr__ (self):
        return str(self)
