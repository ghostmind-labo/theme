"""Command dispatch."""

from __future__ import annotations

import json
import re
import sys

from . import __version__
from .audit import audit, remediate_theme, revert_theme
from .catalog import (
    CUSTOM_STORE,
    GHOSTTY_USER_THEMES,
    HELIX_USER_THEMES,
    load_custom,
    load_favorites,
    resolve,
    save_custom,
    save_favorites,
    save_overrides,
)
from .color import CONTRAST_TARGET, TEXT_SLOTS, swatch
from .generate import write_theme
from .palette import SPEC_KEYS, derive, validate
from .targets import apply, current

USAGE = """theme - recolour Ghostty, herdr and Helix in one command

  theme                     browse themes in a full-screen picker
  theme <name>              apply a theme
  theme list                plain list
  theme current             show what is applied
  theme fav [name]          pin/unpin a theme, or list what is pinned

  theme new <name>          create a theme (wizard, or --from / stdin)
      --from '#rrggbb'      derive a whole palette from one colour
      --mode dark|light     which ramp to derive (default: dark)
      --about '...'         one-line description
  theme edit <name>         print a custom theme's spec as JSON
  theme rm <name>           delete a custom theme
  theme generate            rebuild every custom theme

  theme contrast [name]     WCAG audit
  theme fix <name|--light|--all>
                            correct a theme that falls below the floor
  theme revert <name|--all> undo that correction

  theme doctor              check every theme resolves
  theme version
"""


def _apply_and_report(key: str, themes: dict) -> None:
    result = apply(key, themes)
    report = audit(key, themes)
    print(f"theme -> {key}  ({result['mode']})")
    print(f"  ghostty  {result['ghostty']}")
    print(f"  helix    {result['helix']}")
    print(f"  herdr    {result['herdr']}"
          + ("   (inherits ghostty)" if result["herdr"] == "terminal" else ""))
    if report:
        print(f"  contrast text {report.fg_ratio:.1f}:1, weakest colour {report.worst:.1f}:1")
    if result.get("herdr_chrome"):
        from .herdr_theme import check
        from .targets import palette_of
        pal, bg, fg = palette_of(result["ghostty"])
        worst = min(v for _t, v in check(pal, bg, fg))
        print(f"  sidebar  herdr chrome regenerated, weakest label {worst:.1f}:1")
    if result.get("claude_synced"):
        print(f"  claude   own theme switched to {result['mode']} to match")
    print()
    print("  herdr    " + ("reloaded" if result["herdr_reloaded"]
                           else "not running - picks it up on next start"))
    print("  helix    applies on next launch (or :config-reload)")
    print("  ghostty  press cmd+shift+, to reload  <- required, no CLI reload exists")


def _store(name: str, spec: dict, themes: dict) -> int:
    custom = load_custom()
    custom[name] = spec
    save_custom(custom)
    write_theme(name, spec)
    themes[name] = (name, name, "terminal", spec["mode"])
    report = audit(name, themes)
    print(f"\ncreated {name} ({spec['mode']}) - {spec['about']}")
    print(f"  spec     {CUSTOM_STORE}")
    print(f"  ghostty  {GHOSTTY_USER_THEMES}/{name}")
    print(f"  helix    {HELIX_USER_THEMES}/{name}.toml")
    if report:
        print(f"  contrast text {report.fg_ratio:.1f}:1, weakest colour {report.worst:.1f}:1")
    print(f"\napply it with:  theme {name}")
    return 0


def _ask(prompt: str, default: str = "", check=None) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        try:
            value = input(f"  {prompt}{suffix}: ").strip() or default
        except (EOFError, KeyboardInterrupt):
            print("\n  cancelled")
            raise SystemExit(1)
        if not value:
            continue
        if check and not check(value):
            print("  ! not valid, try again")
            continue
        return value


