#!/usr/bin/env python3
import argparse
import base64
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "commands"
BUNDLED_FILE = Path(__file__).parent / "data" / "commands.json"
DEFAULT_USER_FILE = Path.home() / ".config" / APP_NAME / "commands.json"


class CliError(Exception):
    pass


def read_path():
    env_path = os.environ.get("COMANDI_FILE")
    if env_path:
        return Path(env_path).expanduser()
    if DEFAULT_USER_FILE.exists():
        return DEFAULT_USER_FILE
    return BUNDLED_FILE


def write_path():
    env_path = os.environ.get("COMANDI_FILE")
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_USER_FILE


def load_data(path=None):
    target = path or read_path()
    if not target.exists():
        raise CliError("Commands file not found: {}".format(target))
    try:
        with target.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise CliError("Invalid JSON in {}: {}".format(target, exc))
    if not isinstance(data, dict) or not isinstance(data.get("commands"), list):
        raise CliError("Invalid format in {}: missing 'commands' list".format(target))
    return data


def save_data(data, path=None):
    target = path or write_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def ensure_user_config():
    target = write_path()
    if target.exists():
        return target
    source = read_path()
    if not source.exists():
        source = BUNDLED_FILE
    data = load_data(source)
    save_data(data, target)
    return target


def commands(data):
    return data.get("commands", [])


def aliases(command):
    values = command.get("aliases", [])
    if isinstance(values, list):
        return [str(v) for v in values]
    return []


def tags(command):
    values = command.get("tags", [])
    if isinstance(values, list):
        return [str(v) for v in values]
    return []


def resolve_command(data, name):
    needle = name.lower()
    matches = []
    for command in commands(data):
        command_name = str(command.get("name", ""))
        all_names = [command_name] + aliases(command)
        if any(item.lower() == needle for item in all_names):
            return command
        if needle in command_name.lower() or any(needle in item.lower() for item in aliases(command)):
            matches.append(command)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(str(c.get("name")) for c in matches)
        raise CliError("Ambiguous name '{}'. Matches: {}".format(name, names))
    raise CliError("Command not found: {}".format(name))


def step_command(step):
    if isinstance(step, str):
        return step
    if isinstance(step, dict) and isinstance(step.get("run"), str):
        return step["run"]
    raise CliError("Invalid step: use a string or {\"run\": \"...\"}".format())


def command_steps(command):
    raw_steps = command.get("steps")
    if raw_steps is None and isinstance(command.get("command"), str):
        raw_steps = [command["command"]]
    if not isinstance(raw_steps, list) or not raw_steps:
        raise CliError("Command '{}' has no steps to run".format(command.get("name")))
    return [step_command(step) for step in raw_steps]


def env_lines(command):
    raw_env = command.get("env", {})
    if not isinstance(raw_env, dict):
        raise CliError("Invalid env for '{}'".format(command.get("name")))
    return ["export {}={}".format(key, shlex.quote(str(value))) for key, value in raw_env.items()]


def render_script(command):
    lines = []
    cwd = command.get("cwd")
    if cwd:
        lines.append("cd {}".format(shlex.quote(str(cwd))))
    lines.extend(env_lines(command))
    lines.extend(command_steps(command))
    return "\n".join(lines)


def render_inline(command):
    steps = command_steps(command)
    env = command.get("env", {})
    if len(steps) == 1 and isinstance(env, dict) and env and not command.get("cwd"):
        prefix = " ".join("{}={}".format(key, shlex.quote(str(value))) for key, value in env.items())
        return "{} {}".format(prefix, steps[0])
    return " && ".join(render_script(command).splitlines())


def command_mode(command):
    mode = str(command.get("mode", "exec"))
    if mode not in ("exec", "eval"):
        raise CliError("Unsupported mode for '{}': {}".format(command.get("name"), mode))
    return mode


def command_haystack(command):
    name = str(command.get("name", ""))
    description = str(command.get("description", ""))
    return " ".join([name, description] + aliases(command) + tags(command)).lower()


