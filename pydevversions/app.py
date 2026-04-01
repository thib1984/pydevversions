"""
pydevversions use case
"""

from columnar import columnar
import subprocess

commands = [
    ["cf8", "version"],
    ["bash", "--version"],
    ["zsh", "--version"],
    ["docker", "--version"],
    ["fly", "--version"],
    ["java", "--version"],
    ["mvn", "--version"]
]

def app():
    rows = []
    for cmd in commands:
        
        
        binary=cmd[0]
        resultversion = subprocess.run(cmd, capture_output=True, text=True)
        if resultversion.returncode == 0:
            version=resultversion.stdout.splitlines()[0]
        else:
            version="NA"
        resultpath = subprocess.run(["whereis", cmd[0]], capture_output=True, text=True)
        if resultpath.returncode == 0:
            path=resultpath.stdout.splitlines()[0]
        else:
            path="NA"
        rows.append([binary, version, path])

    table = columnar(rows, headers=["Binary", "Version", "Path"])
    print(table)        