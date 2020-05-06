from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
from maya import cmds
from functools import partial
import core


def get_widget(object_name, type_):
    pointer = omui.MQtUtil.findControl(object_name)
    return wrapInstance(long(pointer), type_)


def create_action(name, func, parent):
    action = QAction(name, parent)
    if func:
        action.triggered.connect(func)
    return action


def list_to_label(ls, limit=0, separator=', '):

    result = list()

    for index, item in enumerate(ls):
        result.append(item)

    s = separator.join(result)
    if limit > 0:
        if len(s) > limit:
            s = s[:limit] + '...'

    return s


class AttributeEditorPlus(QDialog):
    script_job_number = -1
    selection_file = core.SelectionFile.from_maya_folder()

    signal = Signal(object)

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

        self.menu_bar = QMenuBar()

        main_lay = QVBoxLayout(self)
        main_lay.setMenuBar(self.menu_bar)
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

    def refresh_menu_bar(self):
        self.menu_bar.clear()

        file_menu = self.menu_bar.addMenu('File')
        recently_selected_menu = file_menu.addMenu('Recently Selected')
        saved_selections = file_menu.addMenu('Saved Selections')
        file_menu.addAction(create_action('Save Selection', self.save_selection, self))

        for selection in self.selection_file.get_recent():
            action = create_action(list_to_label(selection, limit=50), lambda x=selection: self.select(x), self)
            recently_selected_menu.addAction(action)

        for name, selection in self.selection_file.get_saved():
            label = '{0}: {1}'.format(name, list_to_label(selection, limit=50))
            action = create_action(label, lambda x=selection: self.select(x), self)
            saved_selections.addAction(action)

    @classmethod
    def select(cls, selection):
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            selection += cmds.ls(sl=True)
        elif QApplication.keyboardModifiers() == Qt.ShiftModifier:
            selection = core.subtract_list(cmds.ls(sl=True), selection)
        core.select(selection)

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
        self.refresh_menu_bar()

    def set_script_job_enabled(self, enabled):
        if enabled and self.script_job_number < 0:
            self.script_job_number = cmds.scriptJob(event=["SelectionChanged", partial(self.selection_changed)], protected=True)
        elif not enabled and self.script_job_number >= 0:
            cmds.scriptJob(kill=self.script_job_number, force=True)
            self.script_job_number = -1

    def selection_changed(self):
        self.selection_file.add_recent(cmds.ls(sl=True))
        self.refresh()

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

    def save_selection(self):
        self.selection_file.add_saved([core.randomString(stringLength=8), cmds.ls(sl=True)])
        self.refresh_menu_bar()

    def refresh_attr_tree(self):
        self.attrs_tree.clear()

        attrs_dict = dict()
        nodes = self.get_selected_nodes()
        for node in nodes:
            attrs = (cmds.listAttr(node, cb=True) or list()) + (cmds.listAttr(node, k=True) or list())
            for attr in attrs:
                full = core.f_attr(node, attr)
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
            unique_values = core.remove_duplicates(values)
            unique_types = core.remove_duplicates(types)
            value = str(unique_values[0]) if len(unique_values) == 1 else '...'
            type_ = str(unique_types[0]) if len(unique_types) == 1 else '...'
            locked = core.search_in(True, info['locked'])
            connected = core.search_in(True, info['connected'])

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