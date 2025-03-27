TODO
====

This file outlines planned enhancements for `simplepyq`.

Return Values
-------------

Currently ignored. Options:

1. **Store in DB**
   - Add `results BLOB` column to `tasks`.
   - Add `store_results: bool = False` to `add_channel`.
   - Add `get_results(channel: str = None)` for `(task_id, result)` tuples.
   - Pros: Persistent, accessible.
   - Cons: DB overhead.

2. **Callback Mechanism**
   - Add `on_complete: callable` to `enqueue` or `add_channel`.
   - Pros: Real-time handling.
   - Cons: Complicates API.

3. **Synchronous Returns**
   - Return values in `run_until_complete`.
   - Pros: Simple for scripts.
   - Cons: Useless for `start`.

Decision: TBD—likely "Store in DB".

Exception Handling
------------------

Currently silent except `DelayException`. Options:

1. **Store in DB**
   - Add `error TEXT` column to `tasks`.
   - Store exception details for `failed` tasks.
   - Add `get_failures(channel: str = None)` for `(task_id, args, error)`.
   - Pros: Persistent, queryable.
   - Cons: Extra column.

2. **Logging**
   - Use `logging` to output exceptions.
   - Pros: Immediate visibility.
   - Cons: Not persistent.

3. **Callback on Failure**
   - Add `on_failure: callable`.
   - Pros: Real-time handling.
   - Cons: Complex.

4. **Raise on Sync**
   - Raise in `run_until_complete`.
   - Pros: Clean for scripts.
   - Cons: Inconsistent.

Decision: TBD—likely "Store in DB" + logging.

Other
-----

- Default `retries` (0 → 3)?
- Filter `get_results`/`get_failures` by task ID?
- More `DelayException` params?