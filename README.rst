==========
simplepyq
==========

Queueing tasks in Python doesn't have to be complicated.

Overview
--------

`simplepyq` is a simple task queuing library designed for small projects that need resilient, background task execution without the overhead of tools like Celery or Airflow. It uses SQLite for persistence and supports channels for organizing tasks, retries for resilience, and a `DelayException` for dynamic deferral.

Installation
------------

Install via pip:

.. code-block:: bash

    pip install simplepyq

Usage
-----

.. code-block:: python

    from simplepyq import SimplePyQ, DelayException

    def scrape_url(args):
        url = args["url"]
        if "fail" in url:
            raise Exception("API failed")
        if "wait" in url:
            raise DelayException(10)
        print(f"Scraping {url}")

    scheduler = SimplePyQ("tasks.db")
    scheduler.add_channel("scrape", scrape_url)
    scheduler.enqueue("scrape", {"url": "https://example.com"}, retries=2)
    scheduler.enqueue("scrape", {"url": "https://wait.com"})
    scheduler.run_until_complete()  # Or scheduler.start() for background

Features
--------

- **Channels**: Group tasks by function (e.g., "scrape").
- **Persistence**: Tasks survive restarts via SQLite.
- **Retries**: Automatic retries on failure.
- **DelayException**: Defer tasks dynamically.
- **Simple Setup**: No external dependencies beyond `msgpack`.

Testing
-------

To run the included unit tests:

.. code-block:: bash

    python -m unittest discover -s tests

This will execute all tests in the `tests/` directory and report results.

The tests cover basic task execution, retries, delays, and failed task management.

License
-------

Apache License2.0