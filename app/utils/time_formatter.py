def format_minutes(total_minutes: int) -> str:
    if total_minutes <= 0:
        return "0 minutes"

    if total_minutes < 60:
        return f"{total_minutes} minute" + ("" if total_minutes == 1 else "s")

    hours, minutes = divmod(total_minutes, 60)

    if hours < 24:
        if minutes == 0:
            return f"{hours} hour" + ("" if hours == 1 else "s")
        return (
            f"{hours} hour"
            + ("" if hours == 1 else "s")
            + f" and {minutes} minute"
            + ("" if minutes == 1 else "s")
        )

    days, remaining_hours = divmod(hours, 24)

    if remaining_hours == 0:
        return f"{days} day" + ("" if days == 1 else "s")

    return (
        f"{days} day"
        + ("" if days == 1 else "s")
        + f" and {remaining_hours} hour"
        + ("" if remaining_hours == 1 else "s")
    )
