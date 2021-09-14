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

import json
import dateutil.parser
import datetime
import time
import os
import math
import random
import logging
import boto3
import config as covid_help_desk_config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

kendra_client = boto3.client("kendra")

""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def elicit_intent(
    session_attributes, intent_name, slots, message=None, response_card=None
):
    return {
        "sessionAttributes": session_attributes,
        "dialogAction": {
            "type": "ElicitIntent",
            "intentName": intent_name,
            "slots": slots,
            "message": message,
            "responseCard": response_card,
        },
    }


def elicit_slot(
    session_attributes, intent_name, slots, slot_to_elicit, message, response_card=None
):
    return {
        "sessionAttributes": session_attributes,
        "dialogAction": {
            "type": "ElicitSlot",
            "intentName": intent_name,
            "slots": slots,
            "slotToElicit": slot_to_elicit,
            "message": message,
            "responseCard": response_card,
        },
    }


def confirm_intent(session_attributes, intent_name, slots, message, response_card=None):
    return {
        "sessionAttributes": session_attributes,
        "dialogAction": {
            "type": "ConfirmIntent",
            "intentName": intent_name,
            "slots": slots,
            "message": message,
            "responseCard": response_card,
        },
    }


def close(session_attributes, fulfillment_state, message, response_card=None):
    response = {
        "sessionAttributes": session_attributes,
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": fulfillment_state,
            "message": message
        },
    }

    return response


def delegate(session_attributes, slots):
    return {
        "sessionAttributes": session_attributes,
        "dialogAction": {"type": "Delegate", "slots": slots},
    }


def build_response_card(title, subtitle, options):
    """
    Build a responseCard with a title, subtitle, and an optional set of options which should be displayed as buttons.
    """
    buttons = None
    if options is not None:
        buttons = []
        for i in range(min(5, len(options))):
            buttons.append(options[i])

    return {
        "contentType": "application/vnd.amazonaws.card.generic",
        "version": 1,
        "genericAttachments": [
            {"title": title, "subTitle": subtitle, "buttons": buttons}
        ],
    }


""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float("nan")


def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None


def increment_time_by_thirty_mins(appointment_time):
    hour, minute = map(int, appointment_time.split(":"))
    return "{}:00".format(hour + 1) if minute == 30 else "{}:30".format(hour)


def get_random_int(minimum, maximum):
    """
    Returns a random integer between min (included) and max (excluded)
    """
    min_int = math.ceil(minimum)
    max_int = math.floor(maximum)

    return random.randint(min_int, max_int - 1)


def get_availabilities(date):
    """
    Helper function which in a full implementation would  feed into a backend API to provide query schedule availability.
    The output of this function is an array of 30 minute periods of availability, expressed in ISO-8601 time format.

    In order to enable quick demonstration of all possible conversation paths supported in this example, the function
    returns a mixture of fixed and randomized results.

    On Mondays, availability is randomized; otherwise there is no availability on Tuesday / Thursday and availability at
    10:00 - 10:30 and 4:00 - 5:00 on Wednesday / Friday.
    """
    day_of_week = dateutil.parser.parse(date).weekday()
    availabilities = []
    available_probability = 0.3
    if day_of_week == 0:
        start_hour = 10
        while start_hour <= 16:
            if random.random() < available_probability:
                # Add an availability window for the given hour, with duration determined by another random number.
                vaccine_type = get_random_int(1, 4)
                if vaccine_type == 1:
                    availabilities.append("{}:00".format(start_hour))
                elif vaccine_type == 2:
                    availabilities.append("{}:30".format(start_hour))
                else:
                    availabilities.append("{}:00".format(start_hour))
                    availabilities.append("{}:30".format(start_hour))
            start_hour += 1

    if day_of_week == 2 or day_of_week == 4:
        availabilities.append("10:00")
        availabilities.append("16:00")
        availabilities.append("16:30")

    return availabilities


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def is_available(appointment_time, duration, availabilities):
    """
    Helper function to check if the given time and duration fits within a known set of availability windows.
    Duration is assumed to be one of 30, 60 (meaning minutes).  Availabilities is expected to contain entries of the format HH:MM.
    """
    if duration == 30:
        return appointment_time in availabilities
    elif duration == 60:
        second_half_hour_time = increment_time_by_thirty_mins(appointment_time)
        return (
            appointment_time in availabilities
            and second_half_hour_time in availabilities
        )

    # Invalid duration ; throw error.  We should not have reached this branch due to earlier validation.
    raise Exception("Was not able to understand duration {}".format(duration))


