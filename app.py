from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import random

app = Flask(__name__)
app.secret_key = 'secret-key'

ANIMAL_NAMES = [
    'Aquila', 'Falcone', 'Lupo', 'Orso', 'Tigre', 'Leone', 'Volpe', 'Gatto',
    'Cane', 'Cervo', 'Cinghiale', 'Pantera', 'Gazzella', 'Istrice', 'Riccio',
    'Lepre', 'Capriolo', 'Bufalo', 'Cammello', 'Cobra'
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

    def add_game(self, team):
        if team == 'a':
            self.games_a += 1
            ranking[self.team_a.name] = ranking.get(self.team_a.name, 0) + 1
        else:
            self.games_b += 1
            ranking[self.team_b.name] = ranking.get(self.team_b.name, 0) + 1


def get_ranking():
    data = []
    for name, games_won in ranking.items():
        team_obj = next(t for t in teams if t.name == name)
        initials = ''.join([w[0] for w in team_obj.players])
        data.append({
            'name': name,
            'games': games_won,
            'initials': initials,
            'color': team_obj.color
        })
    data.sort(key=lambda x: x['games'], reverse=True)
    return data


@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    password = request.form.get('password')
    session['admin'] = password == '00000'
    return redirect(url_for('dashboard'))

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
    return redirect(url_for('admin'))

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
    return redirect(url_for('admin'))

@app.route('/start_match', methods=['POST'])
def start_match():
    global current_match
    a_index = int(request.form.get('team_a'))
    b_index = int(request.form.get('team_b'))
    team_a = teams[a_index]
    team_b = teams[b_index]
    current_match = Match(team_a, team_b)
    return redirect(url_for('admin'))

@app.route('/point/<team>', methods=['POST'])
def point(team):
    global current_match
    if not current_match:
        return redirect(url_for('admin'))
    current_match.add_game('a' if team == 'team_a' else 'b')
    return redirect(url_for('admin'))


@app.route('/current_match')
def current_match_data():
    if not current_match:
        return jsonify({})
    return jsonify({
        'team_a': current_match.team_a.name,
        'team_b': current_match.team_b.name,
        'games_a': current_match.games_a,
        'games_b': current_match.games_b,
    })

if __name__ == '__main__':
    app.run(debug=True)
