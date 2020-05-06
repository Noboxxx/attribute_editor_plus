from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
from maya import cmds
from functools import partial
import json
import os

# Filter for nodes, attrs
# Select by type
# Force selection in nodes tree when reloading
# Recently selected
# Save selection
# default value
# Order attrs as given by maya

def f_attr(node, attr):
    return '{0}.{1}'.format(node, attr)


def get_widget(object_name, type_):
    pointer = omui.MQtUtil.findControl(object_name)
    return wrapInstance(long(pointer), type_)


# def get_user_attrs(node):
#     attributes = list()
#     for item in pm.listAttr(node, userDefined=True):
#         if isinstance(item, pm.Attribute):
#             attr = item
#         else:
#             try:
#                 attr = pm.Attribute(f_attr(node, item))
#             except:
#                 continue
#
#         attributes.append(attr)
#     return attributes

def get_user_attrs(node):
    attributes = list()
    for item in cmds.listAttr(node.name(), userDefined=True) or list():
        attributes.append(item)
    return attributes


def get_intersection(ls):
    test = set()
    for a, i in enumerate(ls):
        if a == 0:
            test.update(i)
            continue
        test.intersection_update(i)
    return list(test)

class SavedSelectionFile(object):

    def __init__(self, path):
        if not self.is_one(path):
            cmds.error('\'{0}\' is not a valid {1}.'.format(path, self.__class__.__name__))
        self.__path = path

    @classmethod
    def from_maya_folder(cls):
        maya_folder = cmds.internalVar(userAppDir=True)[:-1]
        path = '{0}/{1}'.format(maya_folder, '{0}.json'.format(cls.__name__))
        return cls(path)

    @classmethod
    def is_one(cls, path):
        location = path.split('/')
        location.pop()
        return os.path.isdir(location)

    def get_path(self):
        return self.__path

    def exists(self):
        return os.path.exists(self.get_path())

    def read(self):
        if not self.exists():
            self.write(dict())

        with open(self.get_path(), 'r') as f:
            return json.load(f)

    def write(self, item):
        with open(self.get_path(), 'w') as f:
            return json.dump(item, f)

    def add(self, label, items):
        content = self.read()
        content[label] = items
        self.write(content)

