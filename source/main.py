import requests
# import json
import time
import random

import agent_repeater_server


LHOST = "localhost"
LPORT = 5000


def main():
    # запускаем репитер
    agent_repeater_server.run(LHOST, LPORT)


if __name__ == "__main__":
    main()