import copy

from dlgo.gotypes import Player, Point
from dlgo import zobrist

__all__ = [
    'Board',
    'GameState',
    'Move',
    'compute_game_result'
]

from dlgo.scoring import GameResult

direction = [
    Point(1, 0),
    Point(1, 1),
    Point(0, 1),
    Point(-1, 1),
    Point(-1, 0),
    Point(-1, -1),
    Point(0, -1),
    Point(1, -1),
]


class Board:
    NUM_IN_ROW = 5

    def __init__(self, num_rows, num_cols):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self._grid = {}
        self._hash = zobrist.EMPTY_BOARD
        self.win = None
        self.stone_counter = 0

    def neighbors(self, point):
        return [Point(row=point.row + direction[i].row, col=point.col + direction[i].col) for i in range(1, len(direction), 2)]

    def corners(self, point):
        return [Point(row=point.row + direction[i].row, col=point.col + direction[i].col) for i in range(0, len(direction), 2)]

    def place_stone(self, player, point):
        assert self.is_on_grid(point)
        assert self._grid.get(point) is None
        assert self.win is None

        # Check win
        if self.win is None and self._check_win_conditions(player, point):
            self.win = player

        # remove empty-point hash code
        self._hash ^= zobrist.HASH_CODE[point, None]
        # Add filled point hash code
        self._hash ^= zobrist.HASH_CODE[point, player]

        self._grid[point] = player
        self.stone_counter += 1

    def _check_win_conditions(self, player, point):
        stones = []

        for d in direction:
            counter = 0
            cur_point = point
            for i in range(Board.NUM_IN_ROW):
                stone_in_line = Point(row=cur_point.row + d.row, col=cur_point.col + d.col)
                if not self.is_on_grid(stone_in_line) or self._grid.get(stone_in_line) != player:
                    break
                else:
                    cur_point = stone_in_line
                    counter += 1
            stones.append(counter)

        count_direction = len(direction) // 2
        for d in range(count_direction):
            if stones[d] + stones[d + count_direction] + 1 >= Board.NUM_IN_ROW:
                return True

        return False

    def is_players_stone(self, player, point):
        return self.is_on_grid(point) and self._grid.get(point) == player

    def is_self_capture(self, player, point):
        return False

    def will_capture(self, player, point):
        return False

    def is_on_grid(self, point):
        return 1 <= point.row <= self.num_rows and 1 <= point.col <= self.num_cols

    def get(self, point):
        return self._grid.get(point)

    def get_go_string(self, point):
        return None

    def __eq__(self, other):
        return isinstance(other, Board) and \
            self.num_rows == other.num_rows and \
            self.num_cols == other.num_cols and \
            self._hash() == other._hash()

    def __deepcopy__(self, memodict={}):
        copied = Board(self.num_rows, self.num_cols)
        # can do a shallow copy b/c the dictionary maps tuples
        # (immutable) to GoStrings (also immutable)
        copied._grid = copy.copy(self._grid)
        copied._hash = self._hash
        copied.win = self.win
        copied.stone_counter = self.stone_counter
        return copied

    def zobrist_hash(self):
        return self._hash


class Move:
    def __init__(self, point=None, is_pass=False, is_resign=False):
        assert (point is not None) ^ is_pass ^ is_resign
        self.point = point
        self.is_play = (self.point is not None)
        self.is_pass = is_pass
        self.is_resign = is_resign

    @classmethod
    def play(cls, point):
        return Move(point=point)

    @classmethod
    def pass_turn(cls):
        return Move(is_pass=True)

    @classmethod
    def resign(cls):
        return Move(is_resign=True)

    def __str__(self):
        if self.is_pass:
            return 'pass'
        if self.is_resign:
            return 'resign'
        return '(r %d, c %d)' % (self.point.row, self.point.col)

    def __hash__(self):
        return hash((
            self.is_play,
            self.is_pass,
            self.is_resign,
            self.point))

    def __eq__(self, other):
        return (
            self.is_play,
            self.is_pass,
            self.is_resign,
            self.point) == (
            other.is_play,
            other.is_pass,
            other.is_resign,
            other.point)


class GameState:
    def __init__(self, board, next_player, previous, move):
        self.board = board
        self.next_player = next_player
        self.previous_state = previous
        if previous is None:
            self.previous_states = frozenset()
        else:
            self.previous_states = frozenset(
                previous.previous_states |
                {(previous.next_player, previous.board.zobrist_hash())})
        self.last_move = move

    def apply_move(self, move):
        if move.is_play:
            next_board = copy.deepcopy(self.board)
            next_board.place_stone(self.next_player, move.point)
        else:
            print("Player " + str(self.next_player) + " make illegal turn [" + ("pass" if move.is_pass else "resign") + "]")
            self.board.win = self.next_player.other
            next_board = self.board
        return GameState(next_board, self.next_player.other, self, move)

    @classmethod
    def new_game(cls, board_size):
        if isinstance(board_size, int):
            board_size = (board_size, board_size)
        board = Board(*board_size)
        return GameState(board, Player.black, None, None)

    def is_move_self_capture(self, player, move):
        if not move.is_play:
            return False
        return self.board.is_self_capture(player, move.point)

    @property
    def situation(self):
        return self.next_player, self.board

    def does_move_violate_ko(self, player, move):
        return False

    def is_valid_move(self, move):
        if self.is_over():
            return False
        if move.is_pass or move.is_resign:
            return False
        return (
            self.board.get(move.point) is None and
            not self.is_move_self_capture(self.next_player, move) and
            not self.does_move_violate_ko(self.next_player, move))

    def is_over(self):
        if self.last_move is None:
            return False
        return self.board.win is not None or self.board.stone_counter >= self.board.num_rows * self.board.num_cols

    def legal_moves(self):
        if self.is_over():
            return []
        moves = []
        for row in range(1, self.board.num_rows + 1):
            for col in range(1, self.board.num_cols + 1):
                move = Move.play(Point(row, col))
                if self.is_valid_move(move):
                    moves.append(move)
        return moves

    def winner(self):
        if not self.is_over():
            return None
        if self.last_move.is_resign:
            return self.next_player
        game_result = compute_game_result(self)
        return game_result.winner


def compute_game_result(game_state: GameState):
    win = game_state.board.win
    if win == Player.black:
        return GameResult(b=Board.NUM_IN_ROW, w=0, komi=0)
    elif win == Player.white:
        return GameResult(b=0, w=Board.NUM_IN_ROW, komi=0)

    skip = set()

    max_b = 0
    max_w = 0

    for r in range(1, game_state.board.num_rows + 1):
        for c in range(1, game_state.board.num_cols + 1):
            cur_point = Point(row=r, col=c)

            if cur_point in skip:
                continue

            skip.add(cur_point)
            player = game_state.board.get(cur_point)

            if player is None:
                continue

            for d in direction[0: len(direction) // 2]:
                counter = 1
                _r = r
                _c = c
                for i in range(Board.NUM_IN_ROW):
                    stone_in_line = Point(row=_r + d.row, col=_c + d.col)
                    if not game_state.board.is_players_stone(player, stone_in_line):
                        break
                    else:
                        skip.add(stone_in_line)
                        _r = stone_in_line.row
                        _c = stone_in_line.col
                        counter += 1
                if Player.black == player and counter > max_b:
                    max_b = counter
                elif Player.white == player and counter > max_w:
                    max_w = counter

    return GameResult(b=max_b, w=max_w, komi=0)
