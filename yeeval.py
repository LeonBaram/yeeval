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
from ruamel.yaml.comments import CommentedMap, CommentedSeq

CommentedMapOrSeq = CommentedMap | CommentedSeq

PREFIX = "#="

_ = None

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 500

helper_spec = None
helper_module = None

root = None


cached = dict()
seen = set()


def prelude() -> str:
    """
    return the contents of the prelude comment as a string.
    each line of the prelude comment is expected to start with PREFIX.
    lines that do not start with PREFIX are skipped.
    """
    starting_comments = root._yaml_get_pre_comment()
    lines = []
    for comment_node in starting_comments:
        comment = comment_node.value
        if comment.startswith(PREFIX):
            lines.append(comment.removeprefix(PREFIX))
    return '\n'.join(lines)


def evaluate(expr: str, curr_val=None):
    """
    evaluate the given expression as Python code, with the following context:
    - all values from the YAML file, accessible using dot notation
    - all code from the prelude string
    - all code from the helper-file
    - optionally, a "current value" for the expression to use
      (useful for YAML nodes whose computation takes
      their current state/value into account)
    """
    global cached, seen, root, helper_module, helper_spec, _
    if expr in cached:
        return cached[expr]

    if expr in seen:
        raise RecursionError(f"detected cycle for expression: {expr}")

    seen.add(expr)

    # add user-provided code from prelude and helper-file
    if helper_spec is not None and helper_module is not None:
        helper_spec.loader.exec_module(helper_module)
        exec("from helper import *", globals(), locals())
    exec(prelude(), globals(), locals())

    _ = curr_val

    result = eval(expr, globals(), locals())
    cached[expr] = result

    _ = None

    return result


def get_comment(node: CommentedMapOrSeq, key: str | int) -> str:
    """
    gets the inline comment next to node[key].
    if there is no comment, defaults to "".
    """
    if not ((isinstance(node, CommentedMap)
             or isinstance(node, CommentedSeq))):
        return ""
    if key not in node.ca.items:
        return ""
    tokens = node.ca.items[key]
    comment_str = ""
    for t in tokens:
        if t is not None:
            comment_str = t.value
            break
    return comment_str


def get_definition(node: CommentedMapOrSeq, key: str | int) -> str | None:
    """
    gets the "definition" of node[key]. if it does not have one, returns None.

    (a "definition" is an inline comment starting with PREFIX.)
    (PREFIX is a module-level variable, see source code.)
    """
    comment = get_comment(node, key)
    if comment.startswith(PREFIX):
        return comment.removeprefix(PREFIX)
    else:
        return None


def commentedmap_getitem(self: CommentedMap, key: str | int):
    """
    overwrites CommentedMap's builtin "getitem" method as follows:

    if self[key] has a "definition", ignore the current value and (re)compute
    it based on the definition.

    otherwise retrieve the current value as normal.

    (a "definition" is an inline comment starting with PREFIX.)
    (PREFIX is a module-level variable, see source code.)
    """
    curr = dict.__getitem__(self, key)
    definition = get_definition(self, key)
    if definition is not None:
        return evaluate(definition, curr)
    return curr


def commentedseq_getitem(self: CommentedSeq, key: str | int):
    """
    overwrites CommentedSeq's builtin "getitem" method as follows:

    if self[key] has a "definition", ignore the current value and (re)compute
    it based on the definition.

    otherwise retrieve the current value as normal.

    (a "definition" is an inline comment starting with PREFIX.)
    (PREFIX is a module-level variable, see source code.)
    """
    curr = list.__getitem__(self, key)
    definition = get_definition(self, key)
    if definition is not None:
        return evaluate(definition, curr)
    return curr


def commentedmap_getattr(self: CommentedMap, key: str):
    """
    implements the builtin "getattr" method for CommentedMap,
    by making it an alias of its builtin "getitem" method.

    this allows dot-notation access (a.b)
    to be equivalent to string indexing (a["b"]).
    """
    if key in self:
        return self[key]
    raise AttributeError(f'no such key "{key}"')


def load(file: TextIOWrapper) -> CommentedMap:
    file.seek(0)
    return yaml.load(file)


def save(file: TextIOWrapper, data: CommentedMap):
    file.seek(0)
    file.truncate(0)
    yaml.dump(data, file)


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
        import helper
        globals().update(helper.__dict__)
    with open(filename, "r+") as f:
        try:
            # save copy of original file in case of unexpected errors
            original_file = f.read()

            # load YAML AST
            global root
            root = load(f)

            # modify AST nodes to evaluate inline definitions
            CommentedMap.__getitem__ = commentedmap_getitem
            CommentedSeq.__getitem__ = commentedseq_getitem

            # modify AST nodes to allow dot-notation
            CommentedMap.__getattr__ = commentedmap_getattr

            globals().update(root)

            # write YAML AST back to file
            save(f, root)
        except Exception as e:
            # write original file back, then throw
            f.seek(0)
            f.truncate(0)
            f.write(original_file)
            raise e


if __name__ == "__main__":
    main()
