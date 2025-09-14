# yeeval

Short for "yaml eval". Allows you to define computed values in yaml as follows:

```yaml
a: 1
b: 2
c: _ := a+b
```

After running the script on a yaml file with the above contents, the yaml file will be re-printed as follows:

```yaml
a: 1
b: 2
c: 3.0 := a+b
```

## Usage

`yeeval.py <filename>`

## What the script does

When executed, the script does the following:

- parse the provided yaml file into an intermediate representation using [PyYAML](https://pyyaml.org/)
- look for any occurrence of a string value containing the walrus operator (`:=`)
- for each such string:
    - treat everything to the right of the operator as the *definition*
    - evaluate the definition as a Python expression (see "Syntax" section below)
    - modify the string in-place such that the definition is the same, but everything to the left of the operator is replaced with the newly-evaluated value
- write the now-updated representation back to the original file

## Syntax

Each definition is evaluated as a Python expression. You can reference any other part of the provided yaml file (as in the example above). In the case of lists or nested properties, you can use indexes and dot notation respectively. You can also use any Python global builtin. Some examples:

- `_ := a.b + c` -- add a property to a nested property
- `_ := a[0] * a[-1]` -- multiply the first and last elements of a list
- `_ := sum(a)` -- add all elements of a list

## Limitations

- **No comment support** -- if the input yaml has any comments, they are erased
- **autoformatting, but worse** -- the script re-prints the entire yaml file when run, resetting any whitespace formatting/indentation

## TODO
- switch from PyYAML to [ruamel.yaml](https://yaml.dev/doc/ruamel.yaml/example/#top)
    - should fix the "no comments" and "worse autoformatting" limitations
