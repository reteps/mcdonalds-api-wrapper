# mcdonalds-api-wrapper

Using python to order mcdonalds from the command line

# Notice

This is over a year old. Most likely depreciated in some way, see [Issue #2](https://github.com/reteps/mcdonalds-api-wrapper/issues/2)
### Setup

+ Find your `api_key`. This can be done using charles or wireshark and
  sniffing the requests made to a `api.mcd.com` endpoint and checking
  the `api_key` header.
+ Add a card on file. Currently, McdonaldsOnline cannot add new cards,
  so after you add a card you can order.
### Example

```python3
#!/usr/bin/env python3

client = Client("API_KEY")
client.sign_in("USERNAME","PASSWORD")
stores = client.find_stores(*client.lookup_zip())
menu = client.menu(stores[0])
items = client.order_picker(menu)
cards = client.cards()
client.order(cards[0], items)
total = client.get_price(items)
confirm = input("Pay {} and complete transaction? [y/N] > ".format(total))
if confirm == "y":
  order_number = client.pickup()
  print("Order #{}".format(order_number))

```

### Documentation

`Client(api_key, market='US', language='en-US')`
+ Creates a new client (other defaults can be set other than what is shown)

`Client.sign_in(email, password)`
+ Signs into account, required for most methods

`Client.register(email, password, zip_code, f_name="", l_name="")`
+ Registers a new account

`Client.lookup_zip(zip_code=-1)`
+ Returns a coordinate from a zip_code or the one used from sign up.

`Client.find_stores(latitude, longitude, range=8)`
+ Finds nearby stores in the range specified of the coordinate

`Client.offers(store=None, coords=None)`
+ Returns offers for a store or by a coordinate

`Client.menu(store, show_promotions=False, lookup_promo_bases=False)`
+ Returns the core or full menu for a store, removing store outages. You can lookup promotional bases for a more complete menu.

`Client.promotion_picker(lookup_items=False, all_deals=False, min_products=0,lookup_promo=False)`
+ Interactive promotion picker with the ability to lookup unknown product codes, 
  show online or all promotions, and automatically lookup items when there is less than
  a certain amount of products to choose from. Lookup promo includes promotional items in lookups.

`Client.lookup_item(item, promotions=False)`
+ Returns the item name from an external item id, and can exclude promotions

`Client.order_picker(menu, promo_lookup_items=False, promo_all_deals=False, promo_min_products=0, promo_lookup_promo=False)`
+ Interactive order picker given a menu from `Client.menu`. Passes `promo_` options to promotion_picker

`Client.get_price(food)`
+ Returns the total including tax for an order

`Client.cards()`
+ Returns the cards a user has on file

`Client.order(card, food=None)`
+ Orders the food given a card returned by `Client.cards()`, using food supplied or 
the food used in `Client.get_price`

`Client.pickup()`
+ Credits the payment method, and returns the order number for in-store pickup.

### Recent changes

+ `Client.pickup` method functional and tested once
+ Added lookup_promo as an option to the `promotion_picker`
