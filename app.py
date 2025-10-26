import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from collections import defaultdict
import json
import csv
import os
from io import StringIO
import atexit  # added

# Use a persistent per-user data directory (works with PyInstaller too)
DATA_DIR = os.path.join(os.path.expanduser("~"), ".basketball_analytics_programjs")
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "basketball_data.json")


class Player:
    def __init__(self, name):
        self.name = name
        self.shots = defaultdict(lambda: {"made": 0, "missed": 0, "contested_made": 0, "contested_missed": 0})
        self.assists = 0
        self.turnovers = 0
        self.rebounds = 0
        self.points = 0
        # --- new tracking fields ---
        self.strike_zone = {"balls": 0, "strikes": 0, "ball_made": 0, "ball_missed": 0, "strike_made": 0, "strike_missed": 0}
        self.cuts = {"total": 0, "pass_to_cutter": 0, "made_shot": 0, "missed_shot": 0}
        self.paint_touches = {"total": 0, "made_shot": 0, "missed_shot": 0, "kick_out": 0}
        self.defense = {"contested_made": 0, "contested_missed": 0, "uncontested_made": 0, "uncontested_missed": 0}

    def record_shot(self, shot_type, made, contested=False):
        shot = self.shots[shot_type]
        if made:
            shot["made"] += 1
            if shot_type == "3pt":
                self.points += 3
            else:
                self.points += 2
            if contested:
                shot["contested_made"] += 1
        else:
            shot["missed"] += 1
            if contested:
                shot["contested_missed"] += 1

    # --- new recorders for requested tracking ---
    def record_strike_pass(self, kind, result):
        # kind in {"ball","strike"}; result in {"made","missed"}
        if kind == "ball":
            self.strike_zone["balls"] += 1
            if result == "made":
                self.strike_zone["ball_made"] += 1
            elif result == "missed":
                self.strike_zone["ball_missed"] += 1
        elif kind == "strike":
            self.strike_zone["strikes"] += 1
            if result == "made":
                self.strike_zone["strike_made"] += 1
            elif result == "missed":
                self.strike_zone["strike_missed"] += 1

    def record_cut(self, result):
        # result in {"pass","made","missed"}
        self.cuts["total"] += 1
        if result == "pass":
            self.cuts["pass_to_cutter"] += 1
        elif result == "made":
            self.cuts["made_shot"] += 1
        elif result == "missed":
            self.cuts["missed_shot"] += 1

    def record_paint_touch(self, result):
        # result in {"made","missed","kick"}
        self.paint_touches["total"] += 1
        if result == "made":
            self.paint_touches["made_shot"] += 1
        elif result == "missed":
            self.paint_touches["missed_shot"] += 1
        elif result == "kick":
            self.paint_touches["kick_out"] += 1

    def record_defense(self, contested, made):
        # contested bool, made bool
        if contested and made:
            self.defense["contested_made"] += 1
        elif contested and not made:
            self.defense["contested_missed"] += 1
        elif not contested and made:
            self.defense["uncontested_made"] += 1
        else:
            self.defense["uncontested_missed"] += 1

    def total_shots(self):
        return sum(v["made"] + v["missed"] for v in self.shots.values())

    def shots_made(self):
        return sum(v["made"] for v in self.shots.values())

    def shots_missed(self):
        return sum(v["missed"] for v in self.shots.values())

    def calc_per(self):
        denom = max(1, self.total_shots() + self.turnovers)
        value = (self.points + self.rebounds + self.assists - self.turnovers) / denom * 15
        return round(value, 2)

    def calc_ts(self):
        fga = self.total_shots()
        if fga == 0:
            return 0.0
        return round(self.points / (2 * fga), 3)

    def calc_ast_to_tov(self):
        if self.turnovers == 0:
            return float(self.assists) if self.assists else 0.0
        return round(self.assists / self.turnovers, 2)

    def calc_usage(self, team_possessions):
        used = self.total_shots() + self.assists + self.turnovers
        if team_possessions <= 0:
            return 0.0
        return round(100 * used / team_possessions, 2)

    def calc_bpm(self):
        possessions = max(1, self.total_shots() + self.turnovers)
        return round((self.points + self.rebounds + self.assists) / possessions * 10, 2)

    def to_dict(self):
        return {
            "name": self.name,
            "shots": {k: dict(v) for k, v in self.shots.items()},
            "assists": self.assists,
            "turnovers": self.turnovers,
            "rebounds": self.rebounds,
            "points": self.points,
            # include new fields
            "strike_zone": dict(self.strike_zone),
            "cuts": dict(self.cuts),
            "paint_touches": dict(self.paint_touches),
            "defense": dict(self.defense),
        }

    @staticmethod
    def from_dict(name, data):
        player = Player(name)
        # Merge loaded shots with default keys so missing contested_* keys are filled with 0
        for shot_type, values in (data.get("shots") or {}).items():
            player.shots[shot_type].update(values or {})
        player.assists = data.get("assists", 0)
        player.turnovers = data.get("turnovers", 0)
        player.rebounds = data.get("rebounds", 0)
        player.points = data.get("points", 0)
        # restore new fields with safe defaults
        sz = data.get("strike_zone") or {}
        player.strike_zone.update({
            "balls": sz.get("balls", 0),
            "strikes": sz.get("strikes", 0),
            "ball_made": sz.get("ball_made", 0),
            "ball_missed": sz.get("ball_missed", 0),
            "strike_made": sz.get("strike_made", 0),
            "strike_missed": sz.get("strike_missed", 0),
        })
        cuts = data.get("cuts") or {}
        player.cuts.update({
            "total": cuts.get("total", 0),
            "pass_to_cutter": cuts.get("pass_to_cutter", 0),
            "made_shot": cuts.get("made_shot", 0),
            "missed_shot": cuts.get("missed_shot", 0),
        })
        pt = data.get("paint_touches") or {}
        player.paint_touches.update({
            "total": pt.get("total", 0),
            "made_shot": pt.get("made_shot", 0),
            "missed_shot": pt.get("missed_shot", 0),
            "kick_out": pt.get("kick_out", 0),
        })
        df = data.get("defense") or {}
        player.defense.update({
            "contested_made": df.get("contested_made", 0),
            "contested_missed": df.get("contested_missed", 0),
            "uncontested_made": df.get("uncontested_made", 0),
            "uncontested_missed": df.get("uncontested_missed", 0),
        })
        return player


