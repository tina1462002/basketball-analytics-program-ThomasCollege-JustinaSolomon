import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import csv

class Player:
    def __init__(self, name):
        self.name = name
        self.shots = {
            'layup': {'made': 0, 'missed': 0, 'contested_made': 0, 'contested_missed': 0},
            'midrange': {'made': 0, 'missed': 0, 'contested_made': 0, 'contested_missed': 0},
            '3pt': {'made': 0, 'missed': 0, 'contested_made': 0, 'contested_missed': 0}
        }
        self.points = 0
        self.strike_zone = {
            'balls': {'total': 0, 'made': 0, 'missed': 0},
            'strikes': {'total': 0, 'made': 0, 'missed': 0}
        }
        self.cuts = {
            'total': 0,
            'pass_to_cutter': 0,
            'made_shot': 0,
            'missed_shot': 0
        }
        self.paint_touches = {
            'total': 0,
            'made': 0,
            'missed': 0,
            'kick': 0
        }
        self.defense = {
            'contested': {'made': 0, 'missed': 0},
            'uncontested': {'made': 0, 'missed': 0}
        }
        self.event_history = []
        self.games_played = 1  # Add this line

    def add_shot(self, shot_type, made, contested=False):
        if made:
            self.shots[shot_type]['made'] += 1
            self.points += 3 if shot_type == '3pt' else 2
            if contested:
                self.shots[shot_type]['contested_made'] += 1
        else:
            self.shots[shot_type]['missed'] += 1
            if contested:
                self.shots[shot_type]['contested_missed'] += 1

    def add_strike_zone_pass(self, made):
        self.strike_zone['balls']['total'] += 1
        if made:
            self.strike_zone['balls']['made'] += 1
            self.points += 2
        else:
            self.strike_zone['balls']['missed'] += 1

    def add_cut(self, pass_to_cutter, shot_made):
        self.cuts['total'] += 1
        if pass_to_cutter:
            self.cuts['pass_to_cutter'] += 1
        if shot_made:
            self.cuts['made_shot'] += 1
            self.points += 2
        else:
            self.cuts['missed_shot'] += 1

    def add_paint_touch(self, made, kick=False):
        self.paint_touches['total'] += 1
        if made:
            self.paint_touches['made'] += 1
            self.points += 2
        else:
            self.paint_touches['missed'] += 1
        if kick:
            self.paint_touches['kick'] += 1

    def add_defense(self, contested, made):
        if contested:
            self.defense['contested']['made' if made else 'missed'] += 1
        else:
            self.defense['uncontested']['made' if made else 'missed'] += 1

class BasketballApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Basketball Analytics")
        self.players = {}
        self.load_data()
        self.create_ui()

    def create_ui(self):
        # Create main frames
        left_frame = ttk.Frame(self.root, padding="5")
        left_frame.grid(row=0, column=0, sticky="nsew")
        
        right_frame = ttk.Frame(self.root, padding="5")
        right_frame.grid(row=0, column=1, sticky="nsew")

        # Left side: Player list and controls
        ttk.Label(left_frame, text="Players").grid(row=0, column=0, sticky="w")
        self.player_list = tk.Listbox(left_frame, width=30, height=15)
        self.player_list.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.player_list.bind('<<ListboxSelect>>', self.on_player_select)

        # Control buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        
        ttk.Button(btn_frame, text="Add Player", command=self.add_player_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self.delete_player).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Undo", command=self.undo_last).pack(side=tk.LEFT, padx=2)

        # Event recording
        ttk.Button(left_frame, text="Record Event", 
                  command=self.show_event_dialog).grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

        # Right side: Stats display
        self.stats_text = tk.Text(right_frame, width=50, height=30)
        self.stats_text.grid(row=0, column=0, sticky="nsew")
        
        # Team stats
        self.team_stats_var = tk.StringVar(value="Team Stats: 0%")
        ttk.Label(right_frame, textvariable=self.team_stats_var, 
                 font=('Helvetica', 12, 'bold')).grid(row=1, column=0, sticky="w", pady=5)

        self.update_player_list()

    def show_event_dialog(self):
        if not self.get_selected_player():
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Record Event")
        
        # Create category buttons
        categories = [
            ("Offensive", [
                ("Strike Zone Pass", self.show_strike_dialog),
                ("Cut", self.show_cut_dialog),
                ("Shot", self.show_shot_dialog)
            ]),
            ("Defensive", [
                ("Paint Touch Defense", self.show_paint_defense_dialog),
                ("Contest Defense", self.show_contest_dialog)
            ])
        ]
        
        for cat_name, events in categories:
            frame = ttk.LabelFrame(dialog, text=cat_name)
            frame.pack(fill="x", padx=5, pady=5)
            
            for event_name, command in events:
                ttk.Button(frame, text=event_name, 
                          command=lambda cmd=command: cmd(dialog)).pack(fill="x", padx=5, pady=2)

    def show_strike_dialog(self, parent):
        dialog = tk.Toplevel(parent)
        dialog.title("Record Strike Zone Pass")
        
        tk.Label(dialog, text="Result:").pack(pady=5)
        ttk.Button(dialog, text="Made", 
                  command=lambda: self.record_strike_zone_pass(dialog, True)).pack(fill='x', padx=20, pady=2)
        ttk.Button(dialog, text="Missed", 
                  command=lambda: self.record_strike_zone_pass(dialog, False)).pack(fill='x', padx=20, pady=2)

    def show_cut_dialog(self, parent):
        dialog = tk.Toplevel(parent)
        dialog.title("Record Cut")
        
        tk.Label(dialog, text="Pass to Cutter?").pack(pady=5)
        ttk.Button(dialog, text="Yes", 
                  command=lambda: self.record_cut(dialog, True)).pack(fill='x', padx=20, pady=2)
        ttk.Button(dialog, text="No", 
                  command=lambda: self.record_cut(dialog, False)).pack(fill='x', padx=20, pady=2)

    def show_shot_dialog(self, parent):
        dialog = tk.Toplevel(parent)
        dialog.title("Record Shot")
        
        # Shot type buttons
        tk.Label(dialog, text="Shot Type:").pack(pady=5)
        for shot_type in ['Layup', 'Midrange', '3pt']:
            ttk.Button(dialog, text=shot_type, 
                     command=lambda t=shot_type: self.show_shot_result(dialog, t.lower())).pack(fill='x', padx=20, pady=2)

    def show_shot_result(self, parent, shot_type):
        dialog = tk.Toplevel(parent)
        dialog.title("Shot Result")
        
        tk.Button(dialog, text="Made", 
                 command=lambda: self.record_shot(dialog, shot_type, True)).pack(fill='x', padx=20, pady=2)
        tk.Button(dialog, text="Missed", 
                 command=lambda: self.record_shot(dialog, shot_type, False)).pack(fill='x', padx=20, pady=2)

    def show_paint_defense_dialog(self, parent):
        dialog = tk.Toplevel(parent)
        dialog.title("Record Paint Touch Defense")
        
        tk.Label(dialog, text="Result:").pack(pady=5)
        ttk.Button(dialog, text="Made Shot", 
                 command=lambda: self.record_paint_touch_defense(dialog, True)).pack(fill='x', padx=20, pady=2)
        ttk.Button(dialog, text="Missed Shot", 
                 command=lambda: self.record_paint_touch_defense(dialog, False)).pack(fill='x', padx=20, pady=2)

    def show_contest_dialog(self, parent):
        dialog = tk.Toplevel(parent)
        dialog.title("Record Contest Defense")
        
        tk.Label(dialog, text="Result:").pack(pady=5)
        ttk.Button(dialog, text="Made", 
                 command=lambda: self.record_defense(dialog, True, contested=True)).pack(fill='x', padx=20, pady=2)
        ttk.Button(dialog, text="Missed", 
                 command=lambda: self.record_defense(dialog, False, contested=True)).pack(fill='x', padx=20, pady=2)
        ttk.Button(dialog, text="Uncontested Made", 
                 command=lambda: self.record_defense(dialog, True, contested=False)).pack(fill='x', padx=20, pady=2)
        ttk.Button(dialog, text="Uncontested Missed", 
                 command=lambda: self.record_defense(dialog, False, contested=False)).pack(fill='x', padx=20, pady=2)

    def record_strike_zone_pass(self, dialog, made):
        player = self.get_selected_player()
        if player:
            player.add_strike_zone_pass(made)
            self.save_data()
            dialog.master.destroy()  # Close both dialogs
            messagebox.showinfo("Success", f"Strike zone pass recorded for {player.name}")

    def record_cut(self, dialog, pass_to_cutter):
        player = self.get_selected_player()
        if player:
            player.add_cut(pass_to_cutter, False)  # Shot made is False by default
            self.save_data()
            dialog.master.destroy()
            messagebox.showinfo("Success", f"Cut recorded for {player.name}")

    def record_shot(self, dialog, shot_type, made):
        player = self.get_selected_player()
        if player:
            player.add_shot(shot_type, made)
            dialog.master.destroy()  # Close both dialogs
            messagebox.showinfo("Success", f"Shot recorded for {player.name}")

    def record_paint_touch_defense(self, dialog, made):
        player = self.get_selected_player()
        if player:
            player.add_paint_touch(made)
            self.save_data()
            dialog.master.destroy()
            messagebox.showinfo("Success", f"Paint touch defense recorded for {player.name}")

    def record_defense(self, dialog, made, contested):
        player = self.get_selected_player()
        if player:
            player.add_defense(contested, made)
            self.save_data()
            dialog.master.destroy()
            messagebox.showinfo("Success", f"Defense recorded for {player.name}")

    def get_selected_player(self):
        selection = self.player_list.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a player first")
            return None
        name = self.player_list.get(selection[0])
        return self.players.get(name)

    def update_player_list(self):
        self.player_list.delete(0, tk.END)
        for name in sorted(self.players.keys()):
            self.player_list.insert(tk.END, name)

    def update_stats_display(self):
        player = self.get_selected_player()
        if not player:
            self.stats_text.delete('1.0', tk.END)
            return
        
        # Calculate total shots and percentages
        total_shots = sum(sum(v.values()) for shot_type in player.shots.values() for v in shot_type.values())
        made_shots = sum(v['made'] + v['contested_made'] for v in player.shots.values())
        
        stats = f"""Stats for {player.name}

Offensive Stats:
---------------
Total Points: {player.points}
Total Shots: {total_shots}
Made Shots: {made_shots}
Shooting %: {(made_shots/total_shots*100 if total_shots > 0 else 0):.1f}%

Shot Details:
Layups: {player.shots['layup']['made'] + player.shots['layup']['contested_made']} / {sum(player.shots['layup'].values())}
Midrange: {player.shots['midrange']['made'] + player.shots['midrange']['contested_made']} / {sum(player.shots['midrange'].values())}
3PT: {player.shots['3pt']['made'] + player.shots['3pt']['contested_made']} / {sum(player.shots['3pt'].values())}

Strike Zone:
Balls: {player.strike_zone['balls']['total']} (Made: {player.strike_zone['balls']['made']})
Strikes: {player.strike_zone['strikes']['total']} (Made: {player.strike_zone['strikes']['made']})

Cuts: {player.cuts['total']}
- Pass to Cutter: {player.cuts['pass_to_cutter']}
- Made Shots: {player.cuts['made_shot']}
- Missed Shots: {player.cuts['missed_shot']}

Defensive Stats:
--------------
Paint Touches: {player.paint_touches['total']}
- Made: {player.paint_touches['made']}
- Missed: {player.paint_touches['missed']}
- Kick Out: {player.paint_touches['kick']}

Defense:
Contested: {player.defense['contested']['made'] + player.defense['contested']['missed']}
- Made: {player.defense['contested']['made']}
- Missed: {player.defense['contested']['missed']}
Uncontested: {player.defense['uncontested']['made'] + player.defense['uncontested']['missed']}
- Made: {player.defense['uncontested']['made']}
- Missed: {player.defense['uncontested']['missed']}
"""
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats)
        
        # Update team stats
        self.update_team_stats()

    def update_team_stats(self):
        total_points = sum(player.points for player in self.players.values())
        total_games = sum(player.games_played for player in self.players.values())
        avg_points = total_points / total_games if total_games > 0 else 0
        self.team_stats_var.set(f"Team Stats: {avg_points:.1f} PPG")

    def save_data(self):
        try:
            data = {name: vars(player) for name, player in self.players.items()}
            with open('basketball_data.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save data: {e}")

    def load_data(self):
        try:
            if os.path.exists('basketball_data.json'):
                with open('basketball_data.json', 'r') as f:
                    data = json.load(f)
                    for name, attrs in data.items():
                        player = Player(name)
                        for key, value in attrs.items():
                            setattr(player, key, value)
                        self.players[name] = player
        except Exception as e:
            messagebox.showerror("Error", f"Could not load data: {e}")

    def export_csv(self):
        player = self.get_selected_player()
        if not player:
            return
        
        filename = filedialog.asksaveasfilename(defaultextension=".csv", 
                                                  filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if not filename:
            return
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                fieldnames = ['Event', 'Detail', 'Result']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for event in player.event_history:
                    writer.writerow(event)
            
            messagebox.showinfo("Success", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not export data: {e}")

    def undo_last(self):
        player = self.get_selected_player()
        if player and player.event_history:
            last_event = player.event_history.pop()
            self.save_data()
            self.update_stats_display()
            messagebox.showinfo("Success", "Last event undone")
        else:
            messagebox.showwarning("Warning", "No event to undo")

    def on_player_select(self, event):
        """Update the stats display when a player is selected"""
        self.update_stats_display()

    def add_player_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Player")
        dialog.geometry("300x100")
        
        tk.Label(dialog, text="Player Name:").pack(pady=5)
        entry = tk.Entry(dialog)
        entry.pack(pady=5)
        
        def add():
            name = entry.get().strip()
            if not name:
                messagebox.showwarning("Warning", "Please enter a name")
                return
            if name in self.players:
                messagebox.showwarning("Warning", "Player already exists")
                return
            self.players[name] = Player(name)
            self.save_data()
            self.update_player_list()
            dialog.destroy()
            self.update_stats_display()
        
        tk.Button(dialog, text="Add", command=add).pack(pady=5)

    def delete_player(self):
        player = self.get_selected_player()
        if not player:
            return
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {player.name}?"):
            del self.players[player.name]
            self.save_data()
            self.update_player_list()
            self.update_stats_display()

if __name__ == '__main__':
    root = tk.Tk()
    app = BasketballApp(root)
    root.mainloop()
