"""Engine for the ecc-arena skill.

The orchestrator (Claude) never judges and never builds. It runs `engine.py next`, launches the
sub-agent jobs it is told to, and repeats. Every module here is pure bookkeeping over the run folder.
"""
import os

VERSION = 1
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_ROOT = ".ecc-arena"
LATEST_FILE = "LATEST"
STATE_FILE = "arena.json"

DEFAULT_AGENTS = 36
QUICK_AGENTS = 12
FULL_AGENTS = 100
DEFAULT_GROUP_SIZE = 10
DEFAULT_TOP_K = 5
DEFAULT_BUILDERS = 3
DEFAULT_MAX_SURGERY = 2
DEFAULT_WAVE = 10

PHASES = ("blueprint", "audit", "verdict", "surgery", "verify", "build", "build_judge", "build_surgery")


class ArenaError(Exception):
    """Anything the orchestrator should read and act on."""
