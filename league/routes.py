from flask import render_template, url_for, redirect, flash, request
from flask_login import current_user, login_user, logout_user, login_required
from math import ceil

from league import app, db, bcrypt
from league.forms import RegistrationForm, LoginForm, CreateLeagueForm, RegisterPlayerForm, StartLeagueForm, RemovePlayerForm, AddPlayerForm, EndLeagueForm
from league.models import User, League, Group, Player

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
        return redirect(url_for('home'))

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
    if league.date_started is not None:
        end_form = EndLeagueForm()
        if end_form.end.data and end_form.validate():
            league.date_ended = end_form.date_ended.data
            db.session.commit()
            flash(f"League '{league.name}' ended successfully!", 'success')
            return redirect(url_for('home'))

    _to_add = Player.query.filter(~Player.id.in_([p.id for p in league.players])).all()
    to_remove = [(p.id, p.name + " " + p.last_name) for p in league.players]
    to_add = [(p.id, p.name + " " + p.last_name) for p in _to_add]

    start_form = StartLeagueForm()
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
            nplayers=len(to_remove))

def generate_league_matches(league, gsize, num_phases):
    nplayers = len(league.players)
    ngroups = ceil(nplayers / gsize)
    groups=[]
    for i in range(ngroups):
        groups.append(Group(league=league, size=gsize))

    for i in range(nplayers):
        loc = divmod(i, ngroups)[1]
        groups[loc].players.append(league.players[i])

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
