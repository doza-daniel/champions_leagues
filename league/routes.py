from flask import render_template, url_for, redirect, flash, request
from flask_login import current_user, login_user, logout_user, login_required
from math import ceil
from itertools import combinations
from functools import reduce
from datetime import datetime
from hashlib import sha1

from league import app, db, bcrypt
from league.forms import RegistrationForm, LoginForm, CreateLeagueForm, RegisterPlayerForm, StartLeagueForm, RemovePlayerForm, AddPlayerForm, EndLeagueForm, generate_edit_match_form
from league.models import User, League, Group, Player, Match

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/create_league", methods=['GET', 'POST'])
@login_required
def create_league():
    form = CreateLeagueForm()
    if form.validate_on_submit():
        league = League(owner=current_user, name=form.name.data)
        db.session.add(league)
        db.session.commit()
        flash(f"League '{league.name}' has been created successfully!", 'success')
        return redirect(url_for('edit_leagues', league_id=league.id))

    return render_template('create_league.html', title='Create League', form=form)

@app.route("/list_leagues")
@login_required
def list_leagues():
    leagues = League.query.filter_by(owner=current_user).all()
    return render_template('list_leagues.html', title='List Leagues', leagues=leagues)

@app.route("/edit_leagues/<int:league_id>", methods=['GET', 'POST'])
@login_required
def edit_leagues(league_id):
    league = League.query.filter_by(id=league_id).first()
    if league.date_ended is not None:
        flash('you are a moron', 'danger')
        return redirect(url_for('home'))

    end_form = None
    phases = None
    if league.date_started is not None:
        phases = sum_matches(league)
        if all(map(lambda x: x.played_on, league.matches)):
            end_form = EndLeagueForm()
            if end_form.end.data and end_form.validate():
                league.date_ended = end_form.date_ended.data
                db.session.commit()
                flash(f"League '{league.name}' ended successfully!", 'success')
                return redirect(url_for('home'))

    _to_add = Player.query.filter(~Player.id.in_([p.id for p in league.players])).all()
    to_remove = [(p.id, p.name + " " + p.last_name) for p in league.players]
    to_add = [(p.id, p.name + " " + p.last_name) for p in _to_add]

    start_form = StartLeagueForm(league)
    remove_form = RemovePlayerForm(to_remove)
    add_form = AddPlayerForm(to_add)

    if start_form.start.data and start_form.validate():
        flash(f"League has been started successfully!", 'success')
        league.date_started = start_form.date_started.data
        generate_league_matches(league,
                start_form.group_size.data,
                start_form.number_of_phases.data)
        db.session.commit()
        return redirect(url_for('home'))

    if add_form.add.data and add_form.validate():
        for pID in add_form.players_to_add.data:
            league.players.append(Player.query.get(pID))
        db.session.commit()
        return redirect(url_for('edit_leagues', league_id=league_id))

    if remove_form.remove.data and remove_form.validate():
        league.players = [p for p in league.players if p.id not in remove_form.players_to_remove.data]
        db.session.commit()
        return redirect(url_for('edit_leagues', league_id=league_id))


    return render_template('edit_league.html',
            title='Edit League',
            start_form=start_form,
            remove_form=remove_form,
            add_form=add_form,
            end_form=end_form,
            league=league,
            nplayers=len(to_remove),
            phases=phases)

# each pair in groups plays two matches, this function groups them by encounter
# and calculates 'meta' score. for example:
# p1 and p2 in group g1 have played 2 matches with scores [p1: 7 - 3 :p2] [p1: 7 - 2 :p2]
# so the meta score will be [p1: 2 - 0 :p2]
def sum_matches(league):
    def hash_player_ids(match):
        key = sha1('-'.join([str(match.player_one.id),str(match.player_two.id)]).encode('utf-8')).hexdigest()
        return (key, match)

    def group_by_hash(acc, key_match_pairs):
        key = key_match_pairs[0]
        match = key_match_pairs[1]

        print(acc)
        p1ms, p2ms = get_meta_score(match)
        if not acc.get(key):
            acc[key] = {"matches":[match], "p1": p1ms, "p2": p2ms}
        else:
            acc[key]["matches"].append(match)
            acc[key]["p1"] += p1ms
            acc[key]["p2"] += p2ms

        return acc

    def set_done_and_id(encounter):
        encounter["done"] = all(map(lambda x: x.played_on, encounter["matches"]))
        encounter["id"] = "-".join(map(lambda x: str(x.id), encounter["matches"]))
        return encounter


    def add_by_phase(acc, group):
        hash_match_pairs = map(hash_player_ids, group.matches)
        matches_by_hash = reduce(group_by_hash, hash_match_pairs, {})
        grouped_matches = {k: set_done_and_id(v) for k, v in matches_by_hash.items()}

        if not acc.get(group.phase):
            acc[group.phase] = {group: grouped_matches}
        else:
            acc[group.phase][group] = grouped_matches
        return acc

    return reduce(add_by_phase, league.groups, {})

def get_meta_score(match):
    p1 = 1 if match.player_one_score > match.player_two_score else 0
    p2 = 1 if match.player_two_score > match.player_one_score else 0
    return (p1, p2)

def generate_league_matches(league, gsize, num_phases):
    nplayers = len(league.players)
    ngroups = gsize
    groups=[]
    for i in range(ngroups):
        group = Group(league=league, size=gsize, phase=0)
        groups.append(group)
        db.session.add(group)

    for i in range(nplayers):
        groups[i % ngroups].players.append(league.players[i])

    matches = []
    for group in groups:
        for p1, p2 in combinations(group.players, 2):
            db.session.add(Match(player_one=p1, player_two=p2, league=league, group=group))
            db.session.add(Match(player_one=p1, player_two=p2, league=league, group=group))

    for phase in range(1,3):
        ng = [Group(league=league, size=gsize, phase=phase) for k in range(ngroups)]

        for i, group in enumerate(ng):
            for j in range(gsize):
                if len(groups[j % gsize].players) > (j * (phase - 1) + i) % gsize:
                    group.players.append(groups[j % gsize].players[(j * (phase - 1) + i) % gsize])

        for group in ng:
            db.session.add(group)
            for p1, p2 in combinations(group.players, 2):
                db.session.add(Match(player_one=p1, player_two=p2, league=league, group=group))
                db.session.add(Match(player_one=p1, player_two=p2, league=league, group=group))


    db.session.commit()

@app.route("/register_player", methods=['GET', 'POST'])
@login_required
def register_player():
    form = RegisterPlayerForm()
    if form.validate_on_submit():
        p = Player(name=form.name.data, last_name=form.last_name.data)
        db.session.add(p)
        db.session.commit()
        flash(f"Player has been registered successfully!", 'success')
        return redirect(url_for('register_player'))

    return render_template('register_player.html', title='Register Player', form=form)


@app.route("/finish_match/<string:matches>", methods=['GET', 'POST'])
@login_required
def finish_match(matches):
    forms = []
    for match_id in map(lambda x: int(x), matches.split('-')):
        match = Match.query.get(match_id)
        form = generate_edit_match_form(match)
        forms.append({"match": match, "form": form})
        if form[str(match.id)].data and form.validate():
            match.player_one_score = form[f"player_one_score_{match.id}"].data
            match.player_two_score = form[f"player_two_score_{match.id}"].data
            match.played_on = form[f"played_on_{match.id}"].data
            db.session.commit()
            flash('Match finished successfully!', 'success')
            return redirect(url_for('edit_leagues', league_id=match.league.id))

    return render_template('finish_match.html', title='Finish Match', forms=forms)

