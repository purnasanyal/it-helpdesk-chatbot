import json
import dateutil.parser
import datetime
import time
import os
import math
import random
import logging
import boto3
import helpers
import config

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

kendra_client = boto3.client("kendra")

""" --- Functions (Intent Handlers) that control the bot's behavior --- """


def welcome_handler(intent_request):
    user_id = intent_request["userId"]

    output_session_attributes = (
        intent_request["sessionAttributes"]
        if intent_request["sessionAttributes"] is not None
        else {}
    )

    try:
        remembered_slots = json.loads(output_session_attributes["rememberedSlots"])

        message = f"""
Hi {remembered_slots['FullName']}! How can I help you today?
Ask a question e.g. "Where is the medical center?"
Text "Schedule" to schedule an appointment."""

    except:
        message = """
Hi there! How can I help you today?
Ask a question e.g. "Where is the medical center?"
Text "Schedule" to schedule an appointment.
"""

    return helpers.close(
        output_session_attributes,
        "Fulfilled",
        {"contentType": "PlainText", "content": message},
    )


def transfer_to_flex_agent_handler(intent_request, user_id):
    source = intent_request["invocationSource"]

    output_session_attributes = (
        intent_request["sessionAttributes"]
        if intent_request["sessionAttributes"] is not None
        else {}
    )

    output_session_attributes["connected_to_agent"] = True
    print(output_session_attributes)

    try:
        flex_code = os.environ['id']
        flex_code = flex_code.replace(" ", "%20")
        print("environment variable: " + os.environ['id'])
        full_name = json.loads(output_session_attributes["rememberedSlots"])["FullName"]
        message = f"Okay {full_name}. Please tap here: http://wa.me/14155238886?text={flex_code} and send the code 'join green-bad' to connect with an agent. Thank you!"
    except:
        message = f"Okay {full_name}. Please tap here: http://wa.me/14155238886?text=join%20green-bad and send the code 'join green-bad' to connect with an agent. Thank you!!!"
    return helpers.close(
        output_session_attributes,
        "Fulfilled",
        {"contentType": "PlainText", "content": message},
    )


def kendra_query_handler(intent_request, session_attributes):
    session_attributes["fallbackCount"] = "0"
    fallbackCount = helpers.increment_counter(session_attributes, "fallbackCount")

    try:
        slot_values = helpers.get_latest_slot_values(intent_request, session_attributes)
    except config.SlotError as err:
        return helpers.close(
            session_attributes,
            "Fulfilled",
            {"contentType": "CustomPayload", "content": str(err)},
        )

    logger.debug(
        "<<covid_help_desk_bot>> kendra_query_handler(): slot_values = %s",
        json.dumps(slot_values),
    )

    query_string = ""
    if intent_request.get("inputTranscript", None) is not None:
        query_string += intent_request["inputTranscript"]

    logger.debug(
        '<<covid_help_desk_bot>> kendra_query_handler(): calling get_kendra_answer(query="%s")',
        query_string,
    )

    kendra_response = helpers.get_kendra_answer(query_string)
    if kendra_response is None:
        response = "Sorry, I was not able to understand your question."
        return helpers.close(
            session_attributes,
            "Fulfilled",
            {"contentType": "CustomPayload", "content": response},
        )
    else:
        logger.debug(
            '<<covid_help_desk_bot>> "kendra_query_handler(): kendra_response = %s',
            kendra_response,
        )
        return helpers.close(
            session_attributes,
            "Fulfilled",
            {"contentType": "CustomPayload", "content": kendra_response},
        )


def confirm_appointment_handler(intent_request):
    output_session_attributes = (
        intent_request["sessionAttributes"]
        if intent_request["sessionAttributes"] is not None
        else {}
    )

    content = "You haven't scheduled any appointments yet."

    if "appointment_time" in output_session_attributes.keys():
        content = "You have an appointment booked at {}".format(
            output_session_attributes["appointment_time"]
        )

    return helpers.close(
        output_session_attributes,
        "Fulfilled",
        {"contentType": "PlainText", "content": content},
    )


