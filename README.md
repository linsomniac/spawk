# TextChomp Text Processing Library

## Overview

This is a text processing library inspired by the AWK tool, in a Python
style.  It is currently a work in progress, exploring different ways of
achieving this.  The library may change significantly as it matures.

## Abilities

- Read lines from an input.

- Call a function if a regex is matched.

- Call a function on every line between a start and end regex.

- Enrich lines from the input such as what line number in the input it came
  from.  Pipeline elements can enrich it as well, such as "split()" to set
  a "fields" attribute on the line containing the split-out fields.

## Snippets

Select lines that start with "a" and save off lines within it that contain a
"q" to "t.context.data":

```python
t = textchomp.TextChomp(sys.stdin)
t.grep(r'^a')
t.context.data = ''

@t.pattern(r'q')
def line(context, line):
    context.data += line
t.run()
```

The context includes the regex match.  The line data is a string subclass with
some extra attributes for line numbers and extracting fields:

```python
t = textchomp.TextChomp(sys.stdin).split()
@t.pattern(r'hello (\S+)')
def line(context, line):
    print(
        'Line {} says hello to {}.  Field 3 is: {}'.format(
        line.line_number, context.regex.group(1), line.fields[2]))
t.run()
```

When a line contains "CREATE TABLE", save it and the remaining lines up until
a closing paren and semi-colon into "t.context.data".  This parses out the
table creation from a SQL schema.

Within a range there is an addition context that includes the line number
within the range, and if it is the last line.  So we can add line numbers and
print the create statement at the end:

```python
t = textchomp.TextChomp(sys.stdin)
t.context.data = ''

@t.range(r'CREATE TABLE', r'\);')
def line(context, line):
    context.data += (('line %d:' % context.range.line_number) + line)
    if context.range.is_last_line:
        print(context.data)
        context.data = ''
t.run()
```

There is also a FileFollower which implements "tail -F" functionality.
It will look for new data to be appended to the file, and will re-open
the file if it shrinks, or a new file is created in place of the old.
Simple "tail +0 -F" implementation:

```python
for line in textchomp.FileFollower('/var/log/syslog'):
    print(line.rstrip())
```

## Examples

There are some example programs in the "Examples" directory:

- "css_colors_to_rgba" - Read lines with CSS colors in the in the form
  "#000000" or "#000" and convert them to "rgba(0, 0, 0, 0.3)".

- "extract_db_tables" - Read a database dump and extract out the "CREATE TABLE"
  commands to reproduce the schema.  This is an example of the "range()"
  decorator.
