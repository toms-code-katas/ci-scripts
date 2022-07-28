import logging
import signal
import sys
import time
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler

LOGGER = logging.getLogger("watchdog")


def add_signal_handler():
    def signal_term_handler(sig, frame):
        if observer:
            observer.stop()
            observer.join()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_term_handler)
    signal.signal(signal.SIGTERM, signal_term_handler)


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    observer = Observer()
    observer.schedule(LoggingEventHandler(),  path='/tmp/secrets',  recursive=False)

    add_signal_handler()

    observer.start()

    try:
        while True:
            time.sleep(1)
    except BaseException:
        pass
