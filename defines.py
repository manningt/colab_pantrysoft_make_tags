import enum

FRIDAY_IDX = 0
SATURDAY_IDX = 1
FRIDAY_SPLIT_REPORT_HOUR = 3 # the time in the afternoon to split into before/after pickup lists

class GUEST_LIST_IDX_E(enum.Enum): 
   Pickup_Friday_before_3 = 0
   Pickup_Friday_after_3 = 1
   Pickup_Saturday = 2
   Delivery = 3

# used in report generation:
DELIVERY_TYPE = 'Delivery'  # used for delivery guest lists
AM_PM_TYPE = 'AM_PM'  # used for AM/PM guest lists
