# -*- coding: utf-8 -*-
import xarray, urllib.parse, copy, os


class URLHttp (object):

    """ Manages absolute and relative HTTP urls """

    def __init__ (self, url, force_ssl = False, use_fragment = False, use_query = True, force_absolute = True):

        url = url.strip()

        url_data = urllib.parse.urlsplit(url)

        if not url_data.hostname and force_absolute:
            url_data = urllib.parse.urlsplit(('https://' if force_ssl else 'http://') + url)
            if not url_data.hostname and force_absolute:
                raise ValueError('URL without address with force_absolute enabled.')

        self.__scheme = ''

        if url_data.scheme != 'http' and url_data.scheme != 'https':
            if force_absolute or url_data.scheme:
                raise ValueError('Invalid self.__scheme.')
        else:
            self.__scheme = 'https' if (force_ssl and force_absolute) else url_data.scheme

        self.__username = urllib.parse.unquote_plus(url_data.username or '')
        self.__username_encoded = urllib.parse.quote_plus(self.__username)

        self.__password = urllib.parse.unquote_plus(url_data.password or '')
        self.__password_encoded = urllib.parse.quote_plus(self.__password)

        self.__port = str(url_data.port or '80')

        self.__hostname = url_data.hostname or ''
        self.__hostname_encoded = '.'.join(x.encode('idna').decode('ascii') for x in self.__hostname.split('.')).lower()

        self.__path = url_data.path or ''
        self.__query = (use_query and url_data.query) or ''

        self.__fragment = urllib.parse.unquote_plus((use_fragment and url_data.fragment) or '')
        self.__fragment_encoded = urllib.parse.quote_plus(self.__fragment)

        self.__netloc = self.__netloc_encoded = ''
        self.__address = self.__address_encoded = ''

        if self.__scheme:
            self.__address = self.__scheme + '://'
            self.__address_encoded = self.__address

        if self.__username:
            self.__netloc += self.__username
            self.__netloc_encoded += self.__username_encoded

            if self.__password:
                self.__netloc += ':' + self.__password
                self.__netloc_encoded += ':' + self.__password_encoded

            self.__netloc += '@'
            self.__netloc_encoded += '@'

        self.__netloc += self.__hostname
        self.__netloc_encoded += self.__hostname_encoded

        if self.__port and self.__port != '80':
            self.__netloc += ':' + self.__port
            self.__netloc_encoded += ':' + self.__port

        self.__address += self.__netloc
        self.__address_encoded += self.__netloc_encoded

        if self.__address and (self.__path == '' or self.__path[0] != '/'):
            self.__path = '/' + self.__path

        self.__path = os.path.normpath(self.__path) + ('/' if len(self.__path) > 1 and self.__path[-1] == '/' else '')

        self.__path_split = tuple(map(urllib.parse.unquote_plus, self.__path.split('/')))

        self.__path = '/'.join(self.__path_split)
        self.__path_encoded = '/'.join(map(urllib.parse.quote_plus, self.__path_split))

        if self.__path_split[-1] == '':
            self.__path_split = self.__path_split[ : -1 ]

        self.__parent, self.__file = os.path.split(self.__path)
        self.__parent_encoded, self.__file_encoded = os.path.split(self.__path_encoded)

        if self.__parent == '' or self.__parent[-1] != '/':
            self.__parent += '/'
            self.__parent_encoded += '/'

        self.__request = self.__path
        self.__request_encoded = self.__path_encoded

        self.__query_xarray = xarray.from_query(self.__query)
        self.__query_encoded = self.__query_xarray.query

        if self.__query:
            self.__request += '?' + self.__query
            self.__request_encoded += '?' + self.__query_encoded

        if self.__fragment:
            self.__request += '#' + self.__fragment
            self.__request_encoded += '#' + self.__fragment_encoded

        self.__url = self.__address + self.__request
        self.__url_encoded = self.__address_encoded + self.__request_encoded

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

    def asdict (self):
        return {
        	'scheme': self.scheme, 'username': self.username,
        	'password': self.password, 'hostname': self.hostname,
        	'port': self.port, 'netloc': self.netloc,
        	'address': self.address, 'parent': self.parent,
        	'file': self.file, 'path': self.path,
        	'query': self.query, 'fragment': self.fragment,
        	'request': self.request, 'full': self.full
        }

    @property
    def scheme (self):
        return self.__scheme

    @property
    def username (self):
        return self.__username

    @property
    def username_encoded (self):
        return self.__username_encoded

    @property
    def password (self):
        return self.__password

    @property
    def password_encoded (self):
        return self.__password_encoded

    @property
    def hostname (self):
        return self.__hostname

    @property
    def hostname_encoded (self):
        return self.__hostname_encoded

    @property
    def port (self):
        return self.__port

    @property
    def netloc (self):
        return self.__netloc

    @property
    def netloc_encoded (self):
        return self.__netloc_encoded

    @property
    def address (self):
        return self.__address

    @property
    def address_encoded (self):
        return self.__address_encoded

    @property
    def parent (self):
        return self.__parent

    @property
    def parent_encoded (self):
        return self.__parent_encoded

    @property
    def file (self):
        return self.__file

    @property
    def file_encoded (self):
        return self.__file_encoded

    @property
    def path (self):
        return self.__path

    @property
    def path_encoded (self):
        return self.__path_encoded

    @property
    def query (self):
        return self.__query

    @property
    def query_encoded (self):
        return self.__query_encoded

    @property
    def fragment (self):
        return self.__fragment

    @property
    def fragment_encoded (self):
        return self.__fragment_encoded

    @property
    def request (self):
        return self.__request

    @property
    def request_encoded (self):
        return self.__request_encoded

    @property
    def full (self):
        return self.__url

    @property
    def encoded (self):
        return self.__url_encoded

    @property
    def ssl (self):
        return self.scheme == 'https'

    @property
    def absolute (self):
        return self.address != ''

    @property
    def relative (self):
        return self.address == ''

    @property
    def path_split (self):
        return self.__path_split

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

    def __format__ (self, _):
        return self.full

    def __str__ (self):
        return self.full

    def __repr__ (self):
        return 'urlhttp.URLHttp(' + repr(self.full) + ')'
