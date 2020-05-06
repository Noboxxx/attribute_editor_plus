from maya import cmds
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
    print a, b
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
