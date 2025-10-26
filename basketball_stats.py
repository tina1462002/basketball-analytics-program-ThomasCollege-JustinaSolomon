import tkinter as tk
from tkinter import ttk, messagebox
import json
from collections import defaultdict
import os

class Player:
    def __init__(self, name):
        self.name = name
        self.shots = defaultdict(lambda: {'made': 0, 'missed': 0})
        self.assists = 0
        self.turnovers = 0
        self.rebounds = 0
        self.points = 0

    def record_shot(self, shot_type, made):
        if made:
            self.shots[shot_type]['made'] += 1
            self.points += 3 if shot_type == '3pt' else 2
        else:
            self.shots[shot_type]['missed'] += 1

    def shots_made(self):
        return sum(v['made'] for v in self.shots.values())

    def shots_missed(self):
        return sum(v['missed'] for v in self.shots.values())

    def total_shots(self):
        return self.shots_made() + self.shots_missed()

    def calc_percentage(self):
        total = self.total_shots()
        if total == 0:
            return 0
        return round((self.shots_made() / total) * 100, 1)

class BasketballApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Basketball Stats Tracker")
        self.team = {}
        self.load_data()
        self.setup_gui()

    def setup_gui(self):
        # Player List
        self.player_frame = ttk.Frame(self.root, padding="10")
        self.player_frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(self.player_frame, text="Players").grid(row=0, column=0)
        self.player_list = tk.Listbox(self.player_frame, height=10)
        self.player_list.grid(row=1, column=0, pady=5)
        self.update_player_list()

        # Controls
        controls = ttk.Frame(self.player_frame)
        controls.grid(row=2, column=0, pady=5)

        ttk.Button(controls, text="Add Player", command=self.add_player).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="Remove Player", command=self.remove_player).pack(side=tk.LEFT, padx=2)

        # Stats Frame
        stats = ttk.LabelFrame(self.root, text="Record Stats", padding="10")
        stats.grid(row=0, column=1, padx=10, sticky="nsew")

        # Shot buttons
        ttk.Button(stats, text="Made 2PT", command=lambda: self.record_shot('2pt', True)).grid(row=0, column=0, pady=2)
        ttk.Button(stats, text="Missed 2PT", command=lambda: self.record_shot('2pt', False)).grid(row=0, column=1, pady=2)
        ttk.Button(stats, text="Made 3PT", command=lambda: self.record_shot('3pt', True)).grid(row=1, column=0, pady=2)
        ttk.Button(stats, text="Missed 3PT", command=lambda: self.record_shot('3pt', False)).grid(row=1, column=1, pady=2)

        # Other stats
        ttk.Button(stats, text="Assist", command=lambda: self.record_stat('assists')).grid(row=2, column=0, pady=2)
        ttk.Button(stats, text="Turnover", command=lambda: self.record_stat('turnovers')).grid(row=2, column=1, pady=2)
        ttk.Button(stats, text="Rebound", command=lambda: self.record_stat('rebounds')).grid(row=3, column=0, pady=2)

        # Team percentage
        self.team_pct = ttk.Label(self.root, text="Team: 0%")
        self.team_pct.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.update_team_percentage()

    def add_player(self):
        name = tk.simpledialog.askstring("Add Player", "Enter player name:")
        if name:
            if name not in self.team:
                self.team[name] = Player(name)
                self.update_player_list()
                self.save_data()
            else:
                messagebox.showerror("Error", "Player already exists!")

    def remove_player(self):
        selection = self.player_list.curselection()
        if selection:
            name = self.player_list.get(selection[0])
            if messagebox.askyesno("Confirm", f"Remove {name}?"):
                del self.team[name]
                self.update_player_list()
                self.save_data()

    def record_shot(self, shot_type, made):
        selection = self.player_list.curselection()
        if selection:
            name = self.player_list.get(selection[0])
            self.team[name].record_shot(shot_type, made)
            self.save_data()
            self.update_team_percentage()

    def record_stat(self, stat):
        selection = self.player_list.curselection()
        if selection:
            name = self.player_list.get(selection[0])
            setattr(self.team[name], stat, getattr(self.team[name], stat) + 1)
            self.save_data()
            self.update_team_percentage()

    def update_player_list(self):
        self.player_list.delete(0, tk.END)
        for name in sorted(self.team.keys()):
            self.player_list.insert(tk.END, name)

    def update_team_percentage(self):
        if not self.team:
            pct = 0
        else:
            total_pct = sum(player.calc_percentage() for player in self.team.values())
            pct = total_pct / len(self.team)
        self.team_pct.config(text=f"Team: {pct:.1f}%")

    def save_data(self):
        data = {}
        for name, player in self.team.items():
            data[name] = {
                'shots': dict(player.shots),
                'assists': player.assists,
                'turnovers': player.turnovers,
                'rebounds': player.rebounds,
                'points': player.points
            }
        with open('basketball_data.json', 'w') as f:
            json.dump(data, f)

    def load_data(self):
        try:
            with open('basketball_data.json', 'r') as f:
                data = json.load(f)
                for name, stats in data.items():
                    player = Player(name)
                    player.shots = defaultdict(lambda: {'made': 0, 'missed': 0})
                    # Handle shots data with default empty dict if missing
                    for shot_type, counts in stats.get('shots', {}).items():
                        player.shots[shot_type] = counts
                    # Use get() with default values for other stats
                    player.assists = stats.get('assists', 0)
                    player.turnovers = stats.get('turnovers', 0)
                    player.rebounds = stats.get('rebounds', 0)
                    player.points = stats.get('points', 0)
                    self.team[name] = player
        except FileNotFoundError:
            pass

if __name__ == '__main__':
    root = tk.Tk()
    app = BasketballApp(root)
    root.mainloop()
