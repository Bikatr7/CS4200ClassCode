import numpy as np
import time

def compute_elements(num_elements: int = 1000, ex=np) -> np.array:
    rd = ex.random.RandomState(88)
    a = rd.randint(1, num_elements, (num_elements, num_elements))
    y = rd.randint(1, num_elements, (num_elements))
    res = ex.linalg.solve(a, y)
    return res

if __name__ == '__main__':
    timed_results = []
    for n_elems in [10, 50, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000]:
        start_time = time.time()
        res = compute_elements(n_elems)
        end_time = time.time()
        print("%d elements res: %s" % (n_elems, res.shape))
        timed_results.append(end_time - start_time)

    print("Timed Results: %s" % timed_results)
