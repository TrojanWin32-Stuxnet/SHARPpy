
from datetime import datetime
from multiprocessing import freeze_support
from pathlib import Path
import sys
import traceback


def main():
    freeze_support()
    try:
        import full_gui as gui

        gui.main()
    except Exception:
        report = "\n=== Unhandled SHARPpy exception ===\n"
        report += "Crash time: %s\n" % datetime.now().isoformat()
        report += traceback.format_exc()
        crash_log = Path.home() / ".sharppy" / "sharppy-crash.log"
        try:
            crash_log.parent.mkdir(parents=True, exist_ok=True)
            with crash_log.open("a", encoding="utf-8") as stream:
                stream.write(report)
        except OSError:
            # Reporting must not replace the original startup exception.
            pass
        if sys.__stderr__ is not None:
            try:
                sys.__stderr__.write(report)
                sys.__stderr__.flush()
            except (OSError, ValueError):
                pass
        raise


if __name__ == "__main__":
    main()

