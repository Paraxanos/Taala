"""CLI entry point for Taala."""
import sys
from .feedback import format_recipe_for_cli

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m taala.cli <password>")
        sys.exit(1)
    if sys.argv[1] in ("--help", "-h"):
        print("Taala — Password Strength Checker")
        sys.exit(0)
        
    password = sys.argv[1]

    # Windows consoles default to cp1252 and crash on Devanagari; never fail on output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    from . import pack
    if not pack.has_word_lists():
        print("Note: Hinglish word lists not found, so only spelling rules and stock zxcvbn "
              "apply. Run: python tools/fetch_wordlists.py", file=sys.stderr)
    if not pack.has_rank_file():
        print("Note: pack ranking file not found, so scores are less strict than the published "
              "results (see README, 'Reproducing the results').", file=sys.stderr)
    
    from .canon import analyze
    from .estimate import estimate
    
    analysis = analyze(password)
    est = estimate(password)
    
    print(f"Password: {password}")
    print(f"Band: {est['band']}")
    print(f"Guesses (log10): {est['guesses_log10']}")
    print(f"Words to add for Strong: {est['words_to_add']}")
    print(f"Canonical forms ({len(analysis['forms'])}):")
    for i, f in enumerate(analysis["forms"], 1):
        print(f"  {i}. {f}")
    print(f"Blocklist hit: {analysis['blocklist_hit']}")
    print(f"Reasons: {', '.join(est['reasons']) if est['reasons'] else 'none'}")
    
    print("\nAttack Recipe (How an attacker would guess this):")
    print(format_recipe_for_cli(est['recipe']))

if __name__ == "__main__":
    main()