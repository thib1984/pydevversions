"""
pydevversions use case
"""

from pydevversions.args import compute_args, get_all_categories
from importlib.metadata import version, PackageNotFoundError
from concurrent.futures import ThreadPoolExecutor, as_completed

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
import shlex
import time

def format_message(label, text, emoji):
    spaces = max(1, 14 - len(label))
    prefix = f"{emoji} " if not (is_json or raw) else ""
    return f"{prefix}{label}{' ' * spaces}: {text}"

#initialisation
args = compute_args()
workers=args.threads
raw=args.raw
is_json=args.json
details=args.details
debug=args.debug
notime=args.notime
noinfo=args.noinfo
noprogress=args.noprogress
noparams=args.noparams
noprograms=args.noprograms
noflatpak=args.noflatpak
noalias=args.noalias
filters =args.filter
categories=args.categories
type_shell=args.shell
is_filter=getattr(args, "filter", None)
json_obj = {}
try:
    app_version = version("pydevversions")
except PackageNotFoundError:
    app_version = "dev"
if not noparams:
    if not is_json:
        print(format_message("pydevversions",f"v{app_version} is running...","🚀"))
        print(format_message("command",' '.join(sys.argv[0:]),"🧾"))
        print(format_message("date",datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"📅"))
    else:      
        json_obj["params"] = {}
        json_obj["params"]["version"] = f"pydevversions {app_version}"  
        json_obj["params"]["command"] = ' '.join(sys.argv[0:])
        json_obj["params"]["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
start_time = time.time()  # 🔹 start timer
BASE_DIR = Path(__file__).resolve().parent
yaml_path = BASE_DIR / "apps.yaml"
word_with_version_regex = re.compile(r'\S*\d\S*')

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
        sys.exit(format_message("error", "non-existent category: "
            + ", ".join(invalid)
            + ". Available category are "
            + ", ".join(sorted(all_categories))
        ,"❌"))
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
        sys.exit(format_message("error", "non-existent application(s): "
            + ", ".join(invalid)
            + ". Available applications: "
            + ", ".join(filtered_command_names)
        ,"❌"))
commands_filtered = [cmd for cmd in filtered_apps if not filters or cmd["name"] in filters]

#prepare shell
if not type_shell:
    shell_path = os.environ.get("SHELL", "/bin/bash")
    shell = os.path.basename(shell_path) 
else:
    shell=type_shell  
if shell == "bash":
    rc_files = ["~/.bashrc"]
elif shell == "zsh":
    rc_files = ["~/.zshrc"]
else:
    sys.exit(format_message("error", "shell not in bash,zsh","❌"))
source_cmd = "source"
source_cmds = " && ".join(
    f"[ -f {os.path.expanduser(f)} ] && {source_cmd} {os.path.expanduser(f)}"
    for f in rc_files
)
cmd_src = f"{source_cmds} && env"
if debug:
    print(format_message("debug cmdsrc",cmd_src,"👾"))
result = subprocess.run([shell, "-c", cmd_src], capture_output=True, text=True)
if debug:
    print(format_message("debug cmdsrc",result,"👾"))
env = dict(
    line.split("=", 1)
    for line in result.stdout.splitlines()
    if "=" in line
)
if noalias:
    aliases=[]
    functions=[]
else:       
    alias_proc = subprocess.run(
        [shell, "-i", "-c", "alias -L | awk -F'[ =]' '{print $2}'"],
        capture_output=True,
        text=True
    )
    aliases = set(alias_proc.stdout.split())
    if debug:
        print(format_message("debug aliases",str(aliases),"👾"))
    func_proc = subprocess.run(
        [shell, "-i", "-c", "compgen -A function"],
        capture_output=True,
        text=True
    )
    functions = set(func_proc.stdout.split())
    if debug:
        print(format_message("debug functions",str(functions),"👾"))

def get_flatpak_version(binary):
    binary = binary.lower()
    for scope in ("--user", "--system"):
        result = subprocess.run(
            ["flatpak", scope, "list", "--app", "--columns=application"],
            capture_output=True,
            text=True
        )
        if debug:
            print(format_message("debug flatpak list",result,"👾"))
        if result.returncode != 0:
            continue

        for app in result.stdout.splitlines():
            app_lower = app.lower()
            words = re.split(r"[._-]", app_lower)
            if binary in words:
                info = subprocess.run(
                    ["flatpak", scope, "info", app],
                    capture_output=True,
                    text=True
                )
                if debug:
                    print(format_message("debug flatpak info",result,"👾"))
                if info.returncode != 0:
                    continue

                for line in info.stdout.splitlines():
                    if line.strip().lower().startswith("version"):
                        return line.split(":", 1)[1].strip()

                return "not available"

    return None


def find_flatpak_command(base_binary):
    base_binary = base_binary.lower()

    for scope in ("--user", "--system"):
        result = subprocess.run(
            ["flatpak", scope, "list", "--app", "--columns=application"],
            capture_output=True,
            text=True
        )
        if debug:
            print(format_message("debug flatpak list",result,"👾"))
        if result.returncode != 0:
            continue
        for app in result.stdout.splitlines():
            app_lower = app.lower()
            words = re.split(r"[._-]", app_lower)
            if base_binary in words:
                return ["echo", f"flatpak {scope} run {app}"]

    return None


def gpu_infos():
    try:
        result = subprocess.run(
            ["lspci"],
            capture_output=True,
            text=True
        )
        if debug:
            print(format_message("debug lspci", result, "👾"))    

        if result.returncode != 0:
            return "gpu information cannot be determined"            

        gpus = []
        for line in result.stdout.splitlines():
            if "VGA compatible controller" in line:
                name = line.split(":", 2)[-1].strip()
                gpus.append(name)

        if gpus:
            return ", ".join(gpus)
        else:
            return "no GPU detected"

    except Exception:
        return "gpu information cannot be determined"
    
def secure_boot_infos():
    try:
        result = subprocess.run(
            ["mokutil", "--sb-state"],
            capture_output=True,
            text=True
        )
        if debug:
            print(format_message("debug mokutil",result,"👾"))      
        if result.returncode != 0:
            return "secure boot state cannot be determined"
        output = result.stdout.lower()
        if "enabled" in output:
            return "secure boot enabled"
        elif "disabled" in output:
            return "secure boot disabled"
        else:
            return "secure boot state cannot be determined"
    except:
        return "secure boot state cannot be determined"    
def disk_encryption_infos():
    try:
        result = subprocess.run(
            ["lsblk", "-f"],
            capture_output=True,
            text=True,
        )
        if debug:
            print(format_message("debug lsblk",result,"👾"))       
        if result.returncode != 0:
            return "disk encryption state cannot be determined"    
        output = result.stdout.lower()
        if "crypto" in output:
            return "disk encrypted"
        else:
            return "disk not encrypted"
    except:
        return "disk encryption state cannot be determined"    

def cpu_infos():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    return line.split(":", 1)[1].strip()
        return "cpu infos cannot be determined"
    except Exception:
        return "cpu infos cannot be determined"

def display_server_infos():
    try:
        if os.environ.get("WAYLAND_DISPLAY"):
            return "Wayland"
        elif os.environ.get("DISPLAY"):
            return "X11"
        else:
            return "display server cannot be determined"
    except Exception:
        return "display server cannot be determined"

def format_bytes(size):
    if size is None:
        return "unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

def stylize_version(cell):
    if not details:
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

def run_command_version(cmd, multi):
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
            return "not installed"   
        #flatpak                 
        if not noflatpak:
            version = get_flatpak_version(binary)
            if version:
                return version
        #alias fonction
        if binary in aliases or binary in functions:
            if multi:
                return "_interactive_"
            result = subprocess.run(
            [shell, "-i", "-c", shlex.join(cmd)],
                capture_output=True,
                text=True,
                env=env
            )
            if result.returncode == 0:
                return (result.stdout.strip() or result.stderr.strip())  
            return "not installed"                       
        return "not installed"
    except Exception as e:
        return "not installed"

def process_item(item, multi):
    name = item["name"]
    base_binary = name.split()[0]

    item_categories = item.get("categories", [])

    if filters and not any(f in name for f in (filters if isinstance(filters, list) else [filters])):
        return None
    if categories and not any(
        c in item_categories for c in (categories if isinstance(categories, list) else [categories])
    ):
        return None

    version_cmd = item.get("version_cmd", [base_binary, "--version"])
    version = run_command_version(version_cmd, multi)

    if not details:
        version = "\n".join(version.splitlines()[:10])

    if version != "not installed" and version != "_interactive_":
        path_cmd = item.get("path_cmd")

        if path_cmd is None:
            if shutil.which(base_binary):
                path_cmd = ["which", base_binary]
            else:
                if not noflatpak:
                    try:
                        path_cmd = find_flatpak_command(base_binary)
                    except FileNotFoundError:
                        path_cmd = None       
                if base_binary in aliases or base_binary in functions:
                    check_type = subprocess.run(
                        [shell, "-i", "-c", f"type {shlex.quote(base_binary)}"],
                        capture_output=True,
                        text=True,
                        env=env
                    )
                    if check_type.returncode == 0:
                        path_cmd = ["echo", check_type.stdout.strip()]


        if path_cmd:
            result = subprocess.run(
                path_cmd,
                capture_output=True,
                text=True,
                env=env
            )
            output = result.stdout.strip().splitlines()
            path_output = output[0] if output else ""
        else:
            path_output = ""

    else:
        path_output = "NA"
    return {
        "name": name,
        "version": stylize_version(version),
        "path": path_output
    }

def app():
    #info bloc
    
    if not noinfo:
        if not is_json:
            print(format_message("user (shell)",getpass.getuser() + " ("+os.environ.get("SHELL")+")","👤"))
            print(format_message("os",f"{distro.name()} {distro.version()} ({platform.release()})","💻"))
            print(format_message("display",((os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or os.environ.get("GDMSESSION") or "") + " " + display_server_infos()).strip(),"💻"))
            print(format_message("cpu",f"{cpu_infos()} ({os.cpu_count()} cores {psutil.cpu_freq() .max/1000:.2f} GHz)","🧠"))
            print(format_message("video",gpu_infos(),"🎮"))
            print(format_message("ram",format_bytes(psutil.virtual_memory().total),"⚡"))
            print(format_message("disk",format_bytes(psutil.disk_usage('/').total),"💾"))
            print(format_message("security",secure_boot_infos() + " / " + disk_encryption_infos(),"🔐"))
        else:
            json_obj["info"]["user_shell"]=getpass.getuser() + "("+os.environ.get("SHELL")+")"
            json_obj["info"]["os"]=f"{distro.name()} {distro.version()} ({platform.release()})"
            json_obj["info"]["desktop"]=((os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or os.environ.get("GDMSESSION") or "") + " " + display_server_infos()).strip()
            json_obj["info"]["cpu"]=f"{cpu_infos()} ({os.cpu_count()} cores {psutil.cpu_freq() .max/1000:.2f} GHz)"
            json_obj["info"]["ram"]=format_bytes(psutil.virtual_memory().total)
            json_obj["info"]["video"]=gpu_infos()
            json_obj["info"]["disk"]=format_bytes(psutil.disk_usage('/').total)
            json_obj["info"]["security"]=secure_boot_infos() + " / " + disk_encryption_infos()

    #apps bloc
    if not noprograms:

        results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(process_item, item, workers>1) for item in commands_filtered]
            iterable = tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="⏳ progress 1/2  : ",
                    bar_format="{desc}{n}/{total}"
                ) if use_tqdm else futures
            for future in iterable:
                result = future.result()
                if result:
                    results.append(result)
        interactive_names = {
            res["name"] for res in results
            if str(res.get("version")) == "_interactive_"
        }  
        interactive_items = [
            item for item in commands_filtered
            if item["name"] in interactive_names
        ]        

        interactive_results = []
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [executor.submit(process_item, item, False) for item in interactive_items]
            iterable = tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="⏳ progress 2/2  : ",
                    bar_format="{desc}{n}/{total}"
                ) if use_tqdm else futures        
            for future in iterable:            
                res = future.result()
                if res:
                    interactive_results.append(res)

        for i, res in enumerate(results):
            if str(res.get("version")) == "_interactive_":
                for ir in interactive_results:
                    if ir["name"] == res["name"]:
                        results[i] = ir
                        break
        results = sorted(results, key=lambda x: x["name"].lower())            
        for r in results:
            if str(r.get("version")) != "not installed" or args.full or is_filter:
                if not is_json:
                    table.add_row(r["name"], r["version"], r["path"])
                else:
                    json_obj["programs"].append(r)

        if not is_json:
            if not notime:
                print(f"⏳ exec. time    : {time.time() - start_time:.1f}s")
            console.print(table)
    else:
        if not is_json and not notime:
            print(f"⏳ exec. time    : {time.time() - start_time:.1f}s")        
    #json bloc
    if is_json:
        print(json.dumps(json_obj, indent=4))
