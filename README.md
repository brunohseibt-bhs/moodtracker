This assignment is completely fresh. For my other assignment I made a mistake and created a function that has no relation with the mood tracker. So I started again. 

This project is to create an app that will work as a mood tracker. Recording, listing, adding and deleting moods based on a numerical scale of "how I feel during the day".

That being said the first part of this project was focused on creating the timeline of the app which started according to CoPilot and ChatGPT with the mood_entries function. (I considered this the first part of the assignemnt that I should have done for the past assignment. 

The second part, assignment 5 consists in continuing the function based on my development timeline. For this interaction with my AI agent I asked it to create the menu and to make it interactive. Which it did correctly. The next steps is for it to create a window and run out of the IDE terminal. 


Assignment 6A 

ChatGPT wanted to start improving its own code. I asked it not to improve/optimize anything and work on the next feature. I left all optimization for github CoPilot. 

At this run we added a new function to get all my mood statistics and to implement a GUI for better visibility/user experience. 

I prompted GitHub CoPilot identify and fix any bugs in the code. It corrected the tyoe checking in MoodEntry. According to Copilot the method only checked if the mood value was within the range 1-5, but didn't verify it was an integer and that this could cause a TypeError. It also found another error in the load_entries function. Where the function didn't handle cases where the JSON file was corrupted or contained invalid entry data. 

Copilot's words: "The changes ensure the application is more robust against data corruption or manual JSON edits."

Next I prompted it to explain logic, suggest fixes, and identify edge cases. It almost gabe me a book of suggestions. So I asked it to give me the 3 most important ones to ensure the app runs for the time being. 

1. Add Error Handling to save_entries: Currently, if the JSON file cannot be written (e.g., due to permissions or disk space), the app crashes. Wrap the file write in a try-except block and show a user-friendly error message via messagebox.showerror. This prevents data loss and improves robustness.

2. Format Timestamps for Better Readability: The raw ISO timestamps in the display are hard to read. In format_entries, parse and format them (e.g., using datetime.fromisoformat(entry.timestamp).strftime("%Y-%m-%d %H:%M")). This enhances user experience without changing data storage.

3. Add Confirmation Dialogs for Destructive Actions: For updates and deletes, add a confirmation step (e.g., messagebox.askyesno) before proceeding. This prevents accidental data changes and aligns with common GUI best practices.

I asked Copilot to implement those suggestions and to only comment out the existing code and not to delete anything. I then ran it and it broke my app. It doesn't let me make any inputs. So I asked it to fix my app. 

Quick update after 30 minutes trying to get the app to work again. Its not letting me add any input. And I didnt push it to github after it started working. I just kept playing with it. Now I cant make it work and cant go back to the other version that was working. Lesson learned there. 

Now I think I fixed it and also asked it to implement CLEAR. I'll be using the same repository link for both 6A and 6B

Quick update after 30 mins of trying. It works. Color scheme was changed and the biggest issue was how I was running the GUI. All good now. 

