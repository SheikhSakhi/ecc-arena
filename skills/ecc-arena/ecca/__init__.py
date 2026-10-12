"""Engine for the ecc-arena skill.

The orchestrator (Claude) never competes, judges, merges or delivers. It runs `engine.py next`,
launches the sub-agent jobs it is told to, and repeats. Every module here is pure bookkeeping over
the run folder.
"""
import os

VERSION = 2
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_ROOT = ".ecc-arena"
LATEST_FILE = "LATEST"
STATE_FILE = "arena.json"

DEFAULT_AGENTS = 10
QUICK_AGENTS = 10
FULL_AGENTS = 100
DEFAULT_GROUP_SIZE = 10
DEFAULT_TOP_K = 5
DEFAULT_MAX_SURGERY = 2
DEFAULT_WAVE = 10

PHASES = ("compete", "audit", "verdict", "surgery", "verify", "deliver")

PACKAGE_REQUIRED = ("MATRIX.md", "PRD.md", "ARCHITECTURE.md", "POLICIES.md", "TASKS.md")
PACKAGE_FILES = PACKAGE_REQUIRED + ("TESTS.md", "OPS.md", "CLAUDE.md", "README.md")


class ArenaError(Exception):
    """Anything the orchestrator should read and act on."""
