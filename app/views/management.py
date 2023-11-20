import io

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from flask import Response, url_for
from flask_admin import AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from markupsafe import Markup

from app.database import Session
from app.models import Game, Player
from app.views.utils import get_active_season


class PlayersView(ModelView):
    def _nickname_formatter(self, *args):
        _, model, _ = args
        return Markup(
            f"<a href={url_for('player.details_view', id=model.id)}>{model.nickname}</a>"
        )

    column_formatters = {"nickname": _nickname_formatter}
    form_columns = ("nickname", "password", "age", "email")
    can_view_details = True


class PlayersStatisticsView(AdminIndexView):
    @expose("/")
    def index(self):
        with Session() as session:
            season = get_active_season(session).scalar()
            return self.render("management/rank_table.html", season=season)


class PlayersGamesStats(BaseView):
    @expose("/")
    def stats(self):
        return self.render("management/stats.html")

    @expose("/plot")
    def plot(self):
        fig = self._create_figure()
        output = io.BytesIO()
        fig.savefig(output)
        return Response(output.getvalue(), mimetype="image/png")

    def _create_figure(self):
        fig, ax = plt.subplots()
        with Session() as session:
            players = session.query(Player).all()
            players_data = self._get_data(players)
            games = session.query(Game).all()
            games_data = self._get_data(games)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator())
        ax.plot(list(players_data.keys()), list(players_data.values()), label="Players")
        ax.plot(list(games_data.keys()), list(games_data.values()), label="Games")
        ax.legend()
        ax.set_xlabel("Days")
        ax.set_ylabel("Quantity")
        plt.gcf().autofmt_xdate()
        return fig

    def _get_data(self, entities):
        data = {}
        for entity in entities:
            created_date = entity.created.date()
            if data.get(created_date):
                data[created_date] += 1
            else:
                data[created_date] = 1
        return data
