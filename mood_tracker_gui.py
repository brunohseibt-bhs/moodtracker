import tkinter as tk
from tkinter import messagebox
from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import os

DATA_FILE = "mood_entries.json"


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


def update_entry(index, new_mood=None, new_note=None, filename=DATA_FILE):
    entries = load_entries(filename)
    if index < 0 or index >= len(entries):
        raise IndexError("Invalid entry index.")

    if new_mood is not None:
        if not 1 <= new_mood <= 5:
            raise ValueError("Mood must be between 1 and 5.")
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
        "lowest": min(moods)
    }


# =========================
# GUI App
# =========================
class MoodTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mood Tracker")
        self.root.geometry("900x600")
        self.root.minsize(760, 500)
        self.root.configure(bg="#0f172a")

        self.entries = []
        self.mood_var = tk.StringVar()
        self.note_var = tk.StringVar()

        self.build_ui()
        self.refresh_entries()

    def build_ui(self):
        page_bg = "#0f172a"
        panel_bg = "#1e293b"
        input_bg = "#fef08a"
        field_bg = "#ffffff"
        button_bg = "#22c55e"
        button_fg = "#052e16"
        text_fg = "#f8fafc"
        dark_text = "#111827"

        input_frame = tk.Frame(
            self.root,
            bg=input_bg,
            bd=2,
            relief="groove",
            padx=14,
            pady=12
        )
        input_frame.pack(fill="x", padx=15, pady=(15, 8))

        tk.Label(
            input_frame,
            text="Type your mood here",
            font=("Arial", 14, "bold"),
            bg=input_bg,
            fg=dark_text
        ).grid(row=0, column=0, columnspan=4, padx=(0, 8), pady=(0, 10), sticky="w")

        tk.Label(input_frame, text="Mood number (1-5):", font=("Arial", 12, "bold"), bg=input_bg, fg=dark_text).grid(
            row=1, column=0, padx=(0, 8), pady=5, sticky="w"
        )

        self.mood_entry = tk.Entry(
            input_frame,
            width=10,
            font=("Arial", 12),
            textvariable=self.mood_var,
            bg=field_bg,
            fg=dark_text,
            insertbackground=dark_text,
            highlightbackground="#dc2626",
            highlightcolor="#dc2626",
            highlightthickness=2,
            relief="sunken",
            bd=2
        )
        self.mood_entry.grid(row=1, column=1, padx=(0, 18), pady=5, sticky="w")

        tk.Label(input_frame, text="Notes:", font=("Arial", 12, "bold"), bg=input_bg, fg=dark_text).grid(
            row=1, column=2, padx=(0, 8), pady=5, sticky="w"
        )

        self.note_entry = tk.Entry(
            input_frame,
            width=50,
            font=("Arial", 12),
            textvariable=self.note_var,
            bg=field_bg,
            fg=dark_text,
            insertbackground=dark_text,
            highlightbackground="#dc2626",
            highlightcolor="#dc2626",
            highlightthickness=2,
            relief="sunken",
            bd=2
        )
        self.note_entry.grid(row=1, column=3, padx=(0, 0), pady=5, sticky="we")

        input_frame.grid_columnconfigure(3, weight=1)

        button_frame = tk.Frame(self.root, bg=page_bg)
        button_frame.pack(pady=(2, 10))

        tk.Button(button_frame, text="Add Entry", width=15, command=self.gui_add_entry, bg=button_bg, fg=button_fg, activebackground="#16a34a", activeforeground=button_fg).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Update Selected", width=15, command=self.gui_update_entry, bg=button_bg, fg=button_fg, activebackground="#16a34a", activeforeground=button_fg).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="Delete Selected", width=15, command=self.gui_delete_entry, bg=button_bg, fg=button_fg, activebackground="#16a34a", activeforeground=button_fg).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Show Statistics", width=15, command=self.gui_show_stats, bg=button_bg, fg=button_fg, activebackground="#16a34a", activeforeground=button_fg).grid(row=0, column=3, padx=5)
        tk.Button(button_frame, text="Refresh Entries", width=15, command=self.refresh_entries, bg=button_bg, fg=button_fg, activebackground="#16a34a", activeforeground=button_fg).grid(row=0, column=4, padx=5)

        self.mood_entry.focus_set()

        main_frame = tk.Frame(self.root, bg=page_bg)
        main_frame.pack(fill="both", expand=True, padx=15, pady=10)

        left_frame = tk.Frame(main_frame, bg=panel_bg, bd=2, relief="groove")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left_frame, text="Saved Entries", font=("Arial", 12, "bold"), bg=panel_bg, fg=text_fg).pack(anchor="w", padx=10, pady=10)

        list_frame = tk.Frame(left_frame, bg=panel_bg)
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
            highlightthickness=2
        )
        self.listbox.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.config(yscrollcommand=scrollbar.set)

        self.listbox.bind("<<ListboxSelect>>", self.on_select_entry)

        right_frame = tk.Frame(main_frame, bg=panel_bg, bd=2, relief="groove")
        right_frame.pack(side="left", fill="both", expand=True)

        tk.Label(right_frame, text="Entry Details", font=("Arial", 12, "bold"), bg=panel_bg, fg=text_fg).pack(anchor="w", padx=10, pady=10)

        self.details_text = tk.Text(
            right_frame,
            wrap="word",
            font=("Arial", 11),
            state="disabled",
            bg="#ecfccb",
            fg=dark_text,
            highlightbackground="#84cc16",
            highlightcolor="#84cc16",
            highlightthickness=2
        )
        self.details_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def refresh_entries(self):
        self.entries = list_entries()
        self.listbox.delete(0, tk.END)

        for index, entry in enumerate(self.entries):
            try:
                time_str = datetime.fromisoformat(entry.timestamp).strftime("%Y-%m-%d %H:%M")
            except ValueError:
                time_str = entry.timestamp

            short_note = entry.note if entry.note else "No note"
            if len(short_note) > 25:
                short_note = short_note[:25] + "..."

            self.listbox.insert(tk.END, f"{index} | Mood {entry.mood} | {time_str} | {short_note}")

        self.clear_details()

    def clear_details(self):
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, "Select an entry to view details.")
        self.details_text.config(state="disabled")

    def on_select_entry(self, event=None):
        selection = self.listbox.curselection()
        if not selection:
            return

        index = selection[0]
        entry = self.entries[index]

        try:
            time_str = datetime.fromisoformat(entry.timestamp).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            time_str = entry.timestamp

        details = (
            f"Entry Number: {index}\n\n"
            f"Mood: {entry.mood}\n"
            f"Time: {time_str}\n"
            f"Note: {entry.note or '—'}"
        )

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", tk.END)
        self.details_text.insert(tk.END, details)
        self.details_text.config(state="disabled")

        self.mood_var.set(str(entry.mood))
        self.note_var.set(entry.note)

    def gui_add_entry(self):
        try:
            mood_text = self.mood_var.get().strip()
            note = self.note_var.get().strip()

            if not mood_text:
                raise ValueError("Please enter a mood from 1 to 5 before adding an entry.")

            mood = int(mood_text)

            if not 1 <= mood <= 5:
                raise ValueError("Mood must be between 1 and 5.")

            add_entry(mood, note)
            self.refresh_entries()

            self.mood_var.set("")
            self.note_var.set("")
            self.mood_entry.focus_set()

            messagebox.showinfo("Success", "Mood entry added.", parent=self.root)

        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_update_entry(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an entry to update.", parent=self.root)
            return

        try:
            index = selection[0]
            mood_text = self.mood_var.get().strip()
            new_note = self.note_var.get().strip()

            if not mood_text:
                raise ValueError("Please enter a mood from 1 to 5 before updating an entry.")

            new_mood = int(mood_text)

            if not 1 <= new_mood <= 5:
                raise ValueError("Mood must be between 1 and 5.")

            confirm = messagebox.askyesno("Confirm Update", f"Update entry {index}?", parent=self.root)
            if not confirm:
                return

            update_entry(index, new_mood=new_mood, new_note=new_note)
            self.refresh_entries()
            messagebox.showinfo("Success", "Mood entry updated.", parent=self.root)

        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_delete_entry(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an entry to delete.", parent=self.root)
            return

        try:
            index = selection[0]

            confirm = messagebox.askyesno("Confirm Delete", f"Delete entry {index}?", parent=self.root)
            if not confirm:
                return

            delete_entry(index)
            self.refresh_entries()

            self.mood_var.set("")
            self.note_var.set("")
            self.mood_entry.focus_set()

            messagebox.showinfo("Success", "Mood entry deleted.", parent=self.root)

        except Exception as error:
            messagebox.showerror("Error", str(error), parent=self.root)

    def gui_show_stats(self):
        stats = get_mood_stats()
        if stats is None:
            messagebox.showinfo("Mood Statistics", "No entries available for statistics.", parent=self.root)
            return

        stats_text = (
            f"Total entries: {stats['count']}\n"
            f"Average mood: {stats['average']:.2f}\n"
            f"Highest mood: {stats['highest']}\n"
            f"Lowest mood: {stats['lowest']}"
        )
        messagebox.showinfo("Mood Statistics", stats_text, parent=self.root)


if __name__ == "__main__":
    root = tk.Tk()
    app = MoodTrackerApp(root)
    root.mainloop()
