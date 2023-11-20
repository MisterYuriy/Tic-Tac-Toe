from flask import make_response, redirect, render_template, request, url_for
from flask.views import MethodView
from flask_jwt_extended import (
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)
from sqlalchemy.exc import IntegrityError

from app.database import Session
from app.models import Game, Player, ValidationError
from app.views.utils import get_active_season, get_game, get_player


class IndexView(MethodView):
    def get(self):
        return render_template("index.html")


class SignUpView(MethodView):
    def get(self):
        return render_template("sign_up.html")

    def post(self):
        with Session() as session:
            try:
                player = Player(**request.form)
                session.add(player)
                session.commit()
            except IntegrityError:
                session.rollback()
                return render_template(
                    "sign_up.html", error="This Nickname or email already exists"
                )
            resp = make_response(redirect(url_for("home")))
            set_access_cookies(resp, player.get_token())
            return resp


class SignInView(MethodView):
    def get(self):
        return render_template("sign_in.html")

    def post(self):
        nickname, password = request.form.get("nickname"), request.form.get("password")
        try:
            player = Player.authenticate(nickname, password)
        except ValidationError as exc:
            return render_template("sign_in.html", error=str(exc))

        resp = make_response(redirect(url_for("home")))
        set_access_cookies(resp, player.get_token())
        return resp


class LogoutView(MethodView):
    def get(self):
        resp = make_response(redirect(url_for("index")))
        unset_jwt_cookies(resp)
        return resp


class HomeView(MethodView):
    @jwt_required()
    def get(self):
        player_id = get_jwt_identity()
        with Session() as session:
            player = session.query(Player).where(Player.id == player_id).scalar()
            season = get_active_season(session)
        return render_template("home.html", player=player, season=season.scalar())


class GameGroupView(MethodView):
    def get(self):
        return render_template("create_game.html")

    def post(self):
        players = request.form.get("players")
        with Session() as session:
            season = get_active_season(session).scalar()
            game = Game(players_number=int(players), season_id=season.id)
            session.add(game)
            session.commit()
            return redirect(url_for("games-item", id=game.id))


class GameItemView(MethodView):
    @jwt_required()
    def get(self, game_id):
        with Session() as session:
            player_id = get_jwt_identity()
            game = get_game(session, game_id).scalar()
            player = get_player(session, player_id).scalar()
            if not game.is_participant(player_id):
                game.add_participant(player)
                session.add(game)
                session.commit()
            return render_template("game.html", game=game, player=player)


class MovesView(MethodView):
    @jwt_required()
    def get(self, game_id, row, col):
        player_id = get_jwt_identity()
        with Session() as session:
            game = get_game(session, game_id).scalar()
            if game.status == "finished":
                return redirect(url_for("game-item", id=game_id))

            player = get_player(session, player_id).scalar()
            if game.get_move(row, col):
                return render_template(
                    "game.html",
                    game=game,
                    player=player,
                    error=f"Move with row {row} and col {col} exist!",
                )

            if not game.check_order(player_id):
                return render_template(
                    "game.html",
                    game=game,
                    player=player,
                    error=f"Next {game.next_player.nickname}",
                )

            move = game.make_move(player_id, col, row)
            session.add(move)

            if game.check_move(move):
                game.finish(player_id)
                session.add(game)

            session.commit()
            return redirect(url_for("games-item", id=game_id))


class StatsView(MethodView):
    @jwt_required()
    def get(self):
        player_id = get_jwt_identity()
        with Session() as session:
            player = get_player(session, player_id).scalar()
            return render_template("management/stats.html", player=player)
