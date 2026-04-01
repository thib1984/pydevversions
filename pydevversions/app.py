"""
pydevversions use case
"""

from columnar import columnar
from tqdm import tqdm
import os
import subprocess
import shutil

shell_path = os.environ.get("SHELL", "/bin/bash")
shell = os.path.basename(shell_path)  # "bash", "zsh", etc.
if shell == "bash":
    rc_files = ["~/.bashrc"]
elif shell == "zsh":
    rc_files = ["~/.zshrc"]
else:
    rc_files = ["~/.profile"]

print("💻 shell: " + shell)    
print("🏠 home: " + os.path.expanduser("~"))
source_cmds = " && ".join(f"[ -f {os.path.expanduser(f)} ] && source {os.path.expanduser(f)}" for f in rc_files)
cmd = f"{source_cmds} && env"

result = subprocess.run([shell, "-c", cmd], capture_output=True, text=True)
env = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)

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

    for item in tqdm(commands, desc="⏳ Progress", bar_format="{l_bar}{bar}"):

        if isinstance(item, str):
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
        if version != "not installed":
            rows.append([name, version, path_output])


    table = columnar(rows, headers=["Binary", "Version", "Path"])
    print(table)