def filtered_commands(data, query="", tag=""):
    query = (query or "").lower()
    tag = (tag or "").lower()
    rows = []
    for command in commands(data):
        if query and query not in command_haystack(command):
            continue
        if tag and tag not in [item.lower() for item in tags(command)]:
            continue
        rows.append(command)
    return rows


def _binary():
    if sys.argv and sys.argv[0]:
        p = Path(sys.argv[0]).resolve()
        if p.stem == "commands":
            return p
    found = shutil.which("commands")
    if found:
        return Path(found).resolve()
    return Path(sys.argv[0]).resolve() if sys.argv else Path("commands")


def _is_wsl():
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def _ask_run_action(command_name):
    import questionary
    choices = [
        questionary.Choice(
            title="Copy to clipboard    paste it anywhere you need",
            value="copy",
        ),
        questionary.Choice(
            title="Run in this terminal  execute here and now",
            value="run",
        ),
        questionary.Choice(
            title="Open new terminal    launch in a separate window",
            value="terminal",
        ),
    ]
    return questionary.select(
        "How do you want to run '{}'?".format(command_name),
        choices=choices,
    ).ask()


def open_in_terminal(script, name=""):
    import stat
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False, prefix="commands_") as f:
        f.write("#!/bin/bash\n")
        if name:
            f.write("echo '=== {} ==='\n".format(name.replace("'", "")))
        f.write(script)
        f.write('\necho\nread -rp "Press Enter to close..." _\n')
        tmp = f.name
    os.chmod(tmp, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)

    if _is_wsl():
        wt = shutil.which("wt.exe")
        if wt:
            subprocess.Popen([wt, "bash", tmp])
            return True
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "bash", tmp])
            return True
        except OSError:
            pass

    terminals = [
        ["gnome-terminal", "--", "bash", tmp],
        ["xterm", "-e", "bash", tmp],
        ["konsole", "-e", "bash {}".format(shlex.quote(tmp))],
        ["xfce4-terminal", "-e", "bash {}".format(shlex.quote(tmp))],
        ["mate-terminal", "--", "bash", tmp],
        ["tilix", "-e", "bash {}".format(shlex.quote(tmp))],
        ["terminator", "-e", "bash {}".format(shlex.quote(tmp))],
    ]
    for term in terminals:
        if shutil.which(term[0]):
            subprocess.Popen(term)
            return True
    return False


def cmd_list(args):
    data = load_data()
    rows = []
    for command in filtered_commands(data, args.query, args.tag):
        name = str(command.get("name", ""))
        description = str(command.get("description", ""))
        alias_text = ", ".join(aliases(command))
        rows.append((name, alias_text, description))

    if not rows:
        if not args.query and not args.tag:
            print("No commands saved yet. Run 'commands add' to add your first command.")
        else:
            print("No commands found.")
        return 1

    name_width = max(len(row[0]) for row in rows)
    for name, alias_text, description in rows:
        suffix = " ({})".format(alias_text) if alias_text else ""
        print("{:<{width}}  {}{}".format(name, description, suffix, width=name_width))
    return 0


def cmd_show(args):
    command = resolve_command(load_data(), args.name)
    print("Name:        {}".format(command.get("name")))
    if aliases(command):
        print("Aliases:     {}".format(", ".join(aliases(command))))
    if tags(command):
        print("Tags:        {}".format(", ".join(tags(command))))
    if command.get("description"):
        print("Description: {}".format(command.get("description")))
    if command.get("notes"):
        print("Notes:       {}".format(command.get("notes")))
    print()
    print(render_script(command))
    return 0


def cmd_print(args):
    command = resolve_command(load_data(), args.name)
    print(render_script(command))
    return 0


def cmd_mode(args):
    command = resolve_command(load_data(), args.name)
    print(command_mode(command))
    return 0


def run_shell(command_line, cwd, env, quiet):
    if not quiet:
        print("+ {}".format(command_line), file=sys.stderr)
    shell = os.environ.get("COMANDI_SHELL") or shutil.which("bash")
    completed = subprocess.run(command_line, shell=True, cwd=cwd, env=env, executable=shell)
    return int(completed.returncode)


