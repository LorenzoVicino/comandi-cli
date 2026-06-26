# commands-cli

Personal CLI for saving and running your frequently used shell commands.

The main command is `commands`. The recommended shell wrapper is `c`, which can
`eval` commands in the current shell when needed.

The interactive picker uses [`fzf`](https://github.com/junegunn/fzf).

## Install

```bash
pip install commands-cli
eval "$(commands shell-init)"
```

To make the `c` wrapper permanent, add to `~/.bashrc` or `~/.zshrc`:

```bash
eval "$(commands shell-init)"
```

### Development install

```bash
git clone https://github.com/your-username/commands-cli
cd commands-cli
pip install -e .
eval "$(commands shell-init)"
```

Or without pip:

```bash
./install.sh
eval "$(commands shell-init)"
```

## Update

If installed from PyPI:

```bash
pip install --upgrade commands-cli
eval "$(commands shell-init)"
```

If installed from a Git checkout:

```bash
cd /path/to/commands-cli
git pull
PYTHON=python3.10  # or another Python 3.8+ executable
$PYTHON -m pip install --user --upgrade "pip>=23" "setuptools>=64,<82"
$PYTHON -m pip uninstall -y comandi-cli
$PYTHON -m pip install -e .
eval "$(commands shell-init)"
```

The `comandi-cli` uninstall is only needed when upgrading from the old package
name. It prevents the old installed `comandi` module from shadowing the editable
checkout.

If installed with `./install.sh`, update the checkout and run the installer again:

```bash
cd /path/to/commands-cli
git pull
./install.sh
eval "$(commands shell-init)"
```

If `pip install -e .` reports that the backend is missing `build_editable`,
upgrade pip and setuptools first:

```bash
PYTHON=python3.10  # or another Python 3.8+ executable
$PYTHON -m pip install --user --upgrade "pip>=23" "setuptools>=64,<82"
$PYTHON -m pip install -e .
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
comando1         # run a saved command through a keyword shortcut
```

## Adding commands

### Interactive wizard

```bash
commands add
```

```
Command name: my-deploy
Description (optional): Deploy app to staging
Shell command (step 1): npm run build
Step 2 (blank to finish): aws s3 sync dist/ s3://my-bucket/
Step 3 (blank to finish):
Add advanced options? (tags, aliases, keywords, env vars, working dir, notes) Yes
Tags (comma-separated, optional): aws,deploy
Aliases (comma-separated, optional): deploy
Keywords (comma-separated, optional): deploy_staging
Working directory (optional):
Env var KEY=VALUE (blank to finish): AWS_PROFILE=staging
Another env var (blank to finish):
Notes (optional):

Added 'my-deploy' to /home/user/.config/commands/commands.json
```

### One-liner flags

```bash
commands add logs-api \
  --desc "Tail CloudWatch logs for the API service" \
  --keyword logs_api \
  --tag aws \
  --env AWS_PROFILE=prod \
  --cmd "aws logs tail /aws/copilot/app/prod/api --follow"
```

After adding or changing keywords, refresh the shell functions:

```bash
eval "$(commands shell-init)"
logs_api
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
commands keywords ssh-agent --add comando1
commands keywords ssh-agent --remove comando1
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
