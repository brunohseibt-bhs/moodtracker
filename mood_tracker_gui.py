import csv
import json
import os
import tkinter as tk
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "mood_entries.json")
EXPORT_FILE = os.path.join(BASE_DIR, "mood_entries_export.csv")


# =========================
# Data Model
# =========================
@dataclass
class MoodEntry:
    mood: int
    note: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if not isinstance(self.mood, int) or not 1 <= self.mood <= 5:
            raise ValueError("Mood must be an integer between 1 and 5.")


# =========================
# Helpers
# =========================
def parse_timestamp(timestamp):
    return datetime.fromisoformat(timestamp)


def format_timestamp(timestamp):
    try:
        return parse_timestamp(timestamp).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return timestamp


# =========================
# File Operations
# =========================
def load_entries(filename=DATA_FILE):
    if not os.path.exists(filename):
        return []

    try:
        with open(filename, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError, IOError):
        return []

    if not isinstance(data, list):
        return []

    entries = []
    for entry in data:
        try:
            entries.append(MoodEntry(**entry))
        except (ValueError, TypeError):
            pass

    return entries


def save_entries(entries, filename=DATA_FILE):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump([asdict(entry) for entry in entries], file, indent=4)


# =========================
# CRUD Functions
# =========================
def add_entry(mood, note="", filename=DATA_FILE):
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
        entries[index].mood = new_mood

    if new_note is not None:
        entries[index].note = new_note

    save_entries(entries, filename)
    return entries[index]


def get_mood_stats(filename=DATA_FILE):
    entries = load_entries(filename)
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

    if min_mood is not None:
        if not isinstance(min_mood, int) or not 1 <= min_mood <= 5:
            raise ValueError("Minimum mood must be an integer between 1 and 5.")

    if max_mood is not None:
        if not isinstance(max_mood, int) or not 1 <= max_mood <= 5:
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

    start = datetime.fromisoformat(start_date).date() if start_date else None
    end = datetime.fromisoformat(end_date).date() if end_date else None

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
    entries = load_entries(filename)
    if len(entries) < 2:
        return None

    first_half_count = len(entries) // 2
    if first_half_count == 0:
        return None

    first_half = entries[:first_half_count]
    second_half = entries[first_half_count:]

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
    entries = load_entries(filename)
    if not entries:
        return None

    counts = Counter(entry.mood for entry in entries)
    mood, frequency = counts.most_common(1)[0]
    return {
        "mood": mood,
        "frequency": frequency,
    }


def get_entries_for_today(filename=DATA_FILE):
    today = datetime.now().date()
    entries = load_entries(filename)

    today_entries = []
    for entry in entries:
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


