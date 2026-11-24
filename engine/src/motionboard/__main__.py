"""python -m motionboard: same as the mb command (used by mb worker --detach)."""

from motionboard.cli import app

if __name__ == "__main__":
    app()
