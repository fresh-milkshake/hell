import sys
import click
import os
import yaml
from loguru import logger

@click.command()
@click.option('--path', default='daemons', show_default=True, help='Path to the daemons directory.')
@click.option('--output', default='daemons-tmp.yaml', show_default=True, help='Output YAML file name.')
@click.option('--target', default='main.py', show_default=True, help='Default target script for each daemon.')
@click.option('--arguments', default='', show_default=True, help='Default arguments for each daemon.')
@click.option('--requirements', default='requirements.txt', show_default=True, help='Default requirements file for each daemon.')
@click.option('--auto-restart', is_flag=True, help='Enable auto-restart for all daemons.')
@click.option('--verbose', is_flag=True, help='Enable verbose logging.')
def generate(path, output, target, arguments, requirements, auto_restart, verbose):
    """
    Generates a YAML configuration for daemons in the specified directory.
    """
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    try:
        daemons = os.listdir(path)
        if not daemons:
            logger.warning(f"No daemons found in the directory: {path}")
            return

        data = {}
        for daemon in daemons:
            daemon_path = os.path.join(path, daemon)
            if os.path.isdir(daemon_path):
                logger.debug(f"Processing daemon: {daemon}")
                data[daemon] = {
                    'dir': daemon,
                    'target': target,
                    'arguments': arguments,
                    'requirements': requirements,
                    'auto-restart': auto_restart
                }
            else:
                logger.debug(f"Skipping non-directory item: {daemon}")

        with open(output, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        logger.info(f"Configuration file '{output}' generated successfully.")

    except FileNotFoundError:
        logger.error(f"Directory not found: {path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    generate()
