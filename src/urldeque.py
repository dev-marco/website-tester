# -*- coding: utf-8 -*-
import copy, urlhttp


class InfiniteRedirection (Exception):

    """ Manage exceptions on loop redirection """

    def __init__ (self, value, urls):
        self.value = value
        self.__urls = urls

    def __repr__ (self):
        return str(self.value)

    def __str__ (self):
        return str(self.value)

    @property
    def urls (self):
        return self.__urls

class URLDeque (object):

    """ Manage HTTPUrls and domains as a queue """

    def ___force_push (self, url, page, *extra, front = False):

        item = ( url, page ) + extra

        if url.address_encoded == self.__address:

            if front:
                queued = [ item, self.__first ]

                if self.empty_domain:
                    self.__last = queued

                self.__first = queued

            else:
                queued = [ item, None ]

                if self.empty_domain:
                    self.__first = queued
                else:
                    self.__last[1] = queued

                self.__last = queued

            self.__size += 1

        else:
            self.__external.setdefault(url.address_encoded, []).append(item)

    def __init__ (self):

        self.__size = 0

        self.__linked = {}
        self.__redirects = {}
        self.__external = {}

        self.__address = None

        self.__first = None
        self.__last = None

    def push_redirect (self, url, page, *extra, front = False):

        redir = url

        road = [ redir ]

        if url == page:
            raise InfiniteRedirection('Infinite url redirection.', road)

        while redir in self.__redirects:
            if self.__redirects[redir] == page:
                raise InfiniteRedirection('Infinite url redirection.', road)
            road.append(redir)
            redir = self.__redirects[redir]
        else:
            self.__redirects[page] = url

            insert = False

            if url not in self.__linked:
                self.__linked[url] = {}
                insert = True

            for location, roads in self.__linked[page].items():
                if not location in self.__linked[url]:
                    self.__linked[url][location] = set()
                for road in roads:
                    self.__linked[url][location].add(road + ( page, ))

            self.__linked[page].clear()

            return insert and self.___force_push(url, page, *extra, front = front)

        return False

    def push (self, url, page, *extra, front = False):

        road = ()

        while url in self.__redirects:
            road += ( url, )
            url = self.__redirects[url]

        insert = False

        if url not in self.__linked:
            self.__linked[url] = {}
            insert = True

        self.__linked[url].setdefault(page, set()).add(road)

        return insert and self.___force_push(url, page, *extra, front = front)

    def pop_url (self):
        item = None

        if not self.empty_domain:
            item, self.__first = self.__first
            self.__size -= 1

        return item

    def change_domain (self, address = None):

        old_domain = []

        while not self.empty_domain:
            old_domain.append(self.pop_url())

        if address is not None:
            try:
                urls = self.__external.pop(address)
            except KeyError:
                urls = []

            self.__address = address
        else:
            self.__address, urls = self.__external.popitem()

        for data in urls:
            self.___force_push(*data)

        for data in old_domain:
            self.___force_push(*data)

    def pop_domain (self, address = None):
        self.clear_domain()
        if not self.empty:
            self.change_domain(address)
        else:
            self.__address = None
        return self.__address

    def clear_domain (self):
        self.__size = 0
        self.__last = self.__first = None
        self.__address = None

    def clear (self):
        self.__external.clear()
        self.clear_domain()

    def references (self, url):
        if url in self.__linked:
            for page in self.__linked[url]:
                yield page

    @property
    def empty_domain (self):
        return self.size_domain is 0

    @property
    def empty (self):
        return self.empty_domain and len(self.__external) is 0

    @property
    def size_domain (self):
        return self.__size

    @property
    def size (self):
        return self.size_domain + sum(map(len, self.__external.values()))

    @property
    def external (self):
        return copy.deepcopy(self.__external)

    def __len__ (self):
        return self.size_domain
