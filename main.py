import sys
from meridian.app import MeridianApp


def main():
    app = MeridianApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
