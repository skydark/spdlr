# -*- coding: utf-8 -*-


from os import path
import json
import yaml

from spdl import SPDLogic, AnotherSPDLogic
from dlogic import DefaultRule, CPDLogic
from symbol import Formula
from lparser import parse, FormulaSyntaxError
from visitor import to_latex


LOGIC_MAP = {
        'cpdl': CPDLogic,
        'spdl1': SPDLogic,
        'spdl2': AnotherSPDLogic,
        }

UNPARSE_MAP = {
        'str': str,
        'latex': to_latex,
        }


class DatasetFormatError(Exception):
    pass


class TestFailed(Exception):
    pass


class DatasetManager(object):
    _engine = None
    _save_options = {}
    _load_options = {}

    def save(self, file_path, data):
        with open(file_path, 'w') as file_handler:
            self._engine.dump(data, file_handler, **self._save_options)

    def load(self, file_path):
        with open(file_path, 'r') as file_handler:
            data = self._engine.load(file_handler, **self._load_options)
        return data


class YamlDatasetManager(DatasetManager):
    _engine = yaml
    _save_options = {
            'default_flow_style': False,
            'allow_unicode': True,
            'encoding': 'utf-8',
            }


class JsonDatasetManager(DatasetManager):
    _engine = json


class QueryAsker(object):
    def __init__(self, dataset_loader=None):
        self.dataset_loader = dataset_loader

    def query_has_extension(self, logic, formula):
        return len(list(logic.all_extensions()))

    def query_all_extensions(self, logic, formula):
        return list(logic.all_extensions())

    def query_credulous_entail(self, logic, formula):
        f = self.dataset_loader.try_parse(formula, Formula)
        return logic.credulous_entail(f)

    def query_not_credulous_entail(self, logic, formula):
        f = self.dataset_loader.try_parse(formula, Formula)
        return not logic.credulous_entail(f)

    def query_skeptical_entail(self, logic, formula):
        f = self.dataset_loader.try_parse(formula, Formula)
        return logic.skeptical_entail(f)

    def query_not_skeptical_entail(self, logic, formula):
        f = self.dataset_loader.try_parse(formula, Formula)
        return not logic.skeptical_entail(f)


class DatasetLoader(object):
    format = 'str'
    dataset_manager = YamlDatasetManager()
    query_asker = QueryAsker()

    def __init__(self, dataset_manager=None, query_asker=None):
        if dataset_manager:
            self.dataset_manager = dataset_manager
        if query_asker:
            self.query_asker = query_asker
        self.query_asker.dataset_loader = self

    def ensure(self, b):
        if not b:
            raise DatasetFormatError('Illegal data!')

    def ensure_in(self, b, l):
        if not b in l:
            raise DatasetFormatError('Illegal data!')

    def ensure_type(self, b, type_):
        if not isinstance(b, type_):
            raise DatasetFormatError('Illegal data!')

    def load(self, file_path):
        config = self.dataset_manager.load(file_path)
        self.ensure_type(config, dict)
        action = config.get('action', 'load')
        do = getattr(self, 'do_{}'.format(action), None)
        self.ensure(do is not None)
        config.setdefault('format', 'str')
        self.ensure_in(config['format'], UNPARSE_MAP)
        self.format = config['format']
        return do(config)

    def do_load(self, config):
        datasets = config.get('dataset', None)
        if datasets is None:
            datasets = [config]
        self.ensure_type(datasets, list)
        self.ensure(len(datasets) == 1)
        dataset = datasets[0]
        return self.make_default(dataset)

    def do_test(self, config):
        logic_maker = LOGIC_MAP.get(config.get('logic', 'spdl1'), None)
        self.ensure(logic_maker is not None)
        datasets = config.get('dataset', None)
        if datasets is None:
            datasets = [config]
        self.test_datasets(datasets, logic_maker)

    def test_datasets(self, datasets, logic_maker):
        self.ensure_type(datasets, list)
        for dataset in datasets:
            self.ensure_type(dataset, dict)
            df = self.make_default(dataset)
            self.test_dataset(dataset, df, logic_maker)

    def make_default(self, dataset):
        rules = dataset.get('rule', [])
        self.ensure_type(rules, list)
        _rules = []
        for rule in rules:
            r = self.try_parse(rule, DefaultRule)
            _rules.append(r)
        facts = dataset.get('fact', [])
        self.ensure_type(facts, list)
        _facts = []
        for fact in facts:
            f = self.try_parse(fact, Formula)
            _facts.append(f)
        return (_rules, _facts)

    def test_dataset(self, dataset, df, logic_maker):
        logic = logic_maker()
        rules, facts = df
        for rule in rules:
            logic.add_rule(rule)
        for fact in facts:
            logic.add_fact(fact)
        has_extension = dataset.get('has_extension', None)
        if has_extension is not None:
            self.ensure_type(has_extension, int)
            if self.query(logic, 'has_extension', None) != has_extension:
                raise TestFailed(
                    'Test failed:\n  Logic {}\n  should has {} extension(s)'\
                                .format(logic, has_extension))
        for name in ('credulous_entail', 'skeptical_entail',
                'not_credulous_entail', 'not_skeptical_entail'):
            l = dataset.get(name, [])
            self.ensure_type(l, list)
            for f in l:
                if not self.query(logic, name, f):
                    raise TestFailed(
                            "Test failed:\n  Logic {}\n  should {} `{}'"\
                                    .format(logic, name, f))
        add = dataset.get('add', None)
        if add:
            self.test_datasets(add, logic_maker=logic.copy)

    def query(self, logic, question, formula):
        func = getattr(self.query_asker, 'query_{}'.format(question), None)
        if func is None:
            raise DatasetFormatError('Unknown question')
        return func(logic, formula)

    def try_parse(self, s, type_=Formula):
        try:
            r = parse(s, format=self.format)
        except FormulaSyntaxError as e:
            raise DatasetFormatError(e)
        self.ensure_type(r, type_)
        return r

    def save_from_default(self, file_path, raw_default, format=None):
        if format is None:
            format = self.format
        self.ensure(format in UNPARSE_MAP)
        rules, facts = raw_default
        obj = {}
        obj['format'] = format
        unparse = UNPARSE_MAP[format]
        obj['fact'] = [unparse(fact) for fact in facts]
        obj['rule'] = [unparse(rule) for rule in rules]
        self.dataset_manager.save(file_path, obj)

    def save(self, file_path, rules, facts, format=None):
        if format is None:
            format = self.format
        self.ensure(format in UNPARSE_MAP)
        obj = {
                'format': format,
                'fact': facts,
                'rule': rules,
                }
        self.dataset_manager.save(file_path, obj)


if __name__ == '__main__':
    c = DatasetLoader()
    c.load('test.yaml')
