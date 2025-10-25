from flask import Flask, render_template, request, redirect, url_for, flash
from collections import defaultdict
import csv
import json
import os
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "dev-key"

# Database config: use DATABASE_URL env var (Postgres on Render/Supabase) or default sqlite for local
db_url = os.getenv('DATABASE_URL') or f"sqlite:///{os.path.join(os.path.dirname(__file__), 'data.db')}"
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Player:
    def __init__(self, name):
        self.name = name
        # Shots structure: {type: {'made': int, 'missed': int, 'contested_made': int, 'contested_missed': int}}
        self.shots = defaultdict(lambda: {'made': 0, 'missed': 0, 'contested_made': 0, 'contested_missed': 0})
        self.assists = 0
        self.turnovers = 0
        self.rebounds = 0
        self.points = 0

        # Strike zone passing
        self.strike_zone = {'balls': 0, 'strikes': 0}

        # Cut tracking
        self.cuts = {'total': 0, 'pass_to_cutter': 0, 'made_shot': 0, 'missed_shot': 0}

        # Paint touches allowed to opponent when defending (we track when this player is on offense allowed by opponent)
        self.paint_touches = {'total': 0, 'made_shot': 0, 'missed_shot': 0, 'kick_out': 0}

        # Defensive contested/uncontested tracking
        self.defense = {
            'contested_made': 0,
            'contested_missed': 0,
            'uncontested_made': 0,
            'uncontested_missed': 0
        }

    # Recording helper methods
    def record_shot(self, shot_type, made, contested=False):
        if made:
            self.shots[shot_type]['made'] += 1
            self.points += 3 if shot_type == '3pt' else 2
            if contested:
                self.shots[shot_type]['contested_made'] += 1
        else:
            self.shots[shot_type]['missed'] += 1
            if contested:
                self.shots[shot_type]['contested_missed'] += 1

    def record_assist(self):
        self.assists += 1

    def record_turnover(self):
        self.turnovers += 1

    def record_rebound(self):
        self.rebounds += 1

    def record_strike_pass(self, kind):
        if kind in ('balls', 'strikes'):
            self.strike_zone[kind] += 1

    def record_cut(self, result):
        self.cuts['total'] += 1
        if result == 'pass':
            self.cuts['pass_to_cutter'] += 1
        elif result == 'made':
            self.cuts['made_shot'] += 1
            self.points += 2
        elif result == 'missed':
            self.cuts['missed_shot'] += 1

    def record_paint_touch(self, result):
        self.paint_touches['total'] += 1
        if result == 'made':
            self.paint_touches['made_shot'] += 1
            self.points += 2
        elif result == 'missed':
            self.paint_touches['missed_shot'] += 1
        elif result == 'kick':
            self.paint_touches['kick_out'] += 1

    def record_defense(self, contested, made):
        if contested:
            if made:
                self.defense['contested_made'] += 1
            else:
                self.defense['contested_missed'] += 1
        else:
            if made:
                self.defense['uncontested_made'] += 1
            else:
                self.defense['uncontested_missed'] += 1

    # Derived metrics
    def total_shots(self):
        return sum(v['made'] + v['missed'] for v in self.shots.values())

    def shots_made(self):
        return sum(v['made'] for v in self.shots.values())

    def shots_missed(self):
        return sum(v['missed'] for v in self.shots.values())

    def calc_per(self):
        # Simplified PER-like value — not the official PER calculation but a single-number summary
        denom = max(1, (self.total_shots() + self.turnovers))
        per = (self.points + self.rebounds + self.assists - self.turnovers) / denom * 15
        return round(per, 2)

    def calc_ts(self):
        # True Shooting % simplified: points / (2 * (FGA + 0.44 * FTA)). We don't track FTA here, so use FGA proxy.
        fga = self.total_shots()
        if fga == 0:
            return 0.0
        ts = self.points / (2 * fga)
        return round(ts, 3)

    def calc_ast_to_tov(self):
        if self.turnovers == 0:
            return float(self.assists) if self.assists > 0 else 0.0
        return round(self.assists / self.turnovers, 2)

    def calc_usage(self, team_possessions=1):
        # Very rough usage: possessions used by player / team possessions.
        # We'll define possessions used as shots + assists + turnovers
        used = self.total_shots() + self.assists + self.turnovers
        if team_possessions <= 0:
            return 0.0
        return round(100 * used / team_possessions, 2)

    def calc_bpm(self):
        # Very rough BPM per 100 possessions placeholder
        possessions = max(1, self.total_shots() + self.turnovers)
        bpm = (self.points + self.rebounds + self.assists) / possessions * 10
        return round(bpm, 2)