def get_duration(vaccine_type):
    appointment_duration_map = {"macbook repair": 30, "windows repair": 30}
    return try_ex(lambda: appointment_duration_map[vaccine_type.lower()])


def get_availabilities_for_duration(duration, availabilities):
    """
    Helper function to return the windows of availability of the given duration, when provided a set of 30 minute windows.
    """
    duration_availabilities = []
    start_time = "10:00"
    while start_time != "17:00":
        if start_time in availabilities:
            if duration == 30:
                duration_availabilities.append(start_time)
            elif increment_time_by_thirty_mins(start_time) in availabilities:
                duration_availabilities.append(start_time)

        start_time = increment_time_by_thirty_mins(start_time)

    return duration_availabilities


def build_validation_result(is_valid, violated_slot, message_content):
    return {
        "isValid": is_valid,
        "violatedSlot": violated_slot,
        "message": {"contentType": "PlainText", "content": message_content},
    }


def validate_book_appointment(vaccine_type, date, appointment_time):
    if vaccine_type and not get_duration(vaccine_type):
        return build_validation_result(
            False,
            "VaccineType",
            "I did not recognize that, can I schedule an appointment for laptop repair?",
        )

    if appointment_time:
        if len(appointment_time) != 5:
            return build_validation_result(
                False,
                "Time",
                "I did not recognize that, what time would you like to book your appointment?",
            )

        hour, minute = appointment_time.split(":")
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            return build_validation_result(
                False,
                "Time",
                "I did not recognize that, what time would you like to book your appointment?",
            )

        if hour < 10 or hour > 16:
            # Outside of business hours
            return build_validation_result(
                False,
                "Time",
                "Our business hours are ten a.m. to five p.m.  What time works best for you?",
            )

        if minute not in [30, 0]:
            # Must be booked on the hour or half hour
            return build_validation_result(
                False,
                "Time",
                "We schedule appointments every half hour, what time works best for you?",
            )

    if date:
        if not isvalid_date(date):
            return build_validation_result(
                False,
                "Date",
                "I did not understand that, what date works best for you?",
            )
        elif (
            datetime.datetime.strptime(date, "%Y-%m-%d").date() <= datetime.date.today()
        ):
            return build_validation_result(
                False,
                "Date",
                "Appointments must be scheduled a day in advance.  Can you try a different date?",
            )
        elif (
            dateutil.parser.parse(date).weekday() == 5
            or dateutil.parser.parse(date).weekday() == 6
        ):
            return build_validation_result(
                False,
                "Date",
                "Our office is not open on the weekends, can you provide a work day?",
            )

    return build_validation_result(True, None, None)


def build_time_output_string(appointment_time):
    hour, minute = appointment_time.split(
        ":"
    )  # no conversion to int in order to have original string form. for eg) 10:00 instead of 10:0
    if int(hour) > 12:
        return "{}:{} p.m.".format((int(hour) - 12), minute)
    elif int(hour) == 12:
        return "12:{} p.m.".format(minute)
    elif int(hour) == 0:
        return "12:{} a.m.".format(minute)

    return "{}:{} a.m.".format(hour, minute)


def build_available_time_string(availabilities):
    """
    Build a string eliciting for a possible time slot among at least two availabilities.
    """
    prefix = "We have time availabilities at "
    if len(availabilities) > 3:
        prefix = "We have plenty of availability, including "

    prefix += build_time_output_string(availabilities[0])
    if len(availabilities) == 2:
        return "{} and {}".format(prefix, build_time_output_string(availabilities[1]))

    return "{}, {} and {}".format(
        prefix,
        build_time_output_string(availabilities[1]),
        build_time_output_string(availabilities[2]),
    )


