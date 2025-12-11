# master_test.py
import multiprocessing
import time
import subprocess

USERS = [f"usuario{i}" for i in range(1, 11)]

def run_process(username, target):
    subprocess.run(["python", "worker.py", username, target])

if __name__ == "__main__":
    procs = []

    for i, username in enumerate(USERS):
        target = USERS[(i + 1) % len(USERS)]

        p = multiprocessing.Process(
            target=run_process,
            args=(username, target)
        )
        procs.append(p)
        p.start()

    for p in procs:
        p.join()
