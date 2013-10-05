# -*- coding: utf-8 -*-

from itertools import product
from symbol import Atom, Not, And, Or, Imply, Implication
from utils import flat


class Visitor(object):
    def dispatch(self, obj, template):
        mro = obj.__class__.mro()
        visit = None
        for class_ in mro:
            visit = getattr(self, template.format(class_.__name__), None)
            if visit is not None:
                return visit(obj)

    def visit(self, formula):
        return self.dispatch(formula, 'visit{}')

    def visitobject(self, formula):
        raise NotImplementedError


class AtomCollector(Visitor):
    def visitAtom(self, obj):
        return [obj]

    def visitConnector(self, obj):
        return flat(self.visit(form) for form in obj.sub_formulas)


class AtomSubstituter(Visitor):
    def __init__(self):
        self.reset()

    def subst(self, formula, atom_name, substitution):
        self.reset()
        self.add(atom_name, substitution)
        return self.visit(formula)

    def subst_all(self, formula, d):
        self.reset()
        self.atom_map.update(d)
        return self.visit(formula)

    def reset(self):
        self.atom_map = {}

    def add(self, atom_name, formula):
        self.atom_map[atom_name] = formula

    def visitAtom(self, obj):
        return self.atom_map.get(obj.name, obj)

    def visitConnector(self, obj):
        return obj.__class__(*[self.visit(form) for form in obj.sub_formulas])


class LaTeXTransformer(Visitor):
    def visitAtom(self, obj):
        return '{{{}}}'.format(obj.name)

    def visitInfixConnector(self, obj):
        return '{{{}}}'.format(obj.latex_symbol.join(
            self.visit(form) for form in obj.sub_formulas))

    def visitPrefixConnector(self, obj):
        return '{{{}{}}}'.format(obj.latex_symbol,
                self.visit(obj.sub_formulas[0]))

    def visitPropositionalLogic(self, obj):
        return r'\{{{}\}}'.format(', '.join(
            self.visit(form) for form in obj.formulas))

    def visitDefaultRule(self, obj):
        return r'\frac{{{}:{}}}{}'.format(self.visit(obj.pre),
                self.visit(obj.jus), self.visit(obj.cons))

    def visitDefaultLogic(self, obj):
        return r'(\{{{}\}}, {})'.format(', '.join(
            self.visit(d) for d in obj.d), self.visit(obj.w))


class CNFTransformer(Visitor):
    def visitAtom(self, obj):
        return And(Or(obj))

    def visitNot(self, obj):
        formula = obj.sub_formulas[0]
        return self.dispatch(formula, 'visitNot{}')

    def visitNotAtom(self, obj):
        return And(Or(Not(obj)))

    def visitNotNot(self, obj):
        return self.visit(obj.sub_formulas[0])

    def visitNotAnd(self, obj):
        return self.visit(
                Or(*[Not(form) for form in obj.sub_formulas]))

    def visitNotOr(self, obj):
        return self.visit(
                And(*[Not(form) for form in obj.sub_formulas]))

    def visitNotImplyConnector(self, obj):
        left, right = obj.sub_formulas
        return self.visit(And(left, Not(right)))

    def visitNotEquiv(self, obj):
        left, right = obj.sub_formulas
        return self.visit(Not(And(Imply(left, right), Imply(right, left))))

    def visitAnd(self, obj):
        return And(*flat(self.visit(form).sub_formulas
            for form in obj.sub_formulas))

    def visitOr(self, obj):
        # FIXME: need optimization!
        def merge_clauses(clauses):
            return Or(*flat(clause.sub_formulas for clause in clauses))

        all_cnfs = [self.visit(form).sub_formulas for form in obj.sub_formulas]
        return And(*map(merge_clauses, product(*all_cnfs)))

    def visitImplyConnector(self, obj):
        left, right = obj.sub_formulas
        return self.visit(Or(Not(left), right))

    def visitEquiv(self, obj):
        left, right = obj.sub_formulas
        return self.visit(And(Imply(left, right), Imply(right, left)))


