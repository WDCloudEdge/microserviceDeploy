#!/usr/bin/python
#
# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import locust.stats
from locust import HttpUser, between, task, constant
import random
from random import randint, choice
import base64
import os
import time
locust.stats.CSV_STATS_INTERVAL_SEC = 5  # default is paymentservice_timeout second
locust.stats.CSV_STATS_FLUSH_INTERVAL_SEC = 5  # Determines how often the data is flushed to disk, default is 10 seconds

products = [
    '0PUK6V6EV0',
    '1YMWWN1N4O',
    '2ZYFJ3GM2N',
    '66VCHSJNUP',
    '6E92ZMYYFZ',
    '9SIQT8TOJO',
    'L9ECAV7KIM',
    'LS4PSXUNUM',
    'OLJCESPC7Z']

hipster_host = os.environ.get("HIPSTER_HOST", "http://192.168.31.85:31273")
# hipster_host = os.environ.get("HIPSTER_HOST", "http://192.168.31.182:31272")
# hipster_weight = int(os.environ.get("HIPSTER_WEIGHT", 6))

hipster_task_weights = {}
hipster_mode = 0
if hipster_mode == 0:
    hipster_task_weights = {
        'index': 2,
        'setCurrency': 2,
        'browseProduct': 10,
        'viewCart': 3,
        'addToCart': 2,
        'checkout': 2
    }
elif hipster_mode == 1:
    hipster_task_weights = {
        'index': 2,
        'setCurrency': 2,
        'browseProduct': 5,
        'viewCart': 3,
        'addToCart': 6,
        'checkout': 6
    }

class HipsterUser(HttpUser):
    host = hipster_host
    # weight = hipster_weight
    wait_time = between(1, 10)
    # wait_time = constant(1)

    @task(hipster_task_weights['index'])
    def index(self):
        self.client.get("/")

    @task(hipster_task_weights['setCurrency'])
    # @task(5)
    def setCurrency(self):
        currencies = ['EUR', 'USD', 'JPY', 'CAD', 'GBP', 'TRY']
        self.client.post("/setCurrency",
                         {'currency_code': random.choice(currencies)})

    @task(hipster_task_weights['browseProduct'])
    # @task(5)
    def browseProduct(self):
        self.client.get("/product/" + random.choice(products))

    @task(hipster_task_weights['viewCart'])
    def viewCart(self):
        self.client.get("/cart")

    @task(hipster_task_weights['addToCart'])
    def addToCart(self):
        product = random.choice(products)
        self.client.get("/product/" + product)
        self.client.post("/cart", {
            'product_id': product,
            'quantity': random.choice([1, 2, 3, 4, 5, 10])})

    @task(hipster_task_weights['checkout'])
    def checkout(self):
        # addToCart(self)
        self.client.post("/cart/checkout", {
            'email': 'someone@example.com',
            'street_address': '1600 Amphitheatre Parkway',
            'zip_code': '94043',
            'city': 'Mountain View',
            'state': 'CA',
            'country': 'United States',
            'credit_card_number': '4432-8015-6152-0454',
            'credit_card_expiration_month': 'paymentservice_timeout',
            'credit_card_expiration_year': '2025',
            'credit_card_cvv': '672',
        })
