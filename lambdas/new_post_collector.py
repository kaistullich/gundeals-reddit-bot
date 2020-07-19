import json
import os

import boto3
import praw


def _load_config():
    """ Load config credentials locally/in AWS for Reddit API

    Returns:
        dict: all credentials
    """
    config_needed = ('client_id', 'client_secret', 'password', 'user_agent', 'username')
    # running in the Lambda
    if os.environ.get('in_aws'):
        creds = dict()
        for config_key in config_needed:
            try:
                creds[config_key] = os.environ[config_key]
            except KeyError as e:
                print(f'Unable to locate env var {config_key} on the Lambda')
                raise e
        return creds
    # running locally
    with open('config.json') as f:
        return json.load(f)


# main connection to all things Reddit
reddit = praw.Reddit(**_load_config())

# work with only r/gundeals
gundeals = reddit.subreddit('gundeals')
# connector to DB
dynamo = boto3.client('dynamodb', region_name='us-east-1')
# table name
DYNAMO_TABLE = 'gundeal-posts'


def gather_new_posts():
    """ Find all new reddit posts

    Determines if a post that was submitted is a new post
    or if it has already been processed and is in the DB.

    Returns:
        Dict[str, List[str]]: post IDs separated by category
    """
    ammo_posts = []
    rifle_posts = []
    handgun_posts = []
    for post in gundeals.new():
        print(f'Processing post title: "{post.title}" ...')
        new_post = determine_if_new_post(post.id)
        # only track post if it is not in the DB already
        if new_post:
            if '[ammo]' in post.title.lower():
                print(f'*NEW* [ammo] post found, ID: "{post.id}"')
                ammo_posts.append(post)
            if '[rifle]' in post.title.lower():
                print(f'*NEW* [rifle] post found, ID: "{post.id}"')
                rifle_posts.append(post)
            if '[handgun]' in post.title.lower() or '[pistol]' in post.title.lower():
                print(f'*NEW* [handgun]/[pistol] post found, ID: "{post.id}"')
                handgun_posts.append(post)
    if any(len(result) > 0 for result in [ammo_posts, rifle_posts, handgun_posts]):
        print({'rifle': rifle_posts, 'handgun': handgun_posts, 'ammo': ammo_posts})
        return {
            'rifle': rifle_posts,
            'handgun': handgun_posts,
            'ammo': ammo_posts
        }
    # check if any of the tracking lists contains at least 1 new post
    return None


def determine_if_new_post(post_id):
    """ Query DB to see if ``post_id`` already present

    Args:
        post_id (str): the post ID to search

    Returns:
        bool: True if `post_id` in DB - False otherwise
    """
    resp = dynamo.get_item(
        TableName=DYNAMO_TABLE,
        Key={'post_id': {'S': post_id}},
        AttributesToGet=['post_id']
    )
    if 'Item' in resp:
        return False
    print(f'"{post_id}" - ALREADY in DB table, not processing further')
    return True


def insert_db_new_post(new_posts):
    """ Crate new post item in DB

    Args:
        new_posts (Dict[str, List[str]]): comes from ``gather_new_posts()``

    Returns:
        None
    """
    processed = {'ammo': [], 'handgun': [], 'rifle': []}
    for post_category in new_posts:
        for post in new_posts[post_category]:
            dynamo.put_item(
                TableName=DYNAMO_TABLE,
                Item={
                    'post_id': {
                        'S': post.id
                    },
                    'url': {
                        'S': post.url
                    },
                    'title': {
                        'S': post.title
                    },
                    'notified': {
                        'BOOL': False
                    },
                    'post_category': {
                        'S': post_category
                    }
                }
            )
            processed[post_category].append(post.id)
    return processed


def lambda_handler(event, context):
    """ Main function

    Returns:
        None
    """
    try:
        found_new_posts = gather_new_posts()
        # only insert if at least 1 new post (regardless of category) is found
        if found_new_posts:
            inserted_items = insert_db_new_post(found_new_posts)
            return {
                'statusCode': 200,
                'newPostsInserted': True,
                'newPostsProcessed': inserted_items
            }
        return {
            'statusCode': 200,
            'newPostsInserted': False,
            'newPostsProcessed': None
        }
    except Exception as e:
        print(e)
        raise e


if __name__ == '__main__':
    # will only run if it is locally executed
    lambda_handler({}, {})
