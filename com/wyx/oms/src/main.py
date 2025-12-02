from web_backend.app import create_app


class OpsAISystem:

    def __init__(self):
        self.web_app = None

    def initialize(self):
        self.web_app = create_app()

    def start(self):
        self.web_app.run(port=8081)


def main():
    system = OpsAISystem()
    system.initialize()
    system.start()


if __name__ == "__main__":
    main()
