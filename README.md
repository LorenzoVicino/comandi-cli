# comandi-cli

Personal CLI for saving and running your frequently used shell commands.

The main command is `commands`. The recommended shell wrapper is `c`, which can
`eval` commands in the current shell when needed.

The interactive picker uses [`fzf`](https://github.com/junegunn/fzf).

## Install

```bash
pip install comandi-cli
eval "$(commands shell-init)"
```

To make the `c` wrapper permanent, add to `~/.bashrc` or `~/.zshrc`:

```bash
eval "$(commands shell-init)"
```

### Development install

```bash
git clone https://github.com/your-username/comandi-cli
cd comandi-cli
pip install -e .
eval "$(commands shell-init)"
```

Or without pip:

```bash
./install.sh
eval "$(commands shell-init)"
```

## Quick start

```bash
commands         # open interactive TUI picker (requires fzf)
commands list     # list all saved commands
commands list aws # filter by keyword
commands show ssh-agent
commands run git-clean
```

With the shell wrapper:

```bash
c                # open picker
c run ssh-agent  # run — uses eval automatically if mode=eval
```

## Adding commands

### Interactive wizard

```bash
commands add
```

```
Interactive command builder — Ctrl+C to cancel

Name> my-deploy
Description (optional)> Deploy app to staging
Tags (comma-separated, optional): aws,deploy
Aliases (comma-separated, optional): deploy
Mode [exec/eval] [exec]> exec
Working directory (optional)>

Environment variables (KEY=VALUE)  (one per line — blank line to finish):
  > AWS_PROFILE=staging
  >

Steps (shell commands)  (one per line — blank line to finish):
  > npm run build
  > aws s3 sync dist/ s3://my-bucket/
  >

Notes (optional)>

Added 'my-deploy' to /home/user/.config/comandi/commands.json
```

### One-liner flags

```bash
commands add logs-api \
  --desc "Tail CloudWatch logs for the API service" \
  --tag aws \
  --env AWS_PROFILE=prod \
  --cmd "aws logs tail /aws/copilot/app/prod/api --follow"
```

Multi-step:

```bash
commands add setup-project \
  --desc "Install dependencies and start dev server" \
  --cwd ~/projects/myapp \
  --cmd "npm install" \
  --cmd "npm run dev"
```

Shell-mutating command (sets env vars in current shell):

```bash
commands add use-java-21 \
  --desc "Set JAVA_HOME for this shell" \
  --mode eval \
  --cmd "export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64" \
  --cmd 'export PATH="$JAVA_HOME/bin:$PATH"'

c run use-java-21
```

## Managing commands

```bash
commands list              # list all
commands list aws          # filter by keyword
commands list --tag aws    # filter by tag
commands show ssh-agent    # show details + script
commands copy ssh-agent    # copy script to clipboard
commands remove ssh-agent  # delete a command
commands edit ssh-agent    # open commands file in $EDITOR
commands path              # show active commands file
commands path --write      # show file that would be written to
```

## eval-mode commands

Commands that modify the current shell (export vars, set aliases) use `mode: eval`.
Run them with the wrapper or eval explicitly:

```bash
c run ssh-agent
# or
eval "$(commands print ssh-agent)"
```

## Data file

Read priority:

1. `$COMANDI_FILE` if set
2. `~/.config/commands/commands.json` if it exists
3. Bundled `data/commands.json` inside the package

This lets you keep the project versioned while keeping personal commands in the
user config file.

## Requirements

- Python 3.8+
- [`fzf`](https://github.com/junegunn/fzf) for the interactive picker (optional)
- A clipboard tool for `copy`/`pick`: `wl-copy`, `xclip`, `xsel`, `pbcopy`, or `clip.exe` (or OSC 52 terminal support)
