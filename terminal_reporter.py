from __future__ import annotations

import shutil
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class _NoteItem:
    level: str
    text: str


class PipelineTerminalReporter:
    def __init__(self, title: str = "Archival Pipeline", notes_limit: int = 8, bar_width: int = 36) -> None:
        self.title = title
        self.notes_limit = max(3, notes_limit)
        self.bar_width = max(12, bar_width)

        self.phase = "Idle"
        self.current_file = "-"
        self.total = 0
        self.current = 0
        self.start_time = time.time()

        self._notes: deque[_NoteItem] = deque(maxlen=self.notes_limit)
        self._last_render_lines = 0
        self._isatty = bool(getattr(sys.stdout, "isatty", lambda: False)())
        self._last_plain_percent = -1

    def set_phase(self, phase: str, total: Optional[int] = None) -> None:
        self.phase = phase
        self.current_file = "-"
        self.current = 0
        if total is not None:
            self.total = max(0, int(total))
        self.render()

    def set_total(self, total: int) -> None:
        self.total = max(0, int(total))
        self.current = min(self.current, self.total) if self.total > 0 else self.current
        self.render()

    def set_current_file(self, file_label: str) -> None:
        self.current_file = file_label or "-"
        self.render()

    def advance(self, step: int = 1) -> None:
        self.current += max(0, int(step))
        if self.total > 0:
            self.current = min(self.current, self.total)
        self.render()

    def note(self, message: str) -> None:
        self._push_note("NOTE", message)

    def warn(self, message: str) -> None:
        self._push_note("WARN", message)

    def error(self, message: str) -> None:
        self._push_note("ERROR", message)

    def finish(self, success: bool = True, message: Optional[str] = None) -> None:
        if self.total > 0:
            self.current = self.total
        if message:
            if success:
                self.note(message)
            else:
                self.error(message)
        self.render(final=True)
        if self._isatty:
            sys.stdout.write("\n")
            sys.stdout.flush()

    def _push_note(self, level: str, message: str) -> None:
        clean = " ".join(str(message).split())
        self._notes.append(_NoteItem(level=level, text=clean))
        self.render()

    def _format_elapsed(self) -> str:
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = divmod(elapsed, 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def _format_progress(self) -> tuple[str, int]:
        if self.total > 0:
            ratio = max(0.0, min(1.0, self.current / self.total))
            pct = int(round(ratio * 100))
            filled = int(round(self.bar_width * ratio))
            bar = "#" * filled + "-" * (self.bar_width - filled)
            return f"[{bar}] {pct:3d}% ({self.current}/{self.total})", pct
        return f"[{'-' * self.bar_width}] --% ({self.current}/?)", -1

    def _truncate(self, text: str, width: int) -> str:
        if width <= 4 or len(text) <= width:
            return text
        return text[: max(1, width - 3)] + "..."

    def render(self, final: bool = False) -> None:
        progress_text, pct = self._format_progress()
        elapsed = self._format_elapsed()
        term_width = shutil.get_terminal_size((120, 40)).columns

        header = self._truncate(f"{self.title} | {self.phase} | elapsed {elapsed}", term_width)
        file_line = self._truncate(f"File: {self.current_file}", term_width)

        note_lines = []
        for note in self._notes:
            note_lines.append(self._truncate(f"[{note.level}] {note.text}", term_width))

        lines = note_lines + [header, file_line, progress_text]

        if not self._isatty:
            # Non-interactive fallback: reduce spam by printing only on percent changes or final.
            should_emit = final
            if pct != -1 and pct != self._last_plain_percent:
                should_emit = True
                self._last_plain_percent = pct
            if should_emit:
                for line in lines[-3:]:
                    print(line)
            return

        if self._last_render_lines > 0:
            sys.stdout.write("\r")
            for i in range(self._last_render_lines):
                sys.stdout.write("\x1b[2K")
                if i < self._last_render_lines - 1:
                    sys.stdout.write("\x1b[1A\r")

        for i, line in enumerate(lines):
            if i > 0:
                sys.stdout.write("\n")
            sys.stdout.write(line)

        sys.stdout.flush()
        self._last_render_lines = len(lines)
