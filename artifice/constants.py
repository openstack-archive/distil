# Date format Ceilometer uses
# 2013-07-03T13:34:17
# which is, as an strftime:
# timestamp = datetime.strptime(res["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
# or
# timestamp = datetime.strptime(res["timestamp"], "%Y-%m-%dT%H:%M:%S")

# Most of the time we use date_format
date_format = "%Y-%m-%dT%H:%M:%S"
# Sometimes things also have milliseconds, so we look for that too.
# Because why not be annoying in all the ways?
other_date_format = "%Y-%m-%dT%H:%M:%S.%f"

# VM states:
active = 1
building = 2
paused = 3
suspended = 4
stopped = 5
rescued = 6
resized = 7
soft_deleted = 8
deleted = 9
error = 10
shelved = 11
shelved_offloaded = 12
