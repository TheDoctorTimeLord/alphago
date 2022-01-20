import argparse
import os
import subprocess

from subprocess import CompletedProcess
from sys import platform

PYTHON_CMD = 'python' if platform == "win32" else 'python3'

PATH_TO_PROJECT_ROOT = os.path.join('')
PATH_TO_AGENTS = os.path.join(PATH_TO_PROJECT_ROOT, 'agents')
PATH_TO_EXPERIENCES = os.path.join(PATH_TO_PROJECT_ROOT, 'experiences')
PATH_TO_LOG = os.path.join(PATH_TO_PROJECT_ROOT, 'log')
ERROR_LOG_FILE_PATH = os.path.join(PATH_TO_LOG, 'erlog.txt')
PROCESS_LOG_FILE_PATH = os.path.join(PATH_TO_LOG, 'prlog.txt')

PATH_TO_TTT = PATH_TO_PROJECT_ROOT

ERROR_LOG = open(ERROR_LOG_FILE_PATH, mode='w')
PROCESS_LOG = open(PROCESS_LOG_FILE_PATH, mode='w')


def print_line_pl(line: str):
    PROCESS_LOG.write(line)
    PROCESS_LOG.write('\n')
    PROCESS_LOG.flush()


class TrainProcessException(Exception):
    pass


def print_text_state(msg_before: str, msg_after: str = None, additional_lines=False):
    def func_wrapper(fn):
        def wrapper(*args, **kwargs):
            print(msg_before)
            if additional_lines:
                print()

            res = fn(*args, **kwargs)

            if msg_after:
                if additional_lines:
                    print()
                print(msg_after)
            return res
        return wrapper
    return func_wrapper


def rewrite_log(fn):
    def wrapper(*args, **kwargs):
        global ERROR_LOG
        ERROR_LOG.close()
        ERROR_LOG = open(ERROR_LOG_FILE_PATH, mode='w')

        return fn(*args, **kwargs)
    return wrapper


@rewrite_log
@print_text_state('Initializing first agent...', 'Agent was completed')
def init_first_agent(board_size: int, agent_filename: str):
    init_ac_path = os.path.join(PATH_TO_PROJECT_ROOT, 'init_ac_agent.py')
    board_size = str(board_size)
    path_to_agent_file = os.path.join(PATH_TO_AGENTS, agent_filename)
    cmd = [
        PYTHON_CMD, init_ac_path,
        '--board-size', board_size,
        '--output-file', path_to_agent_file
    ]

    subprocess.run(cmd, check=True, stderr=ERROR_LOG)

    print(f'Agent [{agent_filename}] was created')
    print_line_pl(f'[{agent_filename}] was created')


@rewrite_log
def self_playing(board_size: int, learning_agent_filename: str, num_games: int, experience_filename: str):
    self_play_ac_path = os.path.join(PATH_TO_TTT, 'self_play_ac_ttt.py')
    board_size = str(board_size)
    path_to_agent_file = os.path.join(PATH_TO_AGENTS, learning_agent_filename)
    num_games = str(num_games)
    path_to_experience_file = os.path.join(PATH_TO_EXPERIENCES, experience_filename)
    cmd = [
        PYTHON_CMD, self_play_ac_path,
        '--board-size', board_size,
        '--learning-agent', path_to_agent_file,
        '--num-games', num_games,
        '--experience-out', path_to_experience_file
    ]

    print('Agent [' + learning_agent_filename + "] start playing")

    subprocess.run(cmd, check=True, stderr=ERROR_LOG)

    print_line_pl(f'[{learning_agent_filename}] played with self -> [{experience_filename}]')


@rewrite_log
@print_text_state('Start agent train...', 'End agent train')
def train(experience_filenames: list, learning_agent_filename: str, new_agent_filename: str, learning_rate: float, batch_size: int):
    self_play_ac_path = os.path.join(PATH_TO_PROJECT_ROOT, 'train_ac.py')
    paths_to_experience_files = map(lambda x: os.path.join(PATH_TO_EXPERIENCES, x), experience_filenames)
    path_to_agent_file = os.path.join(PATH_TO_AGENTS, learning_agent_filename)
    path_to_new_agent_file = os.path.join(PATH_TO_AGENTS, new_agent_filename)
    learning_rate = str(learning_rate)
    batch_size = str(batch_size)
    cmd = [
        PYTHON_CMD, self_play_ac_path,
        '--learning-agent', path_to_agent_file,
        '--agent-out', path_to_new_agent_file,
        '--lr', learning_rate,
        '--bs', batch_size,
    ]
    cmd += paths_to_experience_files

    subprocess.run(cmd, check=True, stderr=ERROR_LOG)

    print_line_pl(f'Training [{learning_agent_filename}] on {experience_filenames} -> [{new_agent_filename}]')


