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