# Mood Tracker

This project is a Tkinter mood tracker app that records how you feel during the day using a 1-5 scale. Entries are stored in `mood_entries.json` and can be managed through a desktop GUI.

## Current Features

- Add, update, delete, and list mood entries
- View entry details with formatted timestamps
- Show overall mood statistics
- Search entries by note text
- Filter entries by mood range
- Filter entries by date range
- Clear the input fields
- Export entries to CSV
- Show only today's entries
- Edit only the note for an existing entry
- Duplicate an existing entry with a new timestamp
- Show the most common mood and a simple mood trend summary

## Files

- `mood_tracker_gui.py`: main application code and GUI
- `mood_entries.json`: stored mood data
- `mood_entries_export.csv`: generated when entries are exported

## Running the App

Run the GUI from the project folder:

```bash
python3 mood_tracker_gui.py
```

## Notes

- Mood values must be integers from 1 to 5.
- Date filters use the format `YYYY-MM-DD`.
- Exported CSV files are written to the project folder by default.
