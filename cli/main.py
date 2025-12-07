import sys
import inspect
import argparse
import shlex
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

class confirmed: pass
class declined: pass

class __Confirmation__(type):
    def __enter__(cls):
        while True:
            user_response = input(cls._prompt_message).lower().strip()
            if user_response in ('y', 'yes'):
                return confirmed
            elif user_response in ('n', 'no'):
                print("Action aborted.")
                return declined
            else:
                print("Invalid input. Please enter 'y', 'yes', 'n', or 'no'.")

    def __exit__(cls, exc_type, exc_val, exc_tb):
        return False

class confirmation(metaclass=__Confirmation__):
    _prompt_message = "Do you want to proceed? (y/n): "

class _Node:
    def __init__(self, name=None, aliases=None, help_desc=""):
        self.name = name
        self.aliases = aliases if aliases is not None else []
        self.help = help_desc
        self.func = None
        self.signature = None
        self.children = dict()
        self.completion = dict()
        self.kwargs = {}
        self.args = ()

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

    def cmd(self, path, help=None, completion=None, aliases=None, kwargs=None, args=None):
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
            cmd_node.kwargs = kwargs or {}
            cmd_node.args = tuple(args or ())
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
                to_node.kwargs = getattr(from_node, 'kwargs', {})
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

    def cmd(self, path, help=None, completion=None, aliases=None, kwargs=None, args=None):
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
            cmd_node.kwargs = kwargs or {}
            cmd_node.args = tuple(args or ())
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
                to_node.kwargs = getattr(from_node, 'kwargs', {})
                to_node.args = getattr(from_node, 'args', ())
            processed_children = set()
            for cname, child in from_node.children.items():
                if child not in processed_children:
                    new_child_node = to_node.get_or_create_child(child.name, child.aliases)
                    copy_subtree(child, new_child_node)
                    processed_children.add(child)

        copy_subtree(group.root, node)

    def find_node(self, argv):
        return self.root.find_node(argv)

    def _handle_dynamic_completion(self, argv):
        try:
            idx = argv.index('--_complete')
        except ValueError:
            return
        argname = None
        i = idx + 1
        while i < len(argv) and argv[i] != '--':
            if argv[i] == '--arg' and i + 1 < len(argv):
                argname = argv[i + 1]
                i += 2
            else:
                i += 1
        words = []
        if i < len(argv) and argv[i] == '--':
            words = argv[i + 1:]

        if not words:
            return

        node, path, remaining = self.find_node(words)

        if node is None or node.func is None:
            return

        seen = {}
        j = 0
        while j < len(remaining):
            tok = remaining[j]
            if tok.startswith('--'):
                if '=' in tok:
                    k, v = tok[2:].split('=', 1)
                    seen[k] = v
                else:
                    k = tok[2:]
                    v = None
                    if j + 1 < len(remaining) and not remaining[j + 1].startswith('--'):
                        v = remaining[j + 1]
                        j += 1
                    seen[k] = '' if v is None else v
            j += 1

        if argname is None:
            if remaining and remaining[-1].startswith('--') and '=' not in remaining[-1]:
                argname = remaining[-1][2:]
            elif len(remaining) >= 2 and remaining[-2].startswith('--'):
                argname = remaining[-2][2:]

        suggestions = []
        comp = node.completion or {}
        if argname in comp:
            entry = comp[argname]
            if isinstance(entry, (list, tuple, set)):
                suggestions = [str(v) for v in entry]
            elif isinstance(entry, dict):
                acc = []
                for dep, func in entry.items():
                    if callable(func) and dep in seen:
                        try:
                            vals = func(seen[dep])
                            if vals:
                                acc.extend([str(v) for v in vals])
                        except Exception:
                            pass
                seen_set = set()
                for v in acc:
                    if v not in seen_set:
                        suggestions.append(v)
                        seen_set.add(v)
        if suggestions:
            print(" ".join(suggestions))

    def exec(self, args=None):
        if args is None:
            argv = sys.argv[1:]
        elif isinstance(args, str):
            argv = shlex.split(args, posix=True)
        else:
            argv = list(args)

        if '--_complete' in argv:
            self._handle_dynamic_completion(argv)
            sys.exit(0)

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

        ap = argparse.ArgumentParser(
            prog=f"{self.name} {' '.join(path)}",
            add_help=True
        )

        fixed_params = []
        var_pos_param = None
        var_kw_param = None

        for p in params:
            if p.kind == inspect.Parameter.VAR_POSITIONAL:
                var_pos_param = p
            elif p.kind == inspect.Parameter.VAR_KEYWORD:
                var_kw_param = p
            else:
                fixed_params.append(p)

        for p in fixed_params:
            is_required = (p.default == inspect.Parameter.empty)
            default = None if is_required else p.default
            ap.add_argument(
                f"--{p.name}",
                dest=p.name,
                default=default,
                required=is_required,
                nargs='+'
            )

        for k, default in (node.kwargs or {}).items():
            ap.add_argument(
                f"--{k}",
                dest=k,
                default=default,
                required=False,
                nargs='+'
            )

        if var_pos_param is not None and node.args:
            for arg_name in node.args:
                ap.add_argument(arg_name)

        ns = ap.parse_args(remaining)

        kw = {}

        for p in fixed_params:
            val = getattr(ns, p.name,
                          None if p.default == inspect.Parameter.empty else p.default)
            if p.default == inspect.Parameter.empty and val is None:
                print(f"Missing required option: --{p.name}")
                sys.exit(1)
            if isinstance(val, list):
                val = ' '.join(val)
            kw[p.name] = val

        if var_kw_param is not None and (node.kwargs or {}):
            for k, default in (node.kwargs or {}).items():
                v = getattr(ns, k, default)
                if isinstance(v, list):
                    v = ' '.join(v)
                if k in kw:
                    raise RuntimeError(
                        f"Expandable kwarg name '{k}' "
                        "conflicts with a regular parameter."
                    )
                kw[k] = v

        if var_pos_param is not None and node.args:
            pos_vals = []
            for arg_name in node.args:
                pos_vals.append(getattr(ns, arg_name))
            kw[var_pos_param.name] = tuple(pos_vals)

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

        # Separate top-level commands and groups
        root_cmds = set()
        root_groups = set()
        processed_root_children = set()
        for name, child in self.root.children.items():
            if child in processed_root_children:
                continue
            processed_root_children.add(child)
            if child.func is None and child.children:
                root_groups.add(child.name)
            else:
                root_cmds.add(child.name)

        subcmds_map = {}
        opt_map = {}
        val_map = {}
        dyn_map = {}

        # Per-parent classification for nested groups
        parent_cmds = {}   # label -> [child names that are commands]
        parent_groups = {} # label -> [child names that are groups]

        for prefix, node, children in self.root.collect_structure():
            if len(prefix) == 0:
                continue
            pfx = "_".join(prefix).replace('-', '_')
            if children:
                subcmds_map[pfx] = sorted(children)
                for ch_name in children:
                    child_node = node.children[ch_name]
                    if child_node.func is None and child_node.children:
                        parent_groups.setdefault(pfx, []).append(ch_name)
                    else:
                        parent_cmds.setdefault(pfx, []).append(ch_name)

        for label, (prefix, node) in nodes.items():
            opt_map.setdefault(label, [])
            param_names = set()

            if node.signature is not None:
                params = list(node.signature.parameters.values())
                param_names = {p.name for p in params}
                for p in params:
                    if p.kind in (inspect.Parameter.VAR_POSITIONAL,
                                  inspect.Parameter.VAR_KEYWORD):
                        continue
                    param_names.add(p.name)
                    opt = f"--{p.name}"
                    if opt not in opt_map[label]:
                        opt_map[label].append(opt)

            if getattr(node, 'kwargs', None):
                for k in node.kwargs.keys():
                    param_names.add(k)
                    opt = f"--{k}"
                    if opt not in opt_map[label]:
                        opt_map[label].append(opt)

            if node.completion and param_names:
                for arg, vals in node.completion.items():
                    if arg not in param_names:
                        continue
                    if f"--{arg}" not in opt_map[label]:
                        opt_map[label].append(f"--{arg}")
                    if isinstance(vals, (list, tuple, set)):
                        val_map.setdefault(label, {})
                        val_map[label][arg] = [str(v) for v in vals]
                    elif isinstance(vals, dict):
                        dyn_map.setdefault(label, set()).add(arg)

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
            # COMP_TYPE is a bitmask. When Bash is in "list all" mode (TAB-TAB or show-all-if-ambiguous),
            # the lower bits typically differ; we detect list mode with a non-zero 0x2 bit.
            '    local comp_type="${COMP_TYPE:-0}"',
            '    local in_list_mode=0',
            '    if (( (comp_type & 2) != 0 )); then',
            '        in_list_mode=1',
            '    fi',
            '',
            f'    cmds_main="{ " ".join(sorted(root_cmds)) }"',
            f'    groups_main="{ " ".join(sorted(root_groups)) }"',
            '',
            '    declare -A subcmds',
        ]
        for k, subs in subcmds_map.items():
            script.append(f'    subcmds["{k}"]="{ " ".join(subs) }"')

        script.append('    declare -A cmds_map')
        for label, cmdlist in parent_cmds.items():
            script.append(f'    cmds_map["{label}"]="{ " ".join(sorted(cmdlist)) }"')

        script.append('    declare -A groups_map')
        for label, grlist in parent_groups.items():
            script.append(f'    groups_map["{label}"]="{ " ".join(sorted(grlist)) }"')

        script.append('    declare -A opts')
        for label, optlist in opt_map.items():
            script.append(f'    opts["{label}"]="{ " ".join(optlist) }"')

        # Fix small typo in previous line:
        script[-1] = script[-1].replace('))', ')')

        script.append('    declare -A vals')
        for label, argvals in val_map.items():
            for arg, vals_ in argvals.items():
                basharr = f'_COMP_{label}__{arg}'
                script.append(f'    vals["{label}__{arg}"]="{ " ".join(vals_) }"')

        script.append('    declare -A dyn')
        for label, argset in dyn_map.items():
            for arg in argset:
                script.append(f'    dyn["{label}__{arg}"]=1')

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
            '    # Top-level completion (after the CLI name)',
            '    if [[ $cword -eq 1 ]]; then',
            '        # If in list mode with empty current token: print headings only, no grid',
            '        if [[ $in_list_mode -eq 1 && -z "$cur" ]]; then',
            '            printf "\\n"',
            '            local _c',
            '            _c=" ${cmds_main// /, }"',
            '            printf "commands: %s" "$_c"',
            '            local _g',
            '            _g=" ${groups_main// /, }"',
            '            COMPREPLY=("$(printf "groups:   %s" "$_g")")',
            '            return 0',
            '        fi',
            '',
            '        # Normal completion mode: do standard token completion',
            '        local all_top',
            '        all_top="$cmds_main $groups_main"',
            '        COMPREPLY=( $(compgen -W "$all_top" -- "$cur") )',
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
            '    # Nested group completion: show commands/groups for the current label',
            '    if [[ -n "${subcmds[$sub_label]}" && $cword -eq $argstart ]]; then',
            '        present=0',
            '        for sub in ${subcmds[$sub_label]}; do',
            '            if [[ "${words[argstart]}" == "$sub" ]]; then',
            '                present=1',
            '            fi',
            '        done',
            '        if [[ $present -eq 0 ]]; then',
            '            local cmds_here groups_here',
            '            cmds_here="${cmds_map[$sub_label]}"',
            '            groups_here="${groups_map[$sub_label]}"',
            '            # In list mode with empty token: print headings only, no grid',
            '            if [[ $in_list_mode -eq 1 && -z "$cur" ]]; then',
            '                printf "\\n"',
            '                local _c',
            '                _c=" ${cmds_here// /, }"',
            '                printf " commands: %s" "$_c"',
            '                local _g',
            '                _g=" ${groups_here// /, }"',
            '                COMPREPLY=("$(printf " groups:   %s" "$_g")")',
            '                return 0',
            '            fi',
            '            # Normal completion mode',
            '            local all_sub',
            '            all_sub="$cmds_here $groups_here"',
            '            COMPREPLY=( $(compgen -W "$all_sub" -- "$cur") )',
            '            return 0',
            '        fi',
            '    fi',
            '',
            '    # Dynamic completion: previous token is an option',
            '    if [[ "$prev" == --* ]]; then',
            '        argname="${prev#--}"',
            '        if [[ -n "${dyn[${sub_label}__${argname}]}" ]]; then',
            f'            suggestions="$({self.name} --_complete --arg "${{argname}}" -- "${{words[@]:1:cword-1}}")"',
            '            COMPREPLY=( $(compgen -W "$suggestions" -- "$cur") )',
            '            return 0',
            '        fi',
            '        if [[ -n "${vals[${sub_label}__${argname}]}" ]]; then',
            '            COMPREPLY=( $(compgen -W "${vals[${sub_label}__${argname}]}" -- "$cur") )',
            '            return 0',
            '        fi',
            '    fi',
            '',
            '    # Dynamic completion for --arg=value form',
            '    if [[ "$cur" == --*=* ]]; then',
            '        argname="${cur%%=*}"',
            '        argname="${argname#--}"',
            '        val_primary="${cur#*=}"',
            '        if [[ -n "${dyn[${sub_label}__${argname}]}" ]]; then',
            f'            suggestions="$({self.name} --_complete --arg "${{argname}}" -- "${{words[@]:1:cword-1}}")"',
            '            COMPREPLY=( $(compgen -W "$suggestions" -- "$val_primary") )',
            '            return 0',
            '        fi',
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
            '    if [[ ${#remaining_opts[@]} > 0 ]]; then',
            '        COMPREPLY+=( $(compgen -W "${remaining_opts[*]}" -- "$cur") )',
            '    fi',
            '',
            '    return 0',
            '}',
            f'complete -F _{self.name}_completion {self.name}'
        ])
        print('\n'.join(script))
