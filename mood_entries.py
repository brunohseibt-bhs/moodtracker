from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import os

# File where data will be stored
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
        if not 1 <= self.mood <= 5:
            raise ValueError("Mood must be between 1 and 5.")


# =========================
# File Operations
# =========================
def load_entries(filename=DATA_FILE):
    if not os.path.exists(filename):
        return []

    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    return [MoodEntry(**entry) for entry in data]


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


# =========================
# Interactive Menu
# =========================

def clear_screen():
    print("\n" * 3)


def print_menu():
    print("==============================")
    print("Mood Tracker")
    print("==============================")
    print("1. Add mood entry")
    print("2. List mood entries")
    print("3. Update mood entry")
    print("4. Delete mood entry")
    print("5. Quit")
    print("==============================")


def prompt_int(prompt, min_value=None, max_value=None, allow_empty=False):
    while True:
        value = input(prompt).strip()

        if allow_empty and value == "":
            return None

        if not value.isdigit():
            print("Please enter a valid number.")
            continue

        value_int = int(value)
        if min_value is not None and value_int < min_value:
            print(f"Please enter a number greater than or equal to {min_value}.")
            continue
        if max_value is not None and value_int > max_value:
            print(f"Please enter a number less than or equal to {max_value}.")
            continue

        return value_int


def prompt_text(prompt, default=None):
    value = input(prompt).rstrip()
    if value == "" and default is not None:
        return default
    return value


def display_entries(entries):
    if not entries:
        print("No mood entries found.")
        return

    print("\nSaved mood entries:")
    print("------------------------------")
    for index, entry in enumerate(entries):
        print(f"{index}. Mood: {entry.mood} | Note: {entry.note or '—'} | Time: {entry.timestamp}")
    print("------------------------------")


def handle_add():
    print("\nAdd a new mood entry")
    mood = prompt_int("Enter mood (1-5): ", min_value=1, max_value=5)
    note = input("Add a note (optional): ").strip()

    try:
        entry = add_entry(mood, note)
        print(f"Entry added: Mood {entry.mood} - {entry.note or 'No note'}")
    except ValueError as error:
        print(f"Error: {error}")


def handle_list():
    entries = list_entries()
    display_entries(entries)


def handle_update():
    entries = list_entries()
    if not entries:
        print("No entries available to update.")
        return

    display_entries(entries)
    index = prompt_int("Enter the entry number to update: ", min_value=0, max_value=len(entries) - 1)
    selected = entries[index]

    print(f"Current mood: {selected.mood}, note: {selected.note or '—'}")
    new_mood = prompt_int("New mood (1-5, leave blank to keep current): ", min_value=1, max_value=5, allow_empty=True)
    new_note = prompt_text("New note (leave blank to keep current): ", default=selected.note)

    if new_mood is None:
        new_mood = selected.mood

    try:
        updated = update_entry(index, new_mood=new_mood, new_note=new_note)
        print(f"Updated entry {index}: Mood {updated.mood}, Note: {updated.note or 'No note'}")
    except (IndexError, ValueError) as error:
        print(f"Error: {error}")


def handle_delete():
    entries = list_entries()
    if not entries:
        print("No entries available to delete.")
        return

    display_entries(entries)
    index = prompt_int("Enter the entry number to delete: ", min_value=0, max_value=len(entries) - 1)
    confirm = input(f"Delete entry {index}? Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("Delete cancelled.")
        return

    try:
        removed = delete_entry(index)
        print(f"Deleted entry {index}: Mood {removed.mood}, Note: {removed.note or 'No note'}")
    except IndexError as error:
        print(f"Error: {error}")


def main():
    while True:
        clear_screen()
        print_menu()
        choice = prompt_int("Choose an action: ", min_value=1, max_value=5)

        if choice == 1:
            handle_add()
        elif choice == 2:
            handle_list()
        elif choice == 3:
            handle_update()
        elif choice == 4:
            handle_delete()
        elif choice == 5:
            print("Goodbye!")
            break

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()