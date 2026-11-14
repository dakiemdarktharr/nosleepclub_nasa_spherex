"""Public cache serves verified bytes, collapses concurrent reads, and stays bounded."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import threading
import time
import unittest
from unittest.mock import patch

from web.api import data


class PublicCacheTests(unittest.TestCase):
    def setUp(self):
        with data._lock:
            data._cache.clear()
            data._inflight.clear()
            data._cache_size = 0

    def test_classroom_thirty_concurrent_reads_use_one_database_read(self):
        payload = b'verified science bytes'
        part = {'sha256': sha256(payload).hexdigest(), 'bytes': len(payload)}
        barrier = threading.Barrier(30)
        def fetch(_):
            time.sleep(.08)
            return payload
        def request(_):
            barrier.wait(timeout=5)
            return data.cached_chunk(part)
        with patch.object(data, 'read_chunk', side_effect=fetch) as reader:
            with ThreadPoolExecutor(max_workers=30) as pool:
                values = list(pool.map(request, range(30)))
            self.assertEqual(values, [payload] * 30)
            self.assertEqual(reader.call_count, 1)
            self.assertEqual(data.cached_chunk(part), payload)
            self.assertEqual(reader.call_count, 1)

    def test_failed_integrity_check_is_not_cached_and_can_recover(self):
        part = {'sha256': 'a' * 64, 'bytes': 2}
        with patch.object(data, 'read_chunk', side_effect=[RuntimeError('asset_integrity_failure'), b'ok']) as reader:
            with self.assertRaisesRegex(RuntimeError, 'asset_integrity_failure'):
                data.cached_chunk(part)
            self.assertEqual(data.cached_chunk(part), b'ok')
            self.assertEqual(reader.call_count, 2)

    def test_pending_readers_are_bounded_and_capacity_recovers(self):
        part = {'sha256': 'a' * 64, 'bytes': 2}
        entered, release = threading.Event(), threading.Event()
        def read(_):
            entered.set()
            if not release.wait(3):
                raise RuntimeError('test timed out')
            return b'ok'
        with patch.object(data, 'MAX_WAITERS', 1), patch.object(data, 'read_chunk', side_effect=read):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(data.cached_chunk, part)
                self.assertTrue(entered.wait(1))
                second = pool.submit(data.cached_chunk, part)
                until = time.monotonic() + 1
                while time.monotonic() < until:
                    with data._lock:
                        waiters = next(iter(data._inflight.values()))['waiters']
                    if waiters == 1:
                        break
                    time.sleep(.005)
                try:
                    self.assertEqual(waiters, 1)
                    with self.assertRaisesRegex(RuntimeError, 'asset_reader_busy'):
                        data.cached_chunk(part)
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=1), b'ok')
                self.assertEqual(second.result(timeout=1), b'ok')
            self.assertEqual(data._inflight, {})
            self.assertEqual(data.cached_chunk(part), b'ok')

    def test_eviction_bounds_memory_and_checks_size_in_key(self):
        with patch.object(data, 'CACHE_BYTES', 4), patch.object(data, 'read_chunk', return_value=b'ab') as reader:
            for value in ['a', 'b', 'c', 'b']:
                data.cached_chunk({'sha256': value * 64, 'bytes': 2})
            self.assertEqual(reader.call_count, 3)
            self.assertEqual(data._cache_size, 4)
            data.cached_chunk({'sha256': 'b' * 64, 'bytes': 3})
            self.assertEqual(reader.call_count, 4)


if __name__ == '__main__':
    unittest.main()
