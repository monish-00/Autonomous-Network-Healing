import tempfile
import unittest
from pathlib import Path

from app.database.database_manager import DatabaseManager
from app.fault_management.alarm_manager import AlarmManager


class AlarmManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.manager = AlarmManager(
            DatabaseManager(Path(self.temp_dir.name) / "isolated.db")
        )
        self.target = "127.0.0.1:8080"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_alarm_creation_repeated_failures_and_resolution(self):
        manager, target = self.manager, self.target
        manager.process_status(target, "UP")
        self.assertEqual(manager.get_active_alarms(), [])

        manager.process_status(target, "DOWN", details="HTTP failed")
        manager.process_status(target, "DOWN", details="HTTP failed again")
        self.assertEqual(len(manager.get_active_alarms()), 1)
        self.assertEqual(manager.get_active_alarms()[0]["occurrences"], 2)

        manager.process_status(target, "UP")
        row = manager.get_all_alarms()[0]
        self.assertEqual(row["status"], "RESOLVED")
        self.assertEqual(row["occurrences"], 2)

    def test_recovery_duration_and_success_persist(self):
        manager, target = self.manager, self.target
        manager.process_status(target, "DOWN", details="HTTP failed")
        manager.record_recovery(target, True, 2.537)
        manager.process_status(target, "UP")

        row = manager.get_all_alarms()[0]
        self.assertEqual(row["status"], "RESOLVED")
        self.assertEqual(row["recovery_success"], 1)
        self.assertAlmostEqual(row["recovery_duration"], 2.537)

    def test_failed_recovery_is_persisted_and_alarm_stays_active(self):
        manager, target = self.manager, self.target
        manager.process_status(target, "DOWN", details="HTTP failed")
        manager.record_recovery(target, False, 5)

        row = manager.get_all_alarms()[0]
        self.assertEqual(row["status"], "ACTIVE")
        self.assertEqual(row["recovery_success"], 0)
        self.assertAlmostEqual(row["recovery_duration"], 5.0)
        self.assertEqual(len(manager.get_active_alarms()), 1)


if __name__ == "__main__":
    unittest.main()
