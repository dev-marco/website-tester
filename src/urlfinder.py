# -*- coding: utf-8 -*-
import re, html.parser, urlutils, abc


class URLFinder (object, metaclass = abc.ABCMeta):

    def _start (self, code, canonical, charset):
        charset = charset.lower()
        self.__code = code
        self.__canonical = canonical
        self.__charset = charset

    def _change_charset (self, value, force_decode = False):
        value = value.lower()

        if value != self.charset or force_decode:
            self._start(self.__code.encode(self.charset).decode(value, errors = 'ignore'), self.__canonical, value)
            return True

        return False

    def __init__ (self, code, canonical, charset):
        self._start(code, canonical, charset)

    @property
    def charset (self):
        return self.__charset

    @property
    def code (self):
        return self.__code

    @property
    def canonical (self):
        return self.__canonical

    @property
    @abc.abstractmethod
    def urls (self): pass

    def __iter__ (self):
        return iter(self.urls)

class URLFinderCSS (URLFinder):

    def _start (self, code, canonical, charset):
        super()._start(code, canonical, charset)

        self.__urls = set()
        self.__imports = []

    def __init__ (self, code, canonical, charset = 'iso-8859-1'):

        super().__init__(code, canonical, charset)

        match_charset = URLFinderCSS.match_css_charset.search(code)

        if match_charset is not None:
            self._change_charset(match_charset.group(2))

        for match in URLFinderCSS.match_css_url.finditer(self.code):
            try:
                url = canonical.hyperlink(match.group(4).strip())
            except ValueError:
                pass
            else:
                self.__urls.add(url)
                if match.group(1) == '@import':
                    self.__imports.append(url)

    @property
    def urls (self):
        return self.__urls

    @property
    def imports (self):
        return self.__imports

URLFinderCSS.match_css_url = re.compile(r'(?:(@import)[ \t]+|(url\([ \t]*?)){1,2}(["\'])((?:\\{2})*|(?:.*?[^\\](?:\\{2})*))\3(?(2)[ \t]*?\)|)')
URLFinderCSS.match_css_charset = re.compile(r'@charset[ \t]+(["\'])((?:\\{2})*|(?:.*?[^\\](?:\\{2})*))\1')

class URLFinderHTML (URLFinder, html.parser.HTMLParser):

    def _start (self, code, canonical, charset):

        html.parser.HTMLParser.__init__(self)
        URLFinder._start(self, code, canonical, charset)

        self.__urls = []

        self.__elements = []
        self.__open_elements = []

        self.__forms = {}
        self.__active_forms = []

        self.__tags = {}

        self.__new_charset = self.charset
        self.feed(self.code)

        if self.__new_charset != self.charset:
            self._change_charset(self.__new_charset)

    def __init__ (self, code, canonical, charset = 'iso-8859-1'):
        URLFinder.__init__(self, code, canonical, charset)

    def handle_starttag (self, tag, tuple_attrs):

        urls = {}

        form_owner = None

        attrs = {}
        element = { 'tag': tag, 'children': [] }

        for attr, value in tuple_attrs:

            attrs.setdefault(attr, value)

            if attr == 'href' or attr == 'src':
                try:
                    urls[attr] = [ ( self.canonical.hyperlink(value.strip()), element ) ]
                except ValueError:
                    pass

            elif attr == 'style':
                urls.setdefault('style', [])

                for url in URLFinderCSS(value, self.canonical):
                    urls['style'].append( ( url, element ) )

            elif tag == 'meta':

                refresh = None
                http_equiv = attrs.get('http-equiv', '').lower()

                if attr == 'content' and http_equiv == 'refresh':
                    refresh = value
                elif attr == 'http-equiv' and http_equiv == 'refresh':
                    refresh = attrs.get('content', None)

                if refresh is not None:
                    for data in refresh.split(';'):
                        data = data.strip()

                        if not data.isdigit():
                            pieces = data.split('=')
                            if pieces[0].lower() == 'url':
                                data = pieces[1]
                            else:
                                data = pieces[0]
                            try:
                                if data[0] == "'" or data[0] == '"':
                                    data = URLFinderHTML.match_inside_quotes(data).group(2)
                                urls['content'] = [ ( self.canonical.hyperlink(data), element ) ]
                            except ValueError:
                                pass
                else:
                    charset = None

                    if attr == 'content' and http_equiv == 'charset':
                        charset = value

                    elif attr == 'content' and http_equiv == 'content-type':
                        charset = urlutils.content_split(value).get('charset', None)

                    elif attr == 'http-equiv' and http_equiv == 'charset':
                        charset = attrs.get('content', None)

                    elif attr == 'http-equiv' and http_equiv == 'content-type':
                        charset = urlutils.content_split(attrs.get('content', '')).get('charset', None)

                    if charset is not None:
                        self.__new_charset = charset.lower()

        element['attrs'] = attrs

        self.__elements.append(element)
        self.__tags.setdefault(tag, []).append(element)

        if len(self.__open_elements):
            self.__open_elements[0]['children'].append(element)

        self.__open_elements.append(element)

        if tag == 'form':

            tag_id = attrs.get('id')
            element['form'] = []

            if tag_id not in self.__forms:
                self.__forms[tag_id] = [ element ]
            else:
                self.__forms[tag_id].append(element)

            self.__active_forms.append(element)

        tag_name = attrs.get('name')

        if tag_name is not None and len(self.__active_forms):
            for form in self.__active_forms:
                form['form'].append(element)

        form_owner = attrs.get('form')

        if form_owner is not None:
            if form_owner in self.__forms:
                self.__forms[form_owner]['form'].append(element)

        for attr, links in urls.items():
            for url, tag in links:
                self.__urls.append(( url, element, attr ))

    def handle_endtag (self, tag):
        tag = tag.strip()

        if tag == 'form':
            if len(self.__active_forms):
                self.__active_forms.pop()

        for i, element in enumerate(reversed(self.__open_elements)):
            if element['tag'] == tag:
                index = len(self.__open_elements) - i - 1
                self.__open_elements.pop(index)
                break

    def by_tag (self, tag):
        if tag in self.__tags:
            for element in self.__tags[tag]:
                yield element

    def forms (self):
        for forms in self.__forms.values():
            for form in forms:
                yield form

    @property
    def urls (self):
        return self.__urls

    @property
    def elements (self):
        return self.__elements

URLFinderHTML.match_inside_quotes = re.compile(r'(["\'])((?:\\{2})*|(?:.*?[^\\](?:\\{2})*))\1')
