"""
pydevversions use case
"""

from pydevversions.args import compute_args, get_all_categories

from tqdm import tqdm
from rich.console import Console
from rich.table import Table
from rich.text import Text
from datetime import datetime
from pathlib import Path

import subprocess
import shutil
import re
import getpass
import json
import yaml
import sys
import os
import getpass
import psutil
import platform
import distro 


#initialisation
BASE_DIR = Path(__file__).resolve().parent
yaml_path = BASE_DIR / "apps.yaml"
word_with_version_regex = re.compile(r'\S*\d\S*')
args = compute_args()
raw=compute_args().raw
is_json=compute_args().json
compact=compute_args().compact
debug=compute_args().debug
noinfo=compute_args().noinfo
noprogress=compute_args().noprogress
noprograms=compute_args().noprograms
filters = getattr(compute_args(), "filter", None)
categories = getattr(compute_args(), "categories", None)
json_obj = {}
if not noinfo:
    json_obj["info"] = {}
if not noprograms:
    json_obj["programs"] = []
console = Console()
header_style = "bold yellow" if not raw else None
if not is_json:
    table = Table(show_header=True, header_style=header_style, show_lines=True)
    table.add_column("Binary")
    table.add_column("Version")
    table.add_column("Path")
    
use_tqdm = not (raw or is_json or debug or noprogress or noprograms)

#filter apps
with open(yaml_path, "r") as f:
    config = yaml.safe_load(f)
apps = config.get("commands", [])
command_names = [cmd["name"] for cmd in apps]
all_categories = set()
for cmd in apps:
    cats = cmd.get("categories", [])
    all_categories.update(cats)
if categories is not None:
    invalid = [cat for cat in categories if cat not in all_categories]
    if invalid:
        message = (
            "Error: non-existent category: "
            + ", ".join(invalid)
            + ". Available category are "
            + ", ".join(sorted(all_categories))
        )
        if not raw:
            message = "⚠️  " + message
        sys.exit(message)
if categories is not None:
    filtered_apps = [
        cmd for cmd in apps
        if any(cat in cmd.get("categories", []) for cat in categories)]
else:
    filtered_apps = apps
filtered_command_names = [cmd["name"] for cmd in filtered_apps]
if filters is not None:
    invalid = [f for f in filters if f not in filtered_command_names]
    if invalid:
        message = (
            "Error: non-existent application(s): "
            + ", ".join(invalid)
            + ". Available applications: "
            + ", ".join(filtered_command_names)
        )
        if not raw:
            message = "⚠️  " + message
        sys.exit(message)
commands_filtered = [cmd for cmd in filtered_apps if not filters or cmd["name"] in filters]

#prepare shell
if not compute_args().shell:
    shell_path = os.environ.get("SHELL", "/bin/bash")
    shell = os.path.basename(shell_path) 
else:
    shell=compute_args().shell  
if shell == "bash":
    rc_files = ["~/.bashrc"]
elif shell == "zsh":
    rc_files = ["~/.zshrc"]
else:
    message = "Erreur : shell not in bash,zsh"
    if not raw:
        message = "⚠️  " + message
    sys.exit(message)
source_cmd = "source"
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



