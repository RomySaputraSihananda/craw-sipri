from sipri import Sipri
from time import perf_counter

if(__name__ == '__main__'):
    start = perf_counter()

    sipri: Sipri = Sipri()

    sipri.start()

    print(perf_counter() - start)

