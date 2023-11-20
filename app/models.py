import datetime
import enum
import uuid

import sqlalchemy as db
from flask_jwt_extended import create_access_token
from sqlalchemy import JSON
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, relationship

from app import bcrypt
from app.database import Session, engine

ALLOWED_SIGNS = ["X", "O", "Y", "U", "P"]


class ValidationError(Exception):
    pass


class Base(DeclarativeBase):
    pass


Base.metadata.create_all(engine)

GamePlayer = db.Table(
    "game_player",
    Base.metadata,
    db.Column("game_id", db.Text(length=36), db.ForeignKey("games.id")),
    db.Column("player_id", db.Text(length=36), db.ForeignKey("players.id")),
)


class GameStatus(enum.Enum):
    created = "created"
    finished = "finished"


class Game(Base):
    __tablename__ = "games"
    id = db.Column(
        "id", db.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=True
    )
    players_number = db.Column(db.Integer())
    status = db.Column(db.Enum(GameStatus), default=GameStatus.created.value)
    season_id = db.Column(db.Text(length=36), db.ForeignKey("seasons.id"))
    winner_id = db.Column(db.Text(length=36), db.ForeignKey("players.id"))
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow())

    _players_order = db.Column(MutableList.as_mutable(JSON), default=list)
    _players_signs = db.Column(MutableDict.as_mutable(JSON), default=dict)

    players = relationship("Player", secondary=GamePlayer, back_populates="games")
    moves = relationship("Move", cascade="all, delete-orphan")
    winner = relationship("Player", foreign_keys="Game.winner_id")

    @property
    def name(self):
        return " vs ".join(player.nickname for player in self.players)

    @property
    def is_open(self):
        return len(self.players) < self.players_number

    @property
    def participants(self):
        return [
            f"{player.nickname} ({self._players_signs[player.id]})"
            for player in self.players
        ]

    @property
    def next_player(self):
        next_player_id = self._players_order[0] if self._players_order else None
        if not next_player_id:
            return None
        for player in self.players:
            if player.id == next_player_id:
                return player
        return None

    def is_participant(self, player_id):
        return player_id in self._players_order

    def add_participant(self, player):
        self.players.append(player)
        self._players_order.append(player.id)
        self._set_sign(player.id)

    def _set_sign(self, player_id):
        self._players_signs[player_id] = ALLOWED_SIGNS[len(self.players) - 1]

    def check_order(self, player_id):
        return player_id == self._players_order[0]

    def get_move(self, row, col):
        filtered_moves = [
            move for move in self.moves if move.row == row and move.column == col
        ]
        return filtered_moves[0] if filtered_moves else None

    def make_move(self, player_id, col, row):
        move = Move(
            column=col,
            row=row,
            sign=self._players_signs.get(player_id),
            player_id=player_id,
            game_id=self.id,
        )
        self._change_order()
        return move

    def _change_order(self):
        first_player = self._players_order.pop(0)
        self._players_order = [*self._players_order, first_player]

    def check_move(self, completed_move):
        moves = [
            move for move in self.moves if move.player_id == completed_move.player_id
        ]
        return (
            self._check_rows(completed_move, moves)
            or self._check_columns(completed_move, moves)
            or self._check_diagonals(completed_move, moves)
        )

    def _check_rows(self, completed_move, moves):
        moves_by_row = [move for move in moves if move.row == completed_move.row]
        return len(moves_by_row) == self.players_number

    def _check_columns(self, completed_move, moves):
        moves_by_column = [
            move for move in moves if move.column == completed_move.column
        ]
        return len(moves_by_column) == self.players_number

    def _check_diagonals(self, completed_move, moves):
        moves_by_diagonal = []
        if completed_move.row == completed_move.column:
            moves_by_diagonal = [move for move in moves if move.row == move.column]
        if completed_move.row == self.players_number - completed_move.column:
            moves_by_diagonal = [
                move for move in moves if move.row == self.players_number - move.column
            ]
        return len(moves_by_diagonal) == self.players_number

    def finish(self, winner_id):
        self.winner_id = winner_id
        self.status = "finished"
        for player in self.players:
            if player.id == winner_id:
                player.rank += 2
            else:
                player.rank += 1


class Move(Base):
    __tablename__ = "moves"
    id = db.Column(
        "id", db.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=True
    )
    column = db.Column(db.Integer())
    row = db.Column(db.Integer())
    sign = db.Column(db.String(length=1))
    player_id = db.Column(db.Text(length=36), db.ForeignKey("players.id"))
    game_id = db.Column(db.Text(length=36), db.ForeignKey("games.id"))

    def __repr__(self):
        return self.sign


class Player(Base):
    __tablename__ = "players"

    id = db.Column(
        "id", db.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=True
    )
    nickname = db.Column(db.String(100), nullable=False, unique=True)
    _password = db.Column(db.String(30), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String(250), nullable=True, unique=True)
    rank = db.Column(db.Integer, default=0)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow())

    games = relationship("Game", secondary=GamePlayer, back_populates="players")

    __table_args__ = (db.UniqueConstraint("nickname", "email"),)

    @hybrid_property
    def password(self):
        """Return the hashed user password."""
        return self._password

    @password.setter
    def password(self, new_pass):
        """Hash and save the user's new password."""
        new_password_hash = bcrypt.generate_password_hash(new_pass).decode("utf-8")
        self._password = new_password_hash

    def get_token(self, expire_time=6):
        expire_delta = datetime.timedelta(expire_time)
        return create_access_token(identity=self.id, expires_delta=expire_delta)

    @classmethod
    def authenticate(cls, nickname, password):
        with Session() as session:
            player = session.query(Player).where(Player.nickname == nickname).scalar()
            if not player:
                raise ValidationError(f"Player {nickname} does not exist!")
            if not bcrypt.check_password_hash(player.password, password):
                raise ValidationError("Password is not valid!")
            return player


class SeasonStatus(enum.Enum):
    active = "active"
    inactive = "inactive"


class Season(Base):
    __tablename__ = "seasons"
    id = db.Column(
        "id", db.Text(length=36), default=lambda: str(uuid.uuid4()), primary_key=True
    )
    name = db.Column(db.String(200), unique=True)
    status = db.Column(db.Enum(SeasonStatus), default=SeasonStatus.active.value)
    created = db.Column(db.DateTime(), default=datetime.datetime.utcnow())

    games = relationship("Game", cascade="all, delete-orphan")

    __table_args__ = (db.UniqueConstraint("name"),)

    @property
    def top_players(self):
        return sorted(
            set(player for game in self.games for player in game.players),
            key=lambda player: player.rank,
            reverse=True,
        )
