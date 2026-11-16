import msvcrt
from contextlib import contextmanager
from pathlib import Path


class SimulationAlreadyRunning(RuntimeError):
    pass


@contextmanager
def execution_lock(simulation_db_path):
    db_path = Path(simulation_db_path).resolve()
    lock_path = db_path.with_name(db_path.name + ".lock")

    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, "a+b") as lock_file:
        # Ensure the lock byte exists without reading a byte
        # potentially locked by another Windows process.
        lock_file.seek(0, 2)
        if lock_file.tell() == 0:
            lock_file.write(b"0")
            lock_file.flush()

        lock_file.seek(0)

        try:
            msvcrt.locking(
                lock_file.fileno(),
                msvcrt.LK_NBLCK,
                1,
            )
        except OSError as error:
            raise SimulationAlreadyRunning(
                f"Simulation already running: {db_path}"
            ) from error

        try:
            yield
        finally:
            lock_file.seek(0)
            msvcrt.locking(
                lock_file.fileno(),
                msvcrt.LK_UNLCK,
                1,
            )
