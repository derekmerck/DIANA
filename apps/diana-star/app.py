"""
diana-star
Merck, Spring 2018

Start a diana-star worker:

$ export DIANA_BROKER=redis://redis_host/1 DIANA_RESULT=redis://redis_host/2
$ celery apps/utils/diana-star/app.py worker -N diana_worker
"""


from diana.star import app

if __name__ == '__main__':
    app.start()
