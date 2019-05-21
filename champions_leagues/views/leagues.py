import flask
import flask_login
from functools import reduce
from itertools import groupby, dropwhile
from hashlib import sha1

import champions_leagues.models as models

leagues = flask.Blueprint('leagues', __name__, url_prefix='/leagues')

@leagues.route("/")
def list_leagues():
    leagues = filter(lambda l: l.date_started, models.League.query.all())
    return flask.render_template('leagues/list.html', leagues=leagues)

@leagues.route("/<id>/matches")
def matches(id):
    active_phase = flask.request.args.get('phase')
    active_phase = 0 if active_phase is None else active_phase

    league = League(id)
    return flask.render_template(
        'leagues/matches.html',
        league=league,
        active_phase=active_phase
    )

@leagues.route("/<id>/match/<match_id>")
def match(id, match_id):
    return flask.redirect(flask.url_for('leagues.phases', id=id))


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
