from flask import Flask, render_template, request, redirect, session, url_for
import random

app = Flask(__name__)
app.secret_key = 'secret-key'

ANIMAL_NAMES = [
    'Aquila', 'Falcone', 'Lupo', 'Orso', 'Tigre', 'Leone', 'Volpe', 'Gatto',
    'Cane', 'Cervo', 'Cinghiale', 'Pantera', 'Gazzella', 'Istrice', 'Riccio',
    'Lepre', 'Capriolo', 'Bufalo', 'Cammello', 'Cobra'
]

players = [f'Player {i}' for i in range(1, 9)]
teams = []
current_match = None
ranking = {}

class Team:
    def __init__(self, name, players):
        self.name = name
        self.players = players

class Match:
    def __init__(self, team_a, team_b):
        self.team_a = team_a
        self.team_b = team_b
        self.points_a = 0
        self.points_b = 0
        self.games_a = 0
        self.games_b = 0
        self.sets_a = 0
        self.sets_b = 0

    def point(self, team):
        if team == 'a':
            self.points_a += 1
        else:
            self.points_b += 1
        self.update_scores()

    def update_scores(self):
        pa, pb = self.points_a, self.points_b
        if pa >= 4 or pb >= 4:
            if abs(pa - pb) >= 2:
                if pa > pb:
                    self.games_a += 1
                else:
                    self.games_b += 1
                self.points_a = 0
                self.points_b = 0
                self.check_set()

    def check_set(self):
        ga, gb = self.games_a, self.games_b
        if (ga >= 6 or gb >= 6) and abs(ga - gb) >= 2:
            if ga > gb:
                self.sets_a += 1
            else:
                self.sets_b += 1
            self.games_a = 0
            self.games_b = 0

    def point_display(self, points, opponent):
        score_map = ['0', '15', '30', '40']
        if points >= 3 and opponent >= 3:
            if points == opponent:
                return '40'
            elif points == opponent + 1:
                return 'AD'
            else:
                return '40'
        return score_map[min(points, 3)]

    @property
    def points_a_display(self):
        return self.point_display(self.points_a, self.points_b)

    @property
    def points_b_display(self):
        return self.point_display(self.points_b, self.points_a)


def get_ranking():
    data = []
    for name, sets_won in ranking.items():
        games_played = 0
        for m in matches:
            if m['team_a'].name == name or m['team_b'].name == name:
                games_played += 1
        initials = ''.join([w[0] for w in next(t.players for t in teams if t.name == name)])
        data.append({'name': name, 'sets': sets_won, 'games': games_played, 'initials': initials})
    data.sort(key=lambda x: x['sets'], reverse=True)
    return data

matches = []

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
    for i in range(0, len(players), 2):
        team = Team(names[i//2], [players[i], players[i+1]])
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
    global current_match, ranking, matches
    if not current_match:
        return redirect(url_for('admin'))
    current_match.point('a' if team == 'team_a' else 'b')
    if current_match.sets_a == 2 or current_match.sets_b == 2:
        # match over
        ranking[current_match.team_a.name] = ranking.get(current_match.team_a.name, 0) + current_match.sets_a
        ranking[current_match.team_b.name] = ranking.get(current_match.team_b.name, 0) + current_match.sets_b
        matches.append({'team_a': current_match.team_a, 'team_b': current_match.team_b,
                        'sets_a': current_match.sets_a, 'sets_b': current_match.sets_b})
        current_match = None
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