# =========================
# GUI App
# =========================
class MoodTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mood Tracker")
        self.root.geometry("1040x650")
        self.root.minsize(860, 560)
        self.root.configure(bg="#0f172a")

        self.entries = []
        self.displayed_entries = []
        self.mood_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.min_mood_var = tk.StringVar()
        self.max_mood_var = tk.StringVar()
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.filters_visible = False
        self.style = ttk.Style(self.root)

        self.build_ui()
        self.refresh_entries()

    def configure_styles(self):
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure("Page.TFrame", background="#0f172a")
        self.style.configure("Input.TFrame", background="#fef08a", borderwidth=2, relief="groove")
        self.style.configure("Panel.TFrame", background="#1e293b", borderwidth=2, relief="groove")
        self.style.configure("List.TFrame", background="#1e293b")
        self.style.configure("Filter.TFrame", background="#dbeafe", borderwidth=2, relief="groove")

        self.style.configure("InputTitle.TLabel", background="#fef08a", foreground="#111827", font=("Arial", 14, "bold"))
        self.style.configure("Input.TLabel", background="#fef08a", foreground="#111827", font=("Arial", 12, "bold"))
        self.style.configure("PanelTitle.TLabel", background="#1e293b", foreground="#f8fafc", font=("Arial", 12, "bold"))
        self.style.configure("FilterTitle.TLabel", background="#dbeafe", foreground="#111827", font=("Arial", 12, "bold"))
        self.style.configure("Filter.TLabel", background="#dbeafe", foreground="#111827", font=("Arial", 10, "bold"))

        self.style.configure("Mood.TEntry", fieldbackground="#ffffff", foreground="#111827", insertcolor="#111827")
        self.style.map("Mood.TEntry", fieldbackground=[("disabled", "#e5e7eb"), ("readonly", "#ffffff")])

        self.style.configure(
            "Action.TButton",
            background="#22c55e",
            foreground="#052e16",
            font=("Arial", 10, "bold"),
            borderwidth=1,
            focusthickness=2,
            focuscolor="#bbf7d0",
        )
        self.style.map(
            "Action.TButton",
            background=[("active", "#16a34a"), ("pressed", "#15803d")],
            foreground=[("active", "#052e16"), ("pressed", "#052e16")],
        )

    def build_ui(self):
        self.configure_styles()

        dark_text = "#111827"

        input_frame = ttk.Frame(self.root, style="Input.TFrame", padding=(14, 12))
        input_frame.pack(fill="x", padx=15, pady=(15, 8))

        ttk.Label(input_frame, text="Type your mood here", style="InputTitle.TLabel").grid(
            row=0, column=0, columnspan=4, padx=(0, 8), pady=(0, 10), sticky="w"
        )

        ttk.Label(input_frame, text="Mood number (1-5):", style="Input.TLabel").grid(
            row=1, column=0, padx=(0, 8), pady=5, sticky="w"
        )

        self.mood_entry = ttk.Entry(
            input_frame,
            width=10,
            font=("Arial", 12),
            textvariable=self.mood_var,
            style="Mood.TEntry",
        )
        self.mood_entry.grid(row=1, column=1, padx=(0, 18), pady=5, sticky="w")

        ttk.Label(input_frame, text="Notes:", style="Input.TLabel").grid(
            row=1, column=2, padx=(0, 8), pady=5, sticky="nw"
        )

        self.note_entry = tk.Text(
            input_frame,
            width=50,
            height=5,
            font=("Arial", 12),
            wrap="word",
            bg="#ffffff",
            fg="#111827",
            insertbackground="#111827",
            relief="solid",
            borderwidth=1,
        )
        self.note_entry.grid(row=1, column=3, padx=(0, 0), pady=5, sticky="we")
        input_frame.grid_columnconfigure(3, weight=1)

        button_frame = ttk.Frame(self.root, style="Page.TFrame")
        button_frame.pack(fill="x", padx=15, pady=(2, 10))

        ttk.Button(button_frame, text="Add Entry", width=14, command=self.gui_add_entry, style="Action.TButton").grid(row=0, column=0, padx=5, pady=4)
        ttk.Button(button_frame, text="Update Selected", width=14, command=self.gui_update_entry, style="Action.TButton").grid(row=0, column=1, padx=5, pady=4)
        ttk.Button(button_frame, text="Delete Selected", width=14, command=self.gui_delete_entry, style="Action.TButton").grid(row=0, column=2, padx=5, pady=4)
        ttk.Button(button_frame, text="Edit Note", width=14, command=self.gui_edit_note_only, style="Action.TButton").grid(row=0, column=3, padx=5, pady=4)
        ttk.Button(button_frame, text="Duplicate", width=14, command=self.gui_duplicate_entry, style="Action.TButton").grid(row=1, column=0, padx=5, pady=4)
        ttk.Button(button_frame, text="Clear Inputs", width=14, command=self.clear_inputs, style="Action.TButton").grid(row=1, column=1, padx=5, pady=4)
        ttk.Button(button_frame, text="Show Statistics", width=14, command=self.gui_show_stats, style="Action.TButton").grid(row=1, column=2, padx=5, pady=4)
        ttk.Button(button_frame, text="Show Today", width=14, command=self.gui_show_today_entries, style="Action.TButton").grid(row=1, column=3, padx=5, pady=4)
        ttk.Button(button_frame, text="Filter Entries", width=14, command=self.toggle_filter_panel, style="Action.TButton").grid(row=2, column=0, padx=5, pady=4)
        ttk.Button(button_frame, text="Export CSV", width=14, command=self.gui_export_csv, style="Action.TButton").grid(row=2, column=1, padx=5, pady=4)
        ttk.Button(button_frame, text="Refresh Entries", width=14, command=self.refresh_entries, style="Action.TButton").grid(row=2, column=2, padx=5, pady=4)
        ttk.Button(button_frame, text="Delete All", width=14, command=self.gui_delete_all_entries, style="Action.TButton").grid(row=3, column=0, padx=5, pady=8)

        self.filter_frame = ttk.Frame(self.root, style="Filter.TFrame", padding=(12, 10))

        ttk.Label(self.filter_frame, text="Search and filters", style="FilterTitle.TLabel").grid(
            row=0, column=0, columnspan=8, sticky="w", pady=(0, 8)
        )
        ttk.Label(self.filter_frame, text="Search:", style="Filter.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(self.filter_frame, width=20, textvariable=self.search_var, style="Mood.TEntry").grid(row=1, column=1, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(self.filter_frame, text="Min mood:", style="Filter.TLabel").grid(row=1, column=2, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(self.filter_frame, width=8, textvariable=self.min_mood_var, style="Mood.TEntry").grid(row=1, column=3, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(self.filter_frame, text="Max mood:", style="Filter.TLabel").grid(row=1, column=4, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(self.filter_frame, width=8, textvariable=self.max_mood_var, style="Mood.TEntry").grid(row=1, column=5, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(self.filter_frame, text="Start date:", style="Filter.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(self.filter_frame, width=20, textvariable=self.start_date_var, style="Mood.TEntry").grid(row=2, column=1, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(self.filter_frame, text="End date:", style="Filter.TLabel").grid(row=2, column=2, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(self.filter_frame, width=20, textvariable=self.end_date_var, style="Mood.TEntry").grid(row=2, column=3, sticky="w", padx=(0, 18), pady=4)
        ttk.Label(self.filter_frame, text="Use YYYY-MM-DD for dates.", style="Filter.TLabel").grid(
            row=2, column=4, columnspan=3, sticky="w", pady=4
        )
        ttk.Button(self.filter_frame, text="Search Notes", width=14, command=self.gui_search_entries, style="Action.TButton").grid(row=3, column=0, padx=5, pady=(8, 4), sticky="w")
        ttk.Button(self.filter_frame, text="Apply Filters", width=14, command=self.gui_apply_filters, style="Action.TButton").grid(row=3, column=1, padx=5, pady=(8, 4), sticky="w")
        ttk.Button(self.filter_frame, text="Close Filters", width=14, command=self.toggle_filter_panel, style="Action.TButton").grid(row=3, column=2, padx=5, pady=(8, 4), sticky="w")

        self.mood_entry.focus_set()

        main_frame = ttk.Frame(self.root, style="Page.TFrame")
        main_frame.pack(fill="both", expand=True, padx=15, pady=10)

        left_frame = ttk.Frame(main_frame, style="Panel.TFrame")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        ttk.Label(left_frame, text="Saved Entries", style="PanelTitle.TLabel").pack(anchor="w", padx=10, pady=10)

        list_frame = ttk.Frame(left_frame, style="List.TFrame")
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.listbox = tk.Listbox(
            list_frame,
            font=("Arial", 11),
            bg="#e0f2fe",
            fg=dark_text,
            selectbackground="#f97316",
            selectforeground="#111827",
            highlightbackground="#38bdf8",
            highlightcolor="#38bdf8",
            highlightthickness=2,
        )
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind("<<ListboxSelect>>", self.on_select_entry)

        right_frame = ttk.Frame(main_frame, style="Panel.TFrame")
        right_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(right_frame, text="Entry Details", style="PanelTitle.TLabel").pack(anchor="w", padx=10, pady=10)

        self.details_text = tk.Text(
            right_frame,
            wrap="word",
            font=("Arial", 11),
            state="disabled",
            bg="#ecfccb",
            fg=dark_text,
            highlightbackground="#84cc16",
            highlightcolor="#84cc16",
            highlightthickness=2,
        )
        self.details_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def populate_listbox(self, entries):
        self.displayed_entries = entries
        self.listbox.delete(0, tk.END)

        for entry in entries:
            try:
                index = self.entries.index(entry)
            except ValueError:
                index = -1

            short_note = entry.note if entry.note else "No note"
            if len(short_note) > 25:
                short_note = short_note[:25] + "..."

            self.listbox.insert(
                tk.END,
                f"{index} | Mood {entry.mood} | {format_timestamp(entry.timestamp)} | {short_note}",
            )

        self.clear_details()

    def refresh_entries(self):
        self.entries = list_entries()
        self.populate_listbox(self.entries)

    def toggle_filter_panel(self):
        if self.filters_visible:
            self.filter_frame.pack_forget()
            self.filters_visible = False
            return

        self.filter_frame.pack(fill="x", padx=15, pady=(0, 10), before=self.root.pack_slaves()[-1])
        self.filters_visible = True

    def clear_details(self):
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, "Select an entry to view details.")
        self.details_text.config(state="disabled")

    def clear_inputs(self):
        self.mood_var.set("")
        self.note_entry.delete("1.0", tk.END)
        self.mood_entry.focus_set()

    def get_note_text(self):
        return self.note_entry.get("1.0", tk.END).strip()

    def set_note_text(self, note):
        self.note_entry.delete("1.0", tk.END)
        self.note_entry.insert("1.0", note)

    def get_selected_entry_index(self):
        selection = self.listbox.curselection()
        if not selection:
            raise IndexError("Please select an entry first.")

        selected_entry = self.displayed_entries[selection[0]]
        return self.entries.index(selected_entry)

    def on_select_entry(self, event=None):
        selection = self.listbox.curselection()
        if not selection:
            return

        entry = self.displayed_entries[selection[0]]
        index = self.entries.index(entry)

        details = (
            f"Entry Number: {index}\n\n"
            f"Mood: {entry.mood}\n"
            f"Time: {format_timestamp(entry.timestamp)}\n"
            f"Note: {entry.note or '—'}"
        )

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, details)
        self.details_text.config(state="disabled")

        self.mood_var.set(str(entry.mood))
        self.set_note_text(entry.note)

    def gui_add_entry(self):
        try:
            mood_text = self.mood_var.get().strip()
            note = self.get_note_text()

            if not mood_text:
                raise ValueError("Please enter a mood from 1 to 5 before adding an entry.")

            mood = int(mood_text)
            add_entry(mood, note)
            self.refresh_entries()
            self.clear_inputs()
            messagebox.showinfo("Success", "Mood entry added.", parent=self.root)
        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_update_entry(self):
        try:
            index = self.get_selected_entry_index()
            mood_text = self.mood_var.get().strip()
            new_note = self.get_note_text()

            if not mood_text:
                raise ValueError("Please enter a mood from 1 to 5 before updating an entry.")

            new_mood = int(mood_text)

            confirm = messagebox.askyesno("Confirm Update", f"Update entry {index}?", parent=self.root)
            if not confirm:
                return

            update_entry(index, new_mood=new_mood, new_note=new_note)
            self.refresh_entries()
            messagebox.showinfo("Success", "Mood entry updated.", parent=self.root)
        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_delete_entry(self):
        try:
            index = self.get_selected_entry_index()
            confirm = messagebox.askyesno("Confirm Delete", f"Delete entry {index}?", parent=self.root)
            if not confirm:
                return

            delete_entry(index)
            self.refresh_entries()
            self.clear_inputs()
            messagebox.showinfo("Success", "Mood entry deleted.", parent=self.root)
        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_edit_note_only(self):
        try:
            index = self.get_selected_entry_index()
            new_note = self.get_note_text()
            edit_note_only(index, new_note)
            self.refresh_entries()
            messagebox.showinfo("Success", "Note updated.", parent=self.root)
        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_duplicate_entry(self):
        try:
            index = self.get_selected_entry_index()
            duplicate_entry(index)
            self.refresh_entries()
            messagebox.showinfo("Success", "Entry duplicated.", parent=self.root)
        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_show_stats(self):
        stats = get_mood_stats()
        if stats is None:
            messagebox.showinfo("Mood Statistics", "No entries available for statistics.", parent=self.root)
            return

        common = get_most_common_mood()
        trend = get_mood_trend()
        trend_text = "Not enough entries."
        if trend is not None:
            trend_text = (
                f"{trend['direction'].title()} "
                f"({trend['first_average']:.2f} -> {trend['second_average']:.2f})"
            )

        stats_text = (
            f"Total entries: {stats['count']}\n"
            f"Average mood: {stats['average']:.2f}\n"
            f"Highest mood: {stats['highest']}\n"
            f"Lowest mood: {stats['lowest']}\n"
            f"Most common mood: {common['mood']} ({common['frequency']} times)\n"
            f"Trend: {trend_text}"
        )
        messagebox.showinfo("Mood Statistics", stats_text, parent=self.root)

    def gui_show_today_entries(self):
        today_entries = get_entries_for_today()
        self.populate_listbox(today_entries)

        if not today_entries:
            messagebox.showinfo("Today's Entries", "No entries found for today.", parent=self.root)

    def gui_search_entries(self):
        keyword = self.search_var.get().strip()
        results = search_entries(keyword)
        self.populate_listbox(results)

        if keyword:
            messagebox.showinfo("Search Results", f"Found {len(results)} matching entries.", parent=self.root)

    def gui_apply_filters(self):
        try:
            filtered_entries = self.entries

            min_mood = int(self.min_mood_var.get()) if self.min_mood_var.get().strip() else None
            max_mood = int(self.max_mood_var.get()) if self.max_mood_var.get().strip() else None
            start_date = self.start_date_var.get().strip() or None
            end_date = self.end_date_var.get().strip() or None

            if min_mood is not None or max_mood is not None:
                mood_matches = filter_by_mood(min_mood=min_mood, max_mood=max_mood)
                filtered_entries = [entry for entry in filtered_entries if entry in mood_matches]

            if start_date or end_date:
                date_matches = filter_by_date(start_date=start_date, end_date=end_date)
                filtered_entries = [entry for entry in filtered_entries if entry in date_matches]

            self.populate_listbox(filtered_entries)
            messagebox.showinfo("Filters", f"Showing {len(filtered_entries)} filtered entries.", parent=self.root)
        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_export_csv(self):
        try:
            export_path = export_entries_csv()
            messagebox.showinfo("Export Complete", f"Entries exported to:\n{export_path}", parent=self.root)
        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

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
            self.refresh_entries()
            self.clear_inputs()
            messagebox.showinfo(
                "Delete All",
                f"Deleted {deleted_count} entries.",
                parent=self.root,
            )
        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)


if __name__ == "__main__":
    root = tk.Tk()
    app = MoodTrackerApp(root)
    root.mainloop()
