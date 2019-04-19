from datetime import datetime
from league import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

leagues_have_players = db.Table(
        'leagues_have_players',
        db.Column('league_id', db.Integer, db.ForeignKey('leagues.id'), nullable=False),
        db.Column('player_id', db.Integer, db.ForeignKey('players.id'), nullable=False),
        db.PrimaryKeyConstraint('player_id', 'league_id')
)


groups_have_players = db.Table(
        'groups_have_players',
        db.Column('group_id', db.Integer, db.ForeignKey('groups.id'), nullable=False),
        db.Column('player_id', db.Integer, db.ForeignKey('players.id'), nullable=False),
        db.Column('phase', db.Integer, default=0, nullable=False),
        db.PrimaryKeyConstraint('player_id', 'group_id')
)


class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)

    leagues = db.relationship(
            "League",
            secondary=leagues_have_players,
            back_populates="players")

    def __repr__(self):
        return f"Player({self.id}, '{self.name}', '{self.last_name}')"


class League(db.Model):
    __tablename__ = 'leagues'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    date_started = db.Column(db.DateTime)
    date_ended = db.Column(db.DateTime)
    groups = db.relationship('Group', backref='league', lazy=True)
    players = db.relationship(
            "Player",
            secondary=leagues_have_players,
            back_populates="leagues")

    matches = db.relationship("Match", backref='league', lazy=True)

class Match(db.Model):
    __tablename__ = 'matches'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    player_one_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    player_two_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False)
    player_one_score = db.Column(db.Integer, default=0, nullable=False)
    player_two_score = db.Column(db.Integer, default=0, nullable=False)
    played_on = db.Column(db.DateTime)
    player_one = db.relationship(Player, foreign_keys=player_one_id)
    player_two = db.relationship(Player, foreign_keys=player_two_id)


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False)
    players = db.relationship('Player', secondary=groups_have_players, backref='groups')
    size = db.Column(db.Integer, nullable=False)
    phase = db.Column(db.Integer, nullable=False)
    matches = db.relationship('Match', backref='group', lazy=True)



class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    leagues = db.relationship('League', backref='owner', lazy=True)
