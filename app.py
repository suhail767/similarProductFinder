import math
from flask import Flask, render_template, request, jsonify, url_for, redirect
from flask_caching import Cache
import webbrowser
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
    return render_template('home.html')


@app.route('/submit_product_id', methods=['POST'])
def submit_product_id():
    product_id = request.form.get('product_id')
    return redirect(url_for('get_recommendations', product_id=product_id))


@app.route('/recommendations')
@cache.cached(timeout=3600)
def get_recommendations():
    search_term = request.args.get('q')
    url = 'https://www.boysnextdoor-apparel.co/collections/all/products.json'

    try:
        # Get the product ID entered by the user
        product_id = int(request.args.get('product_id'))

        if not product_id:
            # If product ID is not provided, display a form to enter the product ID
            return render_template('get_product_id.html')

        # Check if the product ID is valid
        selected_product = get_product_details(product_id)
        if not selected_product:
            return 'Invalid product ID'

        # Call the Celery task asynchronously to get the similar products for the selected product
        similar_products_task = get_similar_products_async.delay(product_id, url, search_term)

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

        # Get the selected product details
        selected_product_details = {
            'id': selected_product['id'],
            'title': selected_product['title'],
            'product_type': selected_product['product_type'],
            'vendor': selected_product['vendor'],
            'tags': selected_product['tags'],
            'images': selected_product['images']
        }

        # Calculate the total number of pages
        num_pages = math.ceil(len(products) / per_page)

        # Check if the similar products task has completed
        if similar_products_task.ready():
            # Get the results from the task
            similar_products = similar_products_task.get()
        else:
            # Set the similar products to None
            similar_products = None

        # Return the current page number, number of pages, and the products and similar products to display
        # on the current page
        return render_template('recommendations.html', page=page, num_pages=num_pages, products=current_page_products,
                               selected_product=selected_product_details, similar_products=similar_products,
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
        if isinstance(product['images'], list):
            return [url_for('static', filename=image) for image in product['images']]
        else:
            return url_for('static', filename=product['images'])
    return {'get_image_url': get_image_url}


if __name__ == '__main__':
    app.run(debug=True)
    webbrowser.open('http://127.0.0.1:5000', new=2)
