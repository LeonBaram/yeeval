# yeeval

Short for "yaml eval". Allows you to define computed values in yaml, evaluate them, and update the yaml in-place.

## Example

```yaml
a: 1
b: 2
c: _ #= a+b
```

After running the script on a yaml file with the above contents, the yaml file will be re-printed as follows:

```yaml
a: 1
b: 2
c: 3 #= a+b
```

## Usage

`yeeval.py <filename>`

## Rationale

Spreadsheets are a very powerful tool, not just for visualizing data, but for dynamic computation. Any cell of a spreadsheet may contain not just a fixed value, but also a value defined by a *formula*, which will be computed on the fly. More than that, this formula can reference other cells in the spreadsheet, including *other* cells defined by formulae.

However, spreadsheets (at time of writing) are overwhelmingly GUI applications. This project seeks to capture some of that dynamic computational capability, by allowing you to create "cells" (yaml values) defined by "formulae" (definitions written as Python expressions), which can reference other "cells" as well.

On a personal level, my use-case is that I want a D&D 5e character sheet that (a) has the benefits of using a spreadsheet, and (b) I can open using Neovim.

## What the script does

When executed, the script does the following:

- parse the provided yaml file into an intermediate representation using [ruamel.yaml](https://yaml.dev/doc/ruamel-yaml/)
- look for any occurrence of a value followed by a *definition comment*
    - a definition comment is any comment starting with an equal sign, which immediately follows a value. e.g. `a: _ #= x+y-z`
    - each such value is treated as a *computed value*
    - its definition (taken from the comment) is evaluated as a *Python expression* (see "Syntax" below)
    - the current value is replaced by the result of the evaluation

## Syntax

Each definition is evaluated as a Python expression. You can reference any other part of the provided yaml file (as in the example above). In the case of lists or nested properties, you can use indexes and dot notation respectively. You can also use any Python global builtin. Some examples:

- `_ := a.b + c` -- add a property to a nested property
- `_ := a[0] * a[-1]` -- multiply the first and last elements of a list
- `_ := sum(a)` -- add all elements of a list

### Self-Reference

When you write the definition for a particular cell, you can refer to its current value using a reserved identifier, `_`:

```yaml
a: 1
b: 2
c: 1 #= a + b + _
```

In the above example, after running `yeeval` once, the value of `c` will be 4. After running `yeeval` another time, it will be 7.

## Prelude

yeeval also allows you to add a *prelude* to a yaml file, using a similar form of comment:

```yaml
#=def example():
#=  return 2+2
a: 1
b: 2
c: _ #= example()
```

After running yeeval on the above yaml file, the result will be:

```yaml
#=def example():
#=  return 2+2
a: 1
b: 2
c: 4 #= example()
```

**Note:** the prelude is evaluated without any "knowledge" of the yaml file. This means that, unlike the previously described inline comments, code within the prelude can't refer to values in the yaml.
