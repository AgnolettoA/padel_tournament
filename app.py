from flask import Flask, render_template, request, redirect, session, url_for, jsonify, Response
import random
import json
import time

app = Flask(__name__)
app.secret_key = 'secret-key'

# "Cool" team names inspired by animals often used for sport clubs
ANIMAL_NAMES = [
    'Aquile Reali', 'Falchi', 'Lupi Grigi', 'Orsi Bruni', 'Tigri Bianche',
    "Leoni d'Africa", 'Pantere Nere', 'Volpi Artiche', 'Gatti Selvatici',
    'Squali', 'Grifoni', 'Tori', 'Gabbiani', 'Puma', 'Ghepardi', 'Gorilla',
    'Rinoceronti', 'Serpenti', 'Bufali', 'Cammelli'
]

COLORS = [
    '#EF4444', '#10B981', '#3B82F6', '#F59E0B', '#8B5CF6',
    '#EC4899', '#F87171', '#34D399', '#FBBF24', '#14B8A6'
]

players = [f'Player {i}' for i in range(1, 9)]
teams = []
current_match = None
ranking = {}

class Team:
    def __init__(self, name, players, color):
        self.name = name
        self.players = players
        self.color = color

class Match:
    def __init__(self, team_a, team_b):
        self.team_a = team_a
        self.team_b = team_b
        self.games_a = 0
        self.games_b = 0
        self.points_a = 0
        self.points_b = 0
        # store previous states for undo functionality
        self.history = []

    def _record_state(self):
        """Save current score to history for undo."""
        self.history.append(
            (self.points_a, self.points_b, self.games_a, self.games_b, ranking.copy())
        )

    def add_point(self, team):
        self._record_state()
        if team == 'a':
            self.points_a += 1
        else:
            self.points_b += 1
        self._check_game()

    def _check_game(self):
        if self.points_a >= 4 or self.points_b >= 4:
            if abs(self.points_a - self.points_b) >= 2:
                winner = 'a' if self.points_a > self.points_b else 'b'
                if winner == 'a':
                    self.games_a += 1
                    ranking[self.team_a.name] = ranking.get(self.team_a.name, 0) + 1
                else:
                    self.games_b += 1
                    ranking[self.team_b.name] = ranking.get(self.team_b.name, 0) + 1
                self.points_a = 0
                self.points_b = 0

    def undo(self):
        if not self.history:
            return
        self.points_a, self.points_b, self.games_a, self.games_b, hist_rank = self.history.pop()
        ranking.clear()
        ranking.update(hist_rank)

    def display_points(self, team):
        p = self.points_a if team == 'a' else self.points_b
        o = self.points_b if team == 'a' else self.points_a
        mapping = {0: '0', 1: '15', 2: '30', 3: '40'}
        if p >= 4 or o >= 4:
            if p == o:
                return '40'
            return 'A' if p > o else ''
        return mapping.get(p, '0')


def get_ranking():
    data = []
    for team_obj in teams:
        name = team_obj.name
        games_won = ranking.get(name, 0)
        players_names = ' & '.join(team_obj.players)
        data.append({
            'name': name,
            'games': games_won,
            'players': players_names,
            'color': team_obj.color
        })
    data.sort(key=lambda x: x['games'], reverse=True)
    return data


def get_state():
    """Return complete state for streaming."""
    state = {
        'teams': [
            {
                'name': t.name,
                'players': t.players,
                'color': t.color
            }
            for t in teams
        ],
        'ranking': get_ranking(),
        'current_match': None
    }
    if current_match:
        state['current_match'] = {
            'team_a': current_match.team_a.name,
            'team_b': current_match.team_b.name,
            'games_a': current_match.games_a,
            'games_b': current_match.games_b,
            'points_a': current_match.display_points('a'),
            'points_b': current_match.display_points('b'),
            'color_a': current_match.team_a.color,
            'color_b': current_match.team_b.color
        }
    return state


@app.route('/stream')
def stream():
    def event_stream():
        while True:
            data = json.dumps(get_state())
            yield f'data: {data}\n\n'
            time.sleep(0.25)
    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password')
    session['admin'] = password == '00000'
    return redirect(url_for('dashboard'), code=303)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if session.get('admin'):
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('user'))

@app.route('/admin')
def admin():
    global current_match
    shuffling = session.pop('shuffling', False)
    return render_template('admin.html', players=players, teams=teams,
                           current_match=current_match,
                           ranking=get_ranking(), shuffling=shuffling)

@app.route('/user')
def user():
    global current_match
    shuffling = session.pop('shuffling', False)
    return render_template('user.html', teams=teams, current_match=current_match,
                           ranking=get_ranking(), shuffling=shuffling)

@app.route('/add_players', methods=['POST'])
def add_players():
    global players, teams, ranking
    text = request.form.get('players', '')
    players = [p.strip() for p in text.splitlines() if p.strip()]
    teams = []
    ranking = {}
    return jsonify(get_state())

@app.route('/shuffle', methods=['POST'])
def shuffle():
    global players, teams
    random.shuffle(players)
    teams = []
    names = random.sample(ANIMAL_NAMES, len(players)//2)
    color_pool = random.sample(COLORS, len(players)//2)
    for i in range(0, len(players), 2):
        color = color_pool[i//2 % len(color_pool)]
        team = Team(names[i//2], [players[i], players[i+1]], color)
        teams.append(team)
    session['shuffling'] = True
    return jsonify(get_state())

@app.route('/start_match', methods=['POST'])
def start_match():
    global current_match
    a_index = int(request.form.get('team_a'))
    b_index = int(request.form.get('team_b'))
    team_a = teams[a_index]
    team_b = teams[b_index]
    current_match = Match(team_a, team_b)
    return jsonify(get_state())

@app.route('/undo', methods=['POST'])
def undo():
    global current_match
    if current_match:
        current_match.undo()
    return jsonify(get_state())

@app.route('/point/<team>', methods=['POST'])
def point(team):
    global current_match
    if not current_match:
        return jsonify({'error': 'no match'})
    current_match.add_point('a' if team == 'team_a' else 'b')
    return jsonify(get_state())


@app.route('/current_match')
def current_match_data():
    if not current_match:
        return jsonify({})
    return jsonify({
        'team_a': current_match.team_a.name,
        'team_b': current_match.team_b.name,
        'games_a': current_match.games_a,
        'games_b': current_match.games_b,
        'points_a': current_match.display_points('a'),
        'points_b': current_match.display_points('b'),
    })

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
