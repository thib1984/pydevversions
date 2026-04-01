"""
pydevversions init
"""


from pydevversions.args import compute_args
from pydevversions.app import app
import colorama


def pydevversions():
    """
    pydevversions entry point
    """
    compute_args()
    colorama.init()

    try:
        app()
    except KeyboardInterrupt:
        exit(1)