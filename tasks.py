from celery_app import celery
from app import get_similar_products

@celery.task(name='tasks.get_similar_products_async')
def get_similar_products_async(product_id, url):
    return get_similar_products(product_id, url)
