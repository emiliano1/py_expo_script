import boto3
import os
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def handler(event, context):
    dynamodb = init_dynamodb()
    if event.get('source', '') == 'aws.events':
        logger.info('Event is from aws')
        handle_aws_event(event, dynamodb)
    else:
        logger.info('Event to publish')
        handle_pub_event(event, dynamodb)

def handle_pub_event(event, dynamodb):
    logger.info('Trying delivery for event:')
    logger.debug(json.dumps(event, indent=4, cls=DecimalEncoder))
    event_table = get_event_table(dynamodb)
    subs_table = get_subs_table(dynamodb)
    subscribers = list_subscribers(subs_table)
    for subscriber in subscribers:
        response = deliver_event(event, subscriber['endpoint'])
        if response:
            logger.info('Event delivered for %s' % subscriber['endpoint'])
        else:
            logger.info('Event not delivered for %s, adding to events table to try again later' % subscriber['endpoint'])
            insert_event(event, subscriber['endpoint'], event_table)

def handle_aws_event(event, dynamodb):
    event_table = get_event_table(dynamodb)
    events_to_deliver = list_events(event_table)
    for event_to_deliver in events_to_deliver:
        logger.info('Trying delivery for event:')
        logger.debug(json.dumps(event_to_deliver, indent=4, cls=DecimalEncoder))
        payload = event_to_deliver['event']
        subscriber = event_to_deliver['subscriber']
        response = deliver_event(payload, subscriber)
        if response:
            logger.info('Event delivered, deleting from events table')
            delete_event(payload, subscriber, event_table)
        else:
            logger.info('Event not delivered')
            created_at = datetime.strptime(event_to_deliver['created_at'],'%Y-%m-%dT%H:%M:%S.%f')
            expire_at = created_at + timedelta(hours=24)
            if datetime.now() > expire_at:
                logger.info('Event expired, deleting from events table')
                delete_event(payload, subscriber, event_table)        

def get_event_table(dynamodb):
    event_table_name = os.environ.get('event_table', 'events')
    return dynamodb.Table(event_table_name)

def get_subs_table(dynamodb):
    subs_table_name = os.environ.get('subs_table', 'subscribers')
    return dynamodb.Table(subs_table_name)

def init_dynamodb():
    region = os.environ.get('region', 'us-east-1')
    endpoint_url = os.environ.get('endpoint_url', 'http://localhost:8000')
    return boto3.resource('dynamodb', region_name=region, endpoint_url=endpoint_url)

def insert_event(event, subscriber, table):
    try:
        response = table.put_item(Item={
            'event': event,
            'subscriber': subscriber,
            'created_at': datetime.now().isoformat()
        })
    except ClientError as e:
        logger.error('Error: %s. %s' % (e.response['Error']['Code'], e.response['Error']['Message']))
        return False
    logger.info("PutItem succeeded:")
    logger.debug(json.dumps(response, indent=4, cls=DecimalEncoder))
    return True

def delete_event(event, subscriber, table):
    try:
        response = table.delete_item(
            Key={
                'event': event,
                'subscriber': subscriber
            }
        )
    except ClientError as e:
        logger.error('Error: %s. %s' % (e.response['Error']['Code'], e.response['Error']['Message']))
        return False
    logger.info("DeleteItem succeeded:")
    logger.debug(json.dumps(response, indent=4, cls=DecimalEncoder))
    return True

def list_events(table):
    try:
        response = table.scan(
            ProjectionExpression="event, subscriber, created_at"
        )
    except ClientError as e:
        logger.error('Error: %s. %s' % (e.response['Error']['Code'], e.response['Error']['Message']))
        return None
    return response['Items']

# Assuming table subscribers has a column named endpoint that contains where the event should be send to
def list_subscribers(table):
    try:
        response = table.scan(
            ProjectionExpression="endpoint"
        )
    except ClientError as e:
        logger.error('Error: %s. %s' % (e.response['Error']['Code'], e.response['Error']['Message']))
        return None
    return response['Items']

def deliver_event(event, endpoint):
    headers = {
        'Content-Type': 'application/json',
    }
    response = requests.post(endpoint, headers=headers, json=event)
    try:
        response.raise_for_status()
    except HTTPError as ex:
        logger.error(response.text)
        logger.error(ex)
        return False
    return True

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)
