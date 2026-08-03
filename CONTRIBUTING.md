
# Contributing to Transcriptase

Thank you for your interest in contributing to **Transcriptase**. We welcome bug reports, feature ideas, documentation improvements, code fixes, tests, and larger design discussions.

This guide explains how to contribute clearly and safely so maintainers can review your work quickly.

---

## Ways You Can Contribute

You can help the project by:

- Reporting bugs
- Suggesting new features
- Improving documentation
- Fixing issues
- Adding tests
- Refactoring code
- Reviewing pull requests
- Helping triage issues
- Improving accessibility, performance, or developer experience
- Becoming a maintainer or long-term contributor

All contributions are appreciated, whether they are small typo fixes or major improvements.

---

## Code of Conduct

Please be respectful and constructive when participating in the project.

By contributing, you agree to help keep this community welcoming, inclusive, and professional. Disagreements are fine, but harassment, personal attacks, trolling, or abusive behaviour are not acceptable.

---

## Development Workflow

We use **GitHub** to host the code, track issues, review changes, and manage releases.

This project follows **GitHub Flow**, meaning all code changes should happen through pull requests.

The usual workflow is:

1. Fork the repository.
2. Create a new branch from `master` or `main`.
3. Make your changes.
4. Add or update tests where appropriate.
5. Update documentation if behaviour, usage, or APIs changed.
6. Run linting and tests.
7. Open a pull request.
8. Respond to review feedback.

---

## Getting Started

### 1. Fork the Repository

Click **Fork** on GitHub, then clone your fork locally:

```bash
git clone https://github.com/YOUR_USERNAME/transcriptase.git
cd transcriptase
````

### 2. Add the Upstream Repository

```bash
git remote add upstream https://github.com/OWNER/transcriptase.git
```

Replace `OWNER` with the correct GitHub organisation or username.

### 3. Create a Branch

Use a descriptive branch name:

```bash
git checkout -b fix/audio-export-bug
```

Good branch name examples:

```bash
fix/missing-transcript-lines
feature/export-json
docs/update-install-guide
test/add-parser-coverage
refactor/cleanup-cli-options
```

---

## Installing Dependencies

This is a Python 3.10+ project. Install the runtime dependencies before making changes:

```bash
pip install -r requirements.txt
```

Only `pyautogui` and `keyboard` are required; everything else is optional and the app
degrades gracefully without it. To check what you are missing:

```bash
python AutoClicker.py doctor
```

---

## Running the Project Locally

Launch the full Control Center:

```bash
python AutoClicker.py
```

Or the lite launcher:

```bash
python lite-version.py
```

The headless commands need no display, which makes them the fastest way to sanity-check a
change:

```bash
python AutoClicker.py --help
```

---

## Running Tests

Before submitting a pull request, run the test suite from the repository root:

```bash
python -m unittest discover -s tests -t . -v
```

`pytest` also works. The tests need no third-party package, so they run anywhere.

New logic belongs in a module-level `_helper()` function wherever possible: the GUI class
lives inside `MAINWINDOW_REDESIGNED()` and is not importable, so only module-level code can
be unit-tested.

If you add new functionality, please add tests when possible.

Useful test contributions include:

* Unit tests for isolated functions
* Integration tests for workflows
* Regression tests for fixed bugs
* Edge-case tests for unusual input
* Parser, exporter, or transcript-format tests

---

## Linting and Formatting

Please keep the code style consistent.

This project prefers:

* 2 spaces for indentation
* Clear variable and function names
* Small, focused functions
* Minimal unnecessary dependencies
* Readable comments where logic is complex

Run linting with:

```bash
python -m compileall -q AutoClicker.py lite-version.py packaging/ tests/
```

If formatting is available, run:

```bash
python -m ruff check .
```

---

## Commit Message Style

Use clear commit messages that explain what changed.

Good examples:

```bash
fix: handle empty transcript files
docs: improve setup instructions
test: add coverage for timestamp parser
feature: add JSON export option
refactor: simplify transcript normalisation
```

Avoid vague messages like:

```bash
update stuff
fix things
changes
```

---

## Reporting Bugs

We use GitHub Issues to track bugs.

When reporting a bug, please include as much detail as possible.

A good bug report includes:

* A clear summary
* Steps to reproduce the issue
* What you expected to happen
* What actually happened
* Screenshots or logs if useful
* Your operating system and browser/runtime version
* The version or commit of Transcriptase you are using
* Example input files or sample code if possible

### Bug Report Template

```markdown
## Summary

Briefly describe the bug.

## Steps to Reproduce

1. Go to...
2. Run...
3. Open...
4. See error...

## Expected Behaviour

What should have happened?

## Actual Behaviour

What happened instead?

## Environment

- OS:
- Browser:
- Python version:
- Transcriptase version/commit:

## Extra Context