TEAM = {}


def get_team_possessions():
    # Simple team possessions proxy: sum of players' used possessions
    pos = 0
    for p in TEAM.values():
        pos += p.total_shots() + p.assists + p.turnovers
    return max(1, pos)


def aggregate_team_totals():
    totals = {
        'players': len(TEAM),
        'shots_made': 0,
        'shots_missed': 0,
        'points': 0,
        'assists': 0,
        'turnovers': 0,
    }
    for p in TEAM.values():
        totals['shots_made'] += p.shots_made()
        totals['shots_missed'] += p.shots_missed()
        totals['points'] += p.points
        totals['assists'] += p.assists
        totals['turnovers'] += p.turnovers
    return totals


def calc_team_percentage():
    """Compute a single team percentage (0-100) summarizing all players.

    Approach (simple, explainable):
    - For each player compute 5 sub-metrics normalized to 0..1 with conservative caps:
      TS% -> capped at 1.0
      PER  -> capped at 30
      A/T  -> capped at 3
      Usage% -> capped at 40 (percent)
      BPM  -> capped at 10
    - Normalize each: e.g. per_norm = min(per,30)/30
    - Player score = average of these normalized metrics (0..1)
    - Team percentage = mean(player_score) * 100

    This gives a single, interpretable percentage representing overall team progress.
    """
    if not TEAM:
        return 0

    player_scores = []
    for p in TEAM.values():
        # collect raw values
        per = p.calc_per()
        ts = p.calc_ts()
        at = p.calc_ast_to_tov()
        # use team possessions for usage normalization
        usage = p.calc_usage(team_possessions=get_team_possessions())
        bpm = p.calc_bpm()

        # normalize with caps
        per_n = max(0.0, min(per, 30.0)) / 30.0
        ts_n = max(0.0, min(ts, 1.0)) / 1.0
        at_n = max(0.0, min(at, 3.0)) / 3.0
        usage_n = max(0.0, min(usage, 40.0)) / 40.0
        bpm_n = (max(-10.0, min(bpm, 10.0)) + 10.0) / 20.0  # map -10..10 to 0..1

        # average the normalized metrics
        player_score = (per_n + ts_n + at_n + usage_n + bpm_n) / 5.0
        player_scores.append(player_score)

    team_score = sum(player_scores) / len(player_scores)
    return round(team_score * 100, 1)


# --- persistence helpers (JSON) -----------------
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data.json')


def player_to_dict(p: 'Player'):
    return {
        'name': p.name,
        'shots': {k: v for k, v in p.shots.items()},
        'assists': p.assists,
        'turnovers': p.turnovers,
        'rebounds': p.rebounds,
        'points': p.points,
        'strike_zone': p.strike_zone,
        'cuts': p.cuts,
        'paint_touches': p.paint_touches,
        'defense': p.defense
    }


