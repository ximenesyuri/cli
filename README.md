# About

`cli` is a lightweight solution to build Python CLIs quickly following a [fastAPI](https://github.com/fastapi/fastapi)-like syntax. No dependencies.

# Install

With `pip`:

```
pip install git+https://github.com/pythonalta/cli
```

With [py](https://github.com/ximenesyuri/py):

```
py install pythonalta/cli
```

# Basic Usage

In `cli` you create a CLI as you create an app in `fastAPI`:

```python
## in cli.py 
from cli import CLI
cli = CLI(name="my_cli", desc="Some description")
```

And you execute the CLI as you execute the app in `fastAPI`:

```python
## in cli.py
if __name__ = '__main___':
    cli.exec()
```

Also, you add commands as you add routers:

```python
## in cli.py
@cli.cmd('/my_command', help='This is a help message')
def my_command_callback(arg1, arg2, ...):
    ...
```
   
The above will produce the command `my_command` which has the arguments `arg1`, `arg2`, etc. The arguments, themselves can be called as positional arguments or keyword arguments. In other words, all the following options will work:

```bash
# positional arguments 
python cli.py my_command arg1_value arg2_value ...
# keyword arguments
python cli.py my_command --arg1=arg1_value --arg2=arg2_value ...
# alternative keyword argument
python cli.py my_command --arg1 arg1_value --arg2 arg2_value ...       
```

Subcommands are created as you create subendpoints:
 
```python
## in cli.py
@cli.cmd('/my_command/subcommand', help='This is another help message')
def subcommand_callback(argA, argB, ...):
    ...
```

The above will provide:

```bash
python cli.py my_command subcommand argA_value argB_value ...
```

Furthermore, you can organize commands into groups as in `fastAPI` you can organize endpoints into routers:
        
```python
# in groups/group.py
from cli import Group

cli_group = Group(
    name='cli_group',
    desc='Some group of commands'
)

@cli_group.cmd('/command', help="some help message")
def group_command_callback(arg1, arg2, ...):
    ...

# in cli.py
from cli import CLI
from groups.group import cli_group

cli = CLI(name="my_cli", desc="Some description")
cli.include_group(cli_group, preffix='/group')
```

# Aliases

You can set command and prefixes aliases:

```python
from cli import CLI
from groups.group import cli_group

# command with aliases
cli = CLI(name="my_cli", desc="Some description")
@cli.cmd('/command', aliases=['/cmd', '/c'])

# group with prefix aliases 
cli.include_group(cli_group, prefix=['/group', '/g'])
```

With the above all the following will equally work:

```bash
python cli.py group command
python cli.py group cmd
python cli.py group c
python cli.py g command
python cli.py g cmd
python cli.py g c
```

# Options
           
Given the implementation of aliases, options with short and long presentations (as in [POSIX standards](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap12.html) ) can be included as commands with aliases:

```python
from cli import CLI
from groups.group import cli_group

# command with aliases
cli = CLI(name="my_cli", desc="Some description")
@cli.cmd('/-o', aliases=['/--option'])
```

# Completion

When you create a CLI with the `CLI` class from `cli`, it comes equipped with a `--completion` option, which prints a `Bash` completion script for your CLI.

```bash
# print the completion script
python cli.py --completion
```
To use it, you should save the script in a file and source the file in your `.bashrc`.

```bash
# save the completion script
python cli.py --completion > /path/to/completion.sh
# use it 
echo "source /path/to/completion.sh" >> $HOME/.bashrc
```

The completion script suggests for commands, subcommands and arguments. You can quickly define suggestions for argument values of some command by using the `completion` directive when defining the command decorator:

```python
@cli.cmd(
    '/my_command',
    help='This is another help message',
    completion={
        'arg1' = ['value1', 'value2', ...],
        ...
    }
)
def my_command_callback(arg1, arg2, ...):
    ...
```

The, when you hit 

```bash
python cli.py my_command arg1 <tab>
```
      
it will suggest for `value1`, `value2`, etc, in the same ordering you provided in the `completion` directive.

# To Do

1. add type checking for the argument values
2. allow the use of variables in the definition of commands, as you can do for endpoints in `fastAPI`.
3. include an option to turn the CLI globally available
