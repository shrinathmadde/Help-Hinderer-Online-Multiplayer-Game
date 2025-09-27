# clock.py - Simple replacement for psychopy.core.Clock
import time


class Clock:
    """
    A simple clock implementation that mimics psychopy.core.Clock
    """

    def __init__(self):
        self.reset()

    def getTime(self):
        """
        Returns the time in seconds since the clock was last reset
        """
        return time.time() - self._start_time

    def reset(self):
        """
        Reset the time on the clock
        """
        self._start_time = time.time()