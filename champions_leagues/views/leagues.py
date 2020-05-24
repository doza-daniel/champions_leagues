import flask
import flask_login
from functools import reduce
from itertools import groupby, combinations
from datetime import date

from random import shuffle

import champions_leagues.models as models
import champions_leagues.forms as forms
from champions_leagues import db

leagues = flask.Blueprint('leagues', __name__, url_prefix='/leagues')

@leagues.route("/")
def list_leagues():
    owned = flask.request.args.get('owned')
    leagues = []
    if flask_login.current_user.is_authenticated and owned:
        leagues = models.League.query.filter_by(owner=flask_login.current_user)
    else:
        leagues = models.League.query.filter(models.League.date_started != None)
    return flask.render_template('leagues/list.html', leagues=leagues)

@leagues.route("/<id>/main_view")
def main_view(id):
    league = League(id)
    page = flask.request.args.get('page')
    if page is None:
        page = 'groups'

    return flask.render_template(
        f'leagues/{page}.html',
        league=league
    )

@leagues.route("/<id>/start", methods=['GET', 'POST'])
@flask_login.login_required
def start(id):
    league = models.League.query.get(id)
    _to_add = models.Player.query.filter(~models.Player.id.in_([p.id for p in league.players])).all()
    to_remove = [(p.id, p.name + " " + p.last_name) for p in league.players]
    to_add = [(p.id, p.name + " " + p.last_name) for p in _to_add]

    start_form = forms.StartLeagueForm(league)
    remove_form = forms.RemovePlayerForm(to_remove)
    add_form = forms.AddPlayerForm(to_add)

    if start_form.start.data and start_form.validate():
        flask.flash(f"League has been started successfully!", 'success')
        league.date_started = date.today()
        generate_league_matches(league)
        db.session.commit()
        return flask.redirect(flask.url_for('leagues.main_view', id=id))

    if add_form.add.data and add_form.validate():
        for pID in add_form.players_to_add.data:
            league.players.append(models.Player.query.get(pID))
        db.session.commit()
        return flask.redirect(flask.url_for('leagues.start', id=id))

    if remove_form.remove.data and remove_form.validate():
        league.players = [p for p in league.players if p.id not in remove_form.players_to_remove.data]
        db.session.commit()
        return flask.redirect(flask.url_for('leagues.start', id=id))

    return flask.render_template(
        'leagues/start.html',
        title='Start League',
        start_form=start_form,
        remove_form=remove_form,
        add_form=add_form,
    )

@leagues.route("/<id>/leaderboards")
def leaderboards(id):
    league = League(id)
    return flask.render_template('leagues/leaderboards.html', leaderboards=league.leaderboards(), league=league)

@leagues.route("/create", methods=['GET', 'POST'])
@flask_login.login_required
def create():
    form = forms.CreateLeagueForm()
    if form.validate_on_submit():
        league = models.League(owner=flask_login.current_user, name=form.name.data)
        db.session.add(league)
        db.session.commit()
        flask.flash(f"League '{league.name}' has been created successfully!", 'success')
        return flask.redirect(flask.url_for('leagues.start', id=league.id))

    return flask.render_template('leagues/create.html', title='Create League', form=form)

@leagues.route("/<int:id>/match/<int:match_id>", methods=['GET', 'POST'])
@flask_login.login_required
def match(id, match_id):
    match = models.Match.query.get(match_id)
    if not flask_login.current_user == match.league.owner:
        flask.flash('Make sure you are logged in and authorize to change scores on this match.', 'danger')
        return flask.redirect(flask.url_for('home'))

    form = forms.EditMatchForm(match)
    print(form.player_one_score.label)
    if form.validate_on_submit():
        match.player_one_score = form.player_one_score.data
        match.player_two_score = form.player_two_score.data
        match.played_on = form.played_on.data
        db.session.commit()
        flask.flash('Match finished successfully!', 'success')
        next_page = flask.request.args.get('next')
        return flask.redirect(next_page) if next_page else flask.redirect(flask.url_for('leagues.main_view', id=id))

    return flask.render_template('leagues/finish_match.html', form=form)


@leagues.route("/<id>/encounter")
def encounter(id):
    league = League(id)

    group_id = int(flask.request.args.get('group_id'))
    encounter_id = flask.request.args.get('encounter_id')

    owner = None
    if flask_login.current_user.is_authenticated and flask_login.current_user == league.model.owner:
        owner = league.model.owner

    return flask.render_template(
        'leagues/encounter.html',
        encounter=league.encounter(group_id, encounter_id),
        league=league,
        owner=owner
    )


