# -*- coding: utf-8 -*-


WIN_SIZE = (800, 600)
GUI_FILE = "gui.html"
PYOBJ_NAME = "pyobj"

from os import path
import sys
import json

try:
    # raise ImportError
    from PySide import QtCore, QtGui, QtWebKit
except ImportError:
    from PyQt4 import QtCore, QtGui, QtWebKit
    QtCore.Slot = QtCore.pyqtSlot

from parser import parse
from symbol import LogicObject, Formula
from dlogic import DefaultRule
from dataset import LOGIC_MAP, DatasetLoader
from visitor import to_latex
from utils import html_escape


def make_latex(formula):
    return '${}$'.format(html_escape(to_latex(formula)))


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, LogicObject):
            return make_latex(o)
        return json.JSONEncoder.default(self, o)

to_json = JSONEncoder().encode
from_json = json.loads


def make_json(error, value, *k, **kw):
    obj = {}
    obj['error'] = error
    obj['value'] = value
    for d in k:
        obj.update(d)
    for k, v in kw.items():
        obj[k] = v
    return to_json(obj)


class PyObj(QtCore.QObject):
    dataset_loader = DatasetLoader()

    def error_msg(self, msg, title="Error!"):
        QtGui.QMessageBox.critical(None, title, msg)
        return make_json(True, msg)

    @QtCore.Slot(result=str)
    def load(self):
        file_name, _filter = QtGui.QFileDialog.getOpenFileName(
                None,
                "Open File",
                "",
                "Dataset (*.yaml)")
        if file_name == '':
            return make_json(True, 'No file selected')
        try:
            ret = self.dataset_loader.load(file_name)
        except Exception as e:
            return self.error_msg('Error occurs while loading {}: {}'.format(
                file_name, e))
        if ret is None:
            return make_json(True, 'Nothing to do')
        if len(ret) != 2:
            return self.error_msg('Error occurs while loading {}: {}'.format(
                file_name, 'mismatched return value'))
        rules, facts = ret
        return make_json(False, 'Successfully loaded', model={
                'rules': [[str(rule), make_latex(rule)] for rule in rules],
                'facts': [[str(fact), make_latex(fact)] for fact in facts],
                })

    @QtCore.Slot(str, result=str)
    def save(self, model):
        try:
            model = from_json(model)
            rules, facts = model['rules'], model['facts']
        except Exception as e:
            return self.error_msg('Error occurs while saving: {}'.format(e))
        file_name, _filter = QtGui.QFileDialog.getSaveFileName(
                None,
                "Save File",
                "",
                "Dataset (*.yaml)")
        try:
            ret = self.dataset_loader.save(file_name,
                    rules, facts, format='str')
        except Exception as e:
            return self.error_msg('Error occurs while saving {}: {}'.format(
                file_name, e))
        return make_json(False, 'Successfully saved')

    @QtCore.Slot(str, str, result=str)
    def formula_to_latex(self, type_, string):
        try:
            f = parse(string)
        except Exception as e:
            return make_json(True, 'Syntax error: {}'.format(e))
        if (type_ == 'fact' and not isinstance(f, Formula)) \
                or (type_ == 'rule' and not isinstance(f, DefaultRule)):
            return make_json(True, 'Illegal {}'.format(type_))
        return make_json(False, make_latex(f))

    @QtCore.Slot(str, str, str, str, result=str)
    def query(self, logic, question, formula, model):
        try:
            model = from_json(model)
            rules, facts = model['rules'], model['facts']
            rules = [parse(rule) for rule in rules]
            facts = [parse(fact) for fact in facts]
        except Exception as e:
            return make_json(True,
                    'Error occurs while receiving default logic: {}'.format(e))
        logic = LOGIC_MAP[logic]()
        for fact in facts:
            logic.add_fact(fact)
        for rule in rules:
            logic.add_rule(rule)
        try:
            ret = self.dataset_loader.query(logic, question, formula)
        except Exception as e:
            return make_json(True, 'Error occurs while asking {} - {}: {}'\
                    .format(question, formula, e))
        return make_json(False, ret)


def main(*argv):
    app = QtGui.QApplication(argv)

    pyobj = PyObj()

    webView = QtWebKit.QWebView()
    webView.page().mainFrame().addToJavaScriptWindowObject(PYOBJ_NAME, pyobj)
    html_path = path.join(path.abspath(path.dirname(__file__)), GUI_FILE)
    webView.load(QtCore.QUrl.fromLocalFile(html_path))

    window = QtGui.QMainWindow()
    window.setCentralWidget(webView)
    window.setFixedSize(*WIN_SIZE)
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main(*sys.argv)