TEAM = {}


def get_team_possessions():
    return max(1, sum(p.total_shots() + p.assists + p.turnovers for p in TEAM.values()))


def calc_team_percentage():
    if not TEAM:
        return 0.0
    team_pos = get_team_possessions()
    scores = []
    for p in TEAM.values():
        per = min(max(p.calc_per(), 0.0), 30.0) / 30.0
        ts = min(max(p.calc_ts(), 0.0), 1.0)
        at = min(max(p.calc_ast_to_tov(), 0.0), 3.0) / 3.0
        usage = min(max(p.calc_usage(team_pos), 0.0), 40.0) / 40.0
        bpm = (min(max(p.calc_bpm(), -10.0), 10.0) + 10.0) / 20.0
        scores.append((per + ts + at + usage + bpm) / 5.0)
    return round(sum(scores) / len(scores) * 100, 1)


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as handle:
        json.dump({name: player.to_dict() for name, player in TEAM.items()}, handle, indent=2)
# Ensure we also save on normal interpreter exit (extra safety)
atexit.register(save_data)


def load_data():
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        TEAM.clear()
        for name, payload in data.items():
            TEAM[name] = Player.from_dict(name, payload)
    except (json.JSONDecodeError, OSError):
        TEAM.clear()


class BasketballApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Basketball Analytics Justina Solomon")
        self.root.geometry("1100x800")  # was 900x650
        self.root.minsize(1000, 700)    # ensure the window stays larger
        self.last_state = None

        load_data()
        self.build_layout()
        self.refresh_views()
        # Save on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_layout(self):
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)
        # Make left column steady and right column wider
        container.columnconfigure(0, weight=2, minsize=260)
        container.columnconfigure(1, weight=4, minsize=700)  # was minsize=420
        container.rowconfigure(0, weight=1)

        self.build_left_panel(container)
        self.build_right_panel(container)

    def build_left_panel(self, parent):
        left = ttk.Frame(parent, padding=(0, 0, 10, 0))
        left.grid(row=0, column=0, sticky="nsew")
        left.rowconfigure(1, weight=1)

        ttk.Label(left, text="Players", font=("Helvetica", 16, "bold")).grid(row=0, column=0, pady=(0, 8))
        self.player_list = tk.Listbox(left, height=20, exportselection=False)
        self.player_list.grid(row=1, column=0, sticky="nsew")
        self.player_list.bind("<<ListboxSelect>>", lambda _: self.refresh_views())

        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=2, column=0, pady=10, sticky="ew")
        for text, cmd in (
            ("Add Player", self.add_player),
            ("Remove Player", self.remove_player),
            ("Rename Player", self.rename_player),
            ("Export CSV", self.export_csv),
            ("Report", self.show_report),
            ("Save Now", lambda: save_data() or messagebox.showinfo("Saved", "Data saved.")),
        ):
            ttk.Button(btn_frame, text=text, command=cmd).pack(fill=tk.X, pady=2)

        self.team_score = ttk.Label(left, text="Team Score: 0.0%", font=("Helvetica", 18, "bold"), foreground="#1a73e8")
        self.team_score.grid(row=3, column=0, pady=(20, 0))

    def build_right_panel(self, parent):
        right = ttk.Frame(parent)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.columnconfigure(1, weight=0)
        right.rowconfigure(1, weight=2)  # give the stats area more vertical space
        right.rowconfigure(2, weight=1)

        self.player_title = ttk.Label(right, text="Select a Player", font=("Helvetica", 16, "bold"))
        self.player_title.grid(row=0, column=0, sticky="w", columnspan=2)

        # Larger stats area
        self.stats_box = tk.Text(right, height=20, wrap=tk.WORD, font=("Courier New", 12), state=tk.DISABLED)
        stats_scroll = ttk.Scrollbar(right, orient="vertical", command=self.stats_box.yview)
        self.stats_box.configure(yscrollcommand=stats_scroll.set)
        self.stats_box.grid(row=1, column=0, sticky="nsew", pady=8)
        stats_scroll.grid(row=1, column=1, sticky="ns", pady=8)

        # Actions organized in tabs to fit everything cleanly
        actions_nb = ttk.Notebook(right)
        actions_nb.grid(row=2, column=0, columnspan=2, sticky="nsew")

        offense_tab = ttk.Frame(actions_nb)
        defense_tab = ttk.Frame(actions_nb)
        general_tab = ttk.Frame(actions_nb)

        actions_nb.add(offense_tab, text="Offense")
        actions_nb.add(defense_tab, text="Defense")
        actions_nb.add(general_tab, text="General")

        # Helper to add buttons in a compact 2-column grid
        def add_buttons_grid(parent, buttons, cols=2):
            for c in range(cols):
                parent.columnconfigure(c, weight=1)
            for i, (label, cmd) in enumerate(buttons):
                r, c = divmod(i, cols)
                ttk.Button(parent, text=label, command=cmd).grid(row=r, column=c, padx=4, pady=6, sticky="ew")

        # Offense buttons
        add_buttons_grid(
            offense_tab,
            [
                ("Record Shot", self.record_shot_flow),
                ("Strike Pass", self.record_strike_flow),
                ("Record Cut", self.record_cut_flow),
            ],
            cols=2,
        )

        # Defense buttons
        add_buttons_grid(
            defense_tab,
            [
                ("Paint Touch", self.record_paint_flow),
                ("Defense Event", self.record_defense_flow),
            ],
            cols=2,
        )

        # General buttons
        add_buttons_grid(
            general_tab,
            [
                ("Assist", lambda: self.bump_stat("assists")),
                ("Rebound", lambda: self.bump_stat("rebounds")),
                ("Turnover", lambda: self.bump_stat("turnovers")),
                ("Edit Totals", self.edit_totals),
            ],
            cols=2,
        )
        # Put Undo as a full-width button at the bottom of General tab
        general_tab.rowconfigure(99, weight=1)
        self.undo_btn = ttk.Button(general_tab, text="Undo Last", command=self.undo_last, state=tk.DISABLED)
        self.undo_btn.grid(row=100, column=0, columnspan=2, padx=4, pady=8, sticky="ew")

    def current_player_name(self):
        selection = self.player_list.curselection()
        if not selection:
            return None
        return self.player_list.get(selection[0])

    def refresh_views(self):
        selected_name = self.current_player_name()
        self.player_list.delete(0, tk.END)
        names = sorted(TEAM.keys())
        for name in names:
            self.player_list.insert(tk.END, name)
        if selected_name in names:
            index = names.index(selected_name)
            self.player_list.selection_set(index)
        elif names:
            self.player_list.selection_set(0)
            selected_name = names[0]
        else:
            selected_name = None

        if selected_name:
            player = TEAM[selected_name]
            self.player_title.configure(text=player.name)
            team_pos = get_team_possessions()

            # Per-type made/attempts (layup, midrange, 3pt)
            def made_att(t): 
                s = player.shots[t]
                return s["made"], s["made"] + s["missed"]
            lay_m, lay_a = made_att("layup")
            mid_m, mid_a = made_att("midrange")
            t3_m, t3_a  = made_att("3pt")

            summary = (
                f"BASIC STATS\n"
                f"  Points:     {player.points}\n"
                f"  Assists:    {player.assists}\n"
                f"  Rebounds:   {player.rebounds}\n"
                f"  Turnovers:  {player.turnovers}\n\n"
                f"SHOOTING (All shots total): {player.shots_made()}/{player.total_shots()}\n"
                f"  Layup:     {lay_m}/{lay_a}\n"
                f"  Midrange:  {mid_m}/{mid_a}\n"
                f"  3PT:       {t3_m}/{t3_a}\n"
                f"  Contested made/missed total: "
                f"{sum(v['contested_made'] for v in player.shots.values())}/"
                f"{sum(v['contested_missed'] for v in player.shots.values())}\n\n"
                f"OFFENSIVE TRACKING\n"
                f"  Strike Zone Passing: Balls {player.strike_zone['balls']} | Strikes {player.strike_zone['strikes']}\n"
                f"    Ball result:   Made {player.strike_zone['ball_made']} | Missed {player.strike_zone['ball_missed']}\n"
                f"    Strike result: Made {player.strike_zone['strike_made']} | Missed {player.strike_zone['strike_missed']}\n"
                f"  Cuts through smile: {player.cuts['total']}  "
                f"(Pass {player.cuts['pass_to_cutter']}, Made {player.cuts['made_shot']}, Missed {player.cuts['missed_shot']})\n\n"
                f"DEFENSIVE TRACKING\n"
                f"  Paint touches allowed: {player.paint_touches['total']}  "
                f"(Made {player.paint_touches['made_shot']}, Missed {player.paint_touches['missed_shot']}, Kick {player.paint_touches['kick_out']})\n"
                f"  Contest outcomes: "
                f"CM {player.defense['contested_made']}, CMs {player.defense['contested_missed']}, "
                f"UM {player.defense['uncontested_made']}, UMs {player.defense['uncontested_missed']}\n\n"
                f"ADVANCED METRICS\n"
                f"  PER: {player.calc_per()} | TS%: {player.calc_ts()} | A/T: {player.calc_ast_to_tov()} | "
                f"Usage%: {player.calc_usage(team_pos)} | BPM: {player.calc_bpm()}\n"
            )
        else:
            summary = "No players yet.\nUse 'Add Player' to begin."
            self.player_title.configure(text="Select a Player")

        self.stats_box.configure(state=tk.NORMAL)
        self.stats_box.delete("1.0", tk.END)
        self.stats_box.insert(tk.END, summary)
        self.stats_box.configure(state=tk.DISABLED)

        self.team_score.configure(text=f"Team Score: {calc_team_percentage()}%")

    # --- small helper dialog (one simple question) ---
    def choice_dialog(self, title, question, options):
        # options: list of (label, value)
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.transient(self.root)
        dlg.grab_set()
        ttk.Label(dlg, text=question).pack(padx=12, pady=10)
        var = tk.StringVar()
        for label, value in options:
            ttk.Radiobutton(dlg, text=label, variable=var, value=str(value)).pack(anchor=tk.W, padx=12)
        selected = {"value": None}
        def ok():
            v = var.get()
            if v == "":
                selected["value"] = None
            else:
                # try bool/int if represented
                if v == "True": selected["value"] = True
                elif v == "False": selected["value"] = False
                else: selected["value"] = v
            dlg.destroy()
        ttk.Button(dlg, text="OK", command=ok).pack(pady=10)
        dlg.wait_window()
        return selected["value"]

    # --- recording flows with simple step-by-step popups ---
    def record_shot_flow(self):
        name = self.current_player_name()
        if not name:
            messagebox.showinfo("Info", "Select a player first.")
            return
        shot_type = self.choice_dialog("Shot Type", "Select shot type:", [("Layup", "layup"), ("Midrange", "midrange"), ("3PT", "3pt")])
        if shot_type is None:
            return
        made = self.choice_dialog("Shot Result", "Was the shot made?", [("Made", True), ("Missed", False)])
        if made is None:
            return
        contested = self.choice_dialog("Shot Contest", "Was it contested?", [("Contested", True), ("Uncontested", False)])
        if contested is None:
            return
        self.store_state()
        TEAM[name].record_shot(shot_type, made, contested)
        save_data()
        self.refresh_views()

    def record_strike_flow(self):
        name = self.current_player_name()
        if not name:
            messagebox.showinfo("Info", "Select a player first.")
            return
        kind = self.choice_dialog("Strike Zone Passing", "Pass type:", [("Ball", "ball"), ("Strike", "strike")])
        if kind is None:
            return
        result = self.choice_dialog("Result", "Result of possession:", [("Made Shot", "made"), ("Missed Shot", "missed")])
        if result is None:
            return
        self.store_state()
        TEAM[name].record_strike_pass(kind, result)
        save_data()
        self.refresh_views()

    def record_cut_flow(self):
        name = self.current_player_name()
        if not name:
            messagebox.showinfo("Info", "Select a player first.")
            return
        result = self.choice_dialog(
            "Cut Result",
            "Result of cut:",
            [("Pass to cutter", "pass"), ("Made shot", "made"), ("Missed shot", "missed")]
        )
        if result is None:
            return
        self.store_state()
        TEAM[name].record_cut(result)
        save_data()
        self.refresh_views()

    def record_paint_flow(self):
        name = self.current_player_name()
        if not name:
            messagebox.showinfo("Info", "Select a player first.")
            return
        result = self.choice_dialog(
            "Paint Touch",
            "Result of paint touch allowed:",
            [("Made shot", "made"), ("Missed shot", "missed"), ("Kick out (pass)", "kick")]
        )
        if result is None:
            return
        self.store_state()
        TEAM[name].record_paint_touch(result)
        save_data()
        self.refresh_views()

    def record_defense_flow(self):
        name = self.current_player_name()
        if not name:
            messagebox.showinfo("Info", "Select a player first.")
            return
        contested = self.choice_dialog("Defense", "Was the shot contested?", [("Contested", True), ("Uncontested", False)])
        if contested is None:
            return
        made = self.choice_dialog("Defense", "Did the opponent make the shot?", [("Made", True), ("Missed", False)])
        if made is None:
            return
        self.store_state()
        TEAM[name].record_defense(bool(contested), bool(made))
        save_data()
        self.refresh_views()

    def add_player(self):
        name = simpledialog.askstring("Add Player", "Player name:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            messagebox.showerror("Invalid", "Name cannot be empty.")
            return
        if name in TEAM:
            messagebox.showerror("Duplicate", "Player already exists.")
            return
        self.store_state()
        TEAM[name] = Player(name)
        save_data()
        self.refresh_views()

    def remove_player(self):
        name = self.current_player_name()
        if not name:
            return
        if not messagebox.askyesno("Confirm", f"Remove {name}?"):
            return
        self.store_state()
        del TEAM[name]
        save_data()
        self.refresh_views()

    def rename_player(self):
        name = self.current_player_name()
        if not name:
            return
        new_name = simpledialog.askstring("Rename Player", "New name:", initialvalue=name, parent=self.root)
        if not new_name:
            return
        new_name = new_name.strip()
        if not new_name:
            messagebox.showerror("Invalid", "Name cannot be empty.")
            return
        if new_name in TEAM and new_name != name:
            messagebox.showerror("Duplicate", "Player already exists.")
            return
        if new_name == name:
            return
        self.store_state()
        TEAM[new_name] = TEAM.pop(name)
        TEAM[new_name].name = new_name
        save_data()
        self.refresh_views()

    def bump_stat(self, attr):
        name = self.current_player_name()
        if not name:
            messagebox.showinfo("Info", "Select a player first.")
            return
        self.store_state()
        player = TEAM[name]
        setattr(player, attr, getattr(player, attr) + 1)
        save_data()
        self.refresh_views()

    def edit_totals(self):
        name = self.current_player_name()
        if not name:
            messagebox.showinfo("Info", "Select a player first.")
            return
        player = TEAM[name]

        popup = tk.Toplevel(self.root)
        popup.title(f"Edit Totals: {player.name}")
        popup.transient(self.root)
        popup.grab_set()

        entries = {}
        for idx, (label, value) in enumerate(
            (("Points", player.points), ("Assists", player.assists), ("Rebounds", player.rebounds), ("Turnovers", player.turnovers))
        ):
            ttk.Label(popup, text=label).grid(row=idx, column=0, padx=10, pady=5, sticky="e")
            entry = ttk.Entry(popup)
            entry.insert(0, str(value))
            entry.grid(row=idx, column=1, padx=10, pady=5)
            entries[label.lower()] = entry

        def submit():
            try:
                new_points = int(entries["points"].get())
                new_assists = int(entries["assists"].get())
                new_rebounds = int(entries["rebounds"].get())
                new_turnovers = int(entries["turnovers"].get())
            except ValueError:
                messagebox.showerror("Invalid", "Use whole numbers.")
                return
            self.store_state()
            player.points = max(0, new_points)
            player.assists = max(0, new_assists)
            player.rebounds = max(0, new_rebounds)
            player.turnovers = max(0, new_turnovers)
            save_data()
            self.refresh_views()
            popup.destroy()

        ttk.Button(popup, text="Apply", command=submit).grid(row=4, column=0, columnspan=2, pady=10)
        popup.mainloop()

    def apply_shot(self, name, shot_type, made, contested):
        self.store_state()
        TEAM[name].record_shot(shot_type, made, contested)
        save_data()
        self.refresh_views()

    def export_csv(self):
        if not TEAM:
            messagebox.showinfo("Info", "No players to export.")
            return
        team_pos = get_team_possessions()
        output = StringIO()
        headers = ["name", "points", "assists", "rebounds", "turnovers", "PER", "TS%", "A/T", "Usage%", "BPM"]
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for player in sorted(TEAM.values(), key=lambda p: p.name):
            writer.writerow(
                {
                    "name": player.name,
                    "points": player.points,
                    "assists": player.assists,
                    "rebounds": player.rebounds,
                    "turnovers": player.turnovers,
                    "PER": player.calc_per(),
                    "TS%": player.calc_ts(),
                    "A/T": player.calc_ast_to_tov(),
                    "Usage%": player.calc_usage(team_pos),
                    "BPM": player.calc_bpm(),
                }
            )
        try:
            with open("team_report.csv", "w", newline="", encoding="utf-8") as handle:
                handle.write(output.getvalue())
            messagebox.showinfo("Exported", f"Saved to {os.path.abspath('team_report.csv')}")
        except OSError as error:
            messagebox.showerror("Error", f"Could not write CSV:\n{error}")

    def store_state(self):
        self.last_state = {name: data.to_dict() for name, data in TEAM.items()}
        self.undo_btn.configure(state=tk.NORMAL)

    def undo_last(self):
        if not self.last_state:
            return
        TEAM.clear()
        for name, payload in self.last_state.items():
            TEAM[name] = Player.from_dict(name, payload)
        self.last_state = None
        self.undo_btn.configure(state=tk.DISABLED)
        save_data()
        self.refresh_views()

    # --- Simple Report popup with per-player and team totals ---
    def show_report(self):
        if not TEAM:
            messagebox.showinfo("Report", "No players.")
            return

        # team aggregates
        team = {
            "points": 0, "assists": 0, "rebounds": 0, "turnovers": 0,
            "shots_made": 0, "shots_att": 0,
            "layup_m": 0, "layup_a": 0, "mid_m": 0, "mid_a": 0, "t3_m": 0, "t3_a": 0,
            "ball": 0, "strike": 0, "ball_m": 0, "ball_x": 0, "strike_m": 0, "strike_x": 0,
            "cuts_total": 0, "cuts_pass": 0, "cuts_m": 0, "cuts_x": 0,
            "pt_total": 0, "pt_m": 0, "pt_x": 0, "pt_k": 0,
            "def_cm": 0, "def_cx": 0, "def_um": 0, "def_ux": 0,
        }

        def made_att(p, t):
            s = p.shots[t]
            return s["made"], s["made"] + s["missed"]

        lines = []
        for p in sorted(TEAM.values(), key=lambda x: x.name):
            lay_m, lay_a = made_att(p, "layup"); mid_m, mid_a = made_att(p, "midrange"); t3_m, t3_a = made_att(p, "3pt")
            shots_made = p.shots_made(); shots_att = p.total_shots()
            lines.append(
                f"{p.name}: Pts {p.points}, Ast {p.assists}, Reb {p.rebounds}, TO {p.turnovers} | "
                f"Shots {shots_made}/{shots_att} (Layup {lay_m}/{lay_a}, Mid {mid_m}/{mid_a}, 3PT {t3_m}/{t3_a}) | "
                f"Strike: Balls {p.strike_zone['balls']}({p.strike_zone['ball_made']}/{p.strike_zone['ball_missed']}) "
                f"Strikes {p.strike_zone['strikes']}({p.strike_zone['strike_made']}/{p.strike_zone['strike_missed']}) | "
                f"Cuts {p.cuts['total']} (Pass {p.cuts['pass_to_cutter']}, Made {p.cuts['made_shot']}, Miss {p.cuts['missed_shot']}) | "
                f"Paint {p.paint_touches['total']} (M {p.paint_touches['made_shot']}, X {p.paint_touches['missed_shot']}, K {p.paint_touches['kick_out']}) | "
                f"Def C(M {p.defense['contested_made']},X {p.defense['contested_missed']}), "
                f"U(M {p.defense['uncontested_made']},X {p.defense['uncontested_missed']})"
            )
            # accumulate team totals
            team["points"] += p.points; team["assists"] += p.assists; team["rebounds"] += p.rebounds; team["turnovers"] += p.turnovers
            team["shots_made"] += shots_made; team["shots_att"] += shots_att
            team["layup_m"] += lay_m; team["layup_a"] += lay_a; team["mid_m"] += mid_m; team["mid_a"] += mid_a; team["t3_m"] += t3_m; team["t3_a"] += t3_a
            team["ball"] += p.strike_zone["balls"]; team["strike"] += p.strike_zone["strikes"]
            team["ball_m"] += p.strike_zone["ball_made"]; team["ball_x"] += p.strike_zone["ball_missed"]
            team["strike_m"] += p.strike_zone["strike_made"]; team["strike_x"] += p.strike_zone["strike_missed"]
            team["cuts_total"] += p.cuts["total"]; team["cuts_pass"] += p.cuts["pass_to_cutter"]
            team["cuts_m"] += p.cuts["made_shot"]; team["cuts_x"] += p.cuts["missed_shot"]
            team["pt_total"] += p.paint_touches["total"]; team["pt_m"] += p.paint_touches["made_shot"]
            team["pt_x"] += p.paint_touches["missed_shot"]; team["pt_k"] += p.paint_touches["kick_out"]
            team["def_cm"] += p.defense["contested_made"]; team["def_cx"] += p.defense["contested_missed"]
            team["def_um"] += p.defense["uncontested_made"]; team["def_ux"] += p.defense["uncontested_missed"]

        report = "INDIVIDUALS\n" + "\n".join(lines) + "\n\nTEAM TOTALS\n" + (
            f"Points {team['points']}, Assists {team['assists']}, Rebounds {team['rebounds']}, TO {team['turnovers']}\n"
            f"Shots {team['shots_made']}/{team['shots_att']} (Layup {team['layup_m']}/{team['layup_a']}, "
            f"Mid {team['mid_m']}/{team['mid_a']}, 3PT {team['t3_m']}/{team['t3_a']})\n"
            f"Strike: Balls {team['ball']} (M {team['ball_m']}/X {team['ball_x']}), "
            f"Strikes {team['strike']} (M {team['strike_m']}/X {team['strike_x']})\n"
            f"Cuts {team['cuts_total']} (Pass {team['cuts_pass']}, M {team['cuts_m']}, X {team['cuts_x']})\n"
            f"Paint {team['pt_total']} (M {team['pt_m']}, X {team['pt_x']}, K {team['pt_k']})\n"
            f"Defense C(M {team['def_cm']}, X {team['def_cx']}), U(M {team['def_um']}, X {team['def_ux']})\n"
        )

        win = tk.Toplevel(self.root)
        win.title("Team Report")
        win.geometry("900x500")
        txt = tk.Text(win, wrap=tk.WORD)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, report)
        txt.config(state=tk.DISABLED)

    def on_close(self):
        # Save data before closing the app window
        try:
            save_data()
        finally:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    BasketballApp(root)
    root.mainloop()
