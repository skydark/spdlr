# -*- coding: utf-8 -*-


class LogicObject(object):
    pass


class Formula(LogicObject):
    def __init__(self, *sub_formulas):
        self.sub_formulas = list(sub_formulas)

    def __eq__(self, obj):
        if self.__class__ == obj.__class__\
                and self.sub_formulas == obj.sub_formulas:
                    return True
        return False


class Connector(Formula):
    str_symbol = None
    latex_symbol = None

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                ', '.join(map(repr, self.sub_formulas)))


class PrefixConnector(Connector):
    def __str__(self):
        return '{}{}'.format(self.str_symbol, self.sub_formulas[0])


class InfixConnector(Connector):
    def __str__(self):
        str_symbol = ' {} '.format(self.str_symbol)
        return '({})'.format(str_symbol.join(map(str, self.sub_formulas)))


class ImplyConnector(InfixConnector):
    pass


class Atom(Formula):
    def __init__(self, name):
        super(Atom, self).__init__(name)
        self.name = name

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.name)

    def __str__(self):
        return self.name


class Not(PrefixConnector):
    str_symbol = '!'
    latex_symbol = '\\lnot'


class And(InfixConnector):
    str_symbol = '&'
    latex_symbol = '\\land'


class Or(InfixConnector):
    str_symbol = '|'
    latex_symbol = '\\lor'


class Imply(ImplyConnector):
    str_symbol = '->'
    latex_symbol = r'\to'


class Implication(ImplyConnector):
    str_symbol = '=)'
    latex_symbol = r'\supset'


class Equiv(InfixConnector):
    str_symbol = '<->'
    latex_symbol = r'\leftrightarrow'
