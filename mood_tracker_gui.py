import contextlib
import csv
import fcntl
import json
import os
import tempfile
import tkinter as tk
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from tkinter import messagebox, simpledialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "mood_entries.json")
EXPORT_FILE = os.path.join(BASE_DIR, "mood_entries_export.csv")
_LOCK_FILE = os.path.join(BASE_DIR, ".mood_entries.lock")
MAX_NOTE_LENGTH = 2000


class DataLoadWarning(Exception):
    """Some entries could not be loaded due to invalid data."""
    def __init__(self, message, entries):
        super().__init__(message)
        self.entries = entries


@contextlib.contextmanager
def _data_lock(exclusive=False):
    flag = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
    with open(_LOCK_FILE, "w") as fd:
        fcntl.flock(fd, flag)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)


def _load_entries_safe(filename=DATA_FILE):
    """Load entries without raising; returns partial results on data warnings."""
    try:
        return load_entries(filename)
    except DataLoadWarning as e:
        return e.entries
    except RuntimeError:
        return []


@dataclass
class MoodEntry:
    mood: int
    note: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if not isinstance(self.mood, int) or not 1 <= self.mood <= 5:
            raise ValueError("Mood must be an integer between 1 and 5.")
        if not isinstance(self.note, str):
            raise TypeError("Note must be a string.")
        if not isinstance(self.timestamp, str):
            raise TypeError("Timestamp must be a string.")
        try:
            datetime.fromisoformat(self.timestamp)
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {self.timestamp!r}")


def parse_timestamp(timestamp):
    return datetime.fromisoformat(timestamp)


def format_timestamp(timestamp):
    try:
        return parse_timestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return timestamp


def load_entries(filename=DATA_FILE):
    if not os.path.exists(filename):
        return []

    try:
        with _data_lock(exclusive=False):
            with open(filename, "r", encoding="utf-8") as file:
                data = json.load(file)
    except json.JSONDecodeError:
        raise RuntimeError(
            "The data file is corrupted and could not be read. "
            "Restore a backup or delete the file to start fresh."
        )
    except OSError as e:
        raise RuntimeError(f"Could not read data file: {e}")

    if not isinstance(data, list):
        raise RuntimeError("The data file contains unexpected data. Expected a list of entries.")

    entries = []
    skipped = 0
    for entry in data:
        try:
            entries.append(MoodEntry(**entry))
        except (ValueError, TypeError):
            skipped += 1

    if skipped:
        raise DataLoadWarning(
            f"{skipped} corrupted entry/entries were skipped and could not be loaded.",
            entries,
        )

    return entries


def save_entries(entries, filename=DATA_FILE):
    dir_name = os.path.dirname(filename) or "."
    tmp_path = None
    try:
        with _data_lock(exclusive=True):
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp", text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                json.dump([asdict(entry) for entry in entries], tmp_file, indent=4)
            os.replace(tmp_path, filename)
            tmp_path = None
    except OSError as e:
        if tmp_path:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
        raise OSError(f"Failed to save entries: {e}") from e


def add_entry(mood, note="", filename=DATA_FILE):
    if len(note) > MAX_NOTE_LENGTH:
        raise ValueError(f"Note exceeds the {MAX_NOTE_LENGTH}-character limit.")
    entries = load_entries(filename)
    new_entry = MoodEntry(mood=mood, note=note)
    entries.append(new_entry)
    save_entries(entries, filename)
    return new_entry


def list_entries(filename=DATA_FILE):
    return load_entries(filename)


def delete_entry(index, filename=DATA_FILE):
    entries = load_entries(filename)
    if index < 0 or index >= len(entries):
        raise IndexError("Invalid entry index.")
    removed = entries.pop(index)
    save_entries(entries, filename)
    return removed


def delete_all_entries(filename=DATA_FILE):
    entries = load_entries(filename)
    save_entries([], filename)
    return len(entries)


def update_entry(index, new_mood=None, new_note=None, filename=DATA_FILE):
    entries = load_entries(filename)
    if index < 0 or index >= len(entries):
        raise IndexError("Invalid entry index.")

    if new_mood is not None:
        if not isinstance(new_mood, int) or not 1 <= new_mood <= 5:
            raise ValueError("Mood must be an integer between 1 and 5.")

    if new_note is not None and len(new_note) > MAX_NOTE_LENGTH:
        raise ValueError(f"Note exceeds the {MAX_NOTE_LENGTH}-character limit.")

    if new_mood is not None:
        entries[index].mood = new_mood
    if new_note is not None:
        entries[index].note = new_note

    save_entries(entries, filename)
    return entries[index]


def get_mood_stats(filename=DATA_FILE):
    entries = _load_entries_safe(filename)
    if not entries:
        return None

    moods = [entry.mood for entry in entries]
    return {
        "count": len(moods),
        "average": sum(moods) / len(moods),
        "highest": max(moods),
        "lowest": min(moods),
    }


def search_entries(keyword, filename=DATA_FILE):
    if not keyword:
        return list_entries(filename)

    normalized_keyword = keyword.lower().strip()
    return [
        entry for entry in load_entries(filename)
        if normalized_keyword in entry.note.lower()
    ]


def filter_by_mood(min_mood=None, max_mood=None, filename=DATA_FILE):
    entries = load_entries(filename)
    if min_mood is not None and (not isinstance(min_mood, int) or not 1 <= min_mood <= 5):
        raise ValueError("Minimum mood must be an integer between 1 and 5.")
    if max_mood is not None and (not isinstance(max_mood, int) or not 1 <= max_mood <= 5):
        raise ValueError("Maximum mood must be an integer between 1 and 5.")
    if min_mood is not None and max_mood is not None and min_mood > max_mood:
        raise ValueError("Minimum mood cannot be greater than maximum mood.")

    return [
        entry for entry in entries
        if (min_mood is None or entry.mood >= min_mood)
        and (max_mood is None or entry.mood <= max_mood)
    ]


