from flask import render_template, url_for, redirect, flash, request
from flask_login import current_user, login_user, logout_user, login_required

from champions_leagues import app, db, bcrypt
from champions_leagues.forms import RegistrationForm, LoginForm,  RegisterPlayerForm
from champions_leagues.models import User, League, Group, Player, Match

@app.route("/")
@app.route("/home")
def home():
    return redirect(url_for('leagues.list_leagues'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(flask.url_for('home'))
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

@app.route("/register_player", methods=['GET', 'POST'])
@login_required
def register_player():
    players = Player.query.all()
    form = RegisterPlayerForm()
    if form.validate_on_submit():
        p = Player(name=form.name.data, last_name=form.last_name.data)
        db.session.add(p)
        db.session.commit()
        flash(f"Player has been registered successfully!", 'success')
        return redirect(url_for('register_player'))

    return render_template('register_player.html', title='Register Player',
                           form=form, players=players)