class AttributeEditorPlus(QDialog):
    script_job_number = -1

    def __init__(self, parent):
        super(AttributeEditorPlus, self).__init__(parent)
        parent.setAttribute(Qt.WA_AlwaysShowToolTips)

        self.setWindowTitle(self.__class__.__name__)
        self.setAttribute(Qt.WA_AlwaysShowToolTips)

        if cmds.about(ntOS=True):
            self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)
        elif cmds.about(macOS=True):
            self.setWindowFlags(Qt.Tool)

        self.nodes_tree = QTreeWidget()
        self.nodes_tree.setColumnCount(2)
        self.nodes_tree.setHeaderLabels(('name', 'type'))
        self.nodes_tree.itemSelectionChanged.connect(self.refresh_attr_tree)
        self.nodes_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.attrs_tree = QTreeWidget()
        self.attrs_tree.setColumnCount(3)
        self.attrs_tree.setHeaderLabels(('name', 'locked', 'connected', 'value'))
        self.attrs_tree.setAttribute(Qt.WA_AlwaysShowToolTips)
        self.attrs_tree.setMouseTracking(True)

        self.node_info_lay = QHBoxLayout()
        self.node_info_lay.addWidget(self.nodes_tree)

        self.attrs_lay = QVBoxLayout()
        self.attrs_lay.addWidget(self.attrs_tree)

        main_lay = QVBoxLayout(self)
        main_lay.addLayout(self.node_info_lay)
        main_lay.addLayout(self.attrs_lay)

    @classmethod
    def display(cls):
        parent = get_widget('MayaWindow', QWidget)

        for child in parent.children():
            if type(child).__name__ == cls.__name__:
                child.deleteLater()

        dialog = cls(parent)
        dialog.show()
        dialog.refresh()
        return dialog

    def refresh(self):
        selected_nodes = self.get_selected_nodes()
        self.nodes_tree.clear()
        selection = cmds.ls(sl=True, objectsOnly=True) or list()

        for index, node in enumerate(selection):
            type_ = cmds.objectType(node)
            widget = QTreeWidgetItem((node, type_))
            icon = QIcon(':/{0}.svg'.format(type_))
            widget.setIcon(1, icon)
            self.nodes_tree.addTopLevelItem(widget)

        iterator = QTreeWidgetItemIterator(self.nodes_tree)
        while iterator.value():
            widget = iterator.value()
            text = widget.text(0)
            if text in selected_nodes:
                widget.setSelected(True)

            iterator += 1

        self.refresh_attr_tree()

    def set_script_job_enabled(self, enabled):
        if enabled and self.script_job_number < 0:
            self.script_job_number = cmds.scriptJob(event=["SelectionChanged", partial(self.refresh)], protected=True)
        elif not enabled and self.script_job_number >= 0:
            cmds.scriptJob(kill=self.script_job_number, force=True)
            self.script_job_number = -1

    def deleteLater(self, *args, **kwargs):
        self.set_script_job_enabled(False)
        super(self.__class__, self).deleteLater(*args, **kwargs)

    def show(self, *args, **kwargs):
        self.set_script_job_enabled(True)
        super(self.__class__, self).show()

    def get_selected_nodes(self):
        selected_nodes = list()
        for widget in self.nodes_tree.selectedItems():
            selected_nodes.append(widget.text(0))
        return selected_nodes

    def refresh_attr_tree(self):
        self.attrs_tree.clear()

        attrs_dict = dict()
        nodes = self.get_selected_nodes()
        for node in nodes:
            attrs = (cmds.listAttr(node, cb=True) or list()) + (cmds.listAttr(node, k=True) or list())
            for attr in attrs:
                full = f_attr(node, attr)
                if not cmds.objExists(full):
                    continue
                value = cmds.getAttr(full)
                type_ = cmds.getAttr(full, type=True)
                locked = cmds.getAttr(full, lock=True)
                connected = bool(cmds.listConnections(full, source=True, destination=False))
                if attr not in attrs_dict:
                    attrs_dict[attr] = {'values': list(),
                                        'types': list(),
                                        'locked': list(),
                                        'keyable': list(),
                                        'connected': list()}
                attrs_dict[attr]['values'].append(value)
                attrs_dict[attr]['types'].append(type_)
                attrs_dict[attr]['locked'].append(locked)
                attrs_dict[attr]['connected'].append(connected)

        for attr, info in attrs_dict.items():
            values = info['values']
            types = info['types']
            unique_values = self.unique(values)
            unique_types = self.unique(types)
            value = str(unique_values[0]) if len(unique_values) == 1 else '...'
            type_ = str(unique_types[0]) if len(unique_types) == 1 else '...'
            locked = self.are_they(info['locked'])
            connected = self.are_they(info['connected'])

            if len(values) == len(nodes):
                widget = QTreeWidgetItem((attr, '', '', value))
                msg = '{0} - type: {1}, value: {2}'.format(attr, type_, value)
                widget.setToolTip(0, msg)
                widget.setStatusTip(0, msg)
                if locked == 1:
                    widget.setText(1, '...')
                if locked > 0:
                    widget.setIcon(1, QIcon(':/lock.png'))

                if connected == 1:
                    widget.setText(2, '...')
                if connected > 0:
                    widget.setIcon(2, QIcon(':/lock.png'))

                self.attrs_tree.addTopLevelItem(widget)

    def are_they(self, ls):
        true_count = ls.count(True)

        if true_count == len(ls):
            return 2
        elif true_count > 0:
            return 1

        return 0

    def unique(self, ls):
        new_ls = list()

        for i in ls:
            if i not in new_ls:
                new_ls.append(i)
        return new_ls