from PySide2.QtWidgets import *
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
import pymel.core as pm
from maya import cmds


class Attribute(object):

    def __init__(self, name):

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
    for item in cmds.listAttr(node.name(), userDefined=True):
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


class AttributeEditorPlus(QDialog):
    transform_attrs = ['translate', 'rotate', 'scale', 'shear',
                       'rotateOrder', 'rotateAxis',
                       'inheritsTransform']

    visibility_attrs = ['visibility']

    groups = {
        'transform': transform_attrs,
        'visibility': visibility_attrs
    }

    def __init__(self, parent):
        super(AttributeEditorPlus, self).__init__(parent)

        self.node_name = QLineEdit()
        self.node_type = QLineEdit()

        self.node_info_lay = QHBoxLayout()
        self.node_info_lay.addWidget(self.node_name)
        self.node_info_lay.addWidget(self.node_type)

        self.attrs_lay = QVBoxLayout()

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
        selection = pm.selected()
        common_attributes = get_intersection([get_user_attrs(node) for node in selection])

        for attr in common_attributes:
            print attr

        # for node in selection:
        #     self.node_name.setText(node.name())
        #     self.node_type.setText(node.type())
        #
        #     user_defined_attrs = list()
        #
        #     for item in pm.listAttr(node, userDefined=True):
        #         if isinstance(item, pm.Attribute):
        #             attr = item
        #         else:
        #             try:
        #                 attr = pm.Attribute(f_attr(node, item))
        #             except:
        #                 continue
        #
        #         user_defined_attrs.append(attr)
        #
        #     attributes = dict()
        #     # for group, attrs in self.groups.items():
        #     #     attributes[group] = list()
        #     #     for attr in attrs:
        #     #         attributes[group].append(pm.PyNode(f_attr(node, attr)))
        #
        #     attributes['userDefined'] = user_defined_attrs
        #
        # for title, attrs in commun_attributes.items():
        #     widget = self.create_group_widget(title, attrs)
        #     self.attrs_lay.addWidget(widget)

    def create_group_widget(self, title, attrs):
        group_box_lay = QVBoxLayout()

        group_box = QGroupBox()
        group_box.setTitle(title)
        group_box.setLayout(group_box_lay)

        for attr in attrs:
            attr_lay = self.create_attr_lay(attr)
            if attr_lay is None:
                continue
            group_box_lay.addLayout(attr_lay)

        return group_box

    def create_attr_lay(self, attr):
        children = list()

        try:
            children = attr.children()
        except:
            pass

        name = attr.name(includeNode=False)
        locked = attr.isLocked()

        name_line = QLineEdit()
        name_line.setText(name)

        type_line = QLineEdit()
        type_line.setText(attr.type())

        value_lay = self.create_value_layout(attr, lock=locked)

        attr_info_lay = QHBoxLayout()
        attr_info_lay.addWidget(name_line)
        # attr_info_lay.addWidget(type_line)
        attr_info_lay.addLayout(value_lay)

        attr_children_lay = QVBoxLayout()

        if children:
            widget = self.create_group_widget('children of {0}'.format(name), children)
            attr_children_lay.addWidget(widget)

        attr_lay = QVBoxLayout()
        attr_lay.addLayout(attr_info_lay)
        attr_lay.addLayout(attr_children_lay)

        return attr_lay

    def create_value_layout(self, attr, lock=False):

        lay = QHBoxLayout()
        raw_value = attr.get()

        if attr.type() == 'double3':
            for value in raw_value:
                line = QLineEdit()
                line.setDisabled(lock)
                line.setText(str(value))
                lay.addWidget(line)
        else:
            line = QLineEdit()
            line.setDisabled(lock)
            line.setText(str(raw_value))
            lay.addWidget(line)

        return lay