def filter_by_date(start_date=None, end_date=None, filename=DATA_FILE):
    entries = load_entries(filename)

    if start_date:
        try:
            start = datetime.fromisoformat(start_date).date()
        except ValueError:
            raise ValueError(f"Invalid start date '{start_date}'. Use YYYY-MM-DD format.")
    else:
        start = None

    if end_date:
        try:
            end = datetime.fromisoformat(end_date).date()
        except ValueError:
            raise ValueError(f"Invalid end date '{end_date}'. Use YYYY-MM-DD format.")
    else:
        end = None

    if start and end and start > end:
        raise ValueError("Start date cannot be after end date.")

    filtered_entries = []
    for entry in entries:
        try:
            entry_date = parse_timestamp(entry.timestamp).date()
        except ValueError:
            continue

        if start and entry_date < start:
            continue
        if end and entry_date > end:
            continue
        filtered_entries.append(entry)

    return filtered_entries


def export_entries_csv(filename=DATA_FILE, export_filename=EXPORT_FILE):
    entries = load_entries(filename)
    with open(export_filename, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["mood", "note", "timestamp"])
        for entry in entries:
            writer.writerow([entry.mood, entry.note, entry.timestamp])
    return export_filename


def get_mood_trend(filename=DATA_FILE):
    entries = _load_entries_safe(filename)
    if len(entries) < 2:
        return None

    split_point = len(entries) // 2
    if split_point == 0:
        return None

    first_half = entries[:split_point]
    second_half = entries[split_point:]
    first_average = sum(entry.mood for entry in first_half) / len(first_half)
    second_average = sum(entry.mood for entry in second_half) / len(second_half)
    difference = second_average - first_average

    if difference > 0:
        direction = "improving"
    elif difference < 0:
        direction = "declining"
    else:
        direction = "stable"

    return {
        "direction": direction,
        "difference": difference,
        "first_average": first_average,
        "second_average": second_average,
    }


def get_most_common_mood(filename=DATA_FILE):
    entries = _load_entries_safe(filename)
    if not entries:
        return None

    mood, frequency = Counter(entry.mood for entry in entries).most_common(1)[0]
    return {"mood": mood, "frequency": frequency}


def get_entries_for_today(filename=DATA_FILE):
    today = datetime.now().date()
    today_entries = []
    for entry in _load_entries_safe(filename):
        try:
            if parse_timestamp(entry.timestamp).date() == today:
                today_entries.append(entry)
        except ValueError:
            continue
    return today_entries


def edit_note_only(index, new_note, filename=DATA_FILE):
    return update_entry(index, new_note=new_note, filename=filename)


def duplicate_entry(index, filename=DATA_FILE):
    entries = load_entries(filename)
    if index < 0 or index >= len(entries):
        raise IndexError("Invalid entry index.")

    source_entry = entries[index]
    duplicated_entry = MoodEntry(mood=source_entry.mood, note=source_entry.note)
    entries.append(duplicated_entry)
    save_entries(entries, filename)
    return duplicated_entry


class MoodTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mood Tracker")
        self.root.geometry("1120x760")
        self.root.minsize(920, 640)

        self.colors = {
            "bg": "#f3fbf8",
            "primary": "#18c7a1",
            "primary_dark": "#0f8f78",
            "primary_soft": "#dff8f2",
            "surface": "#ffffff",
            "surface_alt": "#eef8f5",
            "text": "#17364d",
            "muted": "#6d8192",
            "line": "#d7ebe5",
            "track": "#dde9e6",
        }

        self.root.configure(bg=self.colors["bg"])

        self.entries = []
        self.displayed_entries = []
        self.selected_entry = None
        self.active_view = "home"
        self.filters_visible = False

        self.mood_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.min_mood_var = tk.StringVar()
        self.max_mood_var = tk.StringVar()
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()

        self.build_layout()
        self.refresh_entries()

    def build_layout(self):
        self.build_header()
        self.build_filter_panel()

        self.content_frame = tk.Frame(self.root, bg=self.colors["bg"])
        self.content_frame.pack(fill="both", expand=True, padx=18, pady=18)

        self.home_view = tk.Frame(self.content_frame, bg=self.colors["bg"])
        self.add_view = tk.Frame(self.content_frame, bg=self.colors["bg"])
        self.stats_view = tk.Frame(self.content_frame, bg=self.colors["bg"])
        self.settings_view = tk.Frame(self.content_frame, bg=self.colors["bg"])

        self.build_home_view()
        self.build_add_view()
        self.build_stats_view()
        self.build_settings_view()
        self.build_bottom_nav()
        self.show_view("home")

    def build_header(self):
        self.header_frame = tk.Frame(self.root, bg=self.colors["primary"], height=96)
        self.header_frame.pack(fill="x")
        self.header_frame.pack_propagate(False)

        text_block = tk.Frame(self.header_frame, bg=self.colors["primary"])
        text_block.pack(side="left", fill="both", expand=True, padx=24, pady=16)

        self.header_title = tk.Label(
            text_block,
            text="Mood Tracker",
            bg=self.colors["primary"],
            fg="white",
            font=("Arial", 24, "bold"),
        )
        self.header_title.pack(anchor="w")

        self.header_subtitle = tk.Label(
            text_block,
            text="Track your day with calm, clear snapshots.",
            bg=self.colors["primary"],
            fg="#dffcf6",
            font=("Arial", 11),
        )
        self.header_subtitle.pack(anchor="w", pady=(4, 0))

        self.hero_badge = tk.Label(
            self.header_frame,
            text="0 Entries",
            bg="#ecfffb",
            fg=self.colors["primary_dark"],
            font=("Arial", 11, "bold"),
            padx=18,
            pady=10,
        )
        self.hero_badge.pack(side="right", padx=24, pady=24)

    def build_filter_panel(self):
        self.filter_frame = tk.Frame(
            self.root,
            bg=self.colors["surface"],
            highlightbackground=self.colors["line"],
            highlightthickness=1,
        )

        wrapper = tk.Frame(self.filter_frame, bg=self.colors["surface"])
        wrapper.pack(fill="x", padx=20, pady=18)

        tk.Label(
            wrapper,
            text="Search and Filters",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Arial", 14, "bold"),
        ).grid(row=0, column=0, columnspan=6, sticky="w")

        fields = [
            ("Search", self.search_var),
            ("Min mood", self.min_mood_var),
            ("Max mood", self.max_mood_var),
            ("Start date", self.start_date_var),
            ("End date", self.end_date_var),
        ]
        for index, (label_text, variable) in enumerate(fields):
            row = 1 + (index // 3) * 2
            column = (index % 3) * 2
            tk.Label(
                wrapper,
                text=label_text,
                bg=self.colors["surface"],
                fg=self.colors["muted"],
                font=("Arial", 10, "bold"),
            ).grid(row=row, column=column, sticky="w", pady=(12, 4), padx=(0, 10))
            tk.Entry(
                wrapper,
                textvariable=variable,
                relief="flat",
                bg=self.colors["surface_alt"],
                fg=self.colors["text"],
                insertbackground=self.colors["text"],
                font=("Arial", 11),
                width=22,
            ).grid(row=row + 1, column=column, sticky="we", padx=(0, 18))

        tk.Label(
            wrapper,
            text="Use YYYY-MM-DD for dates.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Arial", 10),
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 0))

        button_row = tk.Frame(wrapper, bg=self.colors["surface"])
        button_row.grid(row=6, column=0, columnspan=6, sticky="w", pady=(14, 0))
        self.create_button(button_row, "Search Notes", self.gui_search_entries, secondary=True).pack(side="left", padx=(0, 10))
        self.create_button(button_row, "Apply Filters", self.gui_apply_filters, secondary=True).pack(side="left", padx=(0, 10))
        self.create_button(button_row, "Close Filters", self.toggle_filter_panel, secondary=True).pack(side="left")

    def build_home_view(self):
        self.home_view.columnconfigure(0, weight=3)
        self.home_view.columnconfigure(1, weight=2)

        left_column = tk.Frame(self.home_view, bg=self.colors["bg"])
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.summary_row = tk.Frame(left_column, bg=self.colors["bg"])
        self.summary_row.pack(fill="x", pady=(0, 14))

        self.entries_card = self.create_card(left_column, "Recent Entries", "A softer card view of your mood history.")
        self.entries_card.pack(fill="both", expand=True)

        self.entries_canvas = tk.Canvas(self.entries_card, bg=self.colors["surface"], highlightthickness=0, bd=0)
        self.entries_scrollbar = tk.Scrollbar(self.entries_card, orient="vertical", command=self.entries_canvas.yview)
        self.entries_canvas.configure(yscrollcommand=self.entries_scrollbar.set)
        self.entries_scrollbar.pack(side="right", fill="y", padx=(0, 10), pady=(0, 12))
        self.entries_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        self.entries_list_frame = tk.Frame(self.entries_canvas, bg=self.colors["surface"])
        self.entries_canvas_window = self.entries_canvas.create_window((0, 0), window=self.entries_list_frame, anchor="nw")
        self.entries_list_frame.bind("<Configure>", self.on_entries_frame_configure)
        self.entries_canvas.bind("<Configure>", self.on_entries_canvas_configure)

        right_column = tk.Frame(self.home_view, bg=self.colors["bg"])
        right_column.grid(row=0, column=1, sticky="nsew")

        self.detail_card = self.create_card(right_column, "Entry Details", "Select a card to load the full entry.")
        self.detail_card.pack(fill="both", expand=True, pady=(0, 14))

        self.detail_mood_label = tk.Label(
            self.detail_card,
            text="Mood --",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            font=("Arial", 18, "bold"),
        )
        self.detail_mood_label.pack(anchor="w", padx=14)

        self.detail_time_label = tk.Label(
            self.detail_card,
            text="Select an entry to populate this panel.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            font=("Arial", 10),
        )
        self.detail_time_label.pack(anchor="w", padx=14, pady=(4, 10))

        self.detail_note_text = tk.Text(
            self.detail_card,
            height=8,
            wrap="word",
            relief="flat",
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            font=("Arial", 11),
            padx=10,
            pady=10,
            state="disabled",
        )
        self.detail_note_text.pack(fill="x", padx=14, pady=(0, 12))

        self.progress_card = self.create_card(right_column, "Wellness Snapshot", "A simple visual summary tied to the mood level.")
        self.progress_card.pack(fill="x")
        self.progress_rows = []
        for label in ["Calm", "Energy", "Focus"]:
            row = self.create_progress_row(self.progress_card, label)
            row.pack(fill="x", padx=14, pady=8)
            self.progress_rows.append(row)

    def build_add_view(self):
        self.add_view.columnconfigure(0, weight=3)
        self.add_view.columnconfigure(1, weight=2)

        form_column = tk.Frame(self.add_view, bg=self.colors["bg"])
        form_column.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        form_card = self.create_card(form_column, "Add or Update Entry", "Keep one strong primary action and nearby secondary controls.")
        form_card.pack(fill="both", expand=True)

        form_inner = tk.Frame(form_card, bg=self.colors["surface"])
        form_inner.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        form_inner.columnconfigure(1, weight=1)

        tk.Label(form_inner, text="Mood number (1-5)", bg=self.colors["surface"], fg=self.colors["muted"], font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        self.mood_entry = tk.Entry(
            form_inner,
            textvariable=self.mood_var,
            relief="flat",
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=("Arial", 14),
            width=10,
        )
        self.mood_entry.grid(row=1, column=0, sticky="w", pady=(0, 16))

        tk.Label(form_inner, text="Notes", bg=self.colors["surface"], fg=self.colors["muted"], font=("Arial", 10, "bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )
        self.note_entry = tk.Text(
            form_inner,
            height=8,
            wrap="word",
            relief="flat",
            bg=self.colors["surface_alt"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            font=("Arial", 12),
            padx=10,
            pady=10,
        )
        self.note_entry.grid(row=3, column=0, columnspan=2, sticky="nsew")
        form_inner.rowconfigure(3, weight=1)

        primary_row = tk.Frame(form_inner, bg=self.colors["surface"])
        primary_row.grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 0))
        self.create_button(primary_row, "Add Entry", self.gui_add_entry).pack(side="left", padx=(0, 10))
        self.create_button(primary_row, "Update Selected", self.gui_update_entry, secondary=True).pack(side="left", padx=(0, 10))
        self.create_button(primary_row, "Clear Inputs", self.clear_inputs, secondary=True).pack(side="left")

        secondary_column = tk.Frame(self.add_view, bg=self.colors["bg"])
        secondary_column.grid(row=0, column=1, sticky="nsew")

        actions_card = self.create_card(secondary_column, "Quick Actions", "Secondary tools grouped away from the form.")
        actions_card.pack(fill="x", pady=(0, 14))

        actions_grid = tk.Frame(actions_card, bg=self.colors["surface"])
        actions_grid.pack(fill="x", padx=14, pady=(0, 14))
        action_specs = [
            ("Edit Note", self.gui_edit_note_only),
            ("Delete Selected", self.gui_delete_entry),
            ("Duplicate", self.gui_duplicate_entry),
            ("Show Today", self.gui_show_today_entries),
            ("Export CSV", self.gui_export_csv),
            ("Delete All", self.gui_delete_all_entries),
        ]
        for index, (label, command) in enumerate(action_specs):
            button = self.create_button(actions_grid, label, command, secondary=(label != "Delete All"))
            if label == "Delete All":
                button.configure(bg="#ffe8e7", fg="#9c403d", activebackground="#ffd3d0")
            button.grid(row=index // 2, column=index % 2, padx=6, pady=6, sticky="we")
        actions_grid.columnconfigure(0, weight=1)
        actions_grid.columnconfigure(1, weight=1)

        hint_card = self.create_card(secondary_column, "Entry Flow", "Select a card on Home, then return here to edit it.")
        hint_card.pack(fill="both", expand=True)
        self.hint_message = tk.Label(
            hint_card,
            text="Use the bottom navigation to switch between Home, Add, Stats, Filters, and Settings.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            wraplength=260,
            font=("Arial", 11),
        )
        self.hint_message.pack(anchor="w", padx=14, pady=(0, 14))

    def build_stats_view(self):
        wrapper = tk.Frame(self.stats_view, bg=self.colors["bg"])
        wrapper.pack(fill="both", expand=True)

        self.stats_summary_card = self.create_card(wrapper, "Mood Overview", "A quick read on your recent mood patterns.")
        self.stats_summary_card.pack(fill="x", pady=(0, 14))

        self.stats_text_label = tk.Label(
            self.stats_summary_card,
            text="No entries available yet.",
            bg=self.colors["surface"],
            fg=self.colors["text"],
            justify="left",
            font=("Arial", 12),
        )
        self.stats_text_label.pack(anchor="w", padx=14, pady=(0, 14))

        self.stats_detail_card = self.create_card(wrapper, "Highlights", "Status-style cards for the main summary metrics.")
        self.stats_detail_card.pack(fill="both", expand=True)
        self.stats_highlights_frame = tk.Frame(self.stats_detail_card, bg=self.colors["surface"])
        self.stats_highlights_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def build_settings_view(self):
        settings_card = self.create_card(self.settings_view, "Tools and Settings", "Support actions and project notes.")
        settings_card.pack(fill="x")

        actions = tk.Frame(settings_card, bg=self.colors["surface"])
        actions.pack(fill="x", padx=14, pady=(0, 14))
        self.create_button(actions, "Refresh Entries", self.refresh_entries, secondary=True).pack(side="left", padx=(0, 10))
        self.create_button(actions, "Filter Entries", self.toggle_filter_panel, secondary=True).pack(side="left", padx=(0, 10))
        self.create_button(actions, "Show Statistics", self.gui_show_stats).pack(side="left")

        tk.Label(
            settings_card,
            text="This Tkinter version adapts the mobile-inspired style into a desktop app with a mint palette, rounded cards, clearer hierarchy, and a bottom navigation bar.",
            bg=self.colors["surface"],
            fg=self.colors["muted"],
            justify="left",
            wraplength=840,
            font=("Arial", 11),
        ).pack(anchor="w", padx=14, pady=(0, 14))

    def build_bottom_nav(self):
        self.bottom_nav = tk.Frame(
            self.root,
            bg=self.colors["surface"],
            height=78,
            highlightbackground=self.colors["line"],
            highlightthickness=1,
        )
        self.bottom_nav.pack(fill="x", side="bottom")
        self.bottom_nav.pack_propagate(False)

        self.nav_buttons = {}
        nav_items = [
            ("Home", "home"),
            ("Add", "add"),
            ("Stats", "stats"),
            ("Filters", "filters"),
            ("Settings", "settings"),
        ]
        for label, view_name in nav_items:
            button = tk.Button(
                self.bottom_nav,
                text=label,
                bd=0,
                relief="flat",
                font=("Arial", 11, "bold"),
                bg=self.colors["surface"],
                fg=self.colors["muted"],
                activebackground=self.colors["surface_alt"],
                activeforeground=self.colors["text"],
                command=lambda name=view_name: self.on_nav_click(name),
            )
            button.pack(side="left", fill="both", expand=True, padx=4, pady=10)
            self.nav_buttons[view_name] = button

    def create_card(self, parent, title, subtitle):
        card = tk.Frame(parent, bg=self.colors["surface"], highlightbackground=self.colors["line"], highlightthickness=1)
        tk.Label(card, text=title, bg=self.colors["surface"], fg=self.colors["text"], font=("Arial", 15, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
        tk.Label(card, text=subtitle, bg=self.colors["surface"], fg=self.colors["muted"], font=("Arial", 10)).pack(anchor="w", padx=14, pady=(0, 14))
        return card

    def create_button(self, parent, text, command, secondary=False):
        bg = self.colors["surface"] if secondary else self.colors["primary"]
        fg = self.colors["primary_dark"] if secondary else "white"
        active_bg = self.colors["surface_alt"] if secondary else self.colors["primary_dark"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bd=0,
            relief="flat",
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            font=("Arial", 11, "bold"),
            padx=16,
            pady=10,
            highlightthickness=1 if secondary else 0,
            highlightbackground=self.colors["line"],
        )

    def create_progress_row(self, parent, label_text):
        row = tk.Frame(parent, bg=self.colors["surface"])
        header = tk.Frame(row, bg=self.colors["surface"])
        header.pack(fill="x")
        tk.Label(header, text=label_text, bg=self.colors["surface"], fg=self.colors["text"], font=("Arial", 11, "bold")).pack(side="left")
        value_label = tk.Label(header, text="0%", bg=self.colors["surface"], fg=self.colors["muted"], font=("Arial", 11, "bold"))
        value_label.pack(side="right")

        track = tk.Frame(row, bg=self.colors["track"], height=8)
        track.pack(fill="x", pady=(6, 0))
        track.pack_propagate(False)
        fill = tk.Frame(track, bg=self.colors["primary"])
        fill.place(relheight=1, relwidth=0)
        row.value_label = value_label
        row.fill = fill
        return row

    def on_entries_frame_configure(self, event=None):
        self.entries_canvas.configure(scrollregion=self.entries_canvas.bbox("all"))

    def on_entries_canvas_configure(self, event):
        self.entries_canvas.itemconfigure(self.entries_canvas_window, width=event.width)

    def get_note_text(self):
        return self.note_entry.get("1.0", tk.END).strip()

    def set_note_text(self, note):
        self.note_entry.delete("1.0", tk.END)
        self.note_entry.insert("1.0", note)

    def clear_inputs(self):
        self.mood_var.set("")
        self.note_entry.delete("1.0", tk.END)
        self.mood_entry.focus_set()

    def get_selected_entry_index(self):
        if self.selected_entry is None:
            raise IndexError("Please select an entry first.")
        return self.entries.index(self.selected_entry)

    def get_mood_color(self, mood):
        palette = {
            1: "#f7a5a2",
            2: "#f7c59f",
            3: "#ffd56a",
            4: "#8fe0d0",
            5: self.colors["primary"],
        }
        return palette.get(mood, self.colors["primary"])

    def get_entry_metrics(self, mood):
        calm = min(100, 20 + mood * 16)
        energy = min(100, 28 + mood * 14)
        focus = min(100, 24 + mood * 15)
        return [calm, energy, focus]

    def update_header(self):
        titles = {
            "home": ("Mood Tracker", "Track your day with calm, clear snapshots."),
            "add": ("Add Entry", "Use a clean form with one primary action."),
            "stats": ("Mood Insights", "A friendlier overview of your patterns."),
            "settings": ("Tools", "Supporting actions and project utilities."),
        }
        title, subtitle = titles.get(self.active_view, titles["home"])
        self.header_title.config(text=title)
        self.header_subtitle.config(text=subtitle)

    def update_nav_state(self):
        for view_name, button in self.nav_buttons.items():
            active = view_name == self.active_view or (view_name == "filters" and self.filters_visible)
            button.configure(
                bg=self.colors["primary_soft"] if active else self.colors["surface"],
                fg=self.colors["primary_dark"] if active else self.colors["muted"],
            )

    def show_view(self, view_name):
        for frame in (self.home_view, self.add_view, self.stats_view, self.settings_view):
            frame.pack_forget()

        self.active_view = view_name
        if view_name == "home":
            self.home_view.pack(fill="both", expand=True)
        elif view_name == "add":
            self.add_view.pack(fill="both", expand=True)
            self.mood_entry.focus_set()
        elif view_name == "stats":
            self.stats_view.pack(fill="both", expand=True)
            self.render_stats_view()
        elif view_name == "settings":
            self.settings_view.pack(fill="both", expand=True)

        self.update_header()
        self.update_nav_state()

    def on_nav_click(self, view_name):
        if view_name == "filters":
            self.toggle_filter_panel()
            return
        self.show_view(view_name)

    def render_summary_cards(self):
        for child in self.summary_row.winfo_children():
            child.destroy()

        stats = get_mood_stats()
        common = get_most_common_mood()
        summary_items = [
            ("Entries", str(stats["count"]) if stats else "0"),
            ("Average", f"{stats['average']:.1f}" if stats else "--"),
            ("Today", str(len(get_entries_for_today()))),
            ("Common", str(common["mood"]) if common else "--"),
        ]

        for label, value in summary_items:
            card = tk.Frame(self.summary_row, bg=self.colors["surface"], highlightbackground=self.colors["line"], highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=6)
            tk.Label(card, text=value, bg=self.colors["surface"], fg=self.colors["text"], font=("Arial", 18, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
            tk.Label(card, text=label, bg=self.colors["surface"], fg=self.colors["muted"], font=("Arial", 10, "bold")).pack(anchor="w", padx=14, pady=(0, 12))

    def create_entry_card(self, parent, entry, index):
        card_bg = self.colors["primary_soft"] if self.selected_entry == entry else self.colors["surface_alt"]
        border = self.colors["primary"] if self.selected_entry == entry else self.colors["line"]
        card = tk.Frame(parent, bg=card_bg, highlightbackground=border, highlightthickness=1, cursor="hand2")
        card.pack(fill="x", padx=6, pady=6)

        header = tk.Frame(card, bg=card_bg)
        header.pack(fill="x", padx=12, pady=(12, 4))
        tk.Label(header, text=f"Mood {entry.mood}", bg=card_bg, fg=self.colors["text"], font=("Arial", 13, "bold")).pack(side="left")
        tk.Label(header, text=format_timestamp(entry.timestamp), bg=card_bg, fg=self.colors["muted"], font=("Arial", 10)).pack(side="right")

        preview = entry.note.strip() or "No note for this entry yet."
        if len(preview) > 88:
            preview = preview[:88] + "..."

        tk.Label(
            card,
            text=preview,
            bg=card_bg,
            fg=self.colors["muted"],
            wraplength=480,
            justify="left",
            font=("Arial", 11),
        ).pack(anchor="w", padx=12, pady=(0, 10))

        mood_bar = tk.Frame(card, bg=self.colors["track"], height=6)
        mood_bar.pack(fill="x", padx=12, pady=(0, 12))
        mood_bar.pack_propagate(False)
        fill = tk.Frame(mood_bar, bg=self.get_mood_color(entry.mood))
        fill.place(relheight=1, relwidth=entry.mood / 5)

        widgets = [card, header]
        widgets.extend(card.winfo_children())
        widgets.extend(header.winfo_children())
        for widget in widgets:
            widget.bind("<Button-1>", lambda event, idx=index: self.select_entry(idx))

    def render_entry_cards(self):
        for child in self.entries_list_frame.winfo_children():
            child.destroy()

        if not self.displayed_entries:
            tk.Label(
                self.entries_list_frame,
                text="No entries found. Add one from the Add tab or adjust your filters.",
                bg=self.colors["surface"],
                fg=self.colors["muted"],
                font=("Arial", 11),
                wraplength=520,
                justify="left",
            ).pack(anchor="w", padx=12, pady=12)
            self.clear_details()
            return

        for index, entry in enumerate(self.displayed_entries):
            self.create_entry_card(self.entries_list_frame, entry, index)

    def clear_details(self):
        self.detail_mood_label.config(text="Mood --")
        self.detail_time_label.config(text="Select a card to populate this panel.")
        self.detail_note_text.config(state="normal")
        self.detail_note_text.delete("1.0", tk.END)
        self.detail_note_text.insert("1.0", "Your notes will appear here once you select an entry.")
        self.detail_note_text.config(state="disabled")
        for row in self.progress_rows:
            row.value_label.config(text="0%")
            row.fill.place_configure(relwidth=0)

    def on_select_entry(self, event=None):
        if self.selected_entry is None:
            return

        entry = self.selected_entry
        self.detail_mood_label.config(text=f"Mood {entry.mood}")
        self.detail_time_label.config(text=format_timestamp(entry.timestamp))
        self.detail_note_text.config(state="normal")
        self.detail_note_text.delete("1.0", tk.END)
        self.detail_note_text.insert("1.0", entry.note or "No note for this entry.")
        self.detail_note_text.config(state="disabled")

        for row, value in zip(self.progress_rows, self.get_entry_metrics(entry.mood)):
            row.value_label.config(text=f"{value}%")
            row.fill.place_configure(relwidth=value / 100)

        self.mood_var.set(str(entry.mood))
        self.set_note_text(entry.note)

    def select_entry(self, display_index):
        if display_index < 0 or display_index >= len(self.displayed_entries):
            return
        self.selected_entry = self.displayed_entries[display_index]
        self.on_select_entry()
        self.render_entry_cards()

    def populate_listbox(self, entries):
        self.displayed_entries = entries
        if self.selected_entry not in self.displayed_entries:
            self.selected_entry = None
        self.render_summary_cards()
        self.render_entry_cards()
        self.render_stats_view()

    def refresh_entries(self):
        try:
            self.entries = list_entries()
        except DataLoadWarning as warning:
            self.entries = warning.entries
            messagebox.showwarning("Data Warning", str(warning), parent=self.root)
        except RuntimeError as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
            self.entries = []
        self.populate_listbox(self.entries)
        self.hero_badge.config(text=f"{len(self.entries)} Entries")

    def toggle_filter_panel(self):
        if self.filters_visible:
            self.filter_frame.pack_forget()
            self.filters_visible = False
        else:
            self.filter_frame.pack(fill="x", padx=18, pady=(0, 8), after=self.header_frame)
            self.filters_visible = True
        self.update_nav_state()

    def render_stats_view(self):
        for child in self.stats_highlights_frame.winfo_children():
            child.destroy()

        stats = get_mood_stats()
        trend = get_mood_trend()
        common = get_most_common_mood()
        if stats is None:
            self.stats_text_label.config(text="No entries available yet.")
            return

        trend_label = trend["direction"].title() if trend else "Not enough data"
        self.stats_text_label.config(
            text=(
                f"Average mood: {stats['average']:.2f}\n"
                f"Highest mood: {stats['highest']}\n"
                f"Lowest mood: {stats['lowest']}\n"
                f"Trend: {trend_label}\n"
                f"Most common mood: {common['mood']} ({common['frequency']} times)"
            )
        )

        highlights = [
            ("Total Entries", str(stats["count"])),
            ("Today", str(len(get_entries_for_today()))),
            ("Common Mood", str(common["mood"])),
            ("Trend", trend_label),
        ]

        for index, (title, value) in enumerate(highlights):
            card = tk.Frame(self.stats_highlights_frame, bg=self.colors["surface_alt"], highlightbackground=self.colors["line"], highlightthickness=1)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)
            tk.Label(card, text=value, bg=self.colors["surface_alt"], fg=self.colors["text"], font=("Arial", 18, "bold")).pack(anchor="w", padx=14, pady=(14, 4))
            tk.Label(card, text=title, bg=self.colors["surface_alt"], fg=self.colors["muted"], font=("Arial", 10, "bold")).pack(anchor="w", padx=14, pady=(0, 14))
        self.stats_highlights_frame.columnconfigure(0, weight=1)
        self.stats_highlights_frame.columnconfigure(1, weight=1)

    def show_success_screen(self, title, body):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.transient(self.root)
        popup.grab_set()
        popup.configure(bg=self.colors["primary"])
        popup.geometry("420x340")
        popup.resizable(False, False)

        circle = tk.Canvas(popup, width=160, height=160, bg=self.colors["primary"], highlightthickness=0)
        circle.pack(pady=(24, 12))
        circle.create_oval(20, 20, 140, 140, fill="#4fe0bf", outline="")
        circle.create_oval(46, 60, 114, 118, fill="#ffffff", outline=self.colors["text"], width=2)
        circle.create_text(80, 89, text=":)", fill=self.colors["primary_dark"], font=("Arial", 20, "bold"))

        tk.Label(popup, text=title, bg=self.colors["primary"], fg="white", font=("Arial", 22, "bold")).pack()
        tk.Label(popup, text=body, bg=self.colors["primary"], fg="#ddfff7", font=("Arial", 11), wraplength=280, justify="center").pack(pady=(12, 24))
        tk.Button(
            popup,
            text="OK",
            command=popup.destroy,
            bd=0,
            relief="flat",
            bg="white",
            fg=self.colors["primary_dark"],
            activebackground="#ecfffb",
            activeforeground=self.colors["primary_dark"],
            font=("Arial", 12, "bold"),
            padx=40,
            pady=10,
        ).pack()

    def gui_add_entry(self):
        try:
            mood_text = self.mood_var.get().strip()
            note = self.get_note_text()
            if not mood_text:
                raise ValueError("Please enter a mood from 1 to 5 before adding an entry.")
            if not mood_text.isdigit():
                raise ValueError("Mood must be a whole number between 1 and 5.")

            new_entry = add_entry(int(mood_text), note)
            self.refresh_entries()
            self.selected_entry = new_entry
            self.populate_listbox(self.entries)
            self.clear_inputs()
            self.show_success_screen("Entry saved", "Your mood was added to the timeline.")
            self.show_view("home")
        except ValueError as error:
            messagebox.showerror("Invalid Input", str(error), parent=self.root)
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Error", str(error), parent=self.root)
        except Exception as error:
            messagebox.showerror("Unexpected Error", str(error), parent=self.root)

    def gui_update_entry(self):
        try:
            index = self.get_selected_entry_index()
            mood_text = self.mood_var.get().strip()
            if not mood_text:
                raise ValueError("Please enter a mood from 1 to 5 before updating an entry.")
            if not mood_text.isdigit():
                raise ValueError("Mood must be a whole number between 1 and 5.")
            confirm = messagebox.askyesno("Confirm Update", f"Update entry {index}?", parent=self.root)
            if not confirm:
                return

            update_entry(index, new_mood=int(mood_text), new_note=self.get_note_text())
            self.refresh_entries()
            if 0 <= index < len(self.entries):
                self.selected_entry = self.entries[index]
                self.on_select_entry()
            self.render_entry_cards()
            self.show_success_screen("Entry updated", "The selected mood entry now reflects your changes.")
        except ValueError as error:
            messagebox.showerror("Invalid Input", str(error), parent=self.root)
        except IndexError as error:
            messagebox.showerror("Selection Error", str(error), parent=self.root)
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Error", str(error), parent=self.root)
        except Exception as error:
            messagebox.showerror("Unexpected Error", str(error), parent=self.root)

    def gui_delete_entry(self):
        try:
            index = self.get_selected_entry_index()
            confirm = messagebox.askyesno("Confirm Delete", f"Delete entry {index}?", parent=self.root)
            if not confirm:
                return

            current_entries = load_entries()
            if index >= len(current_entries) or asdict(current_entries[index]) != asdict(self.selected_entry):
                raise RuntimeError(
                    "The entry list changed since you selected this entry. "
                    "Please refresh and try again."
                )

            delete_entry(index)
            self.selected_entry = None
            self.refresh_entries()
            self.clear_inputs()
            self.show_success_screen("Entry deleted", "The selected mood entry was removed.")
        except IndexError as error:
            messagebox.showerror("Selection Error", str(error), parent=self.root)
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Error", str(error), parent=self.root)
        except Exception as error:
            messagebox.showerror("Unexpected Error", str(error), parent=self.root)

    def gui_edit_note_only(self):
        try:
            index = self.get_selected_entry_index()
            edit_note_only(index, self.get_note_text())
            self.refresh_entries()
            if 0 <= index < len(self.entries):
                self.selected_entry = self.entries[index]
                self.on_select_entry()
            self.render_entry_cards()
            self.show_success_screen("Note updated", "Only the note was changed for this entry.")
        except ValueError as error:
            messagebox.showerror("Invalid Input", str(error), parent=self.root)
        except IndexError as error:
            messagebox.showerror("Selection Error", str(error), parent=self.root)
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Error", str(error), parent=self.root)
        except Exception as error:
            messagebox.showerror("Unexpected Error", str(error), parent=self.root)

    def gui_duplicate_entry(self):
        try:
            index = self.get_selected_entry_index()
            duplicated = duplicate_entry(index)
            self.refresh_entries()
            self.selected_entry = duplicated
            self.populate_listbox(self.entries)
            self.show_success_screen("Entry duplicated", "A new copy was created with the current timestamp.")
        except IndexError as error:
            messagebox.showerror("Selection Error", str(error), parent=self.root)
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Error", str(error), parent=self.root)
        except Exception as error:
            messagebox.showerror("Unexpected Error", str(error), parent=self.root)

    def gui_show_stats(self):
        stats = get_mood_stats()
        if stats is None:
            messagebox.showinfo("Mood Statistics", "No entries available for statistics.", parent=self.root)
            return

        common = get_most_common_mood()
        trend = get_mood_trend()
        trend_text = "Not enough entries."
        if trend is not None:
            trend_text = f"{trend['direction'].title()} ({trend['first_average']:.2f} -> {trend['second_average']:.2f})"

        stats_text = (
            f"Total entries: {stats['count']}\n"
            f"Average mood: {stats['average']:.2f}\n"
            f"Highest mood: {stats['highest']}\n"
            f"Lowest mood: {stats['lowest']}\n"
            f"Most common mood: {common['mood']} ({common['frequency']} times)\n"
            f"Trend: {trend_text}"
        )
        messagebox.showinfo("Mood Statistics", stats_text, parent=self.root)
        self.show_view("stats")

    def gui_show_today_entries(self):
        today_entries = get_entries_for_today()
        self.populate_listbox(today_entries)
        self.show_view("home")
        if not today_entries:
            messagebox.showinfo("Today's Entries", "No entries found for today.", parent=self.root)

    def gui_search_entries(self):
        try:
            results = search_entries(self.search_var.get().strip())
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
            return
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Error", str(error), parent=self.root)
            return
        self.populate_listbox(results)
        self.show_view("home")
        if self.search_var.get().strip():
            messagebox.showinfo("Search Results", f"Found {len(results)} matching entries.", parent=self.root)

    def gui_apply_filters(self):
        try:
            filtered_entries = self.entries
            min_mood_raw = self.min_mood_var.get().strip()
            max_mood_raw = self.max_mood_var.get().strip()

            if min_mood_raw and not min_mood_raw.isdigit():
                raise ValueError("Min mood must be a whole number between 1 and 5.")
            if max_mood_raw and not max_mood_raw.isdigit():
                raise ValueError("Max mood must be a whole number between 1 and 5.")

            min_mood = int(min_mood_raw) if min_mood_raw else None
            max_mood = int(max_mood_raw) if max_mood_raw else None
            start_date = self.start_date_var.get().strip() or None
            end_date = self.end_date_var.get().strip() or None

            if min_mood is not None or max_mood is not None:
                mood_matches = filter_by_mood(min_mood=min_mood, max_mood=max_mood)
                filtered_entries = [entry for entry in filtered_entries if entry in mood_matches]

            if start_date or end_date:
                date_matches = filter_by_date(start_date=start_date, end_date=end_date)
                filtered_entries = [entry for entry in filtered_entries if entry in date_matches]

            self.populate_listbox(filtered_entries)
            self.show_view("home")
            messagebox.showinfo("Filters", f"Showing {len(filtered_entries)} filtered entries.", parent=self.root)
        except ValueError as error:
            messagebox.showerror("Invalid Input", str(error), parent=self.root)
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Error", str(error), parent=self.root)
        except Exception as error:
            messagebox.showerror("Unexpected Error", str(error), parent=self.root)

    def gui_export_csv(self):
        try:
            export_path = export_entries_csv()
            messagebox.showinfo("Export Complete", f"Entries exported to:\n{export_path}", parent=self.root)
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Export Error", str(error), parent=self.root)
        except Exception as error:
            messagebox.showerror("Unexpected Error", str(error), parent=self.root)

    def gui_delete_all_entries(self):
        try:
            if not self.entries:
                messagebox.showinfo("Delete All", "There are no entries to delete.", parent=self.root)
                return

            confirmation_text = simpledialog.askstring(
                "Confirm Delete All",
                'Type "delete all entries" to permanently delete all saved entries.',
                parent=self.root,
            )
            if confirmation_text is None:
                return
            if confirmation_text.strip() != "delete all entries":
                messagebox.showerror(
                    "Confirmation Failed",
                    'Entries were not deleted because the confirmation text did not match "delete all entries".',
                    parent=self.root,
                )
                return

            deleted_count = delete_all_entries()
            self.selected_entry = None
            self.refresh_entries()
            self.clear_inputs()
            self.show_success_screen("All entries deleted", f"Deleted {deleted_count} entries from your tracker.")
        except DataLoadWarning as error:
            messagebox.showerror("Data Error", str(error), parent=self.root)
        except (RuntimeError, OSError) as error:
            messagebox.showerror("Error", str(error), parent=self.root)
        except Exception as error:
            messagebox.showerror("Unexpected Error", str(error), parent=self.root)


if __name__ == "__main__":
    root = tk.Tk()
    app = MoodTrackerApp(root)
    root.mainloop()
