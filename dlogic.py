# -*- coding: utf-8 -*-


from itertools import combinations
from utils import subseteq
from symbol import LogicObject
from plogic import CPLogic


class DefaultRule(LogicObject):
    def __init__(self, pre, jus, cons):
        self.pre = pre
        self.jus = jus
        self.cons = cons

    def __repr__(self):
        return '{}({}, {}, {})'.format(self.__class__.__name__,
                repr(self.pre),
                repr(self.jus),
                repr(self.cons))

    def __str__(self):
        return '{} : {} / {}'.format(self.pre, self.jus, self.cons)


class DefaultLogic(LogicObject):
    ground_logic = CPLogic

    def __init__(self, d=None, w=None, ground_logic=None):
        if ground_logic is not None:
            self.ground_logic = ground_logic
        self.reset()
        if d:
            for rule in d:
                self.add_rule(rule)
        if w:
            if isinstance(w, (tuple, list)):
                formulas = w
            else:
                formulas = w.formulas
            for formula in formulas:
                self.add_fact(formula)

    def reset(self):
        self.d = []
        self.w = self.ground_logic()

    def copy(self):
        obj = self.__class__()
        obj.d = self.d.copy()
        obj.w = self.w.copy()
        return obj

    def add_fact(self, formula):
        self.w.add(formula)

    def add_rule(self, rule):
        self.d.append(rule)

    def all_extensions(self):
        raise NotImplementedError

    def has_extension(self):
        raise NotImplementedError

    def credulous_entail(self, formula):
        for extension in self.all_extensions():
            if extension.entail(formula):
                return True
        return False

    def skeptical_entail(self, formula):
        for extension in self.all_extensions():
            if not extension.entail(formula):
                return False
        return True

    def __repr__(self):
        return '{}({}, {})'.format(self.__class__.__name__,
                '[{}]'.format(', '.join(map(repr, self.d))),
                self.w)

    def __str__(self):
        return '({{{}}}, {})'.format(', '.join(map(str, self.d)), self.w)


class CPDLogic(DefaultLogic):
    def _build_extension(self, gd):
        extension = self.w.copy()
        for rule in gd:
            extension.add(rule.cons)
        return extension

    def _test_rule(self, extension, rule):
        return extension.sat(rule.jus)

    def is_extension(self, rules):
        extension = self._build_extension(rules)
        ds = [d for d in self.d if self._test_rule(extension, d)]
        if not subseteq(rules, ds):
            return False
        iter_ext = self.w.copy()
        applied_rules = []
        while ds:
            new_ds = ds[:]
            for d in ds:
                if iter_ext.entail(d.pre):
                    if d not in rules:
                        return False
                    iter_ext.add(d.cons)
                    applied_rules.append(d)
                    new_ds.remove(d)
            if len(new_ds) == len(ds):
                break
            ds = new_ds
        return subseteq(rules, applied_rules)

    def all_extensions(self):
        for r in range(len(self.d) + 1):
            for rules in combinations(self.d, r):
                if self.is_extension(rules):
                    yield self._build_extension(rules)

    def has_extension(self):
        for extension in self.all_extensions():
            return True
        return False


if __name__ == '__main__':
    from parser import parse
    from visitor import to_latex
    t = CPDLogic()
    t.add_fact(parse('tweety'))
    t.add_fact(parse('tweety->bird'))
    t.add_fact(parse('penguin->!fly'))
    t.add_rule(parse('bird:fly/fly'))
    assert t.has_extension()
    assert t.skeptical_entail(parse('fly'))
    t.add_fact(parse('tweety->penguin'))
    assert not t.credulous_entail(parse('fly'))

    t.reset()
    t.add_fact(parse('tweety'))
    t.add_fact(parse('tweety->bird'))
    t.add_fact(parse('penguin->!fly'))
    t.add_rule(parse('bird:fly/fly'))
    t.add_fact(parse('!bird'))
    assert t.has_extension()
    assert t.skeptical_entail(parse('hahaha'))

    t.reset()
    t.add_fact(parse('tweety'))
    t.add_fact(parse('tweety->bird'))
    t.add_fact(parse('penguin->!fly'))
    t.add_rule(parse('bird:fly/fly'))
    t.add_rule(parse('tweety:fly/!fly'))
    assert not t.has_extension()
    assert not t.credulous_entail(parse('bird'))
    assert t.skeptical_entail(parse('hahaha'))

    t.reset()
    t.add_fact(parse('T'))
    t.add_rule(parse('T:!p/q'))
    t.add_rule(parse('T:!q/p'))
    assert t.credulous_entail(parse('p'))
    assert t.credulous_entail(parse('q'))
    assert not t.skeptical_entail(parse('p'))
    assert not t.skeptical_entail(parse('q'))
    assert len(list(t.all_extensions())) == 2