def gpu_infos():
    result = subprocess.run(
        ["lspci"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return "not available (error running lspci)"            
    gpus = []
    for line in result.stdout.splitlines():
        if "VGA compatible controller" in line:
            name = line.split(":")[-1].strip()
            gpus.append(name)
    return ", ".join(gpus) if gpus else ["no GPU detected"]

def secure_boot_infos():
    result = subprocess.run(
        ["mokutil", "--sb-state"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return "not available (error running mokutil)"
    output = result.stdout.lower()
    if "enabled" in output:
        return "activated"
    elif "disabled" in output:
        return "not activated"
    else:
        return "not available (unexpected output running mokutil)"
    
def disk_encryption_infos():
    result = subprocess.run(
        ["lsblk", "-f"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "not available (error running lsblk)"    
    output = result.stdout.lower()
    if "crypto" in output:
        return "encrypted"
    else:
        return "not encrypted"

def cpu_infos():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    return line.strip().split(":")[1]
    except:
        return "not available (error opening /proc/cpuinfo)"

def display_server_infos():
    if os.environ.get("WAYLAND_DISPLAY"):
        return "Wayland"
    elif os.environ.get("DISPLAY"):
        return "X11"
    else:
        return "not available"

def format_bytes(size):
    if size is None:
        return "unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

def stylize_version(cell):
    if compact:
        matches = list(re.finditer(word_with_version_regex, cell))
        reduced_cell = " ".join(match.group(0) for match in matches)
        if reduced_cell.strip():
            cell = reduced_cell
    if raw or is_json:
        return cell
    text = Text(cell)
    if cell=="not installed":
        text.stylize("red bold")
        return text
    for match in re.finditer(word_with_version_regex, cell):
        text.stylize("yellow bold", match.start(), match.end())
    return text

def stylize_path(cell):
    if raw or is_json:
        return cell    
    text = Text(cell)
    if cell=="NA":
        text.stylize("red bold")
        return text
    return cell

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
            if result.returncode == 0:
                return (result.stdout.strip() or result.stderr.strip())
            if debug:
                print("")
                print(cmd)
                print(f"CODE    : {result.returncode}")
                print(f"STDOUT  : {result.stdout}")
                print(f"STDERR  : {result.stderr}")                   
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
                if debug:
                    print("")
                    print([shell, "-i", "-c", f"type {binary}"])
                    print(f"CODE    : {check.returncode}")
                    print(f"STDOUT  : {check.stdout}")
                    print(f"STDERR  : {check.stderr}") 


                flatpak_check_user = subprocess.run(
                    ["flatpak", "--user", "list", "--app", "--columns=application"],
                    capture_output=True,
                    text=True
                )
                user=False
                if flatpak_check_user.returncode == 0:
                    apps = flatpak_check_user.stdout.splitlines()

                    for app in apps:
                        if binary.lower() in app.lower():

                            info_check = subprocess.run(
                                ["flatpak", "--user", "info", app],
                                capture_output=True,
                                text=True
                            )

                            version = None

                            if info_check.returncode == 0:
                                for line in info_check.stdout.splitlines():
                                    if line.lstrip().lower(). startswith("version"):

                                        version = line.split(":", 1)[1].strip()
                                        user=True
                                        break

                            if version:
                                return f"{version}"
                            else:
                                return "not available"


                else:
                    if debug:
                        print(f"CODE    : {flatpak_check_user.returncode}")
                        print(f"STDOUT  : {flatpak_check_user.stdout}")
                        print(f"STDERR  : {flatpak_check_user.stderr}")
                if user==False:
                    flatpak_check_system = subprocess.run(
                        ["flatpak", "--system", "list", "--app", "--columns=application"],
                        capture_output=True,
                        text=True
                    )
                    user=False
                    if flatpak_check_system.returncode == 0:
                        apps = flatpak_check_system.stdout.splitlines()

                        for app in apps:
                            if binary.lower() in app.lower():

                                info_check = subprocess.run(
                                    ["flatpak", "--system", "info", app],
                                    capture_output=True,
                                    text=True
                                )

                                version = None

                                if info_check.returncode == 0:
                                    for line in info_check.stdout.splitlines():
                                        if line.lstrip().lower(). startswith("version"):

                                            version = line.split(":", 1)[1].strip()
                                            user=True
                                            break

                                if version:
                                    return f"{version}"
                                else:
                                    return "not available"

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
            if debug:
                print("")
                print([shell, "-i", "-c", cmd_str])
                print(f"CODE    : {result.returncode}")
                print(f"STDOUT  : {result.stdout}")
                print(f"STDERR  : {result.stderr}")                         

        # fallback
        return "not installed"
    except Exception as e:
        if debug:
            print(e)
        return "not installed"



def app():
    #info bloc
    if not noinfo:
        labels = {
            "date": "date" if raw else "📅 date",
            "user": "user" if raw else "👤 user",
            "home": "home" if raw else "🏠 home",
            "shell": "shell" if raw else "💻 shell",
            "cpu": "cpu" if raw else "🧠 cpu",
            "ram": "ram" if raw else "⚡ ram",
            "video": "video" if raw else "🎮 video",
            "disk": "disk" if raw else "💾 disk",
            "os": "os" if raw else "💻  os",
            "secureboot": "SecureBoot" if raw else "🔐 SecureBoot",
            "diskcrypto": "Disk Crypto" if raw else "🔐 Disk Crypto",
            "display": "Display" if raw else "💻 Display",            
        }
        info = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": getpass.getuser(),
            "home": os.path.expanduser("~"),
            "shell": shell,
            "cpu": f"{cpu_infos()} ({os.cpu_count()} cores {psutil.cpu_freq() .max/1000:.2f} GHz)",
            "ram": format_bytes(psutil.virtual_memory().total),
            "disk": format_bytes(psutil.disk_usage('/').total),
            "video": gpu_infos(),
            "os": f"{distro.name()} {distro.version()} ({platform.release()})",
            "secureboot": secure_boot_infos(),
            "diskcrypto": disk_encryption_infos(),  
            "display": display_server_infos(),           
        }
        for key in ["date", "user", "home", "shell", "cpu", "ram", "disk", "video", "os", "secureboot", "diskcrypto", "display"]:
            if not is_json:
                print(f"{labels[key]:<15} : {info[key]}")
            else:
                json_obj["info"][key] = info[key]
    
    #apps bloc
    if not noprograms:
        iterable = tqdm(
            commands_filtered,
            desc="⏳ progress      : ",
            bar_format="{desc}{percentage:3.0f}% {postfix}"
        ) if use_tqdm else commands_filtered
        for item in iterable:
            name = item["name"]
            base_binary = name.split()[0]

            item_categories = item.get("categories", [])
            if filters and not any(f in name for f in (filters if isinstance(filters, list) else [filters])):
                continue
            if categories and not any(
                c in item_categories for c in (categories if isinstance(categories, list) else [categories])
            ):
                continue          
            if use_tqdm:
                iterable.set_postfix_str(base_binary)
            
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
                    path_cmd = ["which", base_binary]
                else:
                    check_type = subprocess.run(
                        [shell, "-i", "-c", f"type {base_binary}"],
                        capture_output=True,
                        text=True
                    )
                    if check_type.returncode == 0:
                        path_cmd = ["echo", check_type.stdout.strip()]
                    if check_type.returncode != 0:
                        if debug:
                            print("")
                            print([shell, "-i", "-c", f"type {base_binary}"])
                            print(f"CODE    : {check_type.returncode}")
                            print(f"STDOUT  : {check_type.stdout}")
                            print(f"STDERR  : {check_type.stderr}") 

                        try:
                            user=False
                            flatpak_check_user = subprocess.run(
                                ["flatpak", "--user", "list", "--app", "--columns=application"],
                                capture_output=True,
                                text=True
                            )

                            if flatpak_check_user.returncode == 0:
                                apps = flatpak_check_user.stdout.splitlines()
                                for app in apps:
                                    if base_binary.lower() in app.lower():
                                        user=True
                                        path_cmd = ["echo", f"flatpak --user run {app}"]
                            if not user:
                                flatpak_check_system = subprocess.run(
                                    ["flatpak", "--system", "list", "--app", "--columns=application"],
                                    capture_output=True,
                                    text=True
                                )

                                if flatpak_check_system.returncode == 0:
                                    apps = flatpak_check_system.stdout.splitlines()
                                    for app in apps:
                                        if base_binary.lower() in app.lower():
                                            user=True
                                            path_cmd = ["echo", f"flatpak --system run {app}"]                                
                        except FileNotFoundError:
                            if debug:
                                print("Flatpak not installed")  

            #calcul version
            if not compute_args().compact:
                version = run_command(version_cmd)
            else:
                version_tmp = run_command(version_cmd).splitlines()
                version = "\n".join(version_tmp[:5])               
            if version != "not installed":
                output = run_command(path_cmd).splitlines()
                path_output = output[0] if output else ""
            else:
                path_output = "NA"

            if version != "not installed" or args.full or getattr(compute_args(), "filter", None):  
                if not is_json:                    
                    table.add_row(name, stylize_version(version), stylize_path(path_output))
                else:
                    json_obj["programs"].append({
                        "name": name,
                        "version": stylize_version(version),
                        "path": path_output
                    })
        if not is_json:
            console.print(table)
    
    #json bloc
    if is_json:
        print(json.dumps(json_obj, indent=4))
