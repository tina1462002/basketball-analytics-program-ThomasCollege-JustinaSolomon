import tkinter as tk
from tkinter import messagebox

# Sample Player class to store player data
class Player:
    def __init__(self, name):
        self.name = name
        self.shots_made = 0
        self.shots_missed = 0
        self.assists = 0
        self.turnovers = 0
        self.rebounds = 0
        self.points = 0
        self.paint_touches = 0
        self.contested_shots = 0
        self.uncontested_shots = 0
        self.defensive_stats = {'Contested': {'Missed': 0, 'Made': 0}, 'Uncontested': {'Missed': 0, 'Made': 0}}

    def add_shot(self, made=True, shot_type='layup', contested=False):
        if made:
            self.shots_made += 1
            self.points += 2 if shot_type != '3pt' else 3
        else:
            self.shots_missed += 1

        if contested:
            self.contested_shots += 1
        else:
            self.uncontested_shots += 1

    def add_assist(self):
        self.assists += 1

    def add_turnover(self):
        self.turnovers += 1

    def add_rebound(self):
        self.rebounds += 1

    def add_paint_touch(self, made_shot=False):
        self.paint_touches += 1
        if made_shot:
            self.points += 2

    def calc_per(self):
        # Simplified PER (Player Efficiency Rating)
        per = (self.points + self.rebounds + self.assists + self.shots_made) / (self.shots_made + self.shots_missed + self.turnovers + 1)
        return per

    def calc_ts(self):
        # True Shooting Percentage (simplified)
        total_shots = self.shots_made + self.shots_missed
        ts = self.shots_made / (total_shots + self.points)
        return ts

    def calc_assist_to_turnover_ratio(self):
        if self.turnovers == 0:
            return self.assists  # If no turnovers, assume infinite A/T ratio
        return self.assists / self.turnovers

    def calc_usage_rate(self):
        # Usage Rate (simplified)
        usage = (self.shots_made + self.assists) / (self.shots_made + self.shots_missed + self.assists + 1)
        return usage

    def calc_bpm(self):
        # Box Plus-Minus (simplified)
        bpm = (self.points + self.rebounds + self.assists) / 100  # Just a rough estimate
        return bpm


class BasketballStatsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Basketball Analytics")

        self.players = {}  # Store player objects by name

        self.create_widgets()

    def create_widgets(self):
        self.label_name = tk.Label(self.root, text="Enter Player Name:")
        self.label_name.grid(row=0, column=0)

        self.entry_name = tk.Entry(self.root)
        self.entry_name.grid(row=0, column=1)

        self.add_player_button = tk.Button(self.root, text="Add Player", command=self.add_player)
        self.add_player_button.grid(row=0, column=2)

        self.label_shot = tk.Label(self.root, text="Enter Shot Result (made/missed):")
        self.label_shot.grid(row=1, column=0)

        self.entry_shot = tk.Entry(self.root)
        self.entry_shot.grid(row=1, column=1)

        self.shot_button = tk.Button(self.root, text="Add Shot", command=self.add_shot)
        self.shot_button.grid(row=1, column=2)

        self.label_report = tk.Label(self.root, text="Player Report:")
        self.label_report.grid(row=2, column=0)

        self.report_button = tk.Button(self.root, text="Generate Report", command=self.generate_report)
        self.report_button.grid(row=2, column=1)

    def add_player(self):
        name = self.entry_name.get()
        if name:
            self.players[name] = Player(name)
            messagebox.showinfo("Info", f"Player {name} added!")
        else:
            messagebox.showwarning("Warning", "Please enter a player name.")

    def add_shot(self):
        name = self.entry_name.get()
        result = self.entry_shot.get()
        if name in self.players:
            if result == 'made':
                self.players[name].add_shot(made=True)
            elif result == 'missed':
                self.players[name].add_shot(made=False)
            else:
                messagebox.showwarning("Warning", "Invalid shot result.")
            messagebox.showinfo("Info", f"Shot added for {name}!")
        else:
            messagebox.showwarning("Warning", "Player not found!")

    def generate_report(self):
        report = ""
        for name, player in self.players.items():
            report += f"--- {name} ---\n"
            report += f"PER: {player.calc_per()}\n"
            report += f"TS%: {player.calc_ts()}\n"
            report += f"A/T Ratio: {player.calc_assist_to_turnover_ratio()}\n"
            report += f"Usage Rate: {player.calc_usage_rate()}\n"
            report += f"BPM: {player.calc_bpm()}\n\n"
        
        messagebox.showinfo("Player Report", report)

# Run the app
root = tk.Tk()
app = BasketballStatsApp(root)
root.mainloop()
