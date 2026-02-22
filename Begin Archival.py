from pathlib import Path
import sys


def main() -> None:
    project_root = Path(__file__).resolve().parent
    rosetta_dir = project_root / "rosetta"

    if str(rosetta_dir) not in sys.path:
        sys.path.insert(0, str(rosetta_dir))

    from terminal_reporter import PipelineTerminalReporter
    from HooverWithWhip import run_rosetta
    from forge.build_web_datasets import run_web_dataset_builder, DEFAULT_LOCALES

    reporter = PipelineTerminalReporter(title="Grand Stellaris Archival")
    reporter.set_phase("Begin | Startup")
    reporter.note("Starting Grand Stellaris archival pipeline")
    try:
        run_rosetta(reporter=reporter)
        run_web_dataset_builder(
            output_root=project_root / "output",
            assets_root=project_root / "assets",
            locales=list(DEFAULT_LOCALES),
            reporter=reporter,
        )
        reporter.finish(success=True, message="Archival pipeline complete")
    except Exception as exc:
        reporter.finish(success=False, message=f"Pipeline failed: {exc}")
        raise


if __name__ == "__main__":
    main()
