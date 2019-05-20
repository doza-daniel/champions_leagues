import flask
from champions_leagues.models import League

leagues = flask.Blueprint('leagues', __name__, url_prefix='/leagues')

@leagues.route("/")
def list():
    leagues = filter(lambda l: l.date_started, League.query.all())
    return flask.render_template('leagues/list.html', leagues=leagues)

class LeagueService():
    pass
