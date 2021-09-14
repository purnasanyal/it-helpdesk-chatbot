"""
Python script for Lambda backed custom resource to create/update/delete:
Lex bot
Associated Lex Intents
Associated Lex Slot Types
"""
import os
import logging
import json
import time
import boto3
from botocore import exceptions as botocore_exceptions
from boto3 import exceptions as boto3_exceptions
from crhelper import CfnResource

logger = logging.getLogger(__name__)
helper = CfnResource(
    json_logging=False, log_level="DEBUG", boto_level="CRITICAL", sleep_on_delete=120
)

try:
    lex_client = boto3.client("lex-models", os.environ["AWS_REGION"])
    s3_resource = boto3.resource("s3")
    SLEEP_TIME = 10
except (
    botocore_exceptions.BotoCoreError,
    botocore_exceptions.ClientError,
    boto3_exceptions.Boto3Error,
) as exception:
    helper.init_failure(exception)


def check_required_properties(dictionary, key):
    """
    Check if a key is present in dictionary,
    otherwise raise KeyError stating "key is a required property"
    :param dictionary: Dictionary
    :param key: Key
    :return: None or KeyError
    """
    if key not in dictionary:
        raise KeyError(key + " is a required property")


def read_json_file_from_s3(bucket_name, object_key):
    """
    Reads Json file from S3 and converts it to Python object
    :param bucket_name: S3 Bucket Name
    :param object_key: S3 Object Key
    :return: Python object
    """
    bucket = s3_resource.Bucket(bucket_name)
    lex_json_obj = bucket.Object(object_key)
    return json.loads(lex_json_obj.get()["Body"].read().decode("utf-8"))


def create_lex_intents(
    fulfillment_lambda,
    intents,
    kendra_search_role_arn,
    kendra_index_id,
    account_id,
    slot_type_version,
):
    """
    Creates Lex intents.
    :param fulfillment_lambda: ARN of fulfillment Lambda
    :param intents: List of Lex intents
    :param kendra_search_role_arn: ARN of role created for creating custom Lex bot
    :param kendra_index_id: Kendra Index ID
    :param account_id: AWS Account ID
    :param slot_type_version: Map of Slot type versions.
    :return: List of intents (Name and Version)
    """
    intent_list = []
    for intent in intents:
        if "slots" in intent:
            for slot in intent["slots"]:
                if "slotType" in slot and slot["slotType"] in slot_type_version:
                    slot["slotTypeVersion"] = slot_type_version[slot["slotType"]]

        if intent["name"].startswith("AMAZON."):
            continue
        if (
            "parentIntentSignature" in intent
            and intent["parentIntentSignature"] == "AMAZON.KendraSearchIntent"
        ):
            intent["kendraConfiguration"]["kendraIndex"] = (
                "arn:aws:kendra:"
                + os.environ["AWS_REGION"]
                + ":"
                + account_id
                + ":index/"
                + kendra_index_id
            )
            intent["kendraConfiguration"]["role"] = kendra_search_role_arn
        intent.pop("version", None)
        if intent["fulfillmentActivity"]["type"] == "CodeHook":
            intent["fulfillmentActivity"]["codeHook"]["uri"] = fulfillment_lambda
        if "dialogCodeHook" in intent:
            intent["dialogCodeHook"]["uri"] = fulfillment_lambda
        try:
            intent_get_response = lex_client.get_intent(
                name=intent["name"], version="$LATEST"
            )
            intent["checksum"] = intent_get_response["checksum"]
        except lex_client.exceptions.NotFoundException:
            pass
        intent["createVersion"] = True
        intent_response = lex_client.put_intent(**intent)
        intent_list.append(
            {"intentName": intent["name"], "intentVersion": intent_response["version"]}
        )
        logger.info("Created/updated intent %s", str(intent["name"]))
    return intent_list