Add logs, screenshots, sample files, or anything else helpful.
```

---

## Suggesting Features

Feature requests are welcome.

Before opening a request, please check whether a similar issue already exists.

A good feature request includes:

* The problem you are trying to solve
* Why the feature would be useful
* Example usage
* Possible alternatives
* Any implementation ideas
* Whether you are willing to help build it

### Feature Request Template

```markdown
## Problem

What problem does this feature solve?

## Proposed Solution

Describe the feature you would like.

## Example Usage

Show how someone might use it.

## Alternatives Considered

Are there other ways to solve this?

## Additional Context

Add screenshots, mockups, links, or notes.
```

---

## Pull Request Guidelines

Pull requests are the best way to propose code changes.

Before opening a PR, please make sure:

* Your branch is up to date with `master` or `main`
* Your changes are focused on one clear purpose
* Tests pass locally
* Linting passes locally
* Documentation is updated if needed
* New functionality has tests where possible
* The PR description explains what changed and why

### Pull Request Checklist

```markdown
## What Changed?

Describe the changes in this pull request.

## Why?

Explain why this change is needed.

## Testing

Describe how you tested the change.

- [ ] I ran the test suite
- [ ] I ran linting
- [ ] I added or updated tests
- [ ] I updated documentation where needed

## Screenshots / Logs

Add screenshots, terminal output, or examples if relevant.

## Related Issues

Closes #
```

---

## Code Review Process

Maintainers may ask for changes before merging a pull request.

Please do not take review comments personally. Code review helps improve quality, consistency, and long-term maintainability.

A good review process should be:

* Respectful
* Specific
* Constructive
* Focused on the code, not the person
* Open to discussion

Maintainers may close pull requests that are inactive, out of scope, unsafe, or too difficult to review in their current form.

---

## Documentation Contributions

Documentation improvements are very welcome.

You can help by improving:

* Installation instructions
* Usage examples
* API documentation
* Troubleshooting guides
* README sections
* Code comments
* Tutorials
* Screenshots or diagrams

When changing behaviour, please update the relevant documentation in the same pull request.

---

## Testing Guidelines

When adding tests, try to cover both normal and edge cases.

Examples of useful edge cases:

* Empty input
* Very large transcript files
* Missing timestamps
* Invalid formatting
* Special characters
* Multiple speakers
* Interrupted or partial transcript lines
* Export/import round trips
* Browser compatibility issues

Tests should be clear, deterministic, and easy to understand.

---

## Security Issues

Please do **not** open a public GitHub issue for security vulnerabilities.

Instead, contact the maintainers privately if a security issue is discovered.

Include:

* A description of the vulnerability
* Steps to reproduce it
* Potential impact
* Any suggested fix

Please give maintainers reasonable time to investigate before publicly disclosing the issue.

---

## Dependency Policy

Before adding a new dependency, consider whether it is truly needed.

Good dependencies should be:

* Actively maintained
* Secure
* Lightweight where possible
* Compatible with the project licence
* Worth the extra install size and maintenance cost

If you add a dependency, explain why in the pull request.

---

## Accessibility and Usability

Contributions that improve accessibility are encouraged.

Please consider:

* Keyboard navigation
* Screen reader support
* Colour contrast
* Clear labels
* Responsive layouts
* Reduced-motion preferences
* Helpful error messages

---

## Performance

When making performance-related changes, include before-and-after notes where possible.

Useful performance improvements may include:

* Faster parsing
* Reduced memory usage
* Better handling of large transcripts
* Smaller bundle size
* Less blocking work on the main thread
* Improved export speed
* More efficient file processing

---

## Backwards Compatibility

Avoid breaking existing users unless the change is clearly justified.

If a breaking change is necessary, please:

* Explain why
* Document the migration path
* Update examples
* Mention the change clearly in the pull request

---

## Licensing

By contributing to Transcriptase, you agree that your contributions will be licensed under the same licence as the project.

This project is licensed under the **MIT License** unless otherwise stated.

---

## Maintainer Notes

Maintainers are responsible for:

* Reviewing pull requests
* Managing issues
* Keeping discussions respectful
* Clarifying project direction
* Releasing new versions
* Protecting project quality and security

Maintainers may reject contributions that are out of scope, unsafe, unmaintainable, or inconsistent with the project goals.

---

## Recognition

All contributors help make Transcriptase better.

Contributions may be recognised through:

* GitHub commit history
* Release notes
* Contributor lists
* Documentation credits
* Maintainer invitations for long-term contributors

---

## Helpful Links

* GitHub Flow: [https://guides.github.com/introduction/flow/](https://guides.github.com/introduction/flow/)
* MIT License: [https://choosealicense.com/licenses/mit/](https://choosealicense.com/licenses/mit/)
* How to Write a Good Bug Report: [https://stackoverflow.com/help/minimal-reproducible-example](https://stackoverflow.com/help/minimal-reproducible-example)
* Conventional Commits: [https://www.conventionalcommits.org/](https://www.conventionalcommits.org/)

---

## Thank You

Thank you for helping improve Transcriptase.

Your reports, ideas, fixes, tests, and documentation improvements make the project stronger for everyone.

```
```
