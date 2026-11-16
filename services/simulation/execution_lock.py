import os
from contextlib import contextmanager
from pathlib import Path

if os.name == "nt":
    import msvcrt
elif os.name == "posix":
    import fcntl
else:
    raise RuntimeError(
        f"Unsupported execution-lock platform: {os.name}"
    )


class SimulationAlreadyRunning(RuntimeError):
    pass


@contextmanager
def execution_lock(simulation_db_path):
    db_path = Path(simulation_db_path).resolve()
    lock_path = db_path.with_name(db_path.name + ".lock")

    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, "a+b") as lock_file:
        # Preserve existing Windows lock-byte behavior.
        lock_file.seek(0, 2)

        if lock_file.tell() == 0:
            lock_file.write(b"0")
            lock_file.flush()

        lock_file.seek(0)

        try:
            if os.name == "nt":
                msvcrt.locking(
                    lock_file.fileno(),
                    msvcrt.LK_NBLCK,
                    1,
                )
            else:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
        except OSError as error:
            raise SimulationAlreadyRunning(
                f"Simulation already running: {db_path}"
            ) from error

        try:
            yield
        finally:
            if os.name == "nt":
                lock_file.seek(0)
                msvcrt.locking(
                    lock_file.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
            else:
                fcntl.flock(
                    lock_file.fileno(),
                    fcntl.LOCK_UN,
                )
