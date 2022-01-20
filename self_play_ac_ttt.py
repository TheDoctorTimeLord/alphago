import argparse
import h5py
from collections import namedtuple

from dlgo import rl
from ttt_big import GameState, compute_game_result
from dlgo.gotypes import Player


class GameRecord(namedtuple('GameRecord', 'winner')):
    pass


def simulate_game(black_player, white_player, game_index, in_debug):
    game = GameState.new_game(BOARD_SIZE)
    agents = {
        Player.black: black_player,
        Player.white: white_player,
    }
    while not game.is_over():
        next_move = agents[game.next_player].select_move(game)
        game = game.apply_move(next_move)
    game_result = compute_game_result(game)

    print(game_result, 'game_num:', game_index, end=' ')
    if in_debug:
        print('   -----', str(game.board._grid).replace("<Player.black: 1>", "1").replace("<Player.white: 2>", "2"))
    else:
        print()

    return GameRecord(
        winner=game_result.winner
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--board-size', type=int, required=True)
    parser.add_argument('--learning-agent', required=True)
    parser.add_argument('--num-games', '-n', type=int, default=10)
    parser.add_argument('--experience-out', required=True)
    parser.add_argument('--debug', action='store_true')

    args = parser.parse_args()
    agent_filename = args.learning_agent
    experience_filename = args.experience_out
    num_games = args.num_games
    global BOARD_SIZE
    BOARD_SIZE = args.board_size

    agent1 = rl.load_ac_agent(h5py.File(agent_filename))
    agent2 = rl.load_ac_agent(h5py.File(agent_filename))
    collector1 = rl.ExperienceCollector()
    collector2 = rl.ExperienceCollector()
    agent1.set_collector(collector1)
    agent2.set_collector(collector2)

    for i in range(num_games):
        collector1.begin_episode()
        collector2.begin_episode()

        game_record = simulate_game(agent1, agent2, i + 1, args.debug)
        if game_record.winner == Player.black:
            collector1.complete_episode(reward=1)
            collector2.complete_episode(reward=-1)
        else:
            collector2.complete_episode(reward=1)
            collector1.complete_episode(reward=-1)

    experience = rl.combine_experience([collector1, collector2])
    with h5py.File(experience_filename, 'w') as experience_outf:
        experience.serialize(experience_outf)


if __name__ == '__main__':
    main()
