import fire

from .create_static_site import create_static_site


def main() -> None:
    """Call CLI commands."""
    fire.Fire({"create-static-site": create_static_site})
