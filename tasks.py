from celery import Celery
import requests
import spacy
from PIL import Image
from io import BytesIO
from utils import get_data_from_website, get_product_details, get_nlp_similarity, get_image_similarity


celery = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Load the SpaCy model
nlp = spacy.load("en_core_web_md")

@celery.task
def get_similar_products_async(product_id, url, search_term=None, threshold=0.5):
    similar_products = []
    data = get_data_from_website(url, search_term)
    products = data['products']
    # Get the product details for the selected product
    selected_product = get_product_details(product_id)
    selected_product_name = selected_product['title']
    selected_product_description = selected_product['body_html']
    selected_product_image_url = selected_product['images']
    # Compute the similarity score between the selected product and each other product
    for product in products:
        product_id = product['id']
        product_name = product['title']
        product_description = product['body_html']
        product_image_url = product['images']
        product_similarity_score = 0.0
        if search_term:
            product_similarity_score += get_nlp_similarity(nlp, selected_product_name, product_name)
            product_similarity_score += get_nlp_similarity(nlp, selected_product_description, product_description)
        try:
            product_similarity_score += get_image_similarity(Image.open(BytesIO(requests.get(selected_product_image_url).content)), Image.open(BytesIO(requests.get(product_image_url).content)))
        except Exception as e:
            print(f"Error loading image for product {product_id}: {e}")
            continue
        if product_similarity_score >= threshold:
            similar_product = {'id': product_id, 'name': product_name, 'description': product_description, 'images': product_image_url, 'similarity_score': product_similarity_score}
            similar_products.append(similar_product)
    return similar_products