def cmd_new(name: str, argv: list[str], themes: dict) -> int:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name or ""):
        print("name must be lowercase letters, digits and dashes", file=sys.stderr)
        return 1
    custom = load_custom()
    if name in themes and name not in custom:
        print(f"'{name}' is already a catalog theme - pick another name", file=sys.stderr)
        return 1

    seed = mode = about = None
    args = list(argv)
    while args:
        flag = args.pop(0)
        if flag in ("--from", "--seed") and args:
            seed = args.pop(0)
        elif flag == "--mode" and args:
            mode = args.pop(0)
        elif flag == "--about" and args:
            about = args.pop(0)
        else:
            print(f"unknown option: {flag}", file=sys.stderr)
            return 1

    if seed:
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", seed):
            print("--from must be a #rrggbb colour", file=sys.stderr)
            return 1
        return _store(name, derive(seed.lower(), mode or "dark", about or ""), themes)

    if not sys.stdin.isatty():
        try:
            spec = json.load(sys.stdin)
        except ValueError as error:
            print(f"invalid JSON on stdin: {error}", file=sys.stderr)
            return 1
        problems = validate(spec)
        if problems:
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            print(f"\nrequired keys: {', '.join(SPEC_KEYS)}", file=sys.stderr)
            return 1
        return _store(name, {k: spec[k] for k in SPEC_KEYS}, themes)

    print(f"\ncreating '{name}'\n")
    mode = _ask("mode (dark/light)", "dark", lambda v: v in ("dark", "light"))
    seed = _ask("seed colour #rrggbb", "#7fb4ca",
                lambda v: re.fullmatch(r"#[0-9a-fA-F]{6}", v) is not None)
    about = _ask("one-line description", f"custom {mode} theme")
    spec = derive(seed.lower(), mode, about)
    print()
    for key in SPEC_KEYS:
        if key in ("mode", "about"):
            continue
        print(f"  {key:<5} {swatch(spec[key])} {spec[key]}")
    print()
    if _ask("write it? (y/n)", "y").lower() not in ("y", "yes"):
        print("  discarded")
        return 1
    return _store(name, spec, themes)


def cmd_contrast(name: str | None, themes: dict) -> int:
    if name and name not in themes:
        print(f"unknown theme: {name}", file=sys.stderr)
        return 1
    keys = [name] if name else list(themes)
    print(f"target: WCAG {CONTRAST_TARGET}:1 across text slots {list(TEXT_SLOTS)}\n")
    print(f"{'theme':<22} {'mode':<6} {'text':>6} {'weakest':>8}  result")
    print("-" * 62)
    failing = 0
    for key in keys:
        report = audit(key, themes)
        if not report:
            print(f"{key:<22} (no palette file)")
            continue
        if not report.clean:
            failing += 1
        verdict = "ok" if report.clean else f"{len(report.failing)}/{report.slots} below floor"
        print(f"{key:<22} {report.mode:<6} {report.fg_ratio:6.2f} {report.worst:8.2f}  {verdict}")
    print(f"\n{len(keys) - failing}/{len(keys)} legible")
    if failing:
        print("`theme fix --all` corrects them, preserving hue")
    return 0


def cmd_fix(target: str, themes: dict, overrides: dict) -> int:
    custom = load_custom()
    if target == "--light":
        keys = [k for k, v in themes.items() if v[3] == "light"]
    elif target == "--all":
        keys = list(themes)
    elif target in themes:
        keys = [target]
    else:
        print(f"unknown theme: {target}", file=sys.stderr)
        return 1
    fixed = 0
    for key in keys:
        if key in custom:
            continue  # generated themes are already corrected at write time
        corrected = remediate_theme(key, themes, overrides)
        if corrected:
            print(f"  {key:<22} {corrected} colour(s) corrected")
            fixed += 1
    save_overrides(overrides)
    print(f"\n{fixed} theme(s) corrected. Re-apply the active one to pick it up.")
    return 0


def cmd_revert(target: str, overrides: dict) -> int:
    keys = list(overrides) if target == "--all" else [target]
    for key in keys:
        if revert_theme(key, overrides):
            print(f"  reverted {key}")
    save_overrides(overrides)
    return 0


def cmd_fav(name: str | None, themes: dict) -> int:
    # `stored` is what gets written back, unfiltered. A pin naming a theme that
    # does not currently resolve is hidden from the listing but kept on disk -
    # filtering before saving would let one toggle silently destroy the rest.
    stored = load_favorites()
    if not name:
        visible = [k for k in stored if k in themes]
        if not visible:
            print("nothing pinned yet - `theme fav <name>` pins one")
            return 0
        active = current(themes)
        for key in visible:
            print(f"  {'*' if key == active else ' '} {key}")
        return 0
    if name not in themes:
        print(f"unknown theme: {name}", file=sys.stderr)
        return 1
    if name in stored:
        stored.remove(name)
        print(f"unpinned {name}")
    else:
        stored.append(name)
        print(f"pinned {name}")
    save_favorites(stored)
    return 0


