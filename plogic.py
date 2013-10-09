# -*- coding: utf-8 -*-

import pycosat
from symbol import Atom, Not, And, Or, Imply, Implication, Equiv, LogicObject
from visitor import collect_atoms, to_latex, to_CNF, PNNFTransformer


class PropositionalLogic(LogicObject):
    def __init__(self, formulas=None):
        self.reset()
        if formulas:
            for formula in formulas:
                self.add(formula)

    def add(self, formula):
        self.formulas.append(formula)
        atoms = collect_atoms(formula)
        self.add_atoms(atoms)
        self._add(formula)

    def add_atoms(self, atoms):
        for atom in atoms:
            self._add_atom(atom)

    def reset(self):
        self.formulas = []
        self.atoms = {}

    def copy(self):
        obj = self.__class__()
        obj.formulas = self.formulas.copy()
        obj.atoms = self.atoms.copy()
        return obj

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__,
                ', '.join(map(repr, self.formulas)))

    def __str__(self):
        return '{{{}}}'.format(', '.join(map(str, self.formulas)))

    def _add_atom(self, atom):
        # return isNewFlag, AtomNumber
        atoms = self.atoms
        name = atom.name
        if name in atoms:
            return False, atoms[name]
        num = len(atoms) + 1
        atoms[name] = num
        return True, num

    def _add(self, formula):
        pass

    def sat(self, formula=None):
        raise NotImplementedError

    def entail(self, formula):
        raise NotImplementedError


class CPLogic(PropositionalLogic):
    def reset(self):
        super(CPLogic, self).reset()
        self.cnfs = []

    def copy(self):
        obj = super(CPLogic, self).copy()
        obj.cnfs = [clause.copy() for clause in self.cnfs]
        return obj

    def _roll_back(self, added_clause, atoms):
        if added_clause > 0:
            self.cnfs = self.cnfs[:-added_clause]
        for name in atoms:
            del self.atoms[name]

    def _translate_clause_to_numbers(self, clause):
        num_clause = []
        new_atoms = {}
        for literal in clause.sub_formulas:
            factor = 1
            if isinstance(literal, Not):
                literal = literal.sub_formulas[0]
                factor = -1
            assert isinstance(literal, Atom)
            is_new, num = self._add_atom(literal)
            if is_new:
                new_atoms[literal.name] = num
            num *= factor
            if -num in num_clause:
                # (!a | a | ...), tautology
                self._roll_back(0, new_atoms)
                num_clause = []
                new_atoms = {}
                break
            if num not in num_clause:
                num_clause.append(num)
        return num_clause, new_atoms

    def _add(self, formula):
        # store formula in CNF
        added_clause = 0
        new_atoms = {}
        cnf = to_CNF(formula)
        for clause in cnf.sub_formulas:
            # convert atoms to numbers for pycosat
            num_clause, atoms = self._translate_clause_to_numbers(clause)
            if num_clause:
                self.cnfs.append(num_clause)
                added_clause += 1
                new_atoms.update(atoms)
        return added_clause, new_atoms

    def sat(self, formula=None):
        if formula:
            added_clause, new_atoms = self._add(formula)
        ret = pycosat.solve(self.cnfs)
        if formula:
            self._roll_back(added_clause, new_atoms)
        # FIXME
        return ret not in ('UNSAT', 'UNKNOWN')

    def entail(self, formula):
        return not self.sat(Not(formula))


class SPPLogic(PropositionalLogic):
    _use_cache = True
    # _use_cache = False

    def reset(self):
        super(SPPLogic, self).reset()
        self.set_inconsistents([])
        self.PNNF_transformer = PNNFTransformer()
        if self._use_cache:
            self._cached_theory = ([], [], CPLogic())

    def copy(self):
        obj = super(SPPLogic, self).copy()
        obj.set_inconsistents(self.inconsistents)
        if self._use_cache:
            obj._cached_theory = self._cached_theory
        return obj

    def _make_theory(self):
        if self._use_cache \
                and self.inconsistents == self._cached_theory[0] \
                and self.formulas == self._cached_theory[1]:
            theory = self._cached_theory[2]
        else:
            theory = CPLogic([self.PNNF_transformer.visit(formula)
                for formula in self.formulas])
            if self._use_cache:
                self._cached_theory = (self.inconsistents.copy(),
                        self.formulas.copy(), theory)
        return theory

    def set_inconsistents(self, inconsistents):
        self.inconsistents = list(inconsistents)

    def sat(self, formula=None):
        self.PNNF_transformer.set_inconsistents(self.inconsistents)
        theory = self._make_theory()
        if formula is not None:
            formula = self.PNNF_transformer.visit(formula)
        return theory.sat(formula)

    def entail(self, formula):
        self.PNNF_transformer.set_inconsistents(self.inconsistents)
        theory = self._make_theory()
        formula = self.PNNF_transformer.visit(formula)
        return theory.entail(formula)


