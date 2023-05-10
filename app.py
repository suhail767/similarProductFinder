import math
from flask import Flask, render_template, request, jsonify, url_for
from flask_caching import Cache

from celery_utils import make_celery
from utils import get_data_from_website, get_product_details, get_nlp_similarity, get_image_similarity, get_similar_products
from tasks import get_similar_products_async

import spacy


app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = make_celery(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple', 'CACHE_DEFAULT_TIMEOUT': 60*60})

# Load the SpaCy model
nlp = spacy.load("en_core_web_md")


@app.route('/')
def home():
    return 'Welcome to the recommendation system!'


@app.route('/recommendations')
@cache.cached(timeout=3600)
def get_recommendations():
    search_term = request.args.get('q')
    url = 'https://www.boysnextdoor-apparel.co/collections/all/products.json'

    try:
        # Call the Celery task asynchronously to get the similar products for the selected product
        product_id = int(request.args.get('id', 0))
        similar_products = get_similar_products_async.delay(product_id, url, search_term)

        # Get the product data from the website
        data = get_data_from_website(url, search_term)
        products = data['products']
        if not products:
            return 'No products found.'

        # Get the current page number from the query string, default to page 1
        page = int(request.args.get('page', 1))

        # Calculate the number of products per page
        per_page = 10

        # Calculate the starting and ending index of products to display on the current page
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        # Slice the products list to get only the products to display on the current page
        current_page_products = products[start_index:end_index]

        # Get the selected product ID from the query string, default to the first product on the current page
        if product_id == 0 and current_page_products:
            product_id = current_page_products[0]['id']
        selected_product = get_product_details(product_id)

        # Calculate the total number of pages
        num_pages = math.ceil(len(products) / per_page)

        # Return the current page number, number of pages, and the products and similar products to display
        # on the current page
        return render_template('recommendations.html', page=page, num_pages=num_pages, products=current_page_products,
                               selected_product=selected_product, similar_products=similar_products,
                               search_term=search_term)

    except Exception as e:
        print(f"Error: {str(e)}")
        return "An error occurred while processing your request. Please try again later."


@app.route('/similar_products/<int:product_id>')
def similar_products(product_id):
    url = 'https://www.boysnextdoor-apparel.co/collections/all/products.json'
    search_term = request.args.get('q')
    similar_products = get_similar_products(product_id, url, search_term)
    return jsonify(similar_products)


@app.context_processor
def utility_functions():
    def get_image_url(product):
        return url_for('static', filename=product['images'])
    return {'get_image_url': get_image_url}


if __name__ == '__main__':
    app.run(debug=True)
