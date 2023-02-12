import click
import os, sys
import rich
import yaml

# create click command to generate a new config for daemons
@click.command()
@click.option('--path', default='daemons', help='Path to the daemons directory.')
def generate(path):
    daemons = os.listdir(path)
    data = {}
    for daemon in daemons:
        data[daemon] = {
            'dir': daemon,
            'target': 'main.py',
            'arguments': '',
            'requirements': 'requirements.txt',
            'auto-restart': False
        }
    with open('daemons-tmp.yaml', 'w') as f:
        yaml.dump(data, f)

if __name__ == '__main__':
    generate()
