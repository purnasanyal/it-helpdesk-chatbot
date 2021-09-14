import json
import os
import boto3
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

BOT_NAME = os.environ.get("BOT_NAME")
BOT_ALIAS = os.environ.get("BOT_ALIAS")

lex_client = boto3.client("lex-runtime")


def lambda_handler(event, context):
    print(event)

    xml_response = MessagingResponse()

    profile_name = event["data"]["ProfileName"]
    incoming_message = event["data"]["Body"]
    from_number = event["data"]["From"]
    num_media = event["data"]["NumMedia"]

    from_number = from_number.replace("+", "")

    try:
        lex_session = lex_client.get_session(
            botName=BOT_NAME, botAlias=BOT_ALIAS, userId=from_number
        )
        session_attributes = lex_session.get("sessionAttributes", {})

    except Exception as e:
        remembered_slots = json.dumps(
            {
                "VaccineType": None,
                "FullName": profile_name,
                "Result": None,
                "ContactResult": None,
                "CurrentCondition": None,
                "Date": None,
                "Time": None,
            }
        )

        session_attributes = {"rememberedSlots": remembered_slots}

    try:
        lex_response = lex_client.post_text(
            botName=BOT_NAME,
            botAlias=BOT_ALIAS,
            userId=from_number,
            inputText=incoming_message,
            sessionAttributes=session_attributes,
        )
        print(lex_response)
        session_attributes = lex_response.get("sessionAttributes", {})
        resp_message = lex_response.get("message", "Empty....")

    except Exception as e:
        print(e)
        resp_message = "Sorry, we ran into a problem at our LEX end."

    xml_response.message(resp_message)

    return str(xml_response)
