from celery import Celery
import tasks
celery_config = {
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0'
}

celery_app = Celery('tasks', broker=celery_config['broker_url'], backend=celery_config['result_backend'])
celery_app.autodiscover_tasks(lambda: ['tasks'])