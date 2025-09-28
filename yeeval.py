#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
#     "ruamel-yaml",
# ]
# ///
import sys
import importlib
import importlib.util
import os
from io import TextIOWrapper
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

PREFIX = "#="

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)

helper_spec = None
helper_module = None

root_treenode = None


cached = dict()
seen = set()


def prelude() -> str:
    starting_comments = root_treenode._ast_node._yaml_get_pre_comment()
    lines = []
    for comment_node in starting_comments:
        comment = comment_node.value
        if comment.startswith(PREFIX):
            lines.append(comment.removeprefix(PREFIX))
    return '\n'.join(lines)


def evaluate(expr: str, curr_val=None):
    global cached
    global seen
    global root_treenode
    global helper_module
    global helper_spec
    if expr in cached:
        return cached[expr]

    if expr in seen:
        raise RecursionError(f"detected cycle for expression: {expr}")

    seen.add(expr)

    if helper_spec is not None and helper_module is not None:
        helper_spec.loader.exec_module(helper_module)
        exec("from helper import *", None, root_treenode)
    exec(prelude(), None, root_treenode)
    root_treenode['_'] = curr_val
    result = eval(expr, None, root_treenode)
    cached[expr] = result
    return result


def is_ast_node(x) -> bool:
    return isinstance(x, CommentedMap)


class TreeNode:
    def __init__(self, ast_node: CommentedMap):
        self._ast_node = ast_node
        for key, val in ast_node.items():
            if is_ast_node(val):
                setattr(self, key, TreeNode(val))
            elif isinstance(val, list):
                values = []
                for i in range(len(val)):
                    if is_ast_node(val[i]):
                        values.append(TreeNode(val[i]))
                    else:
                        values.append(val[i])
                setattr(self, key, values)
            else:
                setattr(self, key, val)

    def __is_computed(self, key: str) -> bool:
        return (key in self._ast_node.ca.items
                and self._ast_node.ca.items[key][2] is not None
                and self._ast_node.ca.items[key][2].value.startswith(PREFIX))

    def __get_definition(self, key: str) -> str:
        return self._ast_node.ca.items[key][2].value.removeprefix(PREFIX)

    def _evaluate(self, debug=False):
        for key in dir(self):
            val = getattr(self, key)
            if debug:
                print(f"obj.{key} = {val!r}")
            if isinstance(val, TreeNode):
                val._evaluate(debug)

    def __getitem__(self, key: str):
        try:
            return self.__getattribute__(key)
        except AttributeError:
            try:
                return globals()['__builtins__'].__getattribute__(key)
            except AttributeError:
                return sys.modules[key]

    def __setitem__(self, key: str, val):
        self.__setattr__(key, val)

    def __getattribute__(self, key: str):
        curr = object.__getattribute__(self, key)
        if key.startswith("_"):
            return curr
        if not self.__is_computed(key):
            return curr
        definition = self.__get_definition(key)
        val = evaluate(definition, curr)
        self._ast_node[key] = val
        return val


def load(file: TextIOWrapper) -> TreeNode:
    file.seek(0)
    yaml_ast = yaml.load(file)
    return TreeNode(yaml_ast)


def save(file: TextIOWrapper, data: TreeNode):
    file.seek(0)
    file.truncate(0)
    yaml.dump(data._ast_node, file)


def debug_dump(obj):
    for attr in dir(obj):
        print("obj.%s = %r" % (attr, getattr(obj, attr)))


def main():
    assert len(sys.argv) == 2, "usage: yeeval.py <filename>"
    filename = sys.argv[1]
    directory = os.path.dirname(os.path.realpath(filename))
    helper_file = f'{directory}/helper.py'
    if os.path.exists(helper_file):
        global helper_spec
        global helper_module
        helper_spec = importlib.util.spec_from_file_location(
            "helper", helper_file)
        helper_module = importlib.util.module_from_spec(helper_spec)
        sys.modules["helper"] = helper_module
        helper_spec.loader.exec_module(helper_module)
    with open(filename, "r+") as f:
        try:
            # save copy of original file in case of unexpected errors
            original_file = f.read()
            global root_treenode
            root_treenode = load(f)
            exec(prelude())
            root_treenode._evaluate()
            save(f, root_treenode)
        except Exception as e:
            # write original file back, then throw
            f.seek(0)
            f.truncate(0)
            f.write(original_file)
            raise e


if __name__ == "__main__":
    main()
