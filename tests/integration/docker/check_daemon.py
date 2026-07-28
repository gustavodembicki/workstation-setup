from __future__ import annotations

import argparse
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the active Docker daemon OS")
    parser.add_argument("--expect", choices=("linux", "windows"), required=True)
    args = parser.parse_args()

    result = subprocess.run(
        ["docker", "info", "--format", "{{.OSType}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        print(f"Could not query the Docker daemon: {detail}")
        return 1

    actual = result.stdout.strip().lower()
    if actual != args.expect:
        print(
            f"Docker is using the {actual!r} daemon, but this target requires "
            f"{args.expect!r} containers."
        )
        if args.expect == "windows":
            print("Switch Docker Desktop to Windows containers and retry.")
        else:
            print("Switch Docker Desktop/Engine to Linux containers and retry.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