def build_options(slot, vaccine_type=None, date=None, booking_map=None):
    """
    Build a list of potential options for a given slot, to be used in responseCard generation.
    """
    day_strings = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if slot == "VaccineType":
        return [
            {"text": "macbook Repair (30 min)", "value": "macbook"},
        ]
    elif slot == "Menu":
        return [
            {"text": "Question", "value": "Question"},
            {"text": "Scheduling", "value": "Schedule appointment"}
        ]
    elif slot == "Date":
        # Return the next five weekdays.
        options = []
        potential_date = datetime.date.today()
        while len(options) < 5:
            potential_date = potential_date + datetime.timedelta(days=1)
            if potential_date.weekday() < 5:
                options.append(
                    {
                        "text": "{}-{} ({})".format(
                            (potential_date.month),
                            potential_date.day,
                            day_strings[potential_date.weekday()],
                        ),
                        "value": potential_date.strftime("%A, %B %d, %Y"),
                    }
                )
        return options
    elif slot == "Time":
        # Return the availabilities on the given date.
        if not vaccine_type or not date:
            return None

        availabilities = try_ex(lambda: booking_map[date])
        if not availabilities:
            return None

        availabilities = get_availabilities_for_duration(
            get_duration(vaccine_type), availabilities
        )
        if len(availabilities) == 0:
            return None

        options = []
        for i in range(min(len(availabilities), 5)):
            options.append(
                {
                    "text": build_time_output_string(availabilities[i]),
                    "value": build_time_output_string(availabilities[i]),
                }
            )

        return options


## Kendra HELP DESK


def get_slot_values(slot_values, intent_request):
    if slot_values is None:
        slot_values = {key: None for key in covid_help_desk_config.SLOT_CONFIG}

    slots = intent_request["currentIntent"]["slots"]

    for key, config in covid_help_desk_config.SLOT_CONFIG.items():
        slot_values[key] = slots.get(key)
        logger.debug(
            "<<covid_help_desk_bot>> retrieving slot value for %s = %s",
            key,
            slot_values[key],
        )
        if slot_values[key]:
            if (
                config.get("type", covid_help_desk_config.ORIGINAL_VALUE)
                == covid_help_desk_config.TOP_RESOLUTION
            ):
                # get the resolved slot name of what the user said/typed
                if (
                    len(
                        intent_request["currentIntent"]["slotDetails"][key][
                            "resolutions"
                        ]
                    )
                    > 0
                ):
                    slot_values[key] = intent_request["currentIntent"]["slotDetails"][
                        key
                    ]["resolutions"][0]["value"]
                else:
                    errorMsg = covid_help_desk_config.SLOT_CONFIG[key].get(
                        "error", 'Sorry, I don\'t understand "{}".'
                    )
                    raise covid_help_desk_config.SlotError(
                        errorMsg.format(slots.get(key))
                    )

    return slot_values


def get_remembered_slot_values(slot_values, session_attributes):
    logger.debug(
        "<<covid_help_desk_bot>> get_remembered_slot_values() - session_attributes: %s",
        session_attributes,
    )

    str = session_attributes.get("rememberedSlots")
    remembered_slot_values = (
        json.loads(str)
        if str is not None
        else {key: None for key in covid_help_desk_config.SLOT_CONFIG}
    )

    if slot_values is None:
        slot_values = {key: None for key in covid_help_desk_config.SLOT_CONFIG}

    for key, config in covid_help_desk_config.SLOT_CONFIG.items():
        if config.get("remember", False):
            logger.debug(
                "<<covid_help_desk_bot>> get_remembered_slot_values() - slot_values[%s] = %s",
                key,
                slot_values.get(key),
            )
            logger.debug(
                "<<covid_help_desk_bot>> get_remembered_slot_values() - remembered_slot_values[%s] = %s",
                key,
                remembered_slot_values.get(key),
            )
            if slot_values.get(key) is None:
                slot_values[key] = remembered_slot_values.get(key)

    return slot_values


