from pathlib import Path
import runpy
import sys


def main() -> None:
    root_script = Path(__file__).resolve().parent.parent / "Begin Archival.py"
    if root_script.exists():
        print("[RunRosetta] Forwarding to root launcher: Begin Archival.py")
        runpy.run_path(str(root_script), run_name="__main__")
        return

    # Fallback if the root launcher is unavailable.
    if str(Path(__file__).resolve().parent) not in sys.path:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
    from HooverWithWhip import run_rosetta

    run_rosetta()


if __name__ == "__main__":
    main()
