from celery import Celery
from app import get_similar_products_async


celery = Celery(__name__, broker='redis://localhost:6379/0')

celery.autodiscover_tasks(lambda: ['app'])
celery.tasks.register(get_similar_products_async)


def make_celery(app):
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery
