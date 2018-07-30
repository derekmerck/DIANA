# Use the environment variables DIANA_BROKER and DIANA_RESULT to attach the celery
# app to a message queue.

import os
from celery import Celery

app = Celery('diana')

app.conf.update(
    result_expires = 3600,
    task_serializer = "pickle",
    accept_content = ["pickle"],
    result_serializer = "pickle",
    task_default_queue = 'default',
    task_routes={'*.gpu':  {'queue': 'gpu'},    # Only GPU boxes
                 '*.file': {'queue': 'file'} },   # Access to shared fs
    include=['diana.star.tasks'],
    broker_url=os.environ.get('DIANA_BROKER', "redis://localhost:6379/1"),
    result_backend=os.environ.get('DIANA_RESULT', "redis://localhost:6379/2"),
    timezone = 'America/New_York'
)

print(os.environ.get('DIANA_BROKER', "redis://localhost:6379/1"))