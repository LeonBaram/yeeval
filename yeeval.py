#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
# ]
# ///
import sys
from io import TextIOWrapper
from types import SimpleNamespace
from typing import Any
from yaml import load, dump
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

root = None


cached = dict()
seen = set()


def evaluate(expr):
    global cached
    global seen
    global root
    if expr in cached:
        return cached[expr]

    if expr in seen:
        raise RecursionError(f"detected cycle for expression: {expr}")

    seen.add(expr)
    result = eval(expr, None, root)
    cached[expr] = result
    return result


def is_computed_value(val: Any) -> bool:
    """
    a value is considered "computed" if it is a string with a walrus operator (":=")
    """
    return isinstance(val, str) and ':=' in val


class TreeNode(SimpleNamespace):
    def __getitem__(self, key: str):
        try:
            if key.endswith('__def'):
                key = key.removesuffix('__def')
                return self.__dict__[key]
            return self.__getattribute__(key)
        except AttributeError:
            return globals()['__builtins__'].__getattribute__(key)

    def __getattribute__(self, name: str):
        val = object.__getattribute__(self, name)
        if is_computed_value(val):
            value, definition = val.split(':=')
            value = evaluate(definition)
            self.__dict__[name] = f"{value} := {definition.strip()}"
            return value
        else:
            return val


def to_treenode(tree: Any) -> TreeNode:
    if isinstance(tree, dict):
        return TreeNode(**{key: to_treenode(val) for key, val in tree.items()})
    return tree


def to_raw(tree: Any) -> Any:
    if isinstance(tree, TreeNode):
        for key in tree.__dict__:
            tree.__getattribute__(key)
        return {key: to_raw(val) for key, val in tree.__dict__.items()}
    return tree


def load_yaml(file: TextIOWrapper) -> TreeNode:
    data: Any = load(file, Loader=Loader)
    global root
    root = to_treenode(data)
    return root


def save_yaml(data: TreeNode, file: TextIOWrapper):
    file.seek(0)
    file.truncate(0)
    dump(to_raw(data), file, Dumper=Dumper, sort_keys=False)


def main() -> None:
    assert len(sys.argv) == 2, "usage: yeeval.py <filename>"
    filename = sys.argv[1]
    with open(filename, "r+") as f:
        data = load_yaml(f)
        save_yaml(data, f)


if __name__ == "__main__":
    main()
