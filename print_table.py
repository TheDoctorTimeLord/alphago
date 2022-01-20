import argparse

from dlgo.gotypes import Point


def print_table(f):
    for row in f:
        print(' '.join(row))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--step-by-step', action='store_true')
    args = parser.parse_args()

    step_by_step = args.step_by_step

    print('Table:', end=' ')
    g = eval(input())
    f = [['.' for ii in range(9)] for i in range(9)]

    for p, s in g.items():
        f[p.row - 1][p.col - 1] = 'X' if s == 1 else 'O'
        if step_by_step:
            print_table(f)
            input()

    if not step_by_step:
        print_table(f)
