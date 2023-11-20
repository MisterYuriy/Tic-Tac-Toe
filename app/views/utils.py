from app.models import Game, Player, Season, SeasonStatus


def get_active_season(session):
    return session.query(Season).where(Season.status == SeasonStatus.active.value)


def get_game(session, game_id):
    return session.query(Game).where(Game.id == game_id)


def get_player(session, player_id):
    return session.query(Player).where(Player.id == player_id)
