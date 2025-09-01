.PHONY: setup start kernel jupyter

setup:
	uv sync

start:
	uv run --env-file .env main.py

kernel:
	uv run ipython kernel install --user --env VIRTUAL_ENV $(pwd)/.venv --name=Project

jupyter:
	uv run --with jupyter jupyter lab
