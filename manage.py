"""CLI wrapper that also uses project-local dependencies."""
from app import create_app
from flask.cli import FlaskGroup
cli = FlaskGroup(create_app=create_app)
if __name__ == '__main__':
    cli()
