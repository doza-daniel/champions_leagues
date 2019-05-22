import flask
import flask_login
from functools import reduce
from itertools import groupby
from hashlib import sha1

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
        leagues = models.League.query.filter(models.League.date_started is not None)
    return flask.render_template('leagues/list.html', leagues=leagues)

@leagues.route("/<id>/phases/", defaults={'phase_num':0})
@leagues.route("/<id>/phases/<int:phase_num>")
def phases(id, phase_num=0):
    league = League(id)
    page = flask.request.args.get('page')
    if page is None:
        page = 'groups'
    return flask.render_template(
        f'leagues/{page}.html',
        current_phase=league.phases[phase_num],
        current_phase_num=phase_num,
        max_phases=3,
        league=league
    )


@leagues.route("/<id>/leaderboard")
def leaderboard(id):
    league = League(id)
    temporary_scores = {p.name + " " + p.last_name: 0 for p in league.model.players}
    return flask.render_template('leagues/leaderboard.html', scores=league.leaderboard(), league=league)

@leagues.route("/<int:id>/match/<int:match_id>", methods=['GET', 'POST'])
@flask_login.login_required
def match(id, match_id):
    match = models.Match.query.get(match_id)
    if not flask_login.current_user == match.league.owner:
        flask.flash('Make sure you are logged in and authorize to change scores on this match.', 'danger')
        return flask.redirect(flask.url_for('home'))

    form = forms.EditMatchFormm(match)
    print(form.player_one_score.label)
    if form.validate_on_submit():
        match.player_one_score = form.player_one_score.data
        match.player_two_score = form.player_two_score.data
        match.played_on = form.played_on.data
        db.session.commit()
        flask.flash('Match finished successfully!', 'success')
        next_page = flask.request.args.get('next')
        return flask.redirect(next_page) if next_page else flask.redirect(flask.url_for('leagues.phases', id=id))

    return flask.render_template('leagues/finish_match.html', form=form)


@leagues.route("/<id>/encounter")
def encounter(id):
    league = League(id)

    phase_num = int(flask.request.args.get('phase_num'))
    group_id = int(flask.request.args.get('group_id'))
    encounter_id = flask.request.args.get('encounter_id')

    owner = None
    if flask_login.current_user.is_authenticated and flask_login.current_user == league.model.owner:
        owner = league.model.owner

    return flask.render_template(
        'leagues/encounter.html',
        encounter=league.encounter(phase_num, group_id, encounter_id),
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

        self.phases = {}

        by_phase = lambda match: match.group.phase
        for phase_num, matches in groupby(sorted(self.model.matches, key=by_phase), by_phase):
            self.phases[phase_num] = {}
            self.phases[phase_num]['groups'] = {}

            by_group_id = lambda match: match.group.id
            for group_id, matches in groupby(sorted(matches, key=by_group_id), by_group_id):
                self.phases[phase_num]['groups'][group_id] = {'group': models.Group.query.get(group_id), 'encounters': {}}

                for encounter_id, matches in groupby(sorted(matches, key=self.encounter_key), self.encounter_key):
                    matches = list(matches)

                    scores = reduce(lambda scores, match: pair_add(scores, calc_encounter_score(match)), matches, (0, 0))
                    self.phases[phase_num]['groups'][group_id]['encounters'][encounter_id] = {
                        'matches': matches,
                        'p1': scores[0],
                        'p2': scores[1],
                        'done': all(map(lambda x: x.played_on, matches)),
                    }

    def encounter(self, phase_num, group_id, encounter_id):
        return self.phases[phase_num]['groups'][group_id]['encounters'][encounter_id]

    def encounter_key(self, match):
        return '-'.join([str(match.player_one.id), str(match.player_two.id)])

    def current_phase(self):
        for key in sorted(self.phases.keys()):
            if not all(map(lambda e: e[1]['done'], self.phases[key]['encounters'].items())):
                return key
        return None

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

    def leaderboard(self):
        leaderboard = {p: {"goal_difference": 0, "total": 0} for p in self.model.players}
        for _, phase in self.phases.items():
            for _, group in phase['groups'].items():
                for _, encounter in group['encounters'].items():
                    p1 = encounter['matches'][0].player_one
                    p2 = encounter['matches'][0].player_two
                    scores = self.calculate_scores(encounter)
                    leaderboard[p1]["total"] += scores[0]["total"]
                    leaderboard[p1]["goal_difference"] += scores[0]["goal_difference"]
                    leaderboard[p2]["total"] += scores[1]["total"]
                    leaderboard[p2]["goal_difference"] += scores[1]["goal_difference"]

        leaderboard_sorted = sorted(leaderboard.items(), reverse=True,
                key=lambda item: item[1]["total"]*1000 + item[1]["goal_difference"])

        return leaderboard_sorted


