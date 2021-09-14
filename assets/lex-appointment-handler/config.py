#
# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

ORIGINAL_VALUE = 0
TOP_RESOLUTION = 1
APPOINTMENT_TIME = ""
VACCINE_TYPE = ""
FULL_NAME = ""
RESULT = ""
CONTACT_RESULT = ""
CURRENT_CONDITION = ""
DATE = ""
TIME = ""

SLOT_CONFIG = {
    "VaccineType": {"type": VACCINE_TYPE, "remember": True},
    "FullName": {"type": FULL_NAME, "remember": True},
    "Result": {"type": RESULT, "remember": True},
    "ContactResult": {"type": CONTACT_RESULT, "remember": True},
    "CurrentCondition": {"type": CURRENT_CONDITION, "remember": True},
    "Date": {"type": DATE, "remember": True},
    "Time": {"type": TIME, "remember": True},
}


class SlotError(Exception):
    pass