def test(form, org_str, org_form, CNF, latex):
    assert form.__str__() == org_str, form.__str__()
    assert form == org_form, form
    assert to_CNF(form) == CNF, to_CNF(form)
    assert to_latex(form) == latex, to_latex(form)


TEST_DATA = [
        [
            '!(B | C)',
            Not(Or(Atom('B'), Atom('C'))),
            And(Or(Not(Atom('B'))), Or(Not(Atom('C')))),
            r'{\lnot{{B}\lor{C}}}'
            ],
        [
            '(B <-> (P_1 | P_2))',
            Equiv(Atom('B'), Or(Atom('P_1'), Atom('P_2'))),
            And(Or(Not(Atom('B')), Atom('P_1'), Atom('P_2')),
                Or(Not(Atom('P_1')), Atom('B')),
                Or(Not(Atom('P_2')), Atom('B'))),
            r'{{B}\leftrightarrow{{P_1}\lor{P_2}}}'
            ],
        [
            '(A | (B & C) | D)',
            Or(Atom('A'), And(Atom('B'), Atom('C')), Atom('D')),
            And(Or(Atom('A'), Atom('B'), Atom('D')),
                Or(Atom('A'), Atom('C'), Atom('D'))),
            r'{{A}\lor{{B}\land{C}}\lor{D}}'
            ],
        [
            '(A & (B | (D & E)))',
            And(Atom('A'), Or(Atom('B'), And(Atom('D'), Atom('E')))),
            And(Or(Atom('A')),
                Or(Atom('B'), Atom('D')),
                Or(Atom('B'), Atom('E'))),
            r'{{A}\land{{B}\lor{{D}\land{E}}}}'
            ],
        ]

if __name__ == '__main__':
    from lparser import parse

    for org_str, org_form, CNF, latex in TEST_DATA:
        # TODO: parse from org_str
        form = org_form
        test(form, org_str, org_form, CNF, latex)
        from visitor import to_plain
        assert to_plain(parse(org_str)) == to_plain(form), org_str

    w = CPLogic()
    w.add(parse('A'))
    w.add(parse('A -> !B |(!A&C)'))
    assert w.sat(parse('D->B'))
    assert w.sat(parse('D->A'))
    assert w.entail(parse('!B|E'))
    assert not w.entail(parse('C'))
    assert not w.entail(parse('E'))

    w = SPPLogic()
    w.add(parse('A'))
    w.add(parse('A -> !B |(!A&C)'))
    assert w.sat(parse('D->B'))
    assert w.sat(parse('D->A'))
    assert w.entail(parse('!B|E'))
    assert not w.entail(parse('C'))
    assert not w.entail(parse('E'))
    w.set_inconsistents(['A'])
    assert w.sat(parse('D->B'))
    assert w.sat(parse('D->A'))
    assert w.entail(parse('A'))
    assert not w.entail(parse('!B|E'))
    assert not w.entail(parse('C'))
    assert not w.entail(parse('E'))
    w.reset()
    w.add(parse('A'))
    w.add(parse('A =) !B |(!A&C)'))
    assert w.sat(parse('D->B'))
    assert w.sat(parse('D->A'))
    assert w.entail(parse('!B|E'))
    assert not w.entail(parse('C'))
    assert not w.entail(parse('E'))
    w.set_inconsistents(['A'])
    assert w.sat(parse('D->B'))
    assert w.sat(parse('D->A'))
    assert w.sat(parse('A'))
    assert w.sat(parse('!B'))
    assert not w.entail(parse('!B|E'))
    assert not w.entail(parse('C'))
    assert not w.entail(parse('E'))
    w.add(parse('B'))
    assert w.entail(parse('!A & C'))
    w.add(parse('!C'))
    assert w.entail(parse('E'))
