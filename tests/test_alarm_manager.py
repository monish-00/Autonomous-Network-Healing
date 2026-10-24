from app.fault_management.alarm_manager import AlarmManager


def main():
    manager = AlarmManager()
    target = "127.0.0.1:8080"

    print("\n=== TEST 1: SERVICE IS HEALTHY ===")
    manager.process_status(target, "UP")

    print("\n=== TEST 2: SERVICE FAILS ===")
    manager.process_status(
        target,
        "DOWN",
        details="Connection refused",
    )

    print("\n=== TEST 3: SERVICE REMAINS DOWN ===")
    manager.process_status(
        target,
        "DOWN",
        details="Connection refused",
    )

    print("\n=== TEST 4: SERVICE RECOVERS ===")
    manager.process_status(target, "UP")

    print("\n=== TEST 5: ACTIVE ALARM COUNT ===")
    print("Active alarms:", len(manager.get_active_alarms()))


if __name__ == "__main__":
    main()