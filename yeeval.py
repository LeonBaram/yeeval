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
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.tokens import CommentToken
import fileinput
import argparse

# get name of helper file from CLI args
parser = argparse.ArgumentParser(
    prog="yeeval.py",
    description="updates yaml values based on inline definition comments",
    epilog="Usage: cat myfile.yml | yeeval.py > mynewfile.yml")
parser.add_argument("-H", "--helper")

args = parser.parse_args()
helper = args.helper
if helper is None:
    helper = "./helper.py"

CommentedMapOrSeq = CommentedMap | CommentedSeq

PREFIX = "#="

_ = None

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 500

helper_spec = None
helper_module = None

root = None


def eprint(*args, **kwargs):
    """like `print()`, but outputs to stderr"""
    print(*args, file=sys.stderr, **kwargs)


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


def evaluate(expr: str, curr_val=None, line_number=-1):
    """
    evaluate the given expression as Python code, with the following context:
    - all values from the YAML file, accessible using dot notation
    - all code from the prelude string
    - all code from the helper-file
    - optionally, a "current value" for the expression to use
      (useful for YAML nodes whose computation takes
      their current state/value into account)
    """
    global root, _
    try:
        # add user-provided code from prelude
        exec(prelude(), globals(), locals())

        _ = curr_val

        result = eval(expr, globals(), locals())

    except Exception as err:
        err_name = type(err).__name__
        eprint(f"{err_name} on line {line_number}: {err}")
        result = _

    if result is None:
        eprint(
            f'expression "{expr}" evaluated to "None"; using existing value "{_}"')
        result = _

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
        if isinstance(t, CommentToken):
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


def overwrite_getitem(self: CommentedMap | CommentedSeq, key: str | int):
    """
    overwrites CommentedMap and CommentedSeq's builtin "getitem" method:

    if self[key] has a "definition", ignore the current value and (re)compute
    it based on the definition.

    otherwise retrieve the current value as normal.

    (a "definition" is an inline comment starting with PREFIX.)
    (PREFIX is a module-level variable, see source code.)
    """
    assert isinstance(self, CommentedMap) or isinstance(self, CommentedSeq)
    superclass = dict if isinstance(self, CommentedMap) else list
    curr = superclass.__getitem__(self, key)

    definition = get_definition(self, key)
    if definition is not None:
        line_number = self.lc.key(key)[0]+1
        return evaluate(definition, curr, line_number)

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


def debug_dump(obj):
    for attr in dir(obj):
        print("obj.%s = %r" % (attr, getattr(obj, attr)))


def load_helper_file():
    """
    add user-provided code from helper-file
    """
    args = parser.parse_args()
    helper_file = args.helper
    if helper_file is None:
        helper_file = "./helper.py"
    if os.path.exists(helper_file):
        global helper_spec, helper_module
        helper_spec = importlib.util.spec_from_file_location(
            "helper", helper_file)
        helper_module = importlib.util.module_from_spec(helper_spec)
        sys.modules["helper"] = helper_module
        helper_spec.loader.exec_module(helper_module)
        import helper
        globals().update(helper.__dict__)


def main():
    load_helper_file()
    with fileinput.input(encoding="utf-8") as input_stream:
        input_lines = "".join(input_stream)
    try:
        # load YAML AST
        global root
        root = yaml.load(input_lines)

        globals().update(root)

        # modify AST nodes to evaluate inline definitions
        CommentedMap.__getitem__ = overwrite_getitem
        CommentedSeq.__getitem__ = overwrite_getitem

        # modify AST nodes to allow dot-notation
        CommentedMap.__getattr__ = commentedmap_getattr

        # print updated YAML
        yaml.dump(root, sys.stdout)
    except Exception as e:
        # write original input to stdout
        sys.stdout.write(input_lines)
        raise e


if __name__ == "__main__":
    main()
