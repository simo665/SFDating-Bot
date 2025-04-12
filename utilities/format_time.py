import datetime
from datetime import timedelta



def format_time(input_time) -> str:
    if isinstance(input_time, int):
        delta = timedelta(seconds=input_time)
    elif isinstance(input_time, timedelta):
        delta = input_time
    else:
        raise TypeError("Input must be either an integer (seconds) or a timedelta object.")

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    time_part = f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{days} days, {time_part}" if days else time_part

def get_account_age(created_at):
    created_at_naive = created_at.replace(tzinfo=None)
    now = datetime.datetime.utcnow()
    delta = now - created_at_naive

    # Convert the time difference into days, hours, and minutes
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # Format it into a readable string
    time_string = f"{days} days, {hours}:{minutes}"
    return time_string