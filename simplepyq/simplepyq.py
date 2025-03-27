# Copyright 2025 Kevin Dewald

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sqlite3
import threading
import time
import msgpack
from queue import Empty, Queue
from typing import Callable, Dict, Optional


class DelayException(Exception):
    def __init__(self, delay_seconds: int):
        """Exception to defer a task for a specified time."""
        self.delay_seconds = delay_seconds


class SimplePyQ:
    def __init__(self, store_path: str = "simplepyq_tasks.db"):
        """Initialize the task scheduler with a SQLite store."""
        self.store_path = store_path
        self.channels = {}  # {name: (func, max_workers)}
        self.running = False
        self.task_queues = {}  # {channel: Queue}
        self.workers = []
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite database."""
        with sqlite3.connect(self.store_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel TEXT NOT NULL,
                    args BLOB,
                    status TEXT DEFAULT 'pending',
                    retries INTEGER DEFAULT 0,
                    delay_until INTEGER
                )
            """)
            conn.commit()

    def add_channel(self, name: str, func: Callable, max_workers: int = 1):
        """Add a channel with a function to execute tasks."""
        if name in self.channels:
            raise ValueError(f"Channel '{name}' already exists")
        self.channels[name] = (func, max_workers)
        self.task_queues[name] = Queue()

    def remove_channel(self, name: str):
        """Remove a channel, its configuration, and all its tasks."""
        if name not in self.channels:
            return
        del self.channels[name]
        del self.task_queues[name]
        with sqlite3.connect(self.store_path) as conn:
            conn.execute("DELETE FROM tasks WHERE channel = ?", (name,))
            conn.commit()

    def enqueue(self, channel: str, args: Dict, retries: int = 0):
        """Enqueue a task for a specific channel."""
        if channel not in self.channels:
            raise ValueError(f"Channel '{channel}' not found")
        with sqlite3.connect(self.store_path) as conn:
            conn.execute(
                "INSERT INTO tasks (channel, args, retries) VALUES (?, ?, ?)",
                (channel, msgpack.dumps(args), retries)
            )
            conn.commit()

    def _worker(self, channel: str, func: Callable):
        """Worker thread to process tasks for a channel."""
        queue = self.task_queues[channel]
        while self.running:
            try:
                task = queue.get(timeout=1)
                task_id, args, retries = task
                try:
                    with sqlite3.connect(self.store_path) as conn:
                        conn.execute(
                            "UPDATE tasks SET status = 'running' WHERE id = ?",
                            (task_id,)
                        )
                        conn.commit()
                    func(args)
                    with sqlite3.connect(self.store_path) as conn:
                        conn.execute(
                            "UPDATE tasks SET status = 'done' WHERE id = ?",
                            (task_id,)
                        )
                        conn.commit()
                except DelayException as de:
                    delay_until = int(time.time()) + de.delay_seconds
                    with sqlite3.connect(self.store_path) as conn:
                        conn.execute(
                            "UPDATE tasks SET status = 'delayed', delay_until = ? WHERE id = ?",
                            (delay_until, task_id)
                        )
                        conn.commit()
                except Exception:
                    with sqlite3.connect(self.store_path) as conn:
                        if retries > 0:
                            conn.execute(
                                "UPDATE tasks SET status = 'pending', retries = ? WHERE id = ?",
                                (retries - 1, task_id)
                            )
                        else:
                            conn.execute(
                                "UPDATE tasks SET status = 'failed' WHERE id = ?",
                                (task_id,)
                            )
                        conn.commit()
                finally:
                    queue.task_done()
            except Empty:
                self._load_pending_tasks(channel)

    def _load_pending_tasks(self, channel: str):
        """Load pending or delayed tasks into the queue."""
        now = int(time.time())
        with sqlite3.connect(self.store_path) as conn:
            cursor = conn.execute("""
                SELECT id, args, retries FROM tasks
                WHERE channel = ? AND (status = 'pending' OR (status = 'delayed' AND delay_until <= ?))
            """, (channel, now))
            for task_id, args, retries in cursor.fetchall():
                self.task_queues[channel].put((task_id, msgpack.loads(args), retries))
                conn.execute(
                    "UPDATE tasks SET status = 'pending' WHERE id = ?",
                    (task_id,)
                )
            conn.commit()

    def start(self):
        """Start the scheduler to process tasks in the background."""
        if self.running:
            return
        self.running = True
        for channel, (func, max_workers) in self.channels.items():
            self._load_pending_tasks(channel)
            for _ in range(max_workers):
                worker = threading.Thread(target=self._worker, args=(channel, func), daemon=True)
                worker.start()
                self.workers.append(worker)

    def stop(self):
        """Stop the scheduler and its workers gracefully."""
        self.running = False
        for worker in self.workers:
            worker.join()
        self.workers.clear()

    def run_until_complete(self):
        """Run the scheduler until all tasks are completed, then stop."""
        self.start()
        while True:
            with sqlite3.connect(self.store_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status IN ('pending', 'running', 'delayed')"
                )
                remaining = cursor.fetchone()[0]
            if remaining == 0:
                break
            time.sleep(1)
        self.stop()

    def clear_failed(self, channel: str = None):
        """Remove all failed tasks from the database."""
        with sqlite3.connect(self.store_path) as conn:
            if channel:
                conn.execute("DELETE FROM tasks WHERE status = 'failed' AND channel = ?", (channel,))
            else:
                conn.execute("DELETE FROM tasks WHERE status = 'failed'")
            conn.commit()

    def requeue_failed(self, channel: str = None, retries: int = None):
        """Requeue all failed tasks with their original or new retry count."""
        with sqlite3.connect(self.store_path) as conn:
            if channel:
                cursor = conn.execute(
                    "SELECT id, retries FROM tasks WHERE status = 'failed' AND channel = ?",
                    (channel,)
                )
            else:
                cursor = conn.execute("SELECT id, retries FROM tasks WHERE status = 'failed'")
            for task_id, orig_retries in cursor.fetchall():
                new_retries = retries if retries is not None else orig_retries
                conn.execute(
                    "UPDATE tasks SET status = 'pending', retries = ? WHERE id = ?",
                    (new_retries, task_id)
                )
            conn.commit()