def create_lex_slot_types(slot_types):
    """
    Creates Lex slot types.
    :param slot_types: List of Lex slot types.
    :return: Map of Slot type versions.
    """
    slot_type_version = {}
    for slot_type in slot_types:
        slot_type.pop("version", None)
        try:
            slot_get_response = lex_client.get_slot_type(
                name=slot_type["name"], version="$LATEST"
            )
            slot_type["checksum"] = slot_get_response["checksum"]
        except lex_client.exceptions.NotFoundException:
            pass
        slot_type["createVersion"] = True
        slot_type_response = lex_client.put_slot_type(**slot_type)
        slot_type_version[slot_type["name"]] = slot_type_response["version"]
        logger.info("Created/updated slot type %s", str(slot_type["name"]))
    return slot_type_version


def create_lex_bot(
    lex_bot, fulfillment_lambda, kendra_search_role_arn, kendra_index_id, account_id
):
    """
    Creates Lex Bot.
    :param lex_bot: Bot description
    :param fulfillment_lambda: ARN of fulfillment Lambda
    :param kendra_search_role_arn: ARN of role created for creating custom Lex bot
    :param kendra_index_id: Kendra Index ID
    :param account_id: AWS Account ID
    :return: Lex Bot Name & version
    """
    intent_list = []
    slot_type_version = {}
    if "slotTypes" in lex_bot:
        slot_type_version = create_lex_slot_types(lex_bot["slotTypes"])
        del lex_bot["slotTypes"]
    if "intents" in lex_bot:
        intent_list = create_lex_intents(
            fulfillment_lambda,
            lex_bot["intents"],
            kendra_search_role_arn,
            kendra_index_id,
            account_id,
            slot_type_version,
        )
    lex_bot["intents"] = intent_list
    lex_bot["processBehavior"] = "BUILD"
    lex_bot["createVersion"] = True
    lex_bot.pop("version", None)
    try:
        bot_get_response = lex_client.get_bot(
            name=lex_bot["name"], versionOrAlias="$LATEST"
        )
        lex_bot["checksum"] = bot_get_response["checksum"]
    except lex_client.exceptions.NotFoundException:
        pass
    bot_response = lex_client.put_bot(**lex_bot)
    logger.info("Bot Name: %s", str(bot_response["name"]))

    return bot_response["name"], bot_response["version"]


@helper.create
@helper.update
def create(event, _):
    """
    Helper function for resource creation.
    Populates Data with Lex Bot Name so poll_create helper can refer to it.
    Raises Exception if required resource properties are missing.
    Any exception raised is displayed in CloudFormation console.
    :param event: Event body
    :param _: Context (unused)
    :return: None
    """
    logger.info("Got Create")

    if "ResourceProperties" not in event:
        raise ValueError("Please provide resource properties")
    required_properties = [
        "LexS3Bucket",
        "LexFileKey",
        "FulfillmentLambda",
        "KendraSearchRole",
        "KendraIndex",
        "AccountID",
    ]

    for resource_property in required_properties:
        check_required_properties(event["ResourceProperties"], resource_property)

    lex_json = read_json_file_from_s3(
        event["ResourceProperties"]["LexS3Bucket"],
        event["ResourceProperties"]["LexFileKey"],
    )
    
    lex_json["resource"]["name"] = event["ResourceProperties"]["LexBotName"]

    bot_name, bot_version = create_lex_bot(
        lex_json["resource"],
        event["ResourceProperties"]["FulfillmentLambda"],
        event["ResourceProperties"]["KendraSearchRole"],
        event["ResourceProperties"]["KendraIndex"],
        event["ResourceProperties"]["AccountID"],
    )

    helper.Data["BotName"] = bot_name
    helper.Data["BotVersion"] = bot_version


def check_bot_status(bot_name):
    """
    Checks status of Lex Bot.
    Raises an exception if Lex Bot is in an unexpected state.
    :param bot_name: Lex Bot Name
    :return: True if index is Ready, False otherwise
    """
    bot = lex_client.get_bot(name=bot_name, versionOrAlias="$LATEST")
    status = bot["status"]
    if status == "FAILED":
        raise Exception(
            "Lex Bot is in FAILED state with failure reason: " + bot["failureReason"]
        )
    if status == "BUILDING":
        return False
    if status == "READY":
        return True
    if status == "READY_BASIC_TESTING":
        return False
    raise Exception("Lex Bot is in " + status + " state")


