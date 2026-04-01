"""
pydevversions use case
"""

from tqdm import tqdm
import os
import subprocess
import shutil
import re
from rich.console import Console
from rich.table import Table
from rich.text import Text
from pydevversions.args import compute_args
from datetime import datetime
import getpass
import json

json_obj = {"info": {}, "programs": []}
args = compute_args()
raw=compute_args().raw
is_json=compute_args().json
shell_path = os.environ.get("SHELL", "/bin/bash")
shell = os.path.basename(shell_path)  # "bash", "zsh", etc.
if shell == "bash":
    rc_files = ["~/.bashrc"]
elif shell == "zsh":
    rc_files = ["~/.zshrc"]
else:
    rc_files = ["~/.profile"]

labels = {
    "date": "date" if raw else "📅 date",
    "user": "user" if raw else "👤 user",
    "home": "home" if raw else "🏠 home",
    "shell": "shell" if raw else "💻 shell",
}

# Affichage
info = {
    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "user": getpass.getuser(),
    "home": os.path.expanduser("~"),
    "shell": shell,
}
for key in ["date", "user", "home", "shell"]:
    if not is_json:
        print(f"{labels[key]:<10} : {info[key]}")
    else:
        json_obj["info"][key] = info[key]
  
source_cmds = " && ".join(f"[ -f {os.path.expanduser(f)} ] && source {os.path.expanduser(f)}" for f in rc_files)
cmd = f"{source_cmds} && env"

result = subprocess.run([shell, "-c", cmd], capture_output=True, text=True)
env = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)

# Regex pour tout mot contenant x.y ou x.y.z
word_with_version_regex = re.compile(r'\b\w*\d+\.\d+(?:\.\d+)?\S*\b')

def color_version(cell):
    if raw:
        return cell
    text = Text(cell)
    if cell=="not installed":
        text.stylize("red bold")
        return text
    for match in re.finditer(word_with_version_regex, cell):
        text.stylize("yellow bold", match.start(), match.end())
    return text

def color_path(cell):
    if raw:
        return cell    
    text = Text(cell)
    if cell=="NA":
        text.stylize("red bold")
        return text
    return cell

commands = [
    "bash",
    "biome",
    {"name": "cf", "version_cmd": ["cf", "version"]},
    {"name": "cf7", "version_cmd": ["cf7", "version"]},
    {"name": "cf8", "version_cmd": ["cf8", "version"]},
    "chromedriver",
    "code",
    "curl",
    "docker",
    {
        "name": "docker compose",
        "version_cmd": ["docker", "compose", "version"],
        "path_cmd": ["whereis", "-b", "docker"]
    },
    "firefox",
    "fly",
    "git",
    "gradle",
    "google-chrome",
    "groovy",
    "hadolint",
    {"name": "helm", "version_cmd": ["helm", "version"]},
    "intellij",
    "java",
    "jq",
    {
        "name": "kernel",
        "version_cmd": ["uname", "-r"],
        "path_cmd": [shell, "-c", "readlink -f /boot/vmlinuz-$(uname -r)"] 
    },   
    {
        "name": "kotlin",
        "version_cmd": ["kotlin", "-version"],
    },
    {
        "name": "krew",
        "version_cmd": ["krew", "version"]
    },
    {
        "name": "kubectl",
        "version_cmd": ["kubectl", "version","--client=true"],
    }, 
    {
        "name": "k9s",
        "version_cmd": ["k9s", "version", "-s"],
    },            
    {
        "name": "lift",
        "version_cmd": ["lift", "version"],
    },
    "lino",
    {
        "name": "linux",
        "version_cmd": ["cat", "/etc/os-release"],
        "path_cmd": ["echo", "/etc/os-release"] 
    },  
    "mongo",
    "mvn",
    "node",
    "npm",
    "nvm",
    "pip",
    "pip3",
    "pipx",
    "python",
    "python3",
    "secretops",
    {
        "name": "ssh",
        "version_cmd": ["ssh", "-v"]
    },  
    "trivy",
    "wget",
    "yarn",
    "zsh"
]

def run_command(cmd):

    binary = cmd[0]

    # binaire réel
    if shutil.which(binary):
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env
        )
    else:
        check = subprocess.run(
            [shell, "-i", "-c", f"type {binary}"],
            capture_output=True,
            text=True,
            env=env
        )

        if check.returncode != 0:
            return "not installed"

        cmd_str = " ".join(cmd)
        result = subprocess.run(
            [shell, "-i", "-c", cmd_str],
            capture_output=True,
            text=True,
            env=env
        )

    if result.returncode == 0:
        return (result.stdout.strip() or result.stderr.strip())

    return "NA"

def app():
    rows = []

    console = Console()
    header_style = "bold yellow" if not raw else None
    if not is_json:
        table = Table(show_header=True, header_style=header_style,show_lines=True)
        table.add_column("Binary")
        table.add_column("Version")
        table.add_column("Path")
    one = False
    iterable = commands #if raw else tqdm(commands, desc="⏳ progress ", bar_format="{l_bar}{bar}")

    for item in iterable:
        if isinstance(item, str):
            if getattr(compute_args(), "filter", None) and compute_args().filter not in item:
                continue 
            one=True
            name = item
            base_binary = item.split()[0]
            version_cmd = [base_binary, "--version"]
            if shutil.which(base_binary):
                path_cmd = ["whereis", "-b", base_binary]
            else:
                check_type = subprocess.run(
                    [shell, "-i", "-c", f"type {base_binary}"],
                    capture_output=True,
                    text=True
                )
                path_cmd = ["echo", check_type.stdout.strip()]

        else:
            name = item["name"]
            if getattr(compute_args(), "filter", None) and compute_args().filter not in name:
                continue  
            one=True          
            base_binary = name.split()[0]

            version_cmd = item.get(
                "version_cmd",
                [base_binary, "--version"]
            )

            name = item["name"]
            base_binary = name.split()[0]

            path_cmd = item.get("path_cmd")
            if path_cmd is None:
                if shutil.which(base_binary):
                    path_cmd = ["whereis", "-b", base_binary]
                else:
                    check_type = subprocess.run(
                        [shell, "-i", "-c", f"type {base_binary}"],
                        capture_output=True,
                        text=True
                    )
                    path_cmd = ["echo", check_type.stdout.strip()]

        version = run_command(version_cmd)
        if version != "not installed":
            path_output = run_command(path_cmd)
        else:
            path_output = "NA"

        if version != "not installed" or args.full or getattr(compute_args(), "filter", None):  
            if not is_json:                    
                table.add_row(name, color_version(version), color_path(path_output))
            else:
                json_obj["programs"].append({
                    "name": name,
                    "version": version,
                    "path": path_output
                })
    if not is_json:
        console.print(table)
    else:
        print(json.dumps(json_obj, indent=4))
    if one == False:
        print("⚠️  Nothing found")
