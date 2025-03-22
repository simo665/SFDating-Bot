from datetime import timedelta

def format_time(seconds: int) -> str:
    # Create a timedelta object from the seconds
    delta = timedelta(seconds=seconds)

    # Extract days, hours, minutes, and seconds
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Build the readable string
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

    # Join the parts with commas and "and" for the last part
    if len(parts) > 1:
        readable_time = ", ".join(parts[:-1]) + f" and {parts[-1]}"
    else:
        readable_time = parts[0] if parts else "0 seconds"

    return readable_time