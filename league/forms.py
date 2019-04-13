from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField,  IntegerField, SelectMultipleField
from wtforms.fields.html5 import DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from datetime import date
from league.models import User


class RegistrationForm(FlaskForm):
    username = StringField('Username',
                           validators=[DataRequired(), Length(min=2, max=20)])
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
    date_started = DateField('Start Date', default=date.today(), format='%Y-%m-%d')
    group_size = IntegerField('Group Size', default=1, validators=[DataRequired()])
    number_of_phases = IntegerField('Number of phases', default=1, validators=[DataRequired()])
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
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=20)], render_kw={'autofocus': True})
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=20)])

    submit = SubmitField('Register Player')