@helper.poll_create
@helper.poll_update
def poll_create(event, _):
    """
    Helper function for resource creation, triggered every 2 minutes till resource is created.
    Any exception raised is displayed in CloudFormation console.
    :param event: Event body
    :param _: Context (unused)
    :return: None if Index is still being created.
             Physical Resource (Kendra IndexId) upon successful completion.
    """
    logger.info("Got create poll")
    bot_name = event["CrHelperData"]["BotName"]
    bot_alias = {}
    bot_alias["name"] = "quickstart"
    bot_alias["botVersion"] = event["CrHelperData"]["BotVersion"]
    bot_alias["botName"] = bot_name

    if not check_bot_status(bot_name):
        return None
    try:
        bot_get_alias_response = lex_client.get_bot_alias(
            name="quickstart", botName=bot_name
        )
        bot_alias["checksum"] = bot_get_alias_response["checksum"]
    except lex_client.exceptions.NotFoundException:
        pass
    lex_client.put_bot_alias(**bot_alias)
    return bot_name


def delete_intents(bot_name, intents):
    """
    Delete intents. (Not used)
    :param bot_name: Name of bot
    :param intents: List of intents to be deleted
    :return: List of slot types associated with delete intents
    """
    slot_types = set()
    for intent in intents:
        try:
            if intent["intentName"].startswith("AMAZON."):
                continue
            intent_response = lex_client.get_intent(
                name=intent["intentName"], version="$LATEST"
            )
            for slot in intent_response["slots"]:
                if not slot["slotType"].startswith("AMAZON."):
                    slot_types.add(slot["slotType"])
            lex_client.delete_intent(name=intent["intentName"])
        except lex_client.exceptions.ConflictException:
            time.sleep(SLEEP_TIME)
            lex_client.delete_intent(name=intent["intentName"])
        logger.info("Deleted intent %s of bot %s", str(intent["intentName"]), bot_name)
    return slot_types


def delete_slot_types(bot_name, slot_types):
    """
    Delete slot types. (Not used)
    :param bot_name: Name of bot
    :param slot_types: Set/List of slot type names to be deleted
    :return: None
    """
    for slot_type in slot_types:
        try:
            lex_client.delete_slot_type(name=slot_type)
        except lex_client.exceptions.ConflictException:
            time.sleep(SLEEP_TIME)
            lex_client.delete_slot_type(name=slot_type)
        logger.info("Deleted slot type %s of bot %s", slot_type, bot_name)


def delete_bot_aliases(bot_name):
    """
    Delete aliases associated with bot.
    :param bot_name: Name of bot
    :return: None
    """
    alias_response = lex_client.get_bot_aliases(botName=bot_name)
    for alias in alias_response["BotAliases"]:
        try:
            lex_client.delete_bot_alias(name=alias["name"], botName=bot_name)
        except lex_client.exceptions.ConflictException:
            time.sleep(SLEEP_TIME)
            lex_client.delete_bot_alias(name=alias["name"], botName=bot_name)
        logger.info("Deleted bot alias %s of bot %s", alias["name"], bot_name)


def delete_lex_bot(bot_name):
    """
    Deletes Lex Bot.
    Note that associated intents and slot types are not deleted to properly support updates.
    An update which changes the bot name but uses one or more same intent or slot type names
    will cause issues otherwise.
    :param bot_name: Name of bot to be deleted
    :return: None
    """
    # bot = lex_client.get_bot(name=bot_name, versionOrAlias='$LATEST')
    delete_bot_aliases(bot_name)
    try:
        lex_client.delete_bot(name=bot_name)
    except lex_client.exceptions.ConflictException:
        time.sleep(SLEEP_TIME)
        lex_client.delete_bot(name=bot_name)
    # slot_types = delete_intents(bot_name, bot['intents'])
    # delete_slot_types(bot_name, slot_types)


@helper.delete
def delete(event, _):
    """
    Helper function for resource deletion.
    Should not fail if the underlying resources are already deleted.
    :param event: Event body
    :param _: Context (unused)
    :return: None
    """
    logger.info("Got Delete")
    delete_lex_bot(event["PhysicalResourceId"])


def lambda_handler(event, context):
    print(event)
    """
    Base lambda handler.
    :param event: Event body passed to Lambda
    :param context: Context passed to Lambda
    :return: None
    """
    helper(event, context)
