import sys
import inspect
import argparse
from typed import typed, Nill, name

class cli:
    def exit(code=0):
        sys.exit(code)

    def log(message):
        print(f"log: {message}")

    def error(message):
        print(f'error: {message}')
        sys.exit(1)

    def done(message):
        print(f'done: {message}')
        sys.exit(0)

    def exec(action=None, done='', error=''):
        try:
            action
            if done:
                cli.done(done)
        except Exception as e:
            cli.error(f"{error}\nerror:{e}")

Cmd = Nill
Cmd.__display__ = 'Cmd'

class _Node:
    def __init__(self, name=None, aliases=None, help_desc=""):
        self.name = name
        self.aliases = aliases if aliases is not None else []
        self.help = help_desc
        self.func = None
        self.signature = None
        self.children = dict()
        self.completion = dict()

    def add_child(self, child):
        self.children[child.name] = child
        for alias in child.aliases:
            self.children[alias] = child

    def get_or_create_child(self, name, aliases=None):
        if name not in self.children:
            self.children[name] = _Node(name, aliases)
        return self.children[name]

    def find_node(self, argv):
        node = self
        path = []
        idx = 0
        while idx < len(argv):
            arg = argv[idx]
            if arg in node.children:
                node = node.children[arg]
                path.append(arg)
                idx += 1
            else:
                break
        return node, path, argv[idx:]

    def collect_recursive(self, prefix=()):
        out = []
        if self.func is not None:
            out.append((prefix, self))
        processed_children = set()
        for name, child in self.children.items():
            if child not in processed_children:
                out.extend(child.collect_recursive(prefix + (child.name if child.name else name,)))
                processed_children.add(child)
        return out

    def collect_structure(self, prefix=()):
        out = []
        processed_children = set()
        children_keys = []
        for name, child in self.children.items():
            if child not in processed_children:
                children_keys.append(child.name)
                processed_children.add(child)
        out.append((prefix, self, sorted(children_keys)))
        processed_children = set()
        for name, child in self.children.items():
            if child not in processed_children:
                out.extend(child.collect_structure(prefix + (child.name if child.name else name,)))
                processed_children.add(child)
        return out

class Group:
    def __init__(self, name='group', desc="", aliases=None, prefix=None):
        self.name = name
        self.desc = desc
        self.aliases = aliases if aliases is not None else []
        if isinstance(prefix, list):
            self.prefix = prefix
        elif isinstance(prefix, str):
            self.prefix = [prefix] if prefix else []
        else:
            self.prefix = []
        self.root = _Node(name, self.aliases if not self.prefix else self.prefix, desc)

    def cmd(self, path, help=None, completion=None, aliases=None):
        parts = path.strip('/').split('/')
        def decorator(func):
            node = self.root
            for part in parts[:-1]:
                node = node.get_or_create_child(part)
            node.add_child(_Node(parts[-1], aliases, help or ""))
            cmd_node = node.children[parts[-1]]
            cmd_node.func = func
            cmd_node.completion = completion or {}
            cmd_node.signature = inspect.signature(func)
            func = typed(func)
            if func.cod is not Cmd:
                raise TypeError(
                    "Codomain with wrong type.\n"
                   f"  ==> '{func.__name__}': a command should return Cmd\n"
                    "      [expected_type] Cmd\n"
                   f"      [received_type] {name(func.cod)}"
                )
            return func
        return decorator

    def include_group(self, group, prefix=""):
        def copy_subtree(from_node, to_node):
            if from_node.func is not None:
                to_node.func = from_node.func
                to_node.help = from_node.help
                to_node.completion = from_node.completion
                to_node.signature = from_node.signature
            processed_children = set()
            for cname, child in from_node.children.items():
                if child not in processed_children:
                    new_child_node = to_node.get_or_create_child(child.name, child.aliases)
                    copy_subtree(child, new_child_node)
                    processed_children.add(child)

        if isinstance(prefix, str):
            prefix_parts = [p for p in prefix.strip('/').split('/') if p]
            node = self.root
            for part in prefix_parts:
                node = node.get_or_create_child(part)
            copy_subtree(group.root, node)
        elif isinstance(prefix, list):
            for pref in prefix:
                prefix_parts = [p for p in pref.strip('/').split('/') if p]
                node = self.root
                for part in prefix_parts:
                    node = node.get_or_create_child(part)
                copy_subtree(group.root, node)

