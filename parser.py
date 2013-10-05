# -*- coding: utf-8 -*-

import re
from symbol import Atom, Not, And, Or, Imply, Implication, Equiv
from dlogic import DefaultRule


class FormulaSyntaxError(Exception):
    pass


SYMBOLS = {
        'latex': {},
        'str': {},
        }


def register(connector):
    def _register(class_):
        SYMBOLS['str'][connector.str_symbol] = class_
        SYMBOLS['latex'][connector.latex_symbol] = class_
        return class_
    return _register


def register_symbol(symbol):
    def _register(class_):
        for symbol_map in SYMBOLS.values():
            symbol_map[symbol] = class_
        return class_
    return _register


class Symbol(object):
    lbp = 0

    def as_prefix(self, parser):
        raise NotImplementedError

    def as_infix(self, parser, left):
        raise NotImplementedError


class AtomWrapper(Symbol):
    def __init__(self, name):
        self.name = name

    def as_prefix(self, parser):
        return Atom(self.name)


def make_symbol(name, bp=0):
    @register_symbol(name)
    class s(Symbol):
        lbp = bp
    s.__name__ = name
    return s


def make_connector(connector, bp=0):
    @register(connector)
    class s(Symbol):
        lbp = bp
    s.__name__ = "Op" + connector.__name__
    return s


def infix(connector, bp):
    def as_infix(self, parser, left):
        return connector(left, parser.expression(bp))
    make_connector(connector, bp).as_infix = as_infix


def infix_r(connector, bp):
    def as_infix(self, parser, left):
        return connector(left, parser.expression(bp - 1))
    make_connector(connector, bp).as_infix = as_infix


def prefix(connector, bp):
    def as_prefix(self, parser):
        return connector(parser.expression(bp))
    make_connector(connector, 0).as_prefix = as_prefix


@register_symbol('(')
class LeftParen(Symbol):
    def as_prefix(self, parser):
        expr = parser.expression()
        parser.advance(')')
        return expr


@register_symbol(':')
class Colon(Symbol):
    lbp = 10

    def as_infix(self, parser, pre):
        jus = parser.expression()
        parser.advance('/')
        cons = parser.expression()
        return DefaultRule(pre, jus, cons)


make_symbol(')')
make_symbol('End')
make_symbol('/')
# make_symbol(',')


OP_LIST = [
        (Not, 50, prefix),
        (And, 30, infix),
        (Or, 30, infix),
        (Imply, 20, infix_r),
        (Implication, 20, infix_r),
        (Equiv, 20, infix),
        ]

for connector, bp, method in OP_LIST:
    method(connector, bp)


class Parser(object):
    cur_token = None
    cur_pos = 0
    string = ''
    regex_atom = re.compile(r'\\?[a-zA-Z]+(_[0-9])?')
    error_length = 7

    def parse(self, string, format='str'):
        self.symbol_map = SYMBOLS.get(format, None)
        if self.symbol_map is None:
            raise NotImplementedError
        self.string = string
        self.cur_token = None
        self.cur_pos = 0
        self.next()
        if self.eat('End'):
            raise FormulaSyntaxError('Empty String')
        expr = self.expression(0)
        self.advance('End')
        return expr

    def expression(self, rbp=0):
        t = self.cur_token
        if self.eat('End'):
            raise FormulaSyntaxError('Ends too early')
        self.next()
        left = t.as_prefix(self)
        while rbp < self.cur_token.lbp:
            t = self.cur_token
            self.next()
            left = t.as_infix(self, left)
        return left

    def advance(self, name):
        if not self.eat(name):
            self.error('Expect symbol: {}'.format(name))

    def eat(self, name):
        if self.cur_token.__class__ != self.symbol_map[name]:
            return False
        self.next()
        return True

    def next(self):
        self.skip_space()
        if self.cur_pos >= len(self.string):
            self.cur_token = self.symbol_map['End']()
            return self.cur_token
        for sym in self.symbol_map:
            if self.string.startswith(sym, self.cur_pos):
                next_pos = self.cur_pos + len(sym)
                if sym[-1].isalnum() \
                        and self.string[next_pos:next_pos + 1].isalnum():
                            continue
                self.cur_pos = next_pos
                self.cur_token = self.symbol_map[sym]()
                # print(self.cur_token.__class__.__name__, self.cur_pos)
                return self.cur_token
        atom = self.regex_atom.match(self.string, self.cur_pos)
        if atom:
            start, end = atom.span()
            self.cur_pos = end
            self.cur_token = AtomWrapper(self.string[start:end])
            return self.cur_token
        self.error('Unknown symbol!')

    def skip_space(self):
        while self.string[self.cur_pos:self.cur_pos + 1].isspace():
            self.cur_pos += 1

    def error(self, msg):
        raise FormulaSyntaxError('Syntax Error at {} [...{}...]: {}'.format(
            self.cur_pos,
            self.string[self.cur_pos:self.cur_pos + self.error_length],
            msg,
            ))


parse = Parser().parse


if __name__ == '__main__':
    parser = Parser()

    def try_parse(string, format='str'):
        try:
            ret = parser.parse(string, format)
        except FormulaSyntaxError as e:
            print(e)
            ret = None
        return ret

    print(try_parse('( d | e | (f&e) -> a )'))
    print(try_parse(' a -> b ->c & ( d | e ->a)'))
    print(try_parse(r'\alpha\to\beta \to\gamma \land(d\lor e\to a)', 'latex'))
