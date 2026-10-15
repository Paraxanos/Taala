"""
Taala — password strength checker for Indian (Hinglish) passwords.

Recognizes words regardless of spelling or script.

Usage:
    python -m taala.cli <password>
    python -m taala.cli --help

Public API:
    from taala.canon import analyze
    from taala.estimate import estimate
"""

from .canon import analyze
from .estimate import estimate