class CLI:
    def __init__(self, name='cli', desc=""):
        self.root = _Node(name, help_desc=desc)
        self.name = name
        self.desc = desc

    def cmd(self, path, help=None, completion=None, aliases=None):
        parts = path.strip('/').split('/')
        def decorator(func):
            node = self.root
            for part in parts[:-1]:
                node = node.get_or_create_child(part)
            node.add_child(_Node(parts[-1], aliases, help or ""))
            cmd_node = node.children[parts[-1]]
            cmd_node.func = func
            cmd_node.completion = completion or {}
            cmd_node.signature = inspect.signature(func)
            func = typed(func)
            if func.cod is not Cmd:
                raise TypeError(
                    "Codomain with wrong type.\n"
                   f"  ==> '{func.__name__}': a command should return Cmd\n"
                    "      [expected_type] Cmd\n"
                   f"      [received_type] {name(func.cod)}"
                )
            return func
        return decorator

    def include_group(self, group, prefix=None):
        if isinstance(prefix, list):
            prefix_parts = [p for p_list in prefix for p in p_list.strip('/').split('/') if p] if prefix else []
        elif isinstance(prefix, str):
            prefix_parts = [p for p in prefix.strip('/').split('/') if p] if prefix else []
        else:
            prefix_parts = []

        node = self.root
        for part in prefix_parts:
            node = node.get_or_create_child(part)

        def copy_subtree(from_node, to_node):
            if from_node.func is not None:
                to_node.func = from_node.func
                to_node.help = from_node.help
                to_node.completion = from_node.completion
                to_node.signature = from_node.signature
            processed_children = set()
            for cname, child in from_node.children.items():
                if child not in processed_children:
                    new_child_node = to_node.get_or_create_child(child.name, child.aliases)
                    copy_subtree(child, new_child_node)
                    processed_children.add(child)

        copy_subtree(group.root, node)

    def find_node(self, argv):
        return self.root.find_node(argv)

    def exec(self, args=None):
        argv = sys.argv[1:] if args is None else args
        if '--completion' in argv:
            self.print_completion()
            sys.exit(0)
        if not argv:
            self.show_help()
            sys.exit(1)
        node, path, remaining = self.find_node(argv)
        if node.func is None:
            processed_children = set()
            children_keys = []
            for name, child in node.children.items():
                if child not in processed_children:
                    children_keys.append(child.name)
                    processed_children.add(child)
            if children_keys:
                print(f"Usage: {self.name} {' '.join(path)} <subcommand> [options]")
                print("Subcommands:", ' '.join(sorted(children_keys)))
                sys.exit(1)
            else:
                print(f"Unknown command: {' '.join(argv)}")
                self.show_help()
                sys.exit(1)
        params = list(node.signature.parameters.values())
        ap = argparse.ArgumentParser(prog=f"{self.name} {' '.join(path)}", add_help=True)
        for p in params:
            is_required = (p.default == inspect.Parameter.empty)
            if is_required:
                ap.add_argument(p.name)
            else:
                ap.add_argument(f"--{p.name}", dest=p.name, default=p.default, required=False)
        ns, _ = ap.parse_known_args(remaining)
        kw = {}
        for p in params:
            if p.default == inspect.Parameter.empty:
                val = getattr(ns, p.name, None)
                if val is None:
                    print(f"Missing required argument: {p.name}")
                    sys.exit(1)
            else:
                val = getattr(ns, p.name, p.default)
            kw[p.name] = val
        node.func(**kw)

    def show_help(self):
        print(f"usage: {self.name} <command> [<args>]\n")
        for prefix, node, children in self.root.collect_structure():
            if prefix:
                cmdpath = ' '.join(prefix)
                desc = node.help if node.help else ""
                if node.func is not None:
                    print(f"  {cmdpath} - {desc}")
                if children:
                    print(f"  {cmdpath}: subcommands: {', '.join(children)}")
            else:
                if children:
                    print("Available commands:", ', '.join(children))

    def print_completion(self):
        nodes = {}
        for prefix, node in self.root.collect_recursive():
            label = "_".join(prefix).replace('-', '_')
            nodes[label] = (prefix, node)

        all_cmds = set()
        subcmds_map = {}
        opt_map = {}
        val_map = {}

        for prefix, node, children in self.root.collect_structure():
            if len(prefix) == 0:
                all_cmds.update(children)
            else:
                pfx = "_".join(prefix).replace('-', '_')
                if children:
                    subcmds_map[pfx] = sorted(children)

        for label, (prefix, node) in nodes.items():
            opt_map.setdefault(label, [])
            if node.signature is not None:
                for p in node.signature.parameters.values():
                    opt = f"--{p.name}"
                    if opt not in opt_map[label]:
                        opt_map[label].append(opt)
            if node.completion:
                val_map.setdefault(label, {})
                for arg, vals in node.completion.items():
                    if f"--{arg}" not in opt_map[label]:
                        opt_map[label].append(f"--{arg}")
                    val_map[label][arg] = vals

        arrays = []
        for label, argvals in val_map.items():
            for arg, vals in argvals.items():
                basharr = f"_COMP_{label}__{arg}"
                valstr = " ".join([f'"{v}"' for v in vals])
                arrays.append(f'{basharr}=({valstr})')

        script = [
            "#!/bin/bash",
            *arrays,
            "",
            f'_{self.name}_completion() {{',
            '    local cur prev words cword',
            '    COMPREPLY=()',
            '    cur="${COMP_WORDS[COMP_CWORD]}"',
            '    prev="${COMP_WORDS[COMP_CWORD-1]}"',
            '    words=("${COMP_WORDS[@]}")',
            '    cword=$COMP_CWORD',
            '',
            f'    cmds="{ " ".join(sorted(all_cmds)) }"',
            '',
            '    declare -A subcmds',
        ]
        for k, subs in subcmds_map.items():
            script.append(f'    subcmds["{k}"]="{ " ".join(subs) }"')
        script.append('    declare -A opts')
        for label, optlist in opt_map.items():
            script.append(f'    opts["{label}"]="{ " ".join(optlist) }"')
        script.append('    declare -A vals')
        for label, argvals in val_map.items():
            for arg, vals_ in argvals.items():
                basharr = f'_COMP_{label}__{arg}'
                script.append(f'    vals["{label}__{arg}"]="{ " ".join(vals_) }"')

        script.extend([
            '',
            '    find_cmd_label() {',
            '        local idx=1',
            '        local curr_label=""',
            '        local last_label=""',
            '        while ((idx < cword)); do',
            '            local arg="${words[idx]}"',
            '            [[ "$arg" == --* ]] && break',
            '            if [[ -z "$curr_label" ]]; then',
            '                curr_label="$arg"',
            '            else',
            '                curr_label="${curr_label}_$arg"',
            '            fi',
            '            local normalized_curr_label="${curr_label//-/_}"',
            '            if [[ -n "${subcmds[$normalized_curr_label]}" ]]; then',
            '                last_label="$normalized_curr_label"',
            '            else',
            '                last_label="$normalized_curr_label"',
            '                break',
            '            fi',
            '            ((idx++))',
            '        done',
            '        echo "$last_label $idx"',
            '    }',
            '',
            '    if [[ $cword -eq 1 ]]; then',
            '        COMPREPLY=( $(compgen -W "$cmds" -- "$cur") )',
            '        return 0',
            '    fi',
            '',
            '    read sub_label argstart <<<"$(find_cmd_label)"',
            '',
            '    if [[ -z "$sub_label" ]]; then',
            '        sub_label="${words[1]//-/_}"',
            '        argstart=2',
            '    fi',
            '',
            '    already_set_opts=()',
            '    idx=$argstart',
            '    while ((idx < cword)); do',
            '        word="${words[idx]}"',
            '        if [[ "$word" == --* ]]; then',
            '            argn="${word%%=*}"',
            '            argn="${argn#--}"',
            '            already_set_opts+=("$argn")',
            '            if [[ "$word" != *=* ]]; then',
            '                if ((idx + 1 < cword)); then',
            '                    nextw="${words[idx+1]}"',
            '                    if [[ ! "$nextw" == --* ]]; then',
            '                        ((idx++))',
            '                    fi',
            '                fi',
            '            fi',
            '        fi',
            '        ((idx++))',
            '    done',
            '',
            '    remaining_opts=()',
            '    for opt in ${opts[$sub_label]}; do',
            '        o="${opt#--}"',
            '        skip=0',
            '        for ao in "${already_set_opts[@]}"; do',
            '            [[ "$o" == "$ao" ]] && skip=1 && break',
            '        done',
            '        [[ $skip -eq 0 ]] && remaining_opts+=("$opt")',
            '    done',
            '',
            '    if [[ -n "${subcmds[$sub_label]}" && $cword -eq $argstart ]]; then',
            '        present=0',
            '        for sub in ${subcmds[$sub_label]}; do',
            '            if [[ "${words[argstart]}" == "$sub" ]]; then',
            '                present=1',
            '            fi',
            '        done',
            '        if [[ $present -eq 0 ]]; then',
            '            COMPREPLY=( $(compgen -W "${subcmds[$sub_label]}" -- "$cur") )',
            '            return 0',
            '        fi',
            '    fi',
            '',
            '    if [[ "$prev" == --* ]]; then',
            '        argname="${prev#--}"',
            '        if [[ -n "${vals[${sub_label}__${argname}]}" ]]; then',
            '            COMPREPLY=( $(compgen -W "${vals[${sub_label}__${argname}]}" -- "$cur") )',
            '            return 0',
            '        fi',
            '    fi',
            '',
            '    if [[ "$cur" == --*=* ]]; then',
            '        argname="${cur%%=*}"',
            '        argname="${argname#--}"',
            '        val_primary="${cur#*=}"',
            '        if [[ -n "${vals[${sub_label}__${argname}]}" ]]; then',
            '            COMPREPLY=( $(compgen -W "${vals[${sub_label}__${argname}]}" -- "$val_primary") )',
            '            return 0',
            '        fi',
            '    fi',
            '',
            '    if ((cword>=2)); then',
            '        prev2="${COMP_WORDS[COMP_CWORD-2]}"',
            '        if [[ "$prev2" == --* ]]; then',
            '            argname="${prev2#--}"',
            '            if [[ -n "${vals[${sub_label}__${argname}]}" ]]; then',
            '                if ((${#remaining_opts[@]})); then',
            '                    COMPREPLY=( $(compgen -W "${remaining_opts[*]}" -- "$cur") )',
            '                    return 0',
            '                fi',
            '            fi',
            '        fi',
            '    fi',
            '',
            '    if [[ -z "${subcmds[$sub_label]}" && ${#remaining_opts[@]} -gt 0 ]]; then',
            '        COMPREPLY=( $(compgen -W "${remaining_opts[*]}" -- "$cur") )',
            '        return 0',
            '    fi',
            '',
            '    if [[ ${#remaining_opts[@]} -gt 0 ]]; then',
            '        COMPREPLY+=( $(compgen -W "${remaining_opts[*]}" -- "$cur") )',
            '    fi',
            '',
            '    return 0',
            '}',
            f'complete -F _{self.name}_completion {self.name}'
        ])
        print('\n'.join(script))
