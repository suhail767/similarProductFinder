from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'Welcome to the recommendation system!'


from flask import render_template

import json
import requests
import spacy
from PIL import Image
from io import BytesIO


# Load the SpaCy model
nlp = spacy.load("en_core_web_md")

import requests
import json


import os
import time

# Define the function to get data from the website
def get_data_from_website(url):
    # Check if the local JSON file exists and is not older than 1 day
    if os.path.exists('products.json'):
        age = time.time() - os.path.getmtime('products.json')
        if age < 86400:
            # Load the product data from the local JSON file
            with open('products.json', 'r') as f:
                data = json.load(f)
            return data

    # Download the product data from the website
    response = requests.get(url)
    data = response.json()

    # Save the product data to a local JSON file
    with open('products.json', 'w') as f:
        json.dump(data, f)

    return data



# Define the function to get product details
def get_product_details(product_id):
    # Load the product details from the local JSON data file
    with open('products.json', 'r') as f:
        data = json.load(f)
    products = data['products']
    for product in products:
        if product['id'] == product_id:
            return product
    # Product not found, return an error message
    raise ValueError(f"Product with ID {product_id} not found.")



# Define the function to calculate NLP similarity score between two strings
def get_nlp_similarity(str1, str2):
    doc1 = nlp(str1)
    doc2 = nlp(str2)
    return doc1.similarity(doc2)


# Define the function to calculate image similarity score between two images
def get_image_similarity(image1, image2):
    img1 = Image.open(BytesIO(requests.get(image1).content))
    img2 = Image.open(BytesIO(requests.get(image2).content))
    return img1.histogram() == img2.histogram()

# Define the function to get similar products
def get_similar_products(product_id, url):

    # Get the product data from the website
    data = get_data_from_website(url)
    products = data['products']

    # Get the features for the selected product
    selected_product = get_product_details(product_id)
    print("Selected product:", selected_product)

    # Calculate the NLP similarity score between the selected product's title and the titles of all other products
    nlp_scores = {}
    for product in products:
        if product['id'] != product_id:
            #print("Comparing with product:", product)
            nlp_scores[product['id']] = get_nlp_similarity(selected_product['title'], product['title'])


    # Calculate the image similarity score between the selected product's images and the images of all other products
    image_scores = {}
    for product in products:
        if product['id'] != product_id:
            for image in selected_product['images']:
                for pimage in product['images']:
                    image_scores[product['id']] = get_image_similarity(image['src'], pimage['src'])

    # Combine the NLP and image similarity scores using a weighted sum
    combined_scores = {}
    for pid in nlp_scores:
        combined_scores[pid] = 0.6 * nlp_scores[pid] + 0.4 * image_scores[pid]
    print("Combined scores:", combined_scores)

    # Sort the products by their combined similarity scores and return the top 5
    sorted_products = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:5]
    similar_products = []
    for pid, score in sorted_products:
        product = get_product_details(pid)
        similar_product = {
            'id': pid,
            'title': product['title'],
            'product_type': product['product_type'],
            'tags': product['tags'],
            'similarity_score': score,
            'images': product['images']
        }
        similar_products.append(similar_product)

    return similar_products

url = 'https://www.boysnextdoor-apparel.co/collections/all/products.json'
product_id = 7039306924182

@app.route('/recommendations/<int:product_id>')
def get_recommendations(product_id):
    url = 'https://www.boysnextdoor-apparel.co/collections/all/products.json'
    similar_products = get_similar_products(product_id, url)
    return render_template('recommendations.html', similar_products=similar_products)



if __name__ == '__main__':
    app.run(debug=True)
