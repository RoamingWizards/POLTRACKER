"""PyInstaller entry point for POLTRACKER.app."""

import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from poltracker.desktop.main import main

    sys.exit(main())
