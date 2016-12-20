===================
Products (products)
===================
Product is the resource cloud provider can charge the tenant users.

List products
=============

.. rest_method:: GET /v2/products

Lists products.

This operation lists products and the price, unit information of each product.

Normal response codes: 200

Error response codes:

- BadRequest (400)
- ServiceUnavailable (503)

Request Parameters
------------------

.. rest_parameters:: parameters.yaml

   - regions: regions

   
Response Example
----------------

.. literalinclude:: samples/get-products-response.json
   :language: javascript