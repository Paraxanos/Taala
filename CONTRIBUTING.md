# Contributing

Thanks for looking. Taala is an early beta, so small, well-evidenced changes are the most useful.

## Setup

```bash
git clone https://github.com/Paraxanos/Taala && cd Taala
pip install -e ".[dev]"
python tools/fetch_wordlists.py   # optional, about 3 minutes; tests that need the lists skip without it
python -m pytest
```

## Ground rules

- **No password data in commits, ever.** Do not add RockYou or any other breach corpus,
  anything derived from one, or real passwords (yours or anyone else's). `.gitignore`
  blocks the usual paths; do not work around it.
- **Evaluation numbers need a held-out split.** Rules and word lists are learned from the
  train half only. The test half is scored once; `eval/accuracy.py` refuses a second run.
  If you change the estimator, report the change as post-hoc, not as a new test result.
- **New words and rules need a public source** and must be recorded in
  `locales/hi-latn/pack.toml`. We cannot accept words copied from private lists.
- Add a test with each fix. A bug fix should come with a test that fails without it.
- Keep the code style of the surrounding file. Run `python -m pytest` before opening a PR.

## Licensing

Contributions are accepted under the repository's MIT license (code) and CC BY-SA 4.0
(Wikipedia-derived data). By opening a pull request you confirm you have the right to
submit your work under those terms.
