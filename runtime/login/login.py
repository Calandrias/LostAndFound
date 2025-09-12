"""Lambdafunction for login of owner."""

import json
import os
import logging


def lambda_handler(event, context):
    logging.info(f"Received event: {json.dumps(event)}")
    return {'statusCode': 200, 'body': json.dumps('Hello from login Lambda!')}