def _execute_command(command, quiet=False, subshell=False):
    if command_mode(command) == "eval" and not subshell:
        print(
            "This command must modify the current shell.\n"
            "Use: eval \"$({} print {})\"\n"
            "Or enable the wrapper and use: c run {}".format(
                _binary(), shlex.quote(str(command.get("name", ""))), command.get("name", "")
            ),
            file=sys.stderr,
        )
        return 2

    env = os.environ.copy()
    raw_env = command.get("env", {})
    if isinstance(raw_env, dict):
        env.update({str(key): str(value) for key, value in raw_env.items()})

    cwd = command.get("cwd")
    cwd_value = str(Path(str(cwd)).expanduser()) if cwd else None

    for step in command_steps(command):
        code = run_shell(step, cwd_value, env, quiet)
        if code != 0:
            return code
    return 0


def _dispatch_action(command, action, quiet=False):
    if action == "copy":
        text = render_script(command)
        copied_with = copy_to_clipboard(text)
        if not copied_with:
            print("Clipboard not available. Copy this:")
            print(text)
            return 1
        print("Copied: {}".format(command.get("name")))
        return 0

    if action == "terminal":
        if not open_in_terminal(render_script(command), command.get("name", "")):
            raise CliError(
                "No terminal emulator found. "
                "Install gnome-terminal, xterm, or konsole."
            )
        return 0

    return _execute_command(command, quiet=quiet)


def cmd_run(args):
    command = resolve_command(load_data(), args.name)

    action = getattr(args, "action", None)
    if action is None and sys.stdin.isatty() and sys.stdout.isatty():
        action = _ask_run_action(command.get("name", args.name))
        if action is None:
            print("Cancelled.")
            return 1

    if action is not None:
        return _dispatch_action(command, action, quiet=getattr(args, "quiet", False))

    return _execute_command(command, quiet=args.quiet, subshell=args.subshell)


def clipboard_commands():
    return (
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["pbcopy"],
        ["clip.exe"],
    )


def osc52_copy(text):
    if not sys.stdout.isatty():
        return False
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    sys.stdout.write("\033]52;c;{}\a".format(encoded))
    sys.stdout.flush()
    return True


