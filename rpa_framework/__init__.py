__version__ = "1.0.0"

__all__ = ["run", "__version__"]


def run(path, **kwargs):
    from .scripting import run_path
    return run_path(path, **kwargs)
