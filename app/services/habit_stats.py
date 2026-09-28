from datetime import date, timedelta


def calculate_streaks(log_dates: list[date], today: date) -> tuple[int, int]:
    """Повертає (поточна_серія, найдовша_серія)."""
    days = sorted(set(log_dates))
    if not days:
        return 0, 0

    longest = run = 1
    for prev, cur in zip(days, days[1:]):
        if cur - prev == timedelta(days=1):
            run += 1
        else:
            run = 1
        longest = max(longest, run)

    day_set = set(days)
    # Якщо сьогодні ще не відмічено, серія не обривається: рахуємо від учора
    cursor = today if today in day_set else today - timedelta(days=1)
    current = 0
    while cursor in day_set:
        current += 1
        cursor -= timedelta(days=1)

    return current, longest