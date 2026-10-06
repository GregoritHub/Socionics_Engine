"""Run the finite R14 workshop with an actor-only opportunity scheduler."""
import json
from . import __version__
from .autonomy_demo import main_demo

def main():
    print(json.dumps({'version':__version__,**main_demo()},indent=2))

if __name__=='__main__':main()
