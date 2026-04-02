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
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
yaml_path = BASE_DIR / "apps.yaml"

with open(yaml_path, "r") as f:
    config = yaml.safe_load(f)

json_obj = {"info": {}, "programs": []}
args = compute_args()
raw=compute_args().raw
is_json=compute_args().json
compact=compute_args().compact
if not compute_args().shell:
    shell_path = os.environ.get("SHELL", "/bin/bash")
    shell = os.path.basename(shell_path)  # "bash", "zsh", etc.
else:
    shell=compute_args().shell  
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
  
source_cmd = "source" if shell in ["bash", "zsh"] else "."

source_cmds = " && ".join(
    f"[ -f {os.path.expanduser(f)} ] && {source_cmd} {os.path.expanduser(f)}"
    for f in rc_files
)
cmd = f"{source_cmds} && env"

result = subprocess.run([shell, "-c", cmd], capture_output=True, text=True)

env = dict(
    line.split("=", 1)
    for line in result.stdout.splitlines()
    if "=" in line
)

# Regex pour tout mot contenant une version
word_with_version_regex = re.compile(r'\S*\d\S*')

def color_version(cell):
    if compact:
        matches = list(re.finditer(word_with_version_regex, cell))
        new_cell = " ".join(match.group(0) for match in matches)

        if new_cell.strip():  # non vide après suppression des espaces
            cell = new_cell
    if raw or is_json:
        return cell
    text = Text(cell)
    if cell=="not installed":
        text.stylize("red bold")
        return text
    for match in re.finditer(word_with_version_regex, cell):
        text.stylize("yellow bold", match.start(), match.end())
    return text

def color_path(cell):
    if raw or is_json:
        return cell    
    text = Text(cell)
    if cell=="NA":
        text.stylize("red bold")
        return text
    return cell



commands = config["commands"]
def run_command(cmd):
    try:
        binary = cmd[0]
        # binaire réel
        if shutil.which(binary):
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )        
        # alias ou fonction    
        else:
            check = subprocess.run(
                [shell, "-i", "-c", f"type {binary}"],
                capture_output=True,
                text=True,
                env=env
            )
            # fallback
            if check.returncode != 0:
                return "not installed"

            #appel à l'alias ou la fonction via un shell dédié
            cmd_str = " ".join(cmd)
            result = subprocess.run(
                [shell, "-i", "-c", cmd_str],
                capture_output=True,
                text=True,
                env=env
            )     
        if result.returncode == 0:
            return (result.stdout.strip() or result.stderr.strip())
        # fallback
        return "not installed"
    except Exception:
        return "not installed"
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
    iterable = commands if (raw or is_json) else tqdm(commands, desc="⏳ progress : ", bar_format="{desc}{percentage:3.0f}%")
    filters = getattr(compute_args(), "filter", None)
    categories = getattr(compute_args(), "categories", None)
    for item in iterable:
        name = item["name"]
        item_categories = item.get("categories", [])
        if filters and not any(f in name for f in (filters if isinstance(filters, list) else [filters])):
            continue
        if categories and not any(
            c in item_categories for c in (categories if isinstance(categories, list) else [categories])
        ):
            continue          
        
        name = item["name"]
        base_binary = name.split()[0]


        #preparation commande pour display version
        version_cmd = item.get(
            "version_cmd",
            [base_binary, "--version"]
        )

        #preparation commande pour display path
        path_cmd = item.get("path_cmd")
        if path_cmd is None:
            #gestion binaire/alias
            if shutil.which(base_binary):
                path_cmd = ["whereis", "-b", base_binary]
            else:
                check_type = subprocess.run(
                    [shell, "-i", "-c", f"type {base_binary}"],
                    capture_output=True,
                    text=True
                )
                path_cmd = ["echo", check_type.stdout.strip()]

        #calcul version
        if not compute_args().compact:
            version = run_command(version_cmd)
        else:
            version_tmp = run_command(version_cmd).splitlines()
            version = version_tmp[0] if version_tmp else ""                
        if version != "not installed":
            output = run_command(path_cmd).splitlines()
            path_output = output[0] if output else ""
            
        else:
            path_output = "NA"

        if version != "not installed" or args.full or getattr(compute_args(), "filter", None):  
            if not is_json:                    
                table.add_row(name, color_version(version), color_path(path_output))
            else:
                json_obj["programs"].append({
                    "name": name,
                    "version": color_version(version),
                    "path": path_output
                })
    if not is_json:
        console.print(table)
    else:
        print(json.dumps(json_obj, indent=4))
