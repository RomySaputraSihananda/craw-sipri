from time import perf_counter

from sipri import Sipri
from sipri.helpers import logging

if(__name__ == '__main__'):
    start = perf_counter()

    sipri: Sipri = Sipri()

    sipri.start()

    logging.info(f'finist at {perf_counter() - start}')

