"""Generate one mkdocstrings page per public module under env_proxy/.

Invoked by mkdocs-gen-files at build time. Output lives in the virtual
docs tree (no files are written to disk); SUMMARY.md drives nav via
mkdocs-literate-nav.
"""

from pathlib import Path

import mkdocs_gen_files

PACKAGE = "env_proxy"
SRC_ROOT = Path(__file__).parent.parent / PACKAGE
API_ROOT = Path("reference") / "api"

nav = mkdocs_gen_files.Nav()

modules: list[str] = []
for module_path in sorted(SRC_ROOT.glob("*.py")):
    name = module_path.stem
    if name.startswith("_") or name == "__init__":
        continue

    identifier = f"{PACKAGE}.{name}"
    doc_path = API_ROOT / f"{name}.md"
    modules.append(name)

    nav[(name,)] = doc_path.relative_to(API_ROOT).as_posix()

    with mkdocs_gen_files.open(doc_path, "w") as fd:
        fd.write(f"# `{identifier}`\n\n")
        fd.write(f"::: {identifier}\n")

    mkdocs_gen_files.set_edit_path(doc_path, module_path.relative_to(SRC_ROOT.parent))

with mkdocs_gen_files.open(API_ROOT / "index.md", "w") as fd:
    fd.write("# API Reference\n\n")
    fd.write(
        "Auto-generated from the package's docstrings via "
        "[mkdocstrings](https://mkdocstrings.github.io/).\n\n"
    )
    fd.write("## Modules\n\n")
    for name in modules:
        fd.write(f"- [`{PACKAGE}.{name}`]({name}.md)\n")

with mkdocs_gen_files.open(API_ROOT / "SUMMARY.md", "w") as fd:
    fd.write("* [Overview](index.md)\n")
    fd.writelines(nav.build_literate_nav())
