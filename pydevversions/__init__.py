"""
pydevversions init
"""


from pydevversions.args import compute_args
from pydevversions.app import app


def pydevversions():
    """
    pydevversions entry point
    """
    compute_args()

    try:
        app()
    except KeyboardInterrupt:
        exit(1)