def dict_to_player(d: dict) -> 'Player':
    p = Player(d['name'])
    p.shots = defaultdict(lambda: {'made': 0, 'missed': 0, 'contested_made': 0, 'contested_missed': 0})
    for k, v in d.get('shots', {}).items():
        p.shots[k] = v
    p.assists = d.get('assists', 0)
    p.turnovers = d.get('turnovers', 0)
    p.rebounds = d.get('rebounds', 0)
    p.points = d.get('points', 0)
    p.strike_zone = d.get('strike_zone', {'balls': 0, 'strikes': 0})
    p.cuts = d.get('cuts', {'total': 0, 'pass_to_cutter': 0, 'made_shot': 0, 'missed_shot': 0})
    p.paint_touches = d.get('paint_touches', {'total': 0, 'made_shot': 0, 'missed_shot': 0, 'kick_out': 0})
    p.defense = d.get('defense', p.defense)
    return p


# Database model
class PlayerModel(db.Model):
    __tablename__ = 'players'
    name = db.Column(db.String, primary_key=True)
    shots = db.Column(db.JSON, default={})
    assists = db.Column(db.Integer, default=0)
    turnovers = db.Column(db.Integer, default=0)
    rebounds = db.Column(db.Integer, default=0)
    points = db.Column(db.Integer, default=0)
    strike_zone = db.Column(db.JSON, default={})
    cuts = db.Column(db.JSON, default={})
    paint_touches = db.Column(db.JSON, default={})
    defense = db.Column(db.JSON, default={})

    def to_dict(self):
        return {
            'name': self.name,
            'shots': self.shots or {},
            'assists': self.assists,
            'turnovers': self.turnovers,
            'rebounds': self.rebounds,
            'points': self.points,
            'strike_zone': self.strike_zone or {},
            'cuts': self.cuts or {},
            'paint_touches': self.paint_touches or {},
            'defense': self.defense or {}
        }

# ensure DB tables exist
with app.app_context():
    db.create_all()


def save_data():
    try:
        # sync TEAM into DB (upsert)
        for name, p in TEAM.items():
            pm = PlayerModel.query.get(name)
            if not pm:
                pm = PlayerModel(name=name)
            pm.shots = {k: v for k, v in p.shots.items()}
            pm.assists = p.assists
            pm.turnovers = p.turnovers
            pm.rebounds = p.rebounds
            pm.points = p.points
            pm.strike_zone = p.strike_zone
            pm.cuts = p.cuts
            pm.paint_touches = p.paint_touches
            pm.defense = p.defense
            db.session.add(pm)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error('Failed to save data to DB: %s', e)


def load_data():
    # load from DB into TEAM
    try:
        TEAM.clear()
        for pm in PlayerModel.query.all():
            TEAM[pm.name] = dict_to_player(pm.to_dict())
    except Exception as e:
        app.logger.error('Failed to load data from DB: %s', e)


# load existing data at startup (if any)
with app.app_context():
    load_data()



@app.route('/')
def index():
    team_pct = calc_team_percentage()
    return render_template('index.html', players=sorted(TEAM.keys()), team_pct=team_pct)


@app.route('/add_player', methods=['POST'])
def add_player():
    name = request.form.get('name', '').strip()
    if not name:
        flash('Player name cannot be empty', 'danger')
        return redirect(url_for('index'))
    if name in TEAM:
        flash('Player already exists', 'warning')
        return redirect(url_for('index'))
    TEAM[name] = Player(name)
    save_data()
    flash(f'Player {name} added', 'success')
    return redirect(url_for('player_page', name=name))


@app.route('/player/<name>')
def player_page(name):
    player = TEAM.get(name)
    if not player:
        flash('Player not found', 'danger')
        return redirect(url_for('index'))
    team_pos = get_team_possessions()
    metrics = {
        'PER': player.calc_per(),
        'TS%': player.calc_ts(),
        'A/T': player.calc_ast_to_tov(),
        'Usage%': player.calc_usage(team_possessions=team_pos),
        'BPM': player.calc_bpm()
    }
    return render_template('player.html', player=player, metrics=metrics)


