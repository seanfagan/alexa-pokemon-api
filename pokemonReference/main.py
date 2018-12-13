"""
Alexa Skill for looking up Pokemon information on the PokeAPI.

http://amzn.to/1LzFrj6
http://amzn.to/1LGWsLG
"""

import os
import boto3
import requests

from base64 import b64decode

ENCRYPTED_SLACK_HOOK = os.environ['SLACK_HOOK']
# Decrypt code should run once and variables stored outside of the function
# handler so that these are decrypted once per container
SLACK_HOOK = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_SLACK_HOOK))['Plaintext']

# --------------- My API Helpers ------------------

def get_pokeapi_data(pokemon):
    """ Retrieve data on Pokemon from PokeAPI in JSON format. """
    endpoint = 'http://pokeapi.co/api/v2/pokemon/' + pokemon
    r = requests.get(endpoint)
    r.raise_for_status()

    return r.json()

def post_to_slack(message):
    """ Posts message to IT Peer Group slack team. """
    webhook = SLACK_HOOK
    text = {"text": message}
    r = requests.post(webhook, json=text)

    return bool(r.status_code == requests.codes.ok)


# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    card_title = "Welcome"
    session_attributes = {}
    should_end_session = False

    speech_output = "Welcome to Pokemon Reference, nerdo. " \
                    "Please ask about a Pokemon's information " \
                    "and I will retrieve it for you."
    reprompt_text = "Please ask me about a Pokemon. For instance: " \
                    "How tall is Bulbasaur?."

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "May you catch them all. "
    should_end_session = True

    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def get_pokemon_height(intent, session, slack=False):
    """ Gets the height of the specified pokemon. """
    card_title = "Pokemon Height"
    should_end_session = True

    if 'Pokemon' in intent['slots'] and 'value' in intent['slots']['Pokemon']:
        pokemon = intent['slots']['Pokemon']['value']  # Pokemon was in query
    elif 'pokemon' in session['attributes']:
        pokemon = session['attributes']['pokemon']  # Pokemon was in session
    else:
        pokemon = None

    if pokemon:
        session_attributes = {"pokemon": pokemon}
        height = str(get_pokeapi_data(pokemon)['height'] * 10)
        speech_output = pokemon + " is " + str(height) + " centimeters tall."

        if slack:
            posted = post_to_slack(speech_output)
            if posted:
                speech_output = "The following message was posted to Slack: " + \
                                speech_output
            else:
                speech_output = "I was unable to post the following to Slack: " + \
                                speech_output
    else:
        speech_output = "I'm sorry. I don't know which Pokemon you're asking about."

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def lookup_pokemon(intent, session):
    """ Sets the pokemon in the session. """

    card_title = "Lookup Pokemon"
    session_attributes = {}
    should_end_session = False

    if 'Pokemon' in intent['slots'] and 'value' in intent['slots']['Pokemon']:
        pokemon = intent['slots']['Pokemon']['value']
        session_attributes = {"pokemon": pokemon}
        speech_output = "You are curious about the Pokemon " + pokemon + \
                        ". What would you like to know?"
        reprompt_text = "Ask what you want to know about " + pokemon + "."
    else:
        speech_output = "I'm not sure what Pokemon you're asking about. " \
                        "Please try again."
        reprompt_text = "I'm not sure what Pokemon you're asking about. " \
                        "Please try again."
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """
    pass


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "LookupPokemonIntent":
        return lookup_pokemon(intent, session)

    elif intent_name == "GetPokemonHeightIntent":
        return get_pokemon_height(intent, session)

    elif intent_name == "SlackPokemonHeightIntent":
        return get_pokemon_height(intent, session, slack=True)

    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()

    elif intent_name in ["AMAZON.CancelIntent", "AMAZON.StopIntent"]:
        return handle_session_end_request()

    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    pass


# --------------- Main handler ------------------

def handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
