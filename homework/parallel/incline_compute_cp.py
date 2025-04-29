from incline_compute import compute_elements
import cupy as cp
import time

stream = cp.cuda.Stream(non_blocking=True)

if __name__ == '__main__':
    with stream:
        timed_results = []
        for n_elems in [10, 50, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000]:
            start_time = time.time()
            res = compute_elements(n_elems, ex=cp)
            end_time = time.time()
            print("%d elements res: %s" % (n_elems, res.shape))
            timed_results.append(end_time - start_time)

    print("Timed Results: %s" % timed_results)
