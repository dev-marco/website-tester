# -*- coding: utf-8 -*-

class Color (object):

    enabled = True

    @classmethod
    def make (cls, fg, bg):
        color = Color(None)
        color.__value = ( fg.__value, bg.__value if bg.__value > 40 else bg.__value + 10 )
        return color

    def __init__ (self, value):
        self.__value = value

    def __mod__ (self, other):
        return str(self) + str(other) + str(Color.RESET)

    def __rmod__ (self, other):
        return str(self) + str(other) + str(Color.RESET)

    def __add__ (self, other):
        return str(self) + str(other)

    def __radd__ (self, other):
        return str(other) + str(self)

    def __str__ (self):
        if Color.enabled:
            if type(self.__value) is tuple:
                return '\x1b[0;{0};{1}m'.format(*self.__value)
            return '\x1b[{0}m'.format(self.__value)
        return ''

Color.RED = Color(31)
Color.GREEN = Color(32)
Color.YELLOW = Color(33)
Color.BLUE = Color(34)
Color.PURPLE = Color(35)
Color.CYAN = Color(36)
Color.WHITE = Color(37)

Color.BG_RED = Color(41)
Color.BG_GREEN = Color(42)
Color.BG_YELLOW = Color(43)
Color.BG_BLUE = Color(44)
Color.BG_PURPLE = Color(45)
Color.BG_CYAN = Color(46)
Color.BG_WHITE = Color(47)

Color.RESET = Color(0)