@app.route('/player/<name>/event', methods=['POST'])
def player_event(name):
    player = TEAM.get(name)
    if not player:
        flash('Player not found', 'danger')
        return redirect(url_for('index'))

    event = request.form.get('event')
    # Shots: shot_type (layup, midrange, 3pt), made, contested
    if event == 'shot':
        shot_type = request.form.get('shot_type') or 'layup'
        made = request.form.get('made') == 'yes'
        contested = request.form.get('contested') == 'yes'
        player.record_shot(shot_type, made, contested)
        save_data()
        flash('Shot recorded', 'success')

    elif event == 'assist':
        player.record_assist()
        save_data()
        flash('Assist recorded', 'success')

    elif event == 'turnover':
        player.record_turnover()
        save_data()
        flash('Turnover recorded', 'warning')

    elif event == 'rebound':
        player.record_rebound()
        save_data()
        flash('Rebound recorded', 'info')

    elif event == 'strike':
        kind = request.form.get('kind')
        player.record_strike_pass(kind)
        save_data()
        flash('Strike zone pass recorded', 'success')

    elif event == 'cut':
        result = request.form.get('result')
        player.record_cut(result)
        save_data()
        flash('Cut recorded', 'success')

    elif event == 'paint':
        result = request.form.get('result')
        player.record_paint_touch(result)
        save_data()
        flash('Paint touch recorded', 'success')

    elif event == 'defense':
        contested = request.form.get('contested') == 'yes'
        made = request.form.get('made') == 'yes'
        player.record_defense(contested, made)
        save_data()
        flash('Defensive event recorded', 'success')

    else:
        flash('Unknown event', 'danger')

    return redirect(url_for('player_page', name=name))


@app.route('/report')
def report():
    team_totals = aggregate_team_totals()
    team_pct = calc_team_percentage()
    players = []
    team_pos = get_team_possessions()
    for p in TEAM.values():
        players.append({
            'name': p.name,
            'shots_made': p.shots_made(),
            'shots_missed': p.shots_missed(),
            'points': p.points,
            'assists': p.assists,
            'turnovers': p.turnovers,
            'PER': p.calc_per(),
            'TS%': p.calc_ts(),
            'A/T': p.calc_ast_to_tov(),
            'Usage%': p.calc_usage(team_possessions=team_pos),
            'BPM': p.calc_bpm()
        })

    return render_template('report.html', players=players, team=team_totals, team_pct=team_pct)


@app.route('/export_csv')
def export_csv():
    # Export a simple CSV of player tallies
    rows = []
    for p in TEAM.values():
        rows.append({
            'name': p.name,
            'shots_made': p.shots_made(),
            'shots_missed': p.shots_missed(),
            'points': p.points,
            'assists': p.assists,
            'turnovers': p.turnovers,
            'PER': p.calc_per(),
            'TS%': p.calc_ts()
        })

    # Write CSV to a string-like response
    from io import StringIO
    si = StringIO()
    fieldnames = list(rows[0].keys()) if rows else ['name']
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

    return app.response_class(si.getvalue(), mimetype='text/csv', headers={
        'Content-Disposition': 'attachment;filename=team_report.csv'
    })


@app.route('/download_data')
def download_data():
    # Return the saved JSON file for backup
    if not os.path.exists(DATA_FILE):
        flash('No saved data found', 'warning')
        return redirect(url_for('report'))
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    return app.response_class(content, mimetype='application/json', headers={
        'Content-Disposition': 'attachment;filename=data.json'
    })


@app.route('/restore', methods=['GET', 'POST'])
def restore():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file:
            flash('No file uploaded', 'danger')
            return redirect(url_for('restore'))
        try:
            content = file.read().decode('utf-8')
            rows = json.loads(content)
            TEAM.clear()
            for name, d in rows.items():
                TEAM[name] = dict_to_player(d)
            save_data()
            flash('Data restored', 'success')
            return redirect(url_for('report'))
        except Exception as e:
            flash(f'Failed to restore: {e}', 'danger')
            return redirect(url_for('restore'))

    return render_template('restore.html')


if __name__ == '__main__':
    app.run(debug=True)
