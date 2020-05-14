from maya import cmds, mel
import json
import os
import random
import string


def randomString(stringLength=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))


def search_in(item, ls):
    true_count = ls.count(item)

    if true_count == len(ls):
        return 2
    elif true_count > 0:
        return 1
    return 0


def remove_duplicates(ls):
    new_ls = list()
    for item in ls:
        if not item in new_ls:
            new_ls.append(item)
    return new_ls


def subtract_list(a, b):
    result = list()
    for item in a:
        if item not in b:
            result.append(item)
    return result


def f_attr(node, attr):
    return '{0}.{1}'.format(node, attr)


def select(items):
    result = list()
    for item in items:
        if cmds.objExists(item):
            result.append(item)
        else:
            cmds.warning('Unable to find \'{0}\' in the scene. Therefore it cannot be selected.'.format(item))

    cmds.select(result, ne=True)


def maya_type_to_python_type(type_):
    float_attributes = ('double', 'doubleLinear', 'doubleAngle')
    bool_attributes = ('bool',)
    int_attributes = ('long', 'enum')
    if type_ in float_attributes:
        return float
    if type_ in bool_attributes:
        return bool
    if type_ in int_attributes:
        return int

    return None


def maya_types_to_python_types(types):
    p_types = list()
    for type_ in types:
        p_type = maya_type_to_python_type(type_)
        p_types.append(p_type)
    return p_types


def is_list_full_of_same(ls):
    unique_values = remove_duplicates(ls)
    if len(unique_values) == 1:
        return True
    return False


class SelectionFile(object):
    saved = 'saved'
    recent = 'recent'
    content_template = {recent: list(), saved: list()}

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
        return os.path.isdir('/'.join(location))

    def get_path(self):
        return self.__path

    def exists(self):
        return os.path.exists(self.get_path())

    def read(self):
        if not self.exists():
            self.write(self.content_template)

        with open(self.get_path(), 'r') as f:
            return json.load(f)

    def get_recent(self):
        return self.read()[self.recent]

    def get_saved(self):
        return self.read()[self.saved]

    def write(self, item):
        with open(self.get_path(), 'w') as f:
            return json.dump(item, f)

    def add_saved(self, ls):
        self.add(self.saved, ls)

    def add_recent(self, ls):
        if not ls:
            return
        self.add(self.recent, ls, limit=10)

    def add(self, cat, obj, limit=0):
        content = self.read()
        if content[cat]:
            if content[cat][0] == obj:
                return
        if limit > 0:
            if len(content[cat]) >= limit:
                content[cat].pop()
        content[cat].insert(0, obj)
        self.write(content)


class GroupOfAttributes(object):

    def __init__(self):
        self.__attrs = list()

    def __iter__(self):
        return iter(self.get_attributes())

    def append(self, attr):
        if isinstance(attr, Attribute):
            self.__attrs.append(attr)

    def get_attributes(self):
        return self.__attrs

    def are_locked(self):
        return search_in(True, [item.is_locked() for item in self.get_attributes()])

    def are_source_connected(self):
        return search_in(True, [item.is_source_connected() for item in self.get_attributes()])

    def are_destination_connected(self):
        return search_in(True, [item.is_destination_connected() for item in self.get_attributes()])

    def get_type(self):
        types = [item.get_type() for item in self.get_attributes()]
        if is_list_full_of_same(types):
            return types[0]
        return None

    def get_python_type(self):
        types = [item.get_type() for item in self.get_attributes()]
        types = maya_types_to_python_types(types)
        if is_list_full_of_same(types):
            return types[0]
        return None

    def get_value(self):
        values = [item.get_value() for item in self.get_attributes()]
        if is_list_full_of_same(values):
            return values[0]
        return None


# values = [item.get_value() for item in full_attrs]
#             unique_values = core.remove_duplicates(values)
#             value = str(unique_values[0]) if len(unique_values) == 1 else '...'
#
#             types = [item.get_type() for item in full_attrs]
#             unique_types = core.remove_duplicates(types)
#             type_ = str(unique_types[0]) if len(unique_types) == 1 else '...'
#
#             locked = core.search_in(True, [item.is_locked() for item in full_attrs])
#
#             connected = core.search_in(True, [item.is_source_connected() for item in full_attrs])


class Attribute(object):

    def __init__(self, attr):
        if not self.is_one(attr):
            cmds.error('\'{0}\' is not a valid {1}.'.format(attr, self.__class__.__name__))
        self.__attr = attr

    @classmethod
    def is_one(cls, attr):
        if attr.count('.') > 0:
            if cmds.objExists(attr):
                return True

    def get_name(self):
        return self.__attr

    def get_type(self):
        return cmds.getAttr(self.get_name(), type=True)

    def get_value(self):
        value = cmds.getAttr(self.get_name())
        if value is not None:
            return value
        return ''

    def is_locked(self):
        return cmds.getAttr(self.get_name(), lock=True)

    def is_source_connected(self):
        if cmds.listConnections(self.get_name(), source=True, destination=False):
            return True
        return False

    def is_destination_connected(self):
        if cmds.listConnections(self.get_name(), source=False, destination=True):
            return True
        return False

    def set_value(self, value):
        if self.get_type() == 'string':
            cmds.setAttr(self.get_name(), value, type='string')
        else:
            cmds.setAttr(self.get_name(), value, clamp=True)

    def get_node(self):
        return self.get_name().split('.')[0]

    def get_attr(self):
        return '.'.join(self.get_name().split('.')[1:])

    def get_long_name(self):
        return cmds.attributeName(self.get_name(), long=True)

    def get_nice_name(self):
        return cmds.attributeName(self.get_name())

    def get_default_value(self):
        if self.get_type() == 'string':
            return ''
        elif self.get_long_name().startswith('scale'):
            return 1
        elif self.get_long_name().startswith('translate'):
            return 0
        elif self.get_long_name().startswith('rotate'):
            return 0
        elif self.get_long_name() == 'visibility':
            return True
        return cmds.addAttr(self.get_name(), q=True, defaultValue=True)

    def lock(self, value):
        cmds.setAttr(self.get_name(), lock=value)

    def break_connection(self):
        mel.eval('source generateChannelMenu.mel;')
        mel.eval('CBdeleteConnection "{0}";'.format(self.get_name()))


class Chunk(object):

    def __enter__(self):
        cmds.undoInfo(openChunk=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        cmds.undoInfo(closeChunk=True)