def make_appointment_handler(intent_request, sentiment_label):
    """
    Performs dialog management and fulfillment for booking a vaccination appointment.

    Beyond fulfillment, the implementation for this intent demonstrates the following:
    1) Use of elicitSlot in slot validation and re-prompting
    2) Use of confirmIntent to support the confirmation of inferred slot values, when confirmation is required
    on the bot model and the inferred slot values fully specify the intent.
    """

    output_session_attributes = (
        intent_request["sessionAttributes"]
        if intent_request["sessionAttributes"] is not None
        else {}
    )

    try:
        slot_values = helpers.get_latest_slot_values(
            intent_request, output_session_attributes
        )

    except config.SlotError as err:
        return helpers.close(
            output_session_attributes,
            "Fulfilled",
            {"contentType": "CustomPayload", "content": str(err)},
        )

    full_name = slot_values["FullName"]
    vaccine_type = slot_values["VaccineType"]
    test_result = slot_values["Result"]
    contact_result = slot_values["ContactResult"]
    current_condition = slot_values["CurrentCondition"]

    date = slot_values["Date"]
    appointment_time = slot_values["Time"]

    source = intent_request["invocationSource"]

    booking_map = json.loads(
        helpers.try_ex(lambda: output_session_attributes["bookingMap"]) or "{}"
    )

    sentiment_string_suffix = " [ Current sentiment: {} ]".format(sentiment_label)
    # sentiment_string_suffix = ""

    if intent_request["inputTranscript"].lower() == ("cancel" or "cancel scheduling"):
        return helpers.elicit_intent(
            output_session_attributes,
            "CancelScheduling",
            slot_values,
        )

    if source == "DialogCodeHook":
        # Perform basic validation on the supplied input slots.
        # slots = intent_request["currentIntent"]["slots"]
        validation_result = helpers.validate_book_appointment(
            vaccine_type, date, appointment_time
        )

        if not validation_result["isValid"]:
            slot_values[validation_result["violatedSlot"]] = None
            return helpers.elicit_slot(
                output_session_attributes,
                intent_request["currentIntent"]["name"],
                slot_values,
                validation_result["violatedSlot"],
                validation_result["message"],
                helpers.build_response_card(
                    "Specify {}".format(validation_result["violatedSlot"]),
                    validation_result["message"]["content"],
                    helpers.build_options(
                        validation_result["violatedSlot"],
                        vaccine_type,
                        date,
                        booking_map,
                    ),
                ),
            )

        # Vaccine selection

        if not vaccine_type:
            return helpers.elicit_slot(
                output_session_attributes,
                intent_request["currentIntent"]["name"],
                slot_values,
                "VaccineType",
                {
                    "contentType": "PlainText",
                    "content": "Sure thing! What type of vaccine appointment would you like to schedule?",
                },
                helpers.build_response_card(
                    "Specify Appointment Type",
                    "What type of vaccine appointment would you like to schedule?",
                    helpers.build_options("VaccineType", vaccine_type, date, None),
                ),
            )

        # Vaccine Q/A...

        if vaccine_type and not full_name:
            return helpers.elicit_slot(
                output_session_attributes,
                intent_request["currentIntent"]["name"],
                slot_values,
                "FullName",
                {
                    "contentType": "PlainText",
                    "content": "What is your first and last name? ",
                },
            )

        if (vaccine_type and full_name) and not test_result:
            return helpers.elicit_slot(
                output_session_attributes,
                intent_request["currentIntent"]["name"],
                slot_values,
                "Result",
                {
                    "contentType": "PlainText",
                    "content": "In the past 14 days, have you tested positive for COVID-19? Please reply (Yes/No) ",
                },
            )

        if (vaccine_type and full_name and test_result) and not contact_result:
            return helpers.elicit_slot(
                output_session_attributes,
                intent_request["currentIntent"]["name"],
                slot_values,
                "ContactResult",
                {
                    "contentType": "PlainText",
                    "content": "In the past 14 days, have you been in close contact with anyone who tested positive for COVID-19? Please reply (Yes/No) ",
                },
            )

        if (
            vaccine_type and full_name and test_result and contact_result
        ) and not current_condition:
            return helpers.elicit_slot(
                output_session_attributes,
                intent_request["currentIntent"]["name"],
                slot_values,
                "CurrentCondition",
                {
                    "contentType": "PlainText",
                    "content": "Do you currently have fever, chills, cough, shortness of breath, difficulty breathing, fatigue, muscle or body aches, headache, new loss of taste or smell, sore throat, nausea, vomiting, or diarrhea? Please reply (Yes/No) ",
                },
            )

        # Vaccine date and time scheduling...

        if (
            vaccine_type
            and full_name
            and test_result
            and contact_result
            and current_condition
        ) and not date:
            return helpers.elicit_slot(
                output_session_attributes,
                intent_request["currentIntent"]["name"],
                slot_values,
                "Date",
                {
                    "contentType": "PlainText",
                    "content": "When would you like to schedule your {}?".format(
                        vaccine_type
                    ),
                },
                helpers.build_response_card(
                    "Specify Date",
                    "When would you like to schedule your {}?".format(vaccine_type),
                    helpers.build_options("Date", vaccine_type, date, None),
                ),
            )

        if (
            vaccine_type
            and full_name
            and test_result
            and contact_result
            and current_condition
            and date
        ):
            # Fetch or generate the availabilities for the given date.
            booking_availabilities = helpers.try_ex(lambda: booking_map[date])
            if booking_availabilities is None:
                booking_availabilities = helpers.get_availabilities(date)
                booking_map[date] = booking_availabilities
                output_session_attributes["bookingMap"] = json.dumps(booking_map)

            vaccine_type_availabilities = helpers.get_availabilities_for_duration(
                helpers.get_duration(vaccine_type), booking_availabilities
            )
            if len(vaccine_type_availabilities) == 0:
                # No availability on this day at all; ask for a new date and time.
                slot_values["Date"] = None
                slot_values["Time"] = None
                return helpers.elicit_slot(
                    output_session_attributes,
                    intent_request["currentIntent"]["name"],
                    slot_values,
                    "Date",
                    {
                        "contentType": "PlainText",
                        "content": "We do not have any availability on that date, is there another day which works for you? "
                        + sentiment_string_suffix,
                    },
                    helpers.build_response_card(
                        "Specify Date",
                        "What day works best for you?",
                        helpers.build_options("Date", vaccine_type, date, booking_map),
                    ),
                )

            message_content = "What time on {} works for you? ".format(date)
            if appointment_time:
                output_session_attributes[
                    "formattedTime"
                ] = helpers.build_time_output_string(appointment_time)
                # Validate that proposed time for the appointment can be booked by first fetching the availabilities for the given day.  To
                # give consistent behavior in the sample, this is stored in sessionAttributes after the first lookup.
                if helpers.is_available(
                    appointment_time,
                    helpers.get_duration(vaccine_type),
                    booking_availabilities,
                ):
                    return helpers.delegate(output_session_attributes, slot_values)
                message_content = "The time you requested is not available. "

            if len(vaccine_type_availabilities) == 1:
                # If there is only one availability on the given date, try to confirm it.
                slot_values["Time"] = vaccine_type_availabilities[0]
                return helpers.confirm_intent(
                    output_session_attributes,
                    intent_request["currentIntent"]["name"],
                    slot_values,
                    {
                        "contentType": "PlainText",
                        "content": "{}{} is our only availability, does that work for you?".format(
                            message_content,
                            helpers.build_time_output_string(
                                vaccine_type_availabilities[0]
                            ),
                        ),
                    },
                    helpers.build_response_card(
                        "Confirm Appointment",
                        "Is {} on {} okay?".format(
                            helpers.build_time_output_string(
                                vaccine_type_availabilities[0]
                            ),
                            date,
                        ),
                        [
                            {"text": "yes", "value": "yes"},
                            {"text": "no", "value": "no"},
                        ],
                    ),
                )

            available_time_string = helpers.build_available_time_string(
                vaccine_type_availabilities
            )
            return helpers.elicit_slot(
                output_session_attributes,
                intent_request["currentIntent"]["name"],
                slot_values,
                "Time",
                {
                    "contentType": "PlainText",
                    "content": "{}{}".format(message_content, available_time_string),
                },
                helpers.build_response_card(
                    "Specify Time",
                    "What time works best for you?",
                    helpers.build_options("Time", vaccine_type, date, booking_map),
                ),
            )

        return helpers.delegate(output_session_attributes, slot_values)

    # Book the appointment.  In a real bot, this would likely involve a call to a backend service.
    duration = helpers.get_duration(vaccine_type)
    booking_availabilities = booking_map[date]
    if booking_availabilities:
        # Remove the availability slot for the given date as it has now been booked.
        booking_availabilities.remove(appointment_time)
        if duration == 60:
            second_half_hour_time = helpers.increment_time_by_thirty_mins(
                appointment_time
            )
            booking_availabilities.remove(second_half_hour_time)

        booking_map[date] = booking_availabilities
        output_session_attributes["bookingMap"] = json.dumps(booking_map)
    else:
        # This is not treated as an error as this code sample supports functionality either as fulfillment or dialog code hook.
        logger.debug(
            "Availabilities for {} were null at fulfillment time.  "
            "This should have been initialized if this function was configured as the dialog code hook".format(
                date
            )
        )

    output_session_attributes["appointment_time"] = "{} at {}".format(
        helpers.build_time_output_string(appointment_time), date
    )

    return helpers.close(
        output_session_attributes,
        "Fulfilled",
        {
            "contentType": "PlainText",
            "content": "Okay, I have booked your appointment, {}.  We will see you at {} on {}".format(
                full_name, helpers.build_time_output_string(appointment_time), date
            )
            + sentiment_string_suffix,
        },
    )


