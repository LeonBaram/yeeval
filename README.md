# yeeval

Short for "yaml eval". Allows you to define computed values in yaml as follows:

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

## What the script does

When executed, the script does the following:

- parse the provided yaml file into an intermediate representation using [PyYAML](https://pyyaml.org/)
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
