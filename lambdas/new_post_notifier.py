import boto3

# table name
DYNAMO_TABLE = 'gundeal-posts'
# connector to DB
dynamo = boto3.client('dynamodb', region_name='us-east-1')
sns = boto3.client('sns', region_name='us-east-1')


def get_post_from_db(post_id):
    """ Get url, title, and post_category for the ``post_id``

    Args:
        post_id (str): post ID to lookup

    Returns:
        dict: API call response
    """
    return dynamo.get_item(
        TableName=DYNAMO_TABLE,
        Key={'post_id': {'S': post_id}},
        AttributesToGet=['url', 'title', 'post_category']
    )


def send_sns_notification(post_attrs):
    """ Publish message to the corresponding posts SNS topic

    Args:
        post_attrs (dict): the API call response from ``get_post_from_db()``

    Returns:
        dict: SNS API response (has the message-id)
    """
    post = post_attrs['Item']
    post_categor = post['post_category']['S']
    title = post['title']['S']
    url = post['url']['S']
    msg = f'NEW - "{post_categor.upper()}" deal!!\n\n{title}\n\n{url}'
    return sns.publish(
        TopicArn=f'arn:aws:sns:us-east-1:404426190892:{post_categor}-gundeals-topic',
        Message=msg
    )


def update_notified_attr(post_id):
    """ Update "notified" DB attribute for the ``post_id``

    Args:
        post_id (str): post ID to edit

    Returns:
        dict: AWS Dynamo API call response
    """
    return dynamo.update_item(
        TableName=DYNAMO_TABLE,
        Key={'post_id': {'S': post_id}},
        AttributeUpdates={'notified': {'Value': {'BOOL': True}}}
    )


def lambda_handler(event, context):
    """ AWS lambda handler main function

    Args:
        event (dict): payload response from the "gundeals-reddit-new-post-collector" lambda
        context ():

    Returns:
        None
    """
    lambda_payload = event.get('responsePayload')
    if lambda_payload['newPostsInserted']:
        for _, post_id_list in lambda_payload['newPostsProcessed'].items():
            for post_id in post_id_list:
                send_sns_notification(get_post_from_db(post_id))
                update_notified_attr(post_id)
