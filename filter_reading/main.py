import glob                             # for searching for json file
import os                               # for setting and reading environment variables
from google.cloud import pubsub_v1      # pip install google-cloud-pubsub
import time                             # for sleep function
import json                             # to deal with json objects
import sys                              # for exit function

# Search the current directory for the JSON file (Google Pub/Sub credential)
# to set the GOOGLE_APPLICATION_CREDENTIALS environment variable.
files = glob.glob("*.json")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = files[0]

# Get the environment variables
project_id = os.environ["GCP_PROJECT"]
subscription_id = os.environ["FILTER_SUB_ID"]
topic_name = os.environ["TOPIC_NAME"]

debug = False
if "DEBUG" in os.environ:
    debug = True

if debug:
    print(f"Project: {project_id}, Topic: {topic_name}, Sub: {subscription_id}")

# create a publisher and get the topic path
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_name)

# The callback function for handling received messages
def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    global publisher, topic_path
    message_data = json.loads(message.data)

    if debug:
        print(f"Received: {message_data}")

    # Filter: drop records with any None / missing measurements
    required_fields = ['pressure', 'temperature', 'humidity']
    has_missing = any(message_data.get(field) is None for field in required_fields)

    if has_missing:
        print(f"Filtered out record with missing measurements: {message_data}")
    else:
        # Forward the valid reading for conversion
        if debug:
            print(f"Forwarding valid reading: {message_data}")
        future = publisher.publish(
            topic_path,
            json.dumps(message_data).encode('utf-8'),
            function="convert reading"
        )

    # Acknowledge the message
    message.ack()

# create a subscriber for the project
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path(project_id, subscription_id)

# Filter: only receive messages with function="raw reading"
sub_filter = "attributes.function=\"raw reading\""
print(f"FilterReading service listening on {subscription_path}..\n")

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
