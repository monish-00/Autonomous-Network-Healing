import tempfile
from pathlib import Path

from app.database.database_manager import DatabaseManager
from app.fault_management.alarm_manager import AlarmManager


def main():
    # Use a temporary database so previous application data
    # cannot interfere with this test.
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = Path(temp_dir) / "test_network_healing.db"

        # Replace the alarm manager's database with an isolated test database.
        manager = AlarmManager.__new__(AlarmManager)
        manager.database = DatabaseManager(test_db_path)
        manager.alarms = {}

        target = "127.0.0.1:8080"

        print("\n=== TEST 1: SERVICE IS HEALTHY ===")
        manager.process_status(target, "UP")

        print("\n=== TEST 2: SERVICE FAILS ===")
        manager.process_status(
            target,
            "DOWN",
            details="Connection refused",
        )

        assert len(manager.get_active_alarms()) == 1
        print("PASS: Alarm created.")

        print("\n=== TEST 3: SERVICE REMAINS DOWN ===")
        manager.process_status(
            target,
            "DOWN",
            details="Connection refused",
        )

        active_alarms = manager.get_active_alarms()
        assert len(active_alarms) == 1
        assert active_alarms[0]["occurrences"] == 2
        print("PASS: Existing alarm updated.")

        print("\n=== TEST 4: SERVICE RECOVERS ===")
        manager.process_status(target, "UP")

        assert len(manager.get_active_alarms()) == 0
        print("PASS: Alarm resolved.")

        print("\n=== TEST 5: DATABASE VALIDATION ===")
        all_alarms = manager.get_all_alarms()

        assert len(all_alarms) == 1
        assert all_alarms[0]["status"] == "RESOLVED"
        assert all_alarms[0]["occurrences"] == 2

        print("PASS: Alarm history persisted.")
        print("\nALL TESTS PASSED!")


if __name__ == "__main__":
    main()