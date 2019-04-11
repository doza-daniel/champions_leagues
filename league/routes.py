from flask import render_template, url_for, redirect, flash
from flask_login import current_user, login_user, logout_user, login_required

from league import app, db, bcrypt
from league.forms import RegistrationForm, LoginForm, CreateLeagueForm, RegisterPlayerForm
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


@app.route("/register_player", methods=['GET', 'POST'])
@login_required
def register_player():
    form = RegisterPlayerForm()
    if form.validate_on_submit():
        p = Player(name=form.name.data, last_name=form.last_name.data)
        db.session.add(p)
        db.session.commit()
        flash(f"Player has been registered successfully!", 'success')

    return render_template('register_player.html', title='Register Player', form=form)