""" --- Intents Dispatch --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    sentiment_response = intent_request["sentimentResponse"]
    sentiment_scores = sentiment_response["sentimentScore"][1:-1].split(",")
    sentiment_label = sentiment_response["sentimentLabel"]

    logger.debug(
        "dispatch userId={}, intentName={}".format(
            intent_request["userId"], intent_request["currentIntent"]["name"]
        )
    )

    # user's whatsapp phonenumber
    user_id = intent_request["userId"]
    intent_name = intent_request["currentIntent"]["name"]

    # Dispatch to your bot's intent handlers
    if intent_name == "Greeting":
        return welcome_handler(intent_request)
    elif intent_name == "MakeAppointment":
        return make_appointment_handler(intent_request, sentiment_label)
    elif intent_name == "AskKendraFAQ":
        session_attributes = intent_request["sessionAttributes"]
        return kendra_query_handler(intent_request, session_attributes)
    elif intent_name == "AgentTransfer":
        return transfer_to_flex_agent_handler(intent_request, user_id)
    elif intent_name == "ConfirmAppointment":
        return confirm_appointment_handler(intent_request)

    raise Exception("Intent with name " + intent_name + " not supported")


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    os.environ["TZ"] = "America/New_York"
    time.tzset()
    logger.debug("event.bot.name={}".format(event["bot"]["name"]))

    return dispatch(event)
