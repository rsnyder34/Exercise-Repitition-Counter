import customtkinter as ctk
import json
import os

AVAILABLE_EXERCISES = [
    "Bicep Curls",
    "Squats",
    "Kettlebell Swings",
    "Push-ups",
    "Walking",
    "Running"
]

FILE_PATH = "saved_plans.json"

class PlanBuilderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Workout Plan Builder")
        self.geometry("450x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.current_sequence = []

        # UI
        title_label = ctk.CTkLabel(self, text="Create New Workout Plan", font=("Arial", 24, "bold"))
        title_label.pack(pady=(20, 10))

        # Routine name
        self.plan_name_entry = ctk.CTkEntry(self, placeholder_text="Plan Name (e.g., Heavy Leg Day)", width=300, font=("Arial", 16))
        self.plan_name_entry.pack(pady=10)

        # Exercise select
        self.exercise_dropdown = ctk.CTkOptionMenu(self, values=AVAILABLE_EXERCISES, width=300, font=("Arial", 16))
        self.exercise_dropdown.pack(pady=10)

        # Target Reps/Steps
        self.target_entry = ctk.CTkEntry(self, placeholder_text="Target Reps or Steps (e.g., 25)", width=300, font=("Arial", 16))
        self.target_entry.pack(pady=10)

        # Add Button
        self.add_btn = ctk.CTkButton(self, text="Add to Sequence", command=self.add_to_sequence, width=300, font=("Arial", 16))
        self.add_btn.pack(pady=10)

        # Live Display of the Circuit
        self.display_box = ctk.CTkTextbox(self, width=350, height=150, font=("Arial", 14))
        self.display_box.pack(pady=10)
        self.display_box.insert("end", "Current Sequence:\n------------------\n")
        self.display_box.configure(state="disabled") # read-only

        # Save
        self.save_btn = ctk.CTkButton(self, text="Save to JSON", command=self.save_plan, width=300, fg_color="#1DB954", font=("Arial", 16, "bold"))
        self.save_btn.pack(pady=15)
        
        # Status
        self.status_label = ctk.CTkLabel(self, text="", text_color="gray", font=("Arial", 14))
        self.status_label.pack(pady=5)

    def add_to_sequence(self):
        exercise = self.exercise_dropdown.get()
        target_str = self.target_entry.get()

        if not target_str.isdigit() or int(target_str) <= 0:
            self.status_label.configure(text="Error: Target must be a positive number.", text_color="red")
            return

        target = int(target_str)
        
        # Add to local list
        self.current_sequence.append({"exercise": exercise, "target": target})

        # Update
        self.display_box.configure(state="normal")
        self.display_box.insert("end", f"[{len(self.current_sequence)}] {exercise} - {target} Reps/Steps\n")
        self.display_box.configure(state="disabled")

        # Clear
        self.target_entry.delete(0, 'end')
        self.status_label.configure(text="Exercise added.", text_color="gray")

    def save_plan(self):
        plan_name = self.plan_name_entry.get().strip()

        if not plan_name:
            self.status_label.configure(text="Error: Please enter a Plan Name.", text_color="red")
            return
        
        if not self.current_sequence:
            self.status_label.configure(text="Error: Cannot save an empty sequence.", text_color="red")
            return

        # Load existing plans or create empty dictionary
        if os.path.exists(FILE_PATH):
            try:
                with open(FILE_PATH, "r") as f:
                    plans = json.load(f)
            except json.JSONDecodeError:
                plans = {} # File exists but empty
        else:
            plans = {}

        # Add/overwrite plan
        plans[plan_name] = self.current_sequence

        # Write back to file
        with open(FILE_PATH, "w") as f:
            json.dump(plans, f, indent=4)

        self.status_label.configure(text=f"Success! '{plan_name}' saved.", text_color="#1DB954")
        
        # Reset
        self.current_sequence = []
        self.plan_name_entry.delete(0, 'end')
        self.display_box.configure(state="normal")
        self.display_box.delete("1.0", "end")
        self.display_box.insert("end", "Current Sequence:\n------------------\n")
        self.display_box.configure(state="disabled")

if __name__ == "__main__":
    app = PlanBuilderApp()
    app.mainloop()