class NNFTransformer(Visitor):
    def visitAtom(self, obj):
        return obj

    def visitNot(self, obj):
        formula = obj.sub_formulas[0]
        return self.dispatch(formula, 'visitNot{}')

    def visitNotAtom(self, obj):
        return Not(obj)

    def visitNotNot(self, obj):
        return self.visit(obj.sub_formulas[0])

    def visitNotAnd(self, obj):
        return self.visit(
                Or(*[Not(form) for form in obj.sub_formulas]))

    def visitNotOr(self, obj):
        return self.visit(
                And(*[Not(form) for form in obj.sub_formulas]))

    def visitNotImplyConnector(self, obj):
        left, right = obj.sub_formulas
        return self.visit(And(left, Not(right)))

    def visitAnd(self, obj):
        return And(*[self.visit(form) for form in obj.sub_formulas])

    def visitOr(self, obj):
        return Or(*[self.visit(form) for form in obj.sub_formulas])

    def visitImply(self, obj):
        left, right = obj.sub_formulas
        return self.visit(Or(Not(left), right))

    def visitImplication(self, obj):
        left, right = obj.sub_formulas
        return Implication(self.visit(left), self.visit(right))


class PNNFTransformer(NNFTransformer):
    """ Transform formula to NNF which has doubt about some inconsistent atoms
    """
    def __init__(self):
        super(PNNFTransformer, self).__init__()
        self.set_inconsistents([])

    def set_inconsistents(self, inconsistents):
        self.inconsistents = inconsistents

    def should_rename(self, name):
        return name in self.inconsistents

    def set_atom_renamer(self, renamer):
        self.atom_renamer = renamer

    def atom_renamer(self, name):
        # Not(Atom(name)) ===> Atom(another_name)
        return '{}^-'.format(name)

    def visitNot(self, obj):
        formula = obj.sub_formulas[0]
        return self.dispatch(formula, 'visitNot{}')

    def visitNotAtom(self, obj):
        if self.should_rename(obj.name):
            return Atom(self.atom_renamer(obj.name))
        else:
            return Not(obj)

    def visitNotNot(self, obj):
        return self.visit(obj.sub_formulas[0])

    def visitNotAnd(self, obj):
        return self.visit(
                Or(*[Not(form) for form in obj.sub_formulas]))

    def visitNotOr(self, obj):
        return self.visit(
                And(*[Not(form) for form in obj.sub_formulas]))

    def visitNotImplyConnector(self, obj):
        left, right = obj.sub_formulas
        return self.visit(And(left, Not(right)))

    def visitImplication(self, obj):
        left, right = obj.sub_formulas
        return Or(Not(self.visit(left)), self.visit(right))


class FullPNNFTransformer(PNNFTransformer):
    def should_rename(self, name):
        return True


class PlainTransformer(Visitor):
    """ Example:
        And(And(Atom('A'), Atom('B')), Atom('C')) ==>
            And(Atom('A'), Atom('B'), Atom('C'))
    """
    def visitAtom(self, obj):
        return obj

    def visitConnector(self, obj):
        return obj

    def visitAnd(self, obj):
        sub_formulas = []
        for formula in obj.sub_formulas:
            formula = self.visit(formula)
            if isinstance(formula, And):
                sub_formulas += formula.sub_formulas
            else:
                sub_formulas.append(formula)
        return And(*sub_formulas)

    def visitOr(self, obj):
        sub_formulas = []
        for formula in obj.sub_formulas:
            formula = self.visit(formula)
            if isinstance(formula, Or):
                sub_formulas += formula.sub_formulas
            else:
                sub_formulas.append(formula)
        return Or(*sub_formulas)


collect_atoms = AtomCollector().visit
subst = AtomSubstituter().subst
subst_all = AtomSubstituter().subst_all
to_latex = LaTeXTransformer().visit
to_CNF = CNFTransformer().visit
to_NNF = NNFTransformer().visit
to_FullPNNF = FullPNNFTransformer().visit
to_plain = PlainTransformer().visit
