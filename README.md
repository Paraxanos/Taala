# Taala — Password Strength Checker (Minimal CLI + Web)

A password strength checker for Indian (Hinglish) passwords, recognizing words
regardless of spelling or script. Delivered as:

- **CLI tool** (`python -m taala.cli <password>`) — prints band, canonical forms,
  blocklist hits, structure reason, zxcvbn guesses and overrating multiplier
- **Minimal local web page** (`python -m taala.web`) — shows the band live in a text box

## Quick start

```bash
# CLI
python -m taala.cli football99

# Web (then open http://localhost:8080)
python -m taala.web
```

## Design concepts

- **Canonicalization (N1):** spelling variants, leetspeak and padding are reduced
  to at most 8 canonical forms before any lookup
- **Script independence (N2):** Devanagari and Latin reach the same canonical form,
  including word-final inherent 'a' deletion (राम → ram, not rama)
- **Attack-recipe feedback (N5):** step-by-step guess counts plus calculated fix:
  `ceil(log(10^G) / log(7776))` words to add to reach Strong
- Metrics: merge rate, overrating rate, strictness, rank agreement

## Cite as

> *Taala is, as far as we know, the first password strength checker that
> recognizes Hinglish passwords regardless of spelling or script.* — arXiv preprint,
> cs.CR primary, cs.CL cross-list, CC BY 4.0.

## License

The code is Apache-2.0. Word lists derived from Wikipedia are CC BY-SA 4.0
(kept separate, not committed).

## Status

Beta. Not independently security-reviewed. Use at your own risk.