# -*- coding: utf-8 -*-


from itertools import combinations
from utils import subseteq, update
from symbol import Not, Atom
from plogic import SPPLogic, CPLogic
from dlogic import DefaultLogic, DefaultRule, CPDLogic
from visitor import collect_atoms, subst, subst_all, to_FullPNNF
from parser import parse


class SPDLogicSkeleton(DefaultLogic):
    ''' Skeleton for our Stupid Paraconsistent Default Logic
        Data Structure:
            ground_logic: ground logic for `_cdl`.
            _cdl: a classical default logic to do reasoning.
            atoms: all atom names occur.
        Not Implemented:
            _transform_formula(formula):
                do some transform before add formula.
            _set_inconsistents(cdl, incs):
                do something on `cdl`
                when we know the names of inconsistent atoms are `incs`.
    '''
    ground_logic = None
    # test whether p is classic truth value or not
    inc_tester = parse('p|!p =) p&!p')

    def _transform_formula(self, formula):
        return formula

    def _set_inconsistents(self, cdl, incs):
        raise NotImplementedError

    def _make_tester(self, atom):
        return self._transform_formula(subst(self.inc_tester, 'p', Atom(atom)))

    def _make_classic_default_logic(self, incs):
        cdl = self._cdl.copy()
        self._set_inconsistents(cdl, incs)
        return cdl

    def reset(self):
        super(SPDLogicSkeleton, self).reset()
        self._cdl = CPDLogic(ground_logic=self.ground_logic)
        self.atoms = []

    def copy(self):
        obj = super(SPDLogicSkeleton, self).copy()
        obj._cdl = self._cdl.copy()
        obj.atoms = self.atoms.copy()
        return obj

    def add_fact(self, formula):
        super(SPDLogicSkeleton, self).add_fact(formula)
        self._update_atoms(formula)
        self._cdl.add_fact(self._transform_formula(formula))

    def add_rule(self, rule):
        super(SPDLogicSkeleton, self).add_rule(rule)
        l = [rule.pre, rule.jus, rule.cons]
        for formula in l:
            self._update_atoms(formula)
        self._cdl.add_rule(DefaultRule(*list(map(self._transform_formula, l))))

    def _update_atoms(self, formula):
        return update(self.atoms,
                [atom.name for atom in collect_atoms(formula)])

    def all_extensions(self):
        atoms = self.atoms
        min_incs_set = []
        for inc_count in range(len(atoms) + 1):
            for incs in combinations(atoms, inc_count):
                for min_incs in min_incs_set:
                    if subseteq(min_incs, incs):
                        break
                else:
                    cdl = self._make_classic_default_logic(incs)
                    has_extension = False
                    for extension in cdl.all_extensions():
                        if not extension.sat():
                            break
                        for atom in incs:
                            if not extension.sat(self._make_tester(atom)):
                                break
                        else:
                            yield extension
                            has_extension = True
                    if has_extension:
                        min_incs_set.append(incs)
                        if inc_count == 0:
                            return

    def has_extension(self):
        return True


class SPDLogic(SPDLogicSkeleton):
    ground_logic = SPPLogic

    def _set_inconsistents(self, cdl, incs):
        cdl.w.set_inconsistents(incs)


class AnotherSPDLogic(SPDLogicSkeleton):
    ground_logic = CPLogic
    classic_assert = parse('p <-> !q')

    def _transform_formula(self, formula):
        return to_FullPNNF(formula)

    def _make_assert(self, atom_name):
        formula = subst_all(self.classic_assert, {
            'p': self._transform_formula(Atom(atom_name)),
            'q': self._transform_formula(Not(Atom(atom_name))),
            })
        return formula

    def _set_inconsistents(self, cdl, incs):
        for atom_name in self.atoms:
            if atom_name not in incs:
                cdl.add_fact(self._make_assert(atom_name))

    def _wrap_entail(f):
        def _f(self, formula):
            formula = self._transform_formula(formula)
            old_cdl = self._cdl.copy()
            for atom in collect_atoms(formula):
                name = atom.name
                if name not in self.atoms:
                    self._cdl.add_fact(self._make_assert(name))
            ret = getattr(super(AnotherSPDLogic, self), f.__name__)(formula)
            self._cdl = old_cdl
            return ret
        return _f

    @_wrap_entail
    def credulous_entail(self, formula):
        pass

    @_wrap_entail
    def skeptical_entail(self, formula):
        pass
