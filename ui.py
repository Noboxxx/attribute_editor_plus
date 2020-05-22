from PySide2.QtWidgets import *
from PySide2.QtGui import *
from PySide2.QtCore import *
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
from maya import cmds
from functools import partial
import core
import collections


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


def format_value(value):
    if isinstance(value, str) or isinstance(value, unicode):
        return '\'{0}\''.format(value)
    return '{0}'.format(value)


class AttributeEditorPlus(QDialog):
    script_job_number = -1
    selection_file = core.SelectionFile.from_maya_folder()

    signal = Signal(object)

    def __init__(self, parent):
        super(AttributeEditorPlus, self).__init__(parent)

        self.setWindowTitle(self.__class__.__name__)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setMinimumWidth(500)

        if cmds.about(ntOS=True):
            self.setWindowFlags(self.windowFlags() ^ Qt.WindowContextHelpButtonHint)
        elif cmds.about(macOS=True):
            self.setWindowFlags(Qt.Tool)

        self.nodes_tree = QTreeWidget()
        self.nodes_tree.setHeaderLabels(('name', 'type'))
        self.nodes_tree.itemSelectionChanged.connect(self.refresh_attr_tree)
        self.nodes_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.nodes_tree.setMaximumHeight(250)

        self.attrs_tree = QTreeWidget()
        self.attrs_tree.setHeaderLabels(('name', 'value'))
        self.attrs_tree.setAttribute(Qt.WA_AlwaysShowToolTips)
        self.attrs_tree.setMouseTracking(True)

        self.select_by_name_line_edit = QLineEdit()
        select_by_name_btn = QPushButton('>')
        select_by_name_btn.clicked.connect(self.select_by_name)

        select_by_name_lay = QHBoxLayout()
        select_by_name_lay.addWidget(QLabel('Select by Name'))
        select_by_name_lay.addWidget(self.select_by_name_line_edit)
        select_by_name_lay.addWidget(select_by_name_btn)

        self.node_info_lay = QVBoxLayout()
        self.node_info_lay.addLayout(select_by_name_lay)
        self.node_info_lay.addWidget(self.nodes_tree)

        self.attrs_lay = QVBoxLayout()
        self.attrs_lay.addWidget(self.attrs_tree)

        self.menu_bar = QMenuBar()

        main_lay = QVBoxLayout(self)
        main_lay.setMenuBar(self.menu_bar)
        main_lay.addLayout(self.node_info_lay)
        main_lay.addLayout(self.attrs_lay)
        main_lay.addLayout(self.attrs_lay)

    def select_by_name(self):
        ls = cmds.ls(self.select_by_name_line_edit.text()) or list()
        if not ls:
            return
        self.select(ls)

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

    @classmethod
    def select(cls, selection):
        if QApplication.keyboardModifiers() == Qt.ShiftModifier:
            selection += cmds.ls(sl=True)
        elif QApplication.keyboardModifiers() == Qt.ControlModifier:
            selection = core.subtract_list(cmds.ls(sl=True), selection)
        core.select(selection)

    @classmethod
    def select_children(cls):
        all_children = list()

        for node in cls.get_selected():
            children = cmds.listRelatives(node, children=True) or list()
            all_children += children

        cls.select(all_children)

    @classmethod
    def select_all_descendents(cls):
        all_descendents = list()

        for node in cls.get_selected():
            descendents = cmds.listRelatives(node, allDescendents=True) or list()
            all_descendents += descendents

        cls.select(all_descendents)

    def set_value(self):
        with core.Chunk():
            grp_attrs = self.get_selected_attrs()
            common_value = grp_attrs.get_value()
            if isinstance(common_value, str) or isinstance(common_value, unicode):
                common_value = '\'{0}\''.format(common_value)
            raw_value = QInputDialog.getText(self, "Set value", "Value:", text=str(common_value if common_value is not None else 'current'))[0]
            if raw_value != '':
                for index, attr in enumerate(grp_attrs):
                    if not attr.is_locked() and not attr.is_source_connected():
                        current = attr.get_value()
                        default = attr.get_default_value()
                        value = eval(raw_value)
                        attr.set_value(value)
                    else:
                        cmds.warning('{0}: \'{1}\' cannot be set (locked or source connected).'.format(self.__class__.__name__, attr.get_name()))

        self.refresh_attr_tree()

    def lock(self):
        with core.Chunk():
            for attr in self.get_selected_attrs():
                attr.lock(True)
        self.refresh_attr_tree()

    def unlock(self):
        with core.Chunk():
            for attr in self.get_selected_attrs():
                attr.lock(False)
        self.refresh_attr_tree()

    def break_connection(self):
        with core.Chunk():
            for attr in self.get_selected_attrs():
                attr.break_connection()
        self.refresh_attr_tree()

    def show_context_menu(self, point):
        context_menu = QMenu(self)
        context_menu.addAction(create_action('Set Value', self.set_value, self))
        context_menu.addAction(create_action('Lock', self.lock, self))
        context_menu.addAction(create_action('Unlock', self.unlock, self))
        context_menu.addAction(create_action('Break Connection', self.break_connection, self))
        context_menu.exec_(self.mapToGlobal(point))

    def get_selected_attrs(self):
        for widget in self.attrs_tree.selectedItems():
            return widget.data(0, Qt.UserRole)

    @classmethod
    def get_selected(cls, limit=30):
        selection = cmds.ls(sl=True, objectsOnly=True) or list()
        if len(selection) > limit:
            cmds.warning('{0} : Selection too broad. Limit set to {1}'.format(cls.__name__, limit))
            return selection[:limit]
        return selection

    def refresh(self):
        self.nodes_tree.clear()
        selection = self.get_selected()

        for index, node in enumerate(selection):
            type_ = cmds.objectType(node)
            widget = QTreeWidgetItem((node, type_))
            icon = QIcon(':/{0}.svg'.format(type_))
            widget.setIcon(1, icon)
            self.nodes_tree.addTopLevelItem(widget)

        iterator = QTreeWidgetItemIterator(self.nodes_tree)
        while iterator.value():
            widget = iterator.value()
            widget.setSelected(True)

            iterator += 1

        self.refresh_attr_tree()
        self.refresh_menu_bar()

    def refresh_menu_bar(self):
        self.menu_bar.clear()

        selection_menu = self.menu_bar.addMenu('Selection')
        recently_selected_menu = selection_menu.addMenu('Recently Selected')
        saved_selections = selection_menu.addMenu('Saved Selections')
        selection_menu.addAction(create_action('Save Selection', self.save_selection, self))
        selection_menu.addAction(create_action('Select Children', self.select_children, self))
        selection_menu.addAction(create_action('Select All Descendents', self.select_all_descendents, self))

        for selection in self.selection_file.get_recent():
            action = create_action(list_to_label(selection, limit=50), lambda x=selection: self.select(x), self)
            recently_selected_menu.addAction(action)

        for name, selection in self.selection_file.get_saved():
            label = '{0}: {1}'.format(name, list_to_label(selection, limit=50))
            action = create_action(label, lambda x=selection: self.select(x), self)
            saved_selections.addAction(action)

    def refresh_attr_tree(self):
        self.attrs_tree.clear()

        attrs_dict = collections.OrderedDict()
        nodes = self.get_selected_nodes()
        for node in nodes:
            attrs = (cmds.listAttr(node, cb=True) or list()) + (cmds.listAttr(node, k=True) or list())
            for attr in attrs:
                full = core.f_attr(node, attr)
                if core.Attribute.is_one(full):
                    if attr not in attrs_dict:
                        attrs_dict[attr] = core.GroupOfAttributes()
                    attrs_dict[attr].append(core.Attribute(full))

        for attr, attr_grp in attrs_dict.items():
            if len(attr_grp.get_attributes()) != len(nodes):
                continue
            locked = attr_grp.are_locked()
            source_connected = attr_grp.are_source_connected()
            value = attr_grp.get_value()
            type_ = attr_grp.get_type()
            widget = QTreeWidgetItem((attr_grp.get_attributes()[0].get_nice_name(), format_value(value) if value is not None else '...'))
            msg = '{0} - type: {1}, value: {2}'.format(attr, str(type_) if type_ is not None else '...', value)
            widget.setToolTip(0, msg)
            widget.setStatusTip(0, msg)
            widget.setData(0, Qt.UserRole, attr_grp)
            if source_connected > 0:
                widget.setText(0, '-> {0}'.format(widget.text(0)))

            if attr_grp.are_destination_connected() > 0:
                widget.setText(0, '{0} ->'.format(widget.text(0)))

            for index in range(self.attrs_tree.columnCount()):
                if locked > 0:
                    color = QColor('gray')
                elif source_connected > 0:
                    color = QColor(255, 255, 150)
                else:
                    color = QColor('lightGray')

                widget.setTextColor(index, color)

            self.attrs_tree.addTopLevelItem(widget)

    def set_script_job_enabled(self, enabled):
        if enabled and self.script_job_number < 0:
            self.script_job_number = cmds.scriptJob(event=["SelectionChanged", partial(self.selection_changed)], protected=True)
        elif not enabled and self.script_job_number >= 0:
            cmds.scriptJob(kill=self.script_job_number, force=True)
            self.script_job_number = -1

    def selection_changed(self):
        self.selection_file.add_recent(self.get_selected())
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
        self.selection_file.add_saved([core.randomString(stringLength=8), self.get_selected()])
        self.refresh_menu_bar()

    def get_listed_nodes(self):
        nodes = list()
        iterator = QTreeWidgetItemIterator(self.nodes_tree)
        while iterator.value():
            widget = iterator.value()
            nodes.append(widget.text(0))

            iterator += 1
        return nodes

    def enterEvent(self, *args, **kwargs):
        super(AttributeEditorPlus, self).enterEvent(*args, **kwargs)
        if self.get_selected() != self.get_listed_nodes():
            print 'Refresh'
            self.refresh()