@rewrite_log
@print_text_state('Start agents evaluating...', 'End agents evaluating')
def evaluate_new_bot(evaluating_agent_filename: str, learned_agent_filename: str, num_games: int, is_debug: bool):
    self_play_ac_path = os.path.join(PATH_TO_TTT, 'eval_ac_bot_ttt.py')
    path_to_first_agent_file = os.path.join(PATH_TO_AGENTS, evaluating_agent_filename)
    path_to_second_agent_file = os.path.join(PATH_TO_AGENTS, learned_agent_filename)
    num_games = str(num_games)
    cmd = [
        PYTHON_CMD, self_play_ac_path,
        '--agent1', path_to_first_agent_file,
        '--agent2', path_to_second_agent_file,
        '--num-games', num_games
    ]

    if is_debug:
        cmd.append('--debug')

    proc = subprocess.run(cmd, check=True, stderr=ERROR_LOG, stdout=subprocess.PIPE)
    won, all_games = map(int, proc.stdout[-5:-2].decode('UTF-8').split('/'))
    print(f'Agent [{evaluating_agent_filename}] vs [{learned_agent_filename}] = {won}:{all_games - won}')
    print_line_pl(f'Agent [{evaluating_agent_filename}] vs [{learned_agent_filename}] = {won}:{all_games - won}')
    return won > all_games - won


def get_agent_name(file_id: int):
    return 'ac_v' + str(file_id) + '.h5'


def get_experience_name(file_id: int):
    return 'exp_' + str(file_id) + '.h5'


def create_agent(file_id: int):
    return get_agent_name(file_id), file_id + 1


def create_experience(file_id: int):
    return get_experience_name(file_id), file_id + 1


@print_text_state('Start self playing...', 'Self playing is end', additional_lines=True)
def generate_experience(board_size: int, agent: str, num_games: int, from_exp: int, to_exp: int) -> list:
    exps = []
    for exp_ind in range(from_exp, to_exp + 1):
        exp = get_experience_name(exp_ind)
        exps.append(exp)
        self_playing(board_size, agent, num_games, exp)
    return exps


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--board-size', type=int, default=19)
    parser.add_argument('--self-playing', type=int, default=5000)
    parser.add_argument('--evaluate-num', type=int, default=100)
    parser.add_argument('--add-games', type=int, default=5)
    parser.add_argument('--from-ac', type=int, default=None)
    parser.add_argument('--from-exp', type=int, default=None)
    parser.add_argument('--to-exp', type=int, default=None)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    self_playing_num_games = args.self_playing
    evaluate_num_games = args.evaluate_num
    additional_games = args.add_games
    eval_in_debug = args.debug

    learning_rate = 0.01
    batch_size = 1024
    board_size = args.board_size

    from_ac = args.from_ac
    from_exp = args.from_exp
    to_exp = args.to_exp

    if from_exp is not None and to_exp is not None and from_exp > to_exp:
        raise ValueError('--from-exp can not be greater then --to-exp')

    ac_counter = from_ac if from_ac is not None else 1
    start_exp_counter = from_exp if from_exp is not None else 1
    exp_counter = to_exp if to_exp is not None else start_exp_counter
    start_with_exp = from_exp is not None or to_exp is not None
    exps_files = [get_experience_name(i) for i in range(start_exp_counter, exp_counter + 1)] if start_with_exp else []
    cycle_counter = 1

    current_agent, ac_counter = create_agent(ac_counter)
    new_agent, ac_counter = create_agent(ac_counter)

    if from_ac is None:
        init_first_agent(board_size, current_agent)

    while True:
        if start_exp_counter == exp_counter:
            print('------------------------ cycle', cycle_counter, '------------------------')
            print_line_pl(f'----- cycle {cycle_counter} -----')
        else:
            print(f'------------------------ Relearning agent [{current_agent}] ------------------------')
            print_line_pl(f'----- Relearning agent [{current_agent}] -----')

        if not start_with_exp:
            exps_files += generate_experience(board_size, current_agent, self_playing_num_games, start_exp_counter, exp_counter)
        train(exps_files, current_agent, new_agent, learning_rate, batch_size)
        result = evaluate_new_bot(new_agent, current_agent, evaluate_num_games, eval_in_debug)

        if result:
            exps_files = []
            exp_counter += 1
            start_exp_counter = exp_counter
            current_agent = new_agent
            new_agent, ac_counter = create_agent(ac_counter)
            cycle_counter += 1
        else:
            start_exp_counter = exp_counter + 1
            exp_counter += additional_games
        start_with_exp = False


def stop():
    ERROR_LOG.close()
    PROCESS_LOG.close()


if __name__ == '__main__':
    try:
        main()
    finally:
        stop()