class League():
    def __init__(self, id):
        self.model = models.League.query.get(id)

        def calc_encounter_score(match):
            p1 = 1 if match.player_one_score > match.player_two_score else 0
            p2 = 1 if match.player_two_score > match.player_one_score else 0
            return (p1, p2)

        def pair_add(p1, p2):
           return (p1[0] + p2[0], p1[1] + p2[1])

        self.groups = {}
        all_matches = self.model.matches

        by_group_id = lambda match: match.group.id
        for group_id, group_matches in groupby(sorted(all_matches, key=by_group_id), by_group_id):
            self.groups[group_id] = {'group': models.Group.query.get(group_id), 'encounters': {}}

            for encounter_id, encounter_matches in groupby(sorted(group_matches, key=self.encounter_key), self.encounter_key):
                encounter_matches = list(encounter_matches)

                scores = reduce(
                        lambda scores, match: pair_add(scores, calc_encounter_score(match)),
                        encounter_matches,
                        (0, 0)
                )

                self.groups[group_id]['encounters'][encounter_id] = {
                    'matches': encounter_matches,
                    'p1': scores[0],
                    'p2': scores[1],
                    'done': all(map(lambda x: x.played_on, encounter_matches)),
                }


    def encounter(self, group_id, encounter_id):
        return self.groups[group_id]['encounters'][encounter_id]

    def encounter_key(self, match):
        return '-'.join([str(match.player_one.id), str(match.player_two.id)])

    def number_of_matches_played(self, p):
        count = 0
        for _, group in self.groups.items():
            for _, encounter in group['encounters'].items():
                m = encounter['matches'][0]
                if encounter['done'] and (m.player_one == p or m.player_two == p):
                    count += 1
        return count

    def calculate_scores(self, encounter):
        player_one_score = {"total": 0, "goal_difference": 0}
        player_two_score = {"total": 0, "goal_difference": 0}
        if encounter["done"]:
            if encounter["p1"] > encounter["p2"]:
                player_one_score["total"] = 3
                player_two_score["total"] = 0

            elif encounter["p2"] > encounter["p1"]:
                player_two_score["total"] = 3
                player_one_score["total"] = 0
            else:
                player_two_score["total"] = 1
                player_one_score["total"] = 1

                player_one_score["goal_difference"] = 0
                player_two_score["goal_difference"] = 0

        for match in encounter["matches"]:
            player_one_score["goal_difference"] += match.player_one_score - match.player_two_score
            player_two_score["goal_difference"] += match.player_two_score - match.player_one_score

        return (player_one_score, player_two_score)

    def leaderboards(self):
        leaderboards = []
        for _, v in self.groups.items():
            group = v['group']
            leaderboard = {
                    p: {"goal_difference": 0, "total": 0, "nplayed": self.number_of_matches_played(p)}
                    for p in group.players
            }

            for _, encounter in v['encounters'].items():
                p1 = encounter['matches'][0].player_one
                p2 = encounter['matches'][0].player_two
                scores = self.calculate_scores(encounter)
                leaderboard[p1]["total"] += scores[0]["total"]
                leaderboard[p1]["goal_difference"] += scores[0]["goal_difference"]
                leaderboard[p2]["total"] += scores[1]["total"]
                leaderboard[p2]["goal_difference"] += scores[1]["goal_difference"]

            leaderboards.append(leaderboard)


        sorted_leaderboards = []
        for leaderboard in leaderboards:
            sorted_leaderboard = sorted(leaderboard.items(), reverse=True,
                    key=lambda item: item[1]["total"]*1000 + item[1]["goal_difference"])
            sorted_leaderboards.append(sorted_leaderboard)

        return sorted_leaderboards

def generate_league_matches(league):
    shuffle(league.players)

    groups = [models.Group(league=league, phase=0), models.Group(league=league, phase=0)]

    for i in range(len(league.players)):
        groups[i%2].players.append(league.players[i])

    for group in groups:
        group.size = len(group.players)
        db.session.add(group)
        for p1, p2 in combinations(group.players, 2):
            db.session.add(models.Match(player_one=p1, player_two=p2, league=league, group=group))
            db.session.add(models.Match(player_one=p1, player_two=p2, league=league, group=group))

    db.session.commit()

