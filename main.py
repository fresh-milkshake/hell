# TODO: rewrite this whole file bc it's a mess


import time
from app.hell_gate import app, hell
import threading
import uvicorn
from typing import Callable


class GracefulThread(threading.Thread):
    def __init__(self, target: Callable, name: str, daemon: bool = True):
        super().__init__(target=self._wrapper, name=name, daemon=daemon)
        self.original_target = target
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def _wrapper(self):
        while not self.stop_event.is_set():
            try:
                self.original_target()
            except KeyboardInterrupt:
                break


if __name__ == "__main__":

    def start_hell():
        try:
            hell.start()
        except KeyboardInterrupt:
            pass

    def run_server():
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
        server = uvicorn.Server(config)
        server.run()

    hell_thread = GracefulThread(target=start_hell, name="HellThread")
    server_thread = GracefulThread(target=run_server, name="ServerThread")

    hell_thread.start()
    server_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCtrl+C pressed. Initiating graceful shutdown...")
    finally:
        hell.stop()
        hell_thread.stop()
        server_thread.stop()

        timeout = 10
        for thread in [hell_thread, server_thread]:
            thread.join(timeout)
            if thread.is_alive():
                print(f"Warning: {thread.name} did not terminate gracefully.")
            else:
                print(f"{thread.name} terminated successfully.")

    print("Shutdown complete.")
