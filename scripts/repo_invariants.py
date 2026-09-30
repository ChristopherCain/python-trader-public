from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []
    if (ROOT / "src" / "datamedicine").exists():
        failures.append("legacy src/datamedicine tree is still present")
    if (ROOT / "web" / "src" / "pythontrader").exists():
        failures.append("web contains a duplicated backend pythontrader tree")
    if (ROOT / "pythontrader.pyproject.toml").exists():
        failures.append(
            "legacy pythontrader.pyproject.toml exists; root pyproject.toml is canonical"
        )
    required = [
        ROOT / "pyproject.toml",
        ROOT / "src" / "pythontrader",
        ROOT / "tests",
        ROOT / ".github" / "workflows" / "ci.yml",
    ]
    for path in required:
        if not path.exists():
            failures.append(f"required path missing: {path.relative_to(ROOT)}")
    if failures:
        print("repository invariant failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("repository invariants: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
