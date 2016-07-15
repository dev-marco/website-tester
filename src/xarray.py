# -*- coding: utf-8 -*-
import collections, copy, threading, itertools, re, urllib.parse


class xArray (object):

    @staticmethod
    def __isDict (value):
        return isinstance(value, dict) or isinstance(value, collections.UserDict)

    @staticmethod
    def __isList (value):
        return isinstance(value, list) or isinstance(value, collections.UserList)

    @staticmethod
    def __isSet (value):
        return isinstance(value, set)

    @staticmethod
    def __isTuple (value):
        return isinstance(value, tuple)

    @staticmethod
    def __isXArray (value):
        return isinstance(value, xArray)

    @staticmethod
    def __quoteQuery (query, wrap):
        return urllib.parse.quote_plus(('[{0}]' if wrap else '{0}').format(query))

    @staticmethod
    def __queryTuple (key, val, accum):
        return xArray.__toQuery(data = val, _first = False, _accum = accum)

    @staticmethod
    def __toQuery (data, _first = True, _accum = ''):
        if xArray.__isXArray(data) or xArray.__isDict(data):
            return '&'.join(xArray.__queryTuple(key, val, _accum + xArray.__quoteQuery(key, not _first)) for key, val in data.items())
        elif xArray.__isList(data) or xArray.__isTuple(data) or xArray.__isSet(data):
            return '&'.join(xArray.__queryTuple(key, val, _accum + xArray.__quoteQuery(key, not _first)) for key, val in enumerate(data))
        return _accum + '=' + xArray.__quoteQuery(str(data), False)

    @staticmethod
    def fromQuery (query):
        result = xArray(convert_str = True)
        for value in query.split('&'):

            indexes = []
            arg, val = (value + '=').split('=', 1)

            arg = urllib.parse.unquote_plus(arg)
            val = urllib.parse.unquote_plus(val)

            match_arrays = xArray.query_match_arrays.search(arg)

            if match_arrays is not None:
                start, end = match_arrays.span()
                arrays = arg[ start : end ]
                arg = arg[ : start ]

                start = 1

                while True:

                    end = arrays.find(']', start)

                    if end < 0:
                        break

                    indexes.append(arrays[ start : end ] if start < end else None)
                    start = end + 2

            result.set(val[ : -1 ], arg, *indexes)
        return result

    @staticmethod
    def recursivePack (data):
        data_type = type(data)
        if xArray.__isDict(data):
            result = []
            for key in sorted(data):
                result.append(xArray.recursivePack( ( key, data[key] ) ))
            data = tuple(result)
        elif xArray.__isList(data) or xArray.__isSet(data) or xArray.__isTuple(data):
            result = []
            for value in data:
                result.append(xArray.recursivePack(value))
            data = tuple(result)
        elif xArray.__isXArray(data):
            data = data.__pack()
        return ( data_type, data )

    def __enter__ (self):
        self.__sync_lock.acquire()
        if self.__sync:
            self.__data_lock.acquire()
        return self

    def __exit__ (self, _, __, ___):
        if self.__sync:
            self.__data_lock.release()
        self.__sync_lock.release()
        return False

    def __getIndex (self, key, get_used = False):
        key_type = type(key)
        key_used = key

        if self.__str2int and key_type is str:
            try:
                if self.__float2int:
                    key_used = float(key)
                key_used = int(key_used)
            except ValueError:
                pass
            else:
                key_type = int
        elif self.__float2int and key_type is float:
            key_used = int(key)
            key_type = int

        if key_type in self.__local_registered_types:
            index = self.__local_registered_types[key_type](key_used)
        elif key_type in xArray.default_registered_types:
            index = xArray.default_registered_types[key_type](key_used)
        else:
            index = key_used

        return ( index, key_type, key_used ) if get_used else ( index, key_type )

    def __pack (self):
        return xArray.recursivePack( self.__getState() )

    def __setState (self, data, reg_types, index):
        with self:
            self.__data = data
            self.__local_registered_types = reg_types
            self.__next = index

    def __setFlags (self, sync, str2int, float2int):
        self.__sync = sync
        self.__str2int = str2int
        self.__float2int = float2int

    def __getState (self):
        with self:
            return ( self.__data, self.__local_registered_types, self.__next )

    def __init__ (self, *args, **kwargs):

        self.__sync_lock = threading.RLock()
        self.__next_lock = threading.RLock()
        self.__data_lock = threading.RLock()

        self.__setFlags(kwargs.pop('is_sync', False), kwargs.pop('convert_str', False), kwargs.pop('convert_float', False))
        self.__setState({}, {}, 0)

        for val in args:
            self[None] = val

        for arg, val in kwargs.items():
            self[arg] = val

    def sync (self):
        with self.__sync_lock:
            self.__sync = True

    def async (self):
        with self.__sync_lock:
            self.__sync = False

    def convertString (self):
        self.__str2int = True

    def keepString (self):
        self.__str2int = False

    def convertFloat (self):
        self.__float2int = True

    def keepFloat (self):
        self.__float2int = False

    def register (self, reg, to_key):
        self.__local_registered_types[reg] = to_key

    def set (self, value, index, *indexes):

        location = self
        extra = len(indexes)

        if extra is 0:
            last = index
        else:
            extra -= 1
            last = indexes[extra]

            for key in itertools.chain([ index ], itertools.islice(indexes, None, extra)):
                if key not in location:
                    xarray = xArray(is_sync = self.__sync, convert_str = self.__str2int, convert_float = self.__float2int)
                    location[key] = xarray
                    location = xarray
                else:
                    location = location[key]

        location[last] = value

    def toQuery (self):
        return xArray.__toQuery(self)

    def keys (self):
        return set(self)

    def items (self):
        for _, ( key, val ) in self.__data.items():
            yield ( copy.deepcopy(key), val )

    def __deepcopy__ (self, memo):
        xarray = xArray(is_sync = self.__sync, convert_str = self.__str2int, convert_float = self.__float2int)
        xarray.__setState(copy.deepcopy(self.__data, memo), copy.deepcopy(self.__local_registered_types, memo), self.__next)
        return xarray

    def __copy__ (self):
        xarray = xArray(is_sync = self.__sync, convert_str = self.__str2int, convert_float = self.__float2int)
        xarray.__setState(copy.copy(self.__data), copy.deepcopy(self.__local_registered_types), self.__next)
        return xarray

    def __iter__ (self):
        for key, _ in self.items():
            yield key

    def __len__ (self):
        return self.__data.__len__()

    def __eq__ (self, other):
        if type(other) is xArray and len(self) == len(other):
            for key, val in self.items():
                try:
                    if other[key] != val:
                        return False
                except KeyError:
                    return False
            return True
        return False

    def __setitem__ (self, key, value):

        if key is None:
            with self.__next_lock:
                index = self.__next
                self.__next += 1
            key = index
            key_type = int
        else:
            index, key_type, key = self.__getIndex(key, True)

            with self.__next_lock:
                if key_type is int and key >= self.__next:
                    self.__next = key + 1

        pair = ( copy.deepcopy(key), value )

        with self:
            self.__data[( index, key_type )] = pair

    def __getitem__ (self, key):

        with self:
            with self.__next_lock:
                if key is None:
                    key = self.__next - 1

            try:
                return self.__data[self.__getIndex(key)][1]
            except KeyError:
                raise KeyError(key)

    def __delitem__ (self, key):
        with self:
            try:
                del self.__data[self.__getIndex(key)]
            except KeyError:
                raise KeyError(key)

    def __contains__ (self, key):
        return self.__getIndex(key) in self.__data

    def __str__ (self):
        return '{ ' + ', '.join('{0}: {1}'.format(repr(key), repr(val)) for key, val in self.items()) + ' }'

    def __repr__ (self):
        return self.__str__()

    def __hash__ (self):
        return self.__pack().__hash__()

xArray.default_registered_types = {
    list   : (lambda x: xArray.recursivePack(x)),
    dict   : (lambda x: xArray.recursivePack(x)),
    set    : (lambda x: xArray.recursivePack(x)),
    tuple  : (lambda x: xArray.recursivePack(x)),
    xArray : (lambda x: xArray.recursivePack(x))
}

xArray.query_match_arrays = re.compile(r'(?:\[[^\]]*?\])+$')
