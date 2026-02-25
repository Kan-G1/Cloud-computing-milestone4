import glob                             # for searching for json file
import os                               # for setting and reading environment variables
from google.cloud import pubsub_v1      # pip install google-cloud-pubsub
import time                             # for sleep function
import json                             # to deal with json objects

# Search the current directory for the JSON file (Google Pub/Sub credential)
# to set the GOOGLE_APPLICATION_CREDENTIALS environment variable.
files = glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = files[0]

# Get the environment variables
project_id = os.environ["GCP_PROJECT"]
subscription_id = os.environ["CONVERT_SUB_ID"]
topic_name = os.environ["TOPIC_NAME"]

debug = False
if "DEBUG" in os.environ:
    debug = True

if debug:
    print(f"Project: {project_id}, Topic: {topic_name}, Sub: {subscription_id}")

# create a publisher and get the topic path
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

def convert_pressure(kPa):
    """Convert pressure from kPa to psi: P(psi) = P(kPa) / 6.895"""
    return round(kPa / 6.895, 4)

def convert_temperature(celsius):
    """Convert temperature from Celsius to Fahrenheit: T(F) = T(C) * 1.8 + 32"""
    return round(celsius * 1.8 + 32, 4)

# The callback function for handling received messages
def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    global publisher, topic_path
    message_data = json.loads(message.data)

    if debug:
        print(f"Received: {message_data}")

    # Convert the measurements
    converted = dict(message_data)  # copy original data
    converted['pressure'] = convert_pressure(message_data['pressure'])      # kPa -> psi
    converted['temperature'] = convert_temperature(message_data['temperature'])  # C -> F

    if debug:
        print(f"Converted: {converted}")

    # Publish converted reading
    future = publisher.publish(
        topic_path,
        json.dumps(converted).encode('utf-8'),
        function="converted"
    )

    print(f"Published converted reading: pressure={converted['pressure']} psi, temp={converted['temperature']} F")

    # Acknowledge the message
    message.ack()

# create a subscriber for the project
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# Filter: only receive messages with function="convert reading"
sub_filter = "attributes.function=\"convert reading\""
print(f"ConvertReading service listening on {subscription_path}..\n")

with subscriber:
    try:
        subscription = subscriber.create_subscription(
            request={"name": subscription_path, "topic": topic_path, "filter": sub_filter}
        )
    except:
        pass

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()
