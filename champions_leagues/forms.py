from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField,  IntegerField, SelectMultipleField, Label
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange, EqualTo
from datetime import date
from math import ceil, sqrt
from champions_leagues.models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(),
                           Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class CreateLeagueForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=20)])

    submit = SubmitField('Create league')

class StartLeagueForm(FlaskForm):
    def __init__(self, league, *args, **kwargs):
        super(StartLeagueForm, self).__init__(*args, **kwargs)
        self.league = league

    start = SubmitField('Start league')


class EndLeagueForm(FlaskForm):
    date_ended = DateField('End Date', default=date.today(), format='%Y-%m-%d')
    end = SubmitField('End league')

class RemovePlayerForm(FlaskForm):
    def __init__(self, choices, *args, **kwargs):
        super(RemovePlayerForm, self).__init__(*args, **kwargs)
        self.players_to_remove.choices = choices

    players_to_remove = SelectMultipleField('Players to remove from league', coerce=int)
    remove = SubmitField('Remove')

class AddPlayerForm(FlaskForm):
    def __init__(self, choices, *args, **kwargs):
        super(AddPlayerForm, self).__init__(*args, **kwargs)
        self.players_to_add.choices = choices

    players_to_add = SelectMultipleField('Players to add to league', coerce=int)
    add = SubmitField('Add')

class RegisterPlayerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=20)],
                       render_kw={'autofocus': True})

    last_name = StringField('Last Name', validators=[DataRequired(),
                            Length(min=2, max=20)])

    submit = SubmitField('Register Player')

class EditMatchForm(FlaskForm):
    def __init__(self, match, *args, **kwargs):
        super(EditMatchForm, self).__init__(*args, **kwargs)
        self.player_one_score.label = Label(self.player_one_score.id, f"{match.player_one.name} {match.player_one.last_name}")
        self.player_two_score.label = Label(self.player_two_score.id, f"{match.player_two.name} {match.player_two.last_name}")

    player_one_score = IntegerField(validators=[NumberRange(min=0)], default=0)
    player_two_score = IntegerField(validators=[NumberRange(min=0)], default=0)
    played_on = DateField('Played on', default=date.today(), format='%Y-%m-%d')
    submit = SubmitField('Finish match')

    def validate(self):
        if not FlaskForm.validate(self):
            return False
        valid = self.player_one_score.data != self.player_two_score.data
        if not valid:
            self.player_one_score.errors.append("can't be equal")
            self.player_two_score.errors.append("can't be equal")

        return valid
