import os
import time
import unittest
import sqlite3
from simplepyq import SimplePyQ, DelayException


class TestSimplePyQ(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_tasks.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.scheduler = SimplePyQ(self.db_path)

    def tearDown(self):
        self.scheduler.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_basic_task(self):
        results = []
        def task(args):
            results.append(args["value"])

        self.scheduler.add_channel("test", task)
        self.scheduler.enqueue("test", {"value": 42})
        self.scheduler.run_until_complete()
        self.assertEqual(results, [42])

    def test_retries(self):
        attempts = []
        def task(args):
            attempts.append(1)
            if len(attempts) < 2:
                raise Exception("Fail")

        self.scheduler.add_channel("test", task)
        self.scheduler.enqueue("test", {"value": 1}, retries=1)
        self.scheduler.run_until_complete()
        self.assertEqual(len(attempts), 2)

    def test_delay(self):
        start_time = time.time()
        def task(args):
            raise DelayException(1)

        self.scheduler.add_channel("test", task)
        self.scheduler.enqueue("test", {"value": 1})
        self.scheduler.start()
        time.sleep(2)
        self.scheduler.stop()
        end_time = time.time()
        self.assertGreaterEqual(end_time - start_time, 1)

    def test_clear_failed(self):
        def task(args):
            raise Exception("Fail")

        self.scheduler.add_channel("test", task)
        self.scheduler.enqueue("test", {"value": 1}, retries=0)
        self.scheduler.run_until_complete()
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'").fetchone()[0]
            self.assertEqual(count, 1)
        self.scheduler.clear_failed()
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'").fetchone()[0]
            self.assertEqual(count, 0)

    def test_requeue_failed(self):
        results = []
        attempts = []
        def task(args):
            attempts.append(1)
            if len(attempts) == 1:
                # The first attempt will always fail.
                raise Exception("Fail")
            results.append(args["value"])

        self.scheduler.add_channel("test", task)
        self.scheduler.enqueue("test", {"value": 1}, retries=0)
        self.scheduler.run_until_complete()
        self.scheduler.requeue_failed(retries=1)
        self.scheduler.run_until_complete()
        self.assertEqual(results, [1])


if __name__ == "__main__":
    unittest.main()