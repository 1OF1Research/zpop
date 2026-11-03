#!/usr/bin/env python3
"""zpop entry point. Usage: ./zpop.py <command> ... (see README.md)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from zpop.cli import main
if __name__ == "__main__":
    main()
