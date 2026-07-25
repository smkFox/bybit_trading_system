import sys
from pathlib import Path


def main() -> None:
    print(f"Python version: {sys.version}")
    print(f"Interpreter: {sys.executable}")
    print(f"Project directory: {Path.cwd()}")


if __name__ == "__main__":
    main()