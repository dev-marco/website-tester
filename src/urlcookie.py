# -*- coding: utf-8 -*-
import time, http.cookiejar, urllib.parse, os, re, email.message, copy
import itertools as it


class URLHeader (object):

    def __init__ (self, *args, **kwargs):

        self.size = 0
        self.__message = email.message.Message()
        self.set(*args, **kwargs)

    def set (self, *args, **kwargs):
        for arg, val in it.chain(args, kwargs.items()):
            self[arg] = val
            self.size += 1

    def __setitem__ (self, arg, val):
        self.__message[arg] = val

    def __getitem__ (self, arg):
        return self.__message.get_all(arg)

    def __len__ (self):
        return self.size

    def info (self):
        return copy.deepcopy(self.__message)

class Cookie (object):

    def __init__ (self, name, value, domain, path = '/', expires = None, maxage = None, httponly = False, secure = False, **kwargs):

        self.__name = name
        self.__value = value
        self.__domain = '.'.join(x.encode('idna').decode('ascii') for x in domain.lstrip('.').split('.'))
        self.__path = urllib.parse.unquote_plus(os.path.normpath(path))
        self.__httponly = httponly
        self.__secure = secure
        self.__extra = kwargs

        if maxage is not None:
            try:
                self.__expires = time.time() + float(maxage)
            except ValueError:
                maxage = None

        if maxage is None and isinstance(expires, str):
            for time_format in Cookie.time_formats:
                try:
                    expires_str = time.strptime(expires, time_format)
                except ValueError:
                    pass
                else:
                    self.__expires = time.mktime(expires_str)
                    break
            else:
                self.__expires = None
        else:
            self.__expires = expires

        self.__expires_format = time.strftime(Cookie.time_formats[0], time.gmtime(self.__expires or 0))

    def match (self, scheme, domain, path, test_expired = True, test_secure = True):
        if not test_expired or self.session or not self.expired:
            if not test_secure or scheme == 'https' or not self.secure:
                if self.path == path or ( path.startswith(self.path) and ( self.path[-1] == '/' or path[ len(self.path) ] == '/' ) ):
                    if self.domain == domain or ( domain.endswith(self.domain) and domain[ -(len(self.domain) + 1) ] == '.' ):
                        hn = Cookie.match_domain_hostname.fullmatch(domain)
                        return hn is not None and hn.group(1) is not None
        return False

    def copy (self):
        return copy.deepcopy(self)

    @property
    def name (self):
        return self.__name

    @property
    def value (self):
        return self.__value

    @property
    def domain (self):
        return self.__domain

    @property
    def path (self):
        return self.__path

    @property
    def expires (self):
        return self.__expires

    @property
    def httponly (self):
        return self.__httponly

    @property
    def secure (self):
        return self.__secure

    @property
    def extra (self):
        return self.__extra.copy()

    @property
    def expires_format (self):
        return self.__expires_format

    @property
    def session (self):
        return self.expires is None

    @property
    def expired (self):
        return not self.session and time.time() > self.__expires

    def __bool__ (self):
        return not self.expired

    def __eq__ (self, other):
        try:
            return (
                self.name == other.name and
                self.domain == other.domain and
                self.path == other.path and
                self.secure == other.secure and
                self.httponly == other.httponly
            )
        except AttributeError:
            return False

    def __hash__ (self):
        return hash(( self.path, self.name, self.domain, self.secure, self.httponly ))

    def __str__ (self):
        return '{0}={1}'.format(urllib.parse.quote_plus(self.name), urllib.parse.quote_plus(self.value))

    def __repr__ (self):
        result = '{0}; Path={1}; Domain={2}'.format(self, self.path, self.domain)

        if not self.session:
            if not self.expired:
                result += '; Max-Age={0}'.format(int(self.expires - time.time()))
            result += '; Expires={0}'.format(self.expires_format)

        if self.httponly:
            result += '; HttpOnly'

        if self.secure:
            result += '; Secure'

        return result

Cookie.match_domain_hostname = re.compile(r'(?:([a-z])|[0-9\-.]){1,253}')

Cookie.time_formats = [
    '%a, %d %b %Y %H:%M:%S %Z', # RFC1123
    '%a, %d-%b-%Y %H:%M:%S %Z', # PHP (WHY???)
    '%A, %d-%b-%y %H:%M:%S %Z', # RFC850 (2016 == 1016)
    '%a %b %d %H:%M:%S %Z %Y'   # C
]

class CookieJar (object):

    @classmethod
    def client_header (_, cookies):
        data = '; '.join(map(str, cookies))
        return ('Cookie: ' + data) if data != '' else ''

    @classmethod
    def server_header (_, cookies):
        return '\r\n'.join(('Set-Cookie: ' + repr(x)) for x in cookies)

    def __init__ (self, url = None, *args, **kwargs):

        self.__cookies = kwargs.pop('_initial_cookies', set())

        if url is not None and ( len(args) or len(kwargs) ):
            self.set(url, *args, **kwargs)

    def add_cookie (self, cookie):
        self.__cookies.discard(cookie)
        self.__cookies.add(cookie)

    def set (self, url, *args, **kwargs):

        header = URLHeader()

        url_data = urllib.parse.urlsplit(url)
        domain = url_data.hostname or ''
        path = url_data.path or '/'
        scheme = url_data.scheme or ''

        for name, value in kwargs.items():
            self.add_cookie(Cookie(name, value, domain, path))

        for data in args:
            cookie = filter(bool, (value.strip() for value in data.split(';')))
            name, value = next(cookie).split('=', 1)

            params = { str(p_name).lower(): p_value for p_name, p_value in (
                it.islice(it.chain(x.split('=', 1), it.repeat('')), 0, 2) for x in cookie
            ) }

            params.setdefault('domain', domain)
            params.setdefault('path', path)

            result = Cookie(name, value, **params)

            if params['domain'].lstrip('.') == domain:
                self.add_cookie(result)
            elif result.match(scheme, domain, path, test_expired = False, test_secure = False):
                header.set(( 'Set-Cookie', data ))

        if len(header):
            jar = http.cookiejar.CookieJar()
            jar.extract_cookies(header, urllib.request.Request(url))

            for cookie in jar:
                self.add_cookie(Cookie(cookie.name, cookie.value, cookie.domain, cookie.path, cookie.expires))

    def clear_expired (self):
        self.__cookies = set(filter(bool, self.__cookies))

    def clear_session (self):
        self.__cookies = set(c for c in self.__cookies if not c.session)

    def match (self, scheme, domain, path, **kwargs):
        for cookie in self.__cookies:
            if cookie.match(scheme, domain, path, **kwargs):
                yield cookie

    def match_url (self, url, **kwargs):
        url_data = urllib.parse.urlsplit(url)
        return self.match(url_data.scheme, url_data.domain, url_data.path, **kwargs)

    def copy (self):
        return copy.deepcopy(self)

    @property
    def cookies (self):
        return self.__cookies.copy()

    def __or__ (self, other):
        cookies = set()

        for cookie in it.chain(self.__cookies, other.__cookies):
            if cookie not in cookies:
                cookies.add(cookie)

        return CookieJar(_initial_cookies = cookies)

    def __len__ (self):
        return len(self.__cookies)

    def __bool__ (self):
        return len(self) > 0

    def __str__ (self):
        return CookieJar.client_header(self.__cookies)

    def __repr__ (self):
        return CookieJar.server_header(self.__cookies)

    def __iter__ (self):
        return iter(self.__cookies)
