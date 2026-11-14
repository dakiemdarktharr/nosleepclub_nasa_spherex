"""Health evidence stays sparse and never copies a review or caller identity."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from web.api import _health as health
from web.api import _access_control as control

class HealthPrivacyTest(unittest.TestCase):
    def setUp(self):
        with health._lock:
            health._last.clear()

    def test_classroom_traffic_is_collapsed_and_private_fields_are_never_stored(self):
        db=MagicMock()
        event={'event':'review_request','status':200,'cookie':'private-cookie','note':'private-note','request_id':'a'*32}
        with patch.dict(os.environ,{'VERCEL_ENV':'production'},clear=True), patch.object(control,'database',return_value=db), patch.object(health.time,'monotonic',return_value=100):
            with ThreadPoolExecutor(max_workers=30) as pool:
                list(pool.map(lambda _:health.record(event),range(30)))
            health.record({**event,'status':503})
            health.record({**event,'status':503})
            health.record({**event,'status':429})
        writes=db.service_health.update_one.call_args_list
        self.assertEqual(len(writes),2, 'one successful-activity and one server-error sample, no per-request rows')
        for call in writes:
            self.assertEqual(call.args[0],{'_id':'reviews'})
            self.assertEqual(list(call.args[1]),['$max'])
            self.assertEqual(len(call.args[1]['$max']),1)
            value=next(iter(call.args[1]['$max'].values()))
            self.assertIsInstance(value,datetime)
        self.assertNotIn('private-',str(writes))
        self.assertNotIn('a'*32,str(writes))

    def test_health_storage_outage_cannot_fail_request_or_create_a_retry_storm(self):
        with patch.dict(os.environ,{'VERCEL_ENV':'production'},clear=True), patch.object(control,'database',side_effect=RuntimeError('secret connection string')) as db, patch.object(health.time,'monotonic',return_value=100):
            for _ in range(30):
                health.record({'event':'frame_request','status':503})
        self.assertEqual(db.call_count,1)

    def test_recent_activity_outputs_dates_only(self):
        db=MagicMock()
        now=datetime(2026,11,14,tzinfo=timezone.utc)
        db.service_health.find.return_value.limit.return_value=[{'_id':'reviews','last_success_at':now,'note':'secret','last_error_at':'invalid'}]
        result=health.recent(db)
        self.assertEqual(result,{'reviews':{'last_success_at':now.isoformat()}})
        self.assertNotIn('secret',json.dumps(result))

if __name__=='__main__':
    unittest.main()
