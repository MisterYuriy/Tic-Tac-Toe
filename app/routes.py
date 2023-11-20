from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from app import app
from app.database import Session
from app.models import Player, Season
from app.views.game import (
    GameGroupView,
    GameItemView,
    HomeView,
    IndexView,
    LogoutView,
    MovesView,
    SignInView,
    SignUpView,
    StatsView,
)
from app.views.management import PlayersGamesStats, PlayersStatisticsView, PlayersView

app.add_url_rule(rule="/", view_func=IndexView.as_view("index"))
app.add_url_rule(rule="/games", view_func=GameGroupView.as_view("games-group"))
app.add_url_rule(rule="/games/<game_id>", view_func=GameItemView.as_view("games-item"))
app.add_url_rule(
    rule="/games/<game_id>/moves/<int:row>-<int:col>",
    view_func=MovesView.as_view("moves"),
)
app.add_url_rule(rule="/sign-in", view_func=SignInView.as_view("sign-in"))
app.add_url_rule(rule="/sign-up", view_func=SignUpView.as_view("sign-up"))
app.add_url_rule(rule="/home", view_func=HomeView.as_view("home"))
app.add_url_rule(rule="/logout", view_func=LogoutView.as_view("logout"))
app.add_url_rule(rule="/stats", view_func=StatsView.as_view("stats"))

# Management routes
admin = Admin(
    app,
    name="Management",
    template_mode="bootstrap4",
    index_view=PlayersStatisticsView(
        name="Rank Table", url="/management", endpoint="management"
    ),
)
admin.add_view(PlayersGamesStats(name="Statistics", endpoint="stats"))

with Session() as session:
    admin.add_view(PlayersView(Player, session))
    admin.add_view(ModelView(Season, session))
