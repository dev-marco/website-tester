# -*- coding: utf-8 -*-
import collections, copy, threading, itertools, re, urllib.parse


class NotEmpty (Exception):

    def __init__ (self):
        self.value = 'xArray need to empty to register or change key types.'

    def __repr__ (self):
        return str(self.value)

class xArray (object):


    """
        eXtended Array, accepts dict and lists as key by default and can register functions to add more
        Accepts insertion php like via [ None ], .insert, str2int and float2int
        Thread-safe insertion via .sync and .async functions
    """

    @staticmethod
    def ___is_dict (value):
        return isinstance(value, dict) or isinstance(value, collections.UserDict)

    @staticmethod
    def ___is_list (value):
        return isinstance(value, list) or isinstance(value, collections.UserList)

    @staticmethod
    def ___is_set (value):
        return isinstance(value, set)

    @staticmethod
    def ___is_tuple (value):
        return isinstance(value, tuple)

    @staticmethod
    def __isXArray (value):
        return isinstance(value, xArray)

    @staticmethod
    def ___to_query (data, _first = True, _accum = ''):
        if xArray.__isXArray(data) or xArray.___is_dict(data):
            key_format = '{0}' if _first else '[{0}]'
            return '&'.join(xArray.___to_query(val, False, _accum + urllib.parse.quote_plus(key_format.format(key))) for key, val in data.items())

        elif xArray.___is_list(data) or xArray.___is_tuple(data) or xArray.___is_set(data):
            key_format = '{0}' if _first else '[{0}]'
            return '&'.join(xArray.___to_query(val, False, _accum + urllib.parse.quote_plus(key_format.format(key))) for key, val in enumerate(data))

        return _accum + '=' + urllib.parse.quote_plus(str(data))

    @staticmethod
    def pack_recursive (data):
        data_type = type(data)
        if xArray.___is_dict(data):
            result = []
            for key in sorted(data):
                result.append(xArray.pack_recursive( ( key, data[key] ) ))
            data = tuple(result)
        elif xArray.___is_list(data) or xArray.___is_set(data) or xArray.___is_tuple(data):
            result = []
            for value in data:
                result.append(xArray.pack_recursive(value))
            data = tuple(result)
        elif xArray.__isXArray(data):
            data = data.___pack()
        return ( data_type, data )

    def __enter__ (self):
        self.lock()
        return self

    def __exit__ (self, _, __, ___):
        self.unlock()
        return False

    def ___get_index (self, key, get_used = False):
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

    def ___pack (self):
        return xArray.pack_recursive( self.___get_state() )

    def ___set_state (self, data, reg_types, index):
        self.__data = data
        self.__local_registered_types = reg_types
        self.__next = index

    def ___set_flags (self, sync, str2int, float2int):
        self.__sync = sync
        self.__str2int = str2int
        self.__float2int = float2int

    def ___get_state (self):
        return ( self.__data, self.__local_registered_types, self.__next )

    def __init__ (self, *args, is_sync = False, convert_str = False, convert_float = False, **kwargs):

        self.__data_lock = threading.RLock()

        self.___set_flags(is_sync, convert_str, convert_float)
        self.___set_state({}, {}, 0)

        for val in args:
            self[None] = val

        for arg, val in kwargs.items():
            self[arg] = val

    def lock (self):
        self.__data_lock.acquire()

    def unlock (self):
        self.__data_lock.release()

    def register (self, reg, to_key):
        if len(self) is 0:
            self.__local_registered_types[reg] = to_key
        else:
            raise NotEmpty()

    def insert (self, value, *indexes):

        location = self
        children = len(indexes)

        if children is 0:
            last = None
        else:
            children -= 1
            last = indexes[children]

            for key in itertools.islice(indexes, None, children):
                if key not in location:
                    xarray = xArray()
                    xarray.___set_flags(self.__sync, self.__str2int, self.__float2int)
                    location[key] = xarray
                    location = xarray
                else:
                    location = location[key]

        location[last] = value

    def items (self):
        for _, ( key, val ) in self.__data.items():
            yield ( copy.deepcopy(key), val )

    @property
    def keys (self):
        return set(self)

    @property
    def query (self):
        return xArray.___to_query(self)

    def __deepcopy__ (self, memo):
        xarray = xArray(is_sync = self.__sync, convert_str = self.__str2int, convert_float = self.__float2int)
        xarray.___set_state(copy.deepcopy(self.__data, memo), copy.deepcopy(self.__local_registered_types, memo), self.__next)
        return xarray

    def __copy__ (self):
        xarray = xArray(is_sync = self.__sync, convert_str = self.__str2int, convert_float = self.__float2int)
        xarray.___set_state(copy.copy(self.__data), copy.deepcopy(self.__local_registered_types), self.__next)
        return xarray

    def __iter__ (self):
        for key, _ in self.items():
            yield key

    def __len__ (self):
        return len(self.__data)

    def __eq__ (self, other):
        if type(other) is xArray and len(self) == len(other):
            for key, val in self.items():
                try:
                    if other[key] != val:
                        return False
                except:
                    return False
            return True
        return False

    def __setitem__ (self, key, value):

        if key is None:
            index = self.__next
            self.__next += 1
            key = index
            key_type = int
        else:
            index, key_type, key = self.___get_index(key, True)

            if key_type is int and key >= self.__next:
                self.__next = key + 1

        pair = ( copy.deepcopy(key), value )

        self.__data[( index, key_type )] = pair

    def __getitem__ (self, key):
            if key is None:
                key = self.__next - 1

            try:
                return self.__data[self.___get_index(key)][1]
            except KeyError:
                raise KeyError(key)

    def __delitem__ (self, key):
        try:
            del self.__data[self.___get_index(key)]
        except KeyError:
            raise KeyError(key)

    def __contains__ (self, key):
        return self.___get_index(key) in self.__data

    def __str__ (self):
        return '{ ' + ', '.join('{0}: {1}'.format(repr(key), repr(val)) for key, val in self.items()) + ' }'

    def __repr__ (self):
        return str(self)

    def __hash__ (self):
        return hash(self.___pack())

xArray.default_registered_types = {
    list   : xArray.pack_recursive,
    dict   : xArray.pack_recursive,
    set    : xArray.pack_recursive,
    tuple  : xArray.pack_recursive,
    xArray : xArray.pack_recursive
}

def from_query (query):
    result = xArray(convert_str = True)
    for value in from_query.query_split_keys.split(query):

        if value:
            indexes = []
            arg, val = (value + '=').split('=', 1)

            arg = urllib.parse.unquote_plus(arg)
            val = urllib.parse.unquote_plus(val)

            match_arrays = from_query.query_match_arrays.search(arg)

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

            result.insert(val[ : -1 ], arg, *indexes)
    return result

from_query.query_match_arrays = re.compile(r'(?:\[[^\]]*?\])+$')
from_query.query_split_keys = re.compile(r'[&;]+')
