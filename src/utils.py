"""
Utilities for NovaStream.
"""

from art import text2art
from colorama import init as colorama_init, Fore

# initialize colorama
colorama_init(autoreset=True)

def banner():
    """Print the NovaStream ASCII art banner."""
    art = text2art("NovaStream")
    print(Fore.CYAN + art)

def expand_ranges(s):
    """Convert '1,3-5' → [1,3,4,5]."""
    nums = set()
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            nums.update(range(int(a), int(b) + 1))
        else:
            nums.add(int(part))
    return sorted(nums) 