from PySide2.QtWidgets import *
from PySide2.QtGui import *
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
from maya import cmds
import copy


def f_attr(node, attr):
    return '{0}.{1}'.format(node, attr)


def get_widget(object_name, type_):
    pointer = omui.MQtUtil.findControl(object_name)
    return wrapInstance(long(pointer), type_)


class AttributeEditorPlus(QDialog):
    transform_attrs = ['translateX', 'translateY', 'translateZ',
                       'rotateX', 'rotateY', 'rotateZ',
                       'scaleX', 'scaleY', 'scaleZ',
                       'shearXY', 'shearXZ', 'shearYZ',
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
        selection = cmds.ls(sl=True) or list()

        if not selection:
            return

        self.node_name.setText(selection[-1])
        self.node_type.setText(cmds.nodeType(selection[-1]))

        user_defined_attrs = cmds.listAttr(selection[-1], userDefined=True)

        attributes = copy.deepcopy(self.groups)
        attributes['userDefined'] = user_defined_attrs

        for group, attributes in attributes.items():
            group_lay = QVBoxLayout()

            group_box = QGroupBox()
            group_box.setTitle(group)
            group_box.setLayout(group_lay)
            self.attrs_lay.addWidget(group_box)

            for attr in attributes:
                full_attr = f_attr(selection[-1], attr)
                if not cmds.objExists(full_attr):
                    print attr
                    continue

                value = cmds.getAttr(full_attr)
                locked = cmds.getAttr(full_attr, lock=True)
                type_ = cmds.getAttr(full_attr, type=True)

                attr_name = QLineEdit()
                attr_name.setText(attr)
                attr_name.setEnabled(not locked)

                attr_type = QLineEdit()
                attr_type.setText(type_)
                attr_type.setEnabled(not locked)

                attr_value = self.create_value_widget(type_, value)
                attr_value.setEnabled(not locked)

                attr_lay = QHBoxLayout()
                attr_lay.addWidget(attr_name)
                attr_lay.addWidget(attr_type)
                attr_lay.addWidget(attr_value)

                group_lay.addLayout(attr_lay)

    def create_value_widget(self, type_, value):
        line_edit = QLineEdit()
        if type_ == 'double':
            line_edit.setValidator(QDoubleValidator())
        line_edit.setText(str(value))
        return line_edit