def cmd_list(themes: dict) -> int:
    custom = load_custom()
    active = current(themes)
    favorites = [k for k in load_favorites() if k in themes]
    rest = [k for k in themes if k not in favorites]
    sections = (
        ("favorites", favorites),
        ("preset", [k for k in rest if k not in custom]),
        ("custom", [k for k in rest if k in custom]),
    )
    for label, keys in sections:
        if not keys:
            continue
        print(f"\n{label}")
        for mode in ("dark", "light"):
            group = [k for k in keys if themes[k][3] == mode]
            if not group:
                continue
            print(f"  {mode}")
            for key in group:
                marker = "*" if key == active else " "
                print(f"    {marker} {key}")
    print(f"\ncurrent: {active}")
    return 0


def cmd_doctor(themes: dict) -> int:
    import os
    import re as _re
    import subprocess

    from .catalog import GHOSTTY_BIN

    ghostty = set()
    try:
        listing = subprocess.run([GHOSTTY_BIN, "+list-themes"], capture_output=True, text=True).stdout
        ghostty = {_re.sub(r"\s*\(.*\)$", "", line).strip() for line in listing.splitlines() if line.strip()}
    except OSError:
        pass
    if os.path.isdir(GHOSTTY_USER_THEMES):
        ghostty |= set(os.listdir(GHOSTTY_USER_THEMES))

    helix = set()
    for root, _dirs, files in os.walk("/opt/homebrew/Cellar/helix"):
        if root.endswith("/runtime/themes"):
            helix |= {f[:-5] for f in files if f.endswith(".toml")}
    if os.path.isdir(HELIX_USER_THEMES):
        helix |= {f[:-5] for f in os.listdir(HELIX_USER_THEMES) if f.endswith(".toml")}

    bad = 0
    for key, (g, h, _herdr, _mode) in themes.items():
        problems = []
        if ghostty and g not in ghostty:
            problems.append(f"ghostty missing '{g}'")
        if helix and h not in helix:
            problems.append(f"helix missing '{h}'")
        if problems:
            bad += 1
            print(f"  FAIL {key}: {'; '.join(problems)}")
    print(f"{len(themes)} themes checked, {bad} problem(s)")
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    themes, custom, overrides = resolve()

    if not argv:
        from .tui import browse

        try:
            chosen = browse(themes, custom, overrides, load_favorites())
        except RuntimeError as error:
            print(error, file=sys.stderr)
            return cmd_list(themes)
        if chosen == "\0new":
            name = input("new theme name: ").strip()
            return cmd_new(name, [], themes) if name else 0
        if chosen:
            print(f"applied {chosen} - press cmd+shift+, in Ghostty to reload")
        return 0

    command, rest = argv[0], argv[1:]

    if command in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    if command in ("version", "--version"):
        print(__version__)
        return 0
    if command == "list":
        return cmd_list(themes)
    if command == "current":
        print(current(themes))
        return 0
    if command == "fav":
        return cmd_fav(rest[0] if rest else None, themes)
    if command == "generate":
        for key, spec in sorted(custom.items()):
            write_theme(key, spec)
            print(f"  {key:<12} {spec.get('about', '')}")
        print(f"\n{len(custom)} themes written")
        return 0
    if command == "contrast":
        return cmd_contrast(rest[0] if rest else None, themes)
    if command == "fix" and rest:
        return cmd_fix(rest[0], themes, overrides)
    if command == "revert" and rest:
        return cmd_revert(rest[0], overrides)
    if command == "new" and rest:
        return cmd_new(rest[0], rest[1:], themes)
    if command == "edit" and rest:
        if rest[0] not in custom:
            print(f"{rest[0]} is not a custom theme", file=sys.stderr)
            return 1
        print(json.dumps(custom[rest[0]], indent=2))
        return 0
    if command == "rm" and rest:
        import os

        name = rest[0]
        if name not in custom:
            print(f"{name} is not a custom theme", file=sys.stderr)
            return 1
        del custom[name]
        save_custom(custom)
        favorites = load_favorites()
        if name in favorites:
            favorites.remove(name)
            save_favorites(favorites)
        for path in (f"{GHOSTTY_USER_THEMES}/{name}", f"{HELIX_USER_THEMES}/{name}.toml"):
            if os.path.exists(path):
                os.remove(path)
        print(f"removed {name}")
        return 0
    if command == "doctor":
        return cmd_doctor(themes)
    if command in themes:
        _apply_and_report(command, themes)
        return 0

    print(f"unknown command or theme: {command}\n", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return 1