def copy_to_clipboard(text):
    for clip in clipboard_commands():
        if not shutil.which(clip[0]):
            continue
        try:
            subprocess.run(
                clip,
                input=text.encode("utf-8"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return "clipboard"
        except (OSError, subprocess.CalledProcessError):
            continue
    if osc52_copy(text):
        return "terminal"
    return None


def cmd_copy(args):
    command = resolve_command(load_data(), args.name)
    text = render_script(command)
    copied_with = copy_to_clipboard(text)
    if not copied_with:
        print("Clipboard not available. Copy this:")
        print(text)
        return 1
    print("Copied: {}".format(command.get("name")))
    return 0


def one_line(value):
    return str(value or "").replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def command_summary(command):
    parts = []
    description = one_line(command.get("description", ""))
    if description:
        parts.append(description)
    if aliases(command):
        parts.append("aliases: {}".format(", ".join(aliases(command))))
    if tags(command):
        parts.append("tags: {}".format(", ".join(tags(command))))
    return " | ".join(parts)


def command_picker_lines(data, initial_query):
    lines = []
    for index, command in enumerate(commands(data)):
        if initial_query and initial_query.lower() not in command_haystack(command):
            continue
        script = one_line(render_script(command).replace("\n", " ; "))
        line = "\t".join(
            [
                str(index),
                one_line(command.get("name", "")),
                script,
                command_summary(command),
            ]
        )
        lines.append(line)
    return lines


def run_fzf_picker(data, initial_query):
    fzf = shutil.which("fzf")
    if not fzf:
        raise CliError(
            "fzf not found. Install fzf to use the TUI picker "
            "or use 'commands list' and 'commands run <name>'."
        )
    picker_lines = command_picker_lines(data, "")
    if not picker_lines:
        raise CliError("No saved commands")

    preview_command = "{} _preview {{1}}".format(shlex.quote(str(_binary())))
    fzf_args = [
        fzf,
        "--height=90%",
        "--layout=reverse",
        "--border",
        "--cycle",
        "--prompt=commands> ",
        "--header=Enter to select | type to search | Esc cancels",
        "--delimiter=\t",
        "--with-nth=2..",
        "--preview",
        preview_command,
        "--preview-window=down,45%,wrap",
    ]
    if initial_query:
        fzf_args.extend(["--query", initial_query])

    completed = subprocess.run(
        fzf_args,
        input=("\n".join(picker_lines) + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
    )
    if completed.returncode != 0:
        return None

    selected = completed.stdout.decode("utf-8", "replace").strip()
    if not selected:
        return None
    index_text = selected.split("\t", 1)[0]
    try:
        return commands(data)[int(index_text)]
    except (ValueError, IndexError):
        raise CliError("Invalid selection returned by fzf")


def cmd_preview(args):
    data = load_data()
    try:
        command = commands(data)[int(args.index)]
    except (ValueError, IndexError):
        raise CliError("Invalid preview index: {}".format(args.index))
    print(command.get("name", ""))
    if command.get("description"):
        print(command.get("description"))
    if aliases(command):
        print("Aliases: {}".format(", ".join(aliases(command))))
    if tags(command):
        print("Tags: {}".format(", ".join(tags(command))))
    print()
    print(render_script(command))
    return 0


def cmd_pick(args):
    data = load_data()
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise CliError("Interactive picker requires a TTY")

    selected = run_fzf_picker(data, args.query or "")
    if not selected:
        print("Cancelled.")
        return 1

    action = _ask_run_action(selected.get("name", ""))
    if action is None:
        print("Cancelled.")
        return 1

    return _dispatch_action(selected, action)


def parse_key_value(items):
    parsed = {}
    for item in items:
        if "=" not in item:
            raise CliError("Invalid value '{}'. Use KEY=VALUE".format(item))
        key, value = item.split("=", 1)
        if not key:
            raise CliError("Empty env key in '{}'".format(item))
        parsed[key] = value
    return parsed


def cmd_add_wizard():
    import questionary

    print()

    name = questionary.text(
        "Command name:",
        validate=lambda v: bool(v.strip()) or "Name is required",
    ).ask()
    if name is None:
        raise KeyboardInterrupt
    name = name.strip()

    description = questionary.text("Description (optional):").ask()
    if description is None:
        raise KeyboardInterrupt

    steps = []
    while True:
        label = (
            "Shell command (step 1):"
            if not steps
            else "Step {} (blank to finish):".format(len(steps) + 1)
        )
        val = questionary.text(label).ask()
        if val is None:
            raise KeyboardInterrupt
        if not val.strip():
            if not steps:
                print("  At least one step is required.")
                continue
            break
        steps.append(val.strip())

    advanced = questionary.confirm(
        "Add advanced options? (tags, aliases, env vars, working dir, notes)",
        default=False,
    ).ask()
    if advanced is None:
        raise KeyboardInterrupt

    tags_list = []
    aliases_list = []
    cwd = None
    env_raw = []
    notes = None

    if advanced:
        tags_raw = questionary.text("Tags (comma-separated, optional):").ask()
        if tags_raw is None:
            raise KeyboardInterrupt
        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()]

        aliases_raw = questionary.text("Aliases (comma-separated, optional):").ask()
        if aliases_raw is None:
            raise KeyboardInterrupt
        aliases_list = [a.strip() for a in aliases_raw.split(",") if a.strip()]

        cwd_val = questionary.text("Working directory (optional):").ask()
        if cwd_val is None:
            raise KeyboardInterrupt
        cwd = cwd_val.strip() or None

        while True:
            label = (
                "Env var KEY=VALUE (blank to finish):"
                if not env_raw
                else "Another env var (blank to finish):"
            )
            val = questionary.text(label).ask()
            if val is None:
                raise KeyboardInterrupt
            if not val.strip():
                break
            env_raw.append(val.strip())

        notes_val = questionary.text("Notes (optional):").ask()
        if notes_val is None:
            raise KeyboardInterrupt
        notes = notes_val.strip() or None

    return argparse.Namespace(
        name=name,
        description=description or "",
        tag=tags_list or None,
        alias=aliases_list or None,
        mode="exec",
        cwd=cwd,
        env=env_raw or None,
        cmd=steps,
        notes=notes,
    )


def cmd_add(args):
    if not args.cmd:
        if not sys.stdin.isatty():
            raise CliError("--cmd is required when stdin is not a TTY")
        try:
            args = cmd_add_wizard()
        except KeyboardInterrupt:
            print("\nCancelled.")
            return 1

    target = ensure_user_config()
    data = load_data(target)

    try:
        resolve_command(data, args.name)
    except CliError:
        pass
    else:
        raise CliError("Command '{}' already exists".format(args.name))

    new_command = {
        "name": args.name,
        "description": args.description or "",
        "tags": args.tag or [],
        "aliases": args.alias or [],
        "steps": [{"run": item} for item in args.cmd],
    }
    if getattr(args, "mode", "exec") == "eval":
        new_command["mode"] = "eval"
    env = parse_key_value(args.env or [])
    if env:
        new_command["env"] = env
    if args.cwd:
        new_command["cwd"] = args.cwd
    if args.notes:
        new_command["notes"] = args.notes

    data.setdefault("commands", []).append(new_command)
    save_data(data, target)
    print("Added '{}' to {}".format(args.name, target))
    return 0


def cmd_remove(args):
    target = ensure_user_config()
    data = load_data(target)
    command = resolve_command(data, args.name)
    name = command.get("name")

    if not args.yes:
        answer = input("Remove '{}'? [y/N] ".format(name)).strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return 1

    data["commands"] = [c for c in commands(data) if c.get("name") != name]
    save_data(data, target)
    print("Removed '{}'".format(name))
    return 0


def cmd_edit(args):
    target = ensure_user_config()
    command = resolve_command(load_data(target), args.name)
    name = command.get("name")

    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or shutil.which("nano") or shutil.which("vi")
    if not editor:
        raise CliError("No editor found. Set $EDITOR or $VISUAL.")

    completed = subprocess.run([editor, str(target)])
    if completed.returncode != 0:
        return completed.returncode

    try:
        load_data(target)
    except CliError as exc:
        raise CliError("File is invalid after edit: {}".format(exc))

    print("Saved '{}'".format(name))
    return 0


def cmd_init(args):
    target = write_path()
    if target.exists() and not args.force:
        print("Config already exists: {}".format(target))
        return 0
    data = load_data(BUNDLED_FILE)
    save_data(data, target)
    print("Config created: {}".format(target))
    return 0


def cmd_path(args):
    if args.write:
        print(write_path())
    else:
        print(read_path())
    return 0


def cmd_shell_init(args):
    function_name = args.name
    binary = shlex.quote(str(_binary()))
    template = """# commands shell integration
{function_name}() {{
  local __comandi_bin={binary}
  if [ "$#" -eq 0 ]; then
    command "$__comandi_bin" pick
    return
  fi

  case "$1" in
    run)
      shift
      if [ "$#" -eq 0 ]; then
        command "$__comandi_bin" run
        return
      fi
      local __mode
      __mode="$(command "$__comandi_bin" mode "$1" 2>/dev/null)" || return $?
      if [ "$__mode" = "eval" ]; then
        eval "$(command "$__comandi_bin" print "$1")"
      else
        command "$__comandi_bin" run --action run "$@"
      fi
      ;;
    use|eval)
      shift
      eval "$(command "$__comandi_bin" print "$@")"
      ;;
    *)
      command "$__comandi_bin" "$@"
      ;;
  esac
}}"""
    print(template.format(function_name=function_name, binary=binary))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="Personal archive of recurring shell commands. Run without arguments to open the interactive picker.",
    )
    sub = parser.add_subparsers(dest="command")

    list_p = sub.add_parser("list", aliases=["ls"], help="list saved commands")
    list_p.add_argument("query", nargs="?", help="text to search")
    list_p.add_argument("--tag", help="filter by tag")
    list_p.set_defaults(func=cmd_list)

    show_p = sub.add_parser("show", help="show details and script for a command")
    show_p.add_argument("name")
    show_p.set_defaults(func=cmd_show)

    print_p = sub.add_parser("print", help="print the shell script only")
    print_p.add_argument("name")
    print_p.set_defaults(func=cmd_print)

    mode_p = sub.add_parser("mode", help="print exec/eval mode for a command")
    mode_p.add_argument("name")
    mode_p.set_defaults(func=cmd_mode)

    run_p = sub.add_parser("run", help="run a saved command")
    run_p.add_argument("name")
    run_p.add_argument("--quiet", "-q", action="store_true", help="suppress command echo before running")
    run_p.add_argument("--subshell", action="store_true", help="allow eval-mode commands in a subshell")
    run_p.add_argument(
        "--action",
        choices=["copy", "run", "terminal"],
        default=None,
        help="how to run: copy to clipboard, run here, or open new terminal",
    )
    run_p.set_defaults(func=cmd_run)

    copy_p = sub.add_parser("copy", help="copy command script to clipboard")
    copy_p.add_argument("name")
    copy_p.set_defaults(func=cmd_copy)

    pick_p = sub.add_parser("pick", aliases=["ui"], help="interactive TUI picker")
    pick_p.add_argument("query", nargs="?", help="initial search text")
    pick_p.set_defaults(func=cmd_pick)

    add_p = sub.add_parser(
        "add",
        help="add a command — interactive wizard when called with no flags",
    )
    add_p.add_argument("name", nargs="?", default=None, help="command name (optional — prompted if omitted)")
    add_p.add_argument("--cmd", action="append", default=None, help="shell step to save; repeatable")
    add_p.add_argument("--desc", dest="description", default="", help="short description")
    add_p.add_argument("--alias", action="append", help="alias; repeatable")
    add_p.add_argument("--tag", action="append", help="tag; repeatable")
    add_p.add_argument("--env", action="append", help="env variable KEY=VALUE; repeatable")
    add_p.add_argument("--cwd", help="working directory")
    add_p.add_argument("--mode", choices=["exec", "eval"], default="exec", help=argparse.SUPPRESS)
    add_p.add_argument("--notes", help="free-form notes")
    add_p.set_defaults(func=cmd_add)

    remove_p = sub.add_parser("remove", aliases=["rm"], help="remove a saved command")
    remove_p.add_argument("name")
    remove_p.add_argument("--yes", "-y", action="store_true", help="skip confirmation prompt")
    remove_p.set_defaults(func=cmd_remove)

    edit_p = sub.add_parser("edit", help="open the commands file in $EDITOR")
    edit_p.add_argument("name", help="command name (used to verify file is still valid after edit)")
    edit_p.set_defaults(func=cmd_edit)

    init_p = sub.add_parser("init", help="create ~/.config/commands/commands.json")
    init_p.add_argument("--force", action="store_true", help="overwrite existing config")
    init_p.set_defaults(func=cmd_init)

    path_p = sub.add_parser("path", help="print the active commands file path")
    path_p.add_argument("--write", action="store_true", help="print the file that would be written to")
    path_p.set_defaults(func=cmd_path)

    shell_p = sub.add_parser("shell-init", help="print shell wrapper to eval in your shell profile")
    shell_p.add_argument("--name", default="c", help="shell function name to create (default: c)")
    shell_p.set_defaults(func=cmd_shell_init)

    return parser


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "_preview":
        if len(argv) < 2:
            print("Error: missing preview index", file=sys.stderr)
            return 1
        return cmd_preview(argparse.Namespace(index=argv[1]))

    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        if sys.stdin.isatty() and sys.stdout.isatty():
            data = load_data()
            if not commands(data):
                print("Welcome to commands-cli!")
                print("No commands saved yet.\n")
                print("Run 'commands add' to add your first command.")
                return 0
            return cmd_pick(argparse.Namespace(query=None))
        return cmd_list(argparse.Namespace(query=None, tag=None))
    try:
        return int(args.func(args))
    except CliError as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