def remember_slot_values(slot_values, session_attributes):
    if slot_values is None:
        slot_values = {
            key: None
            for key, config in covid_help_desk_config.SLOT_CONFIG.items()
            if config["remember"]
        }
    session_attributes["rememberedSlots"] = json.dumps(slot_values)
    logger.debug("<<covid_help_desk_bot>> Storing updated slot values: %s", slot_values)
    return slot_values


def get_latest_slot_values(intent_request, session_attributes):
    slot_values = session_attributes.get("slot_values")

    try:
        slot_values = get_slot_values(slot_values, intent_request)
    except covid_help_desk_config.SlotError as err:
        raise covid_help_desk_config.SlotError(err)

    logger.debug(
        '<<covid_help_desk_bot>> "get_latest_slot_values(): slot_values: %s',
        slot_values,
    )

    slot_values = get_remembered_slot_values(slot_values, session_attributes)
    logger.debug(
        '<<covid_help_desk_bot>> "get_latest_slot_values(): slot_values after get_remembered_slot_values: %s',
        slot_values,
    )

    remember_slot_values(slot_values, session_attributes)

    return slot_values


def increment_counter(session_attributes, counter):
    counter_value = session_attributes.get(counter, "0")

    if counter_value:
        count = int(counter_value) + 1
    else:
        count = 1

    session_attributes[counter] = count

    return count


def get_kendra_answer(question):
    try:
        KENDRA_INDEX = os.environ["KENDRA_INDEX"]
    except KeyError:
        return "Configuration error - please set the Kendra index ID in the environment variable KENDRA_INDEX."

    try:
        response = kendra_client.query(IndexId=KENDRA_INDEX, QueryText=question)
    except:
        return None

    logger.debug(
        "<<covid_help_desk_bot>> get_kendra_answer() - response = "
        + json.dumps(response)
    )

    #
    # determine which is the top result from Kendra, based on the Type attribue
    #  - QUESTION_ANSWER = a result from a FAQ: just return the FAQ answer
    #  - ANSWER = text found in a document: return the text passage found in the document plus a link to the document
    #  - DOCUMENT = link(s) to document(s): check for several documents and return the links
    #

    first_result_type = ""
    try:
        first_result_type = response["ResultItems"][0]["Type"]
    except KeyError:
        return None

    if first_result_type == "QUESTION_ANSWER":
        try:
            faq_answer_text = response["ResultItems"][0]["DocumentExcerpt"]["Text"]
        except KeyError:
            faq_answer_text = "Sorry, I could not find an answer in our FAQs."

        return faq_answer_text

    elif first_result_type == "ANSWER":
        # return the text answer from the document, plus the URL link to the document
        try:
            document_title = response["ResultItems"][0]["DocumentTitle"]["Text"]
            document_excerpt_text = response["ResultItems"][0]["DocumentExcerpt"][
                "Text"
            ]
            document_url = response["ResultItems"][0]["DocumentURI"]
            answer_text = "I couldn't find a specific answer, but here's an excerpt from a document ("
            answer_text += "<" + document_url + "|" + document_title + ">"
            answer_text += ") that might help:\n\n" + document_excerpt_text + "...\n"
        except KeyError:
            answer_text = "Sorry, I could not find the answer in our documents."

        return answer_text

    elif first_result_type == "DOCUMENT":
        # assemble the list of document links
        document_list = "Here are some documents you could review:\n"
        for item in response["ResultItems"]:
            document_title = None
            document_url = None
            if item["Type"] == "DOCUMENT":
                if item.get("DocumentTitle", None):
                    if item["DocumentTitle"].get("Text", None):
                        document_title = item["DocumentTitle"]["Text"]
                if item.get("DocumentId", None):
                    document_url = item["DocumentURI"]

            if document_title is not None:
                document_list += "-  <" + document_url + "|" + document_title + ">\n"

        return document_list

    else:
        return None
