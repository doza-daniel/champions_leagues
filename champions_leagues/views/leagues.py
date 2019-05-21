import flask
from functools import reduce
from itertools import groupby, dropwhile
from hashlib import sha1

import champions_leagues.models as models

leagues = flask.Blueprint('leagues', __name__, url_prefix='/leagues')

@leagues.route("/")
def list_leagues():
    leagues = filter(lambda l: l.date_started, models.League.query.all())
    return flask.render_template('leagues/list.html', leagues=leagues)

@leagues.route("/<id>")
def phases(id):
    active_phase = flask.request.args.get('phase')
    league = League(id)
    return flask.render_template(
        'leagues/phases.html',
        league=league,
        active_phase=active_phase
    )


class League():
    def __init__(self, id):
        self.league = models.League.query.get(id)

        def calc_encounter_score(match):
            p1 = 1 if match.player_one_score > match.player_two_score else 0
            p2 = 1 if match.player_two_score > match.player_one_score else 0
            return (p1, p2)

        def pair_add(p1, p2):
           return (p1[0] + p2[0], p1[1] + p2[1])

        self.phases = {}

        by_phase = lambda match: match.group.phase
        for phase_num, matches in groupby(sorted(self.league.matches, key=by_phase), by_phase):
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

    def encounter_key(self, match):
        return '-'.join([str(match.player_one.id), str(match.player_two.id)])

    def current_phase(self):
        for key in sorted(self.phases.keys()):
            if not all(map(lambda e: e[1]['done'], self.phases[key]['encounters'].items())):
                return key
        return None
