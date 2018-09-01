#!/usr/bin/env python3
import requests, json, math, sys, urllib3


class McDonaldsError(Exception):
    pass
    
class Client(object):
    BASE = "https://api.mcd.com/v3"
    SIGN_IN = BASE + "/customer/session/sign-in-and-authenticate"
    REGISTER = BASE + "/customer/registration"
    OFFERS = BASE + "/customer/offer"
    STORES = BASE + "/restaurant/location"
    STORE_INFO = BASE + "/restaurant/information"
    MENU_CATEGORIES = BASE + "/nutrition/category/list"
    MENU_CATEGORY = BASE + "/nutrition/category/detail"
    ZIP_LOOKUP = 'http://geoservices.tamu.edu/Services/Geocode/WebService/GeocoderWebServiceHttpNonParsed_V04_01.aspx'
    ORDER_TOTAL = BASE + "/order/total"
    ORDER_INITIAL = BASE + "/order/pickup"
    ORDER_INITIAL_CONFIRM = ORDER_INITIAL + "/{}" # format
    ORDER_PICKUP = BASE + "/orders/pickup/{}" # format
    ORDER_FINAL = ORDER_INITIAL_CONFIRM + "/unattended" # format
    PROFILE = BASE + '/customer/profile'
    LOOKUP_ITEM = BASE + "/item/nutrition/listExternal"

    def __init__(self, api_key:str, hash:str="MCDONALDS", market:str='US', application:str='MOT', language:str='en-US', platform:str='iphone', version:str='0.0.1.I', nonce:str='happybaby', verify_certificates:bool=True):
        self.api_key = api_key
        self.hash = hash
        self.market = market
        self.application = application
        self.language = language
        self.platform = platform
        self.version = version
        self.nonce = nonce
        self.verify_certificates = verify_certificates
        self.username = None
        self.token = None
        self.zip_code = None
        self.store = None
        self.items = {}
        self.items_internal = {}
        self.food = None
        self.food_price = -1
        self.card = None
        self.order_payment_id = -1
        self.client = requests.Session()
        self.client.verify = verify_certificates
        if not verify_certificates:
            urllib3.disable_warnings()
        self.client.headers.update({'marketId': market, 'mcd_apikey': api_key})
        self.check_in_code = None
    def sign_in(self, email: str, password: str):
        '''
        signs into mcdonalds account and gets the login token
        '''
        payload = {"marketId":self.market,
            "application":self.application,
            "languageName":self.language,
            "platform":self.platform,
            "versionId":self.version,
            "nonce":self.nonce,
            "hash":self.hash,
            "userName":email,
            "password":password,
            "newPassword":None,
        }

        response = self.client.post(self.SIGN_IN, json=payload).json()
        self._check_for_error(response)
        self.username = email
        self.token = response["Data"]["AccessData"]["Token"]
        self.client.headers.update({"Token":self.token})
        self.zip_code = response["Data"]["CustomerData"]["ZipCode"] 
    @staticmethod
    def _check_for_error(response):
        '''
        checks to make sure the error code is 1
        '''
        if response["ResultCode"] != 1:
            raise McDonaldsError("error code {}".format(result_code))

    def _check_signed_in(f):
        def wrapper(self, *args, **kwargs):
            if not self.username:
                raise McDonaldsError('You must sign in to access this method.')
            return f(self, *args, **kwargs)
        return wrapper
    def register(self, email:str, password: str, zip_code:str, f_name:str="First", l_name:str="Last"):
        '''
        registers a mcdonalds account
        '''
        payload = {
			"marketId": self.market,
			"application": self.application,
			"languageName": self.language,
			"platform": self.platform,
			"userName": email,
			"password": password,
			"firstName": f_name,
			"lastName": l_name,
			"nickName": null,
			"mobileNumber": "",
			"emailAddress": email,
			"isPrivacyPolicyAccepted": True,
			"preferredNotification": 0,
			"receivePromotions": True,
			"cardItems": [],
			"accountItems": [],
			"zipCode": zip_code,
			"optInForCommunicationChannel": False,
			"optInForSurveys": False,
			"optInForProgramChanges": False,
			"optInForContests": False,
			"optInForOtherMarketingMessages": False,
			"notificationPreferences": {
				"AppNotificationPreferences_OfferExpirationOption": 0,
				"EmailNotificationPreferences_LimitedTimeOffers": False,
				"AppNotificationPreferences_Enabled": False,
				"EmailNotificationPreferences_EverydayOffers": False,
				"EmailNotificationPreferences_YourOffers": False,
				"AppNotificationPreferences_YourOffers": False,
				"AppNotificationPreferences_PunchcardOffers": False,
				"AppNotificationPreferences_LimitedTimeOffers": False,
				"EmailNotificationPreferences_OfferExpirationOption": 0,
				"EmailNotificationPreferences_Enabled": False,
				"EmailNotificationPreferences_PunchcardOffers": False,
				"AppNotificationPreferences_EverydayOffers": False
			},
			"preferredOfferCategories": [],
			"subscribedToOffer": True,
			"isActive": True
		}
        response = self.client.post(self.REGISTER, json=payload).json()
        self._check_for_error(response)
    @staticmethod
    def _distance(lat1:float, lon1:float, lat2:float, lon2:float):
        '''
        calculates the distance between 2 coordinates
        '''
        radius = 3959 # mi, 6371 km

        dlat = math.radians(lat2-lat1)
        dlon = math.radians(lon2-lon1)
        a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
            * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return radius * c

    def lookup_zip(self,zip_code:int=-1):
        '''
        looks up a coordinate from a zip code / account zip code
        '''
        if not zip_code:
            if not self.username:
                raise McDonaldsError("Supply a zip code or sign in to use this method.")
            zip_code = self.zip_code
        payload = {
                "apikey":"demo",
                "format":"json",
                "version":"4.01",
                "zip":zip_code
        }
        response = requests.get(self.ZIP_LOOKUP, params=payload).json()
        geocode = response["OutputGeocodes"][0]["OutputGeocode"]
        if geocode["Latitude"] == "0" and geocode["Longitude"] == "0":
            raise McDonaldsError("geoservices.tamu.edu has banned your ip (apikey = demo).")
        return geocode["Latitude"], geocode["Longitude"]

    @_check_signed_in
    def find_stores(self, latitude:str, longitude:str, range:int=8):
        '''
        finds stores near a latitude and longitude location
        '''
        payload = {"filter":"search",
                    "query":json.dumps({
                        "generalStoreStatusCode":"OPEN",#,TEMPCLOSE,RENOVATION",
                        "market":self.market,
                        "storeAttributes":[],
                        "pageSize":25,
                        "local":self.language,
                        "locationCriteria":{
                            "distance":str(range),
                            "longitude":longitude,
                            "latitude":latitude
                        }
                    })
        }
        response = self.client.get(self.STORES, params=payload).json()
        data = []
        for store in response:
            store_lat = float(store["address"]["location"]["lat"])
            store_long = float(store["address"]["location"]["lon"])
            data.append({
                "status":store["generalStatus"]['status'],
                "address":"{}, {}, {} {}".format(store["address"]["addressLine1"], store["address"]["cityTown"], store["address"]["subdivision"],
                    store["address"]["postalZip"]),
                "coordinates": {"latitude":store_lat, "longitude":store_long},
                "id":store["identifiers"]["storeIdentifier"][1]["identifierValue"],
                "distance":self._distance(float(latitude),float(longitude),store_lat,store_long),
                "phone":store["storeNumbers"]["phonenumber"][0]["number"]
            })
        return data
    @_check_signed_in
    def offers(self,store=None, coords:list=None):
        '''
        finds offers for a store or by a coordinate
        '''
        payload = {"application":self.application,
                "languageName": self.language,
                "marketId": self.market,
                "platform": self.platform,
                "userName": self.username,
        }
        if coords:
            payload["latitude"] = coords[0]
            payload["longitude"] = coords[1]
        elif store:
            payload["storeId"] = [store["id"]]
            payload["latitude"] = store["coordinates"]["latitude"]
            payload["longitude"] = store["coordinates"]["longitude"]

        response = self.client.get(self.OFFERS, params=payload).json()
        self._check_for_error(response)
        return response["Data"]

    @_check_signed_in
    def menu(self, store,show_promotions:bool=False, lookup_promo_bases:bool=False):
        '''
        creates the store menu by going through each category,
        and removing the store outages
        '''
        self.store = store
        store_payload = {
                "application":self.application,
                "languageName":self.language,
                "marketId":self.market,
                "platform":self.platform,
                "storeNumber":store["id"]
        }
        response = self.client.get(self.STORE_INFO, params=store_payload).json()
        self._check_for_error(response)
        missing_products = response["Data"]["OutageProductCodes"]

        base_payload = {
                "country":self.market,
                "language":self.language[:2],
                "languageName":self.language,
                "showLiveData":1
        }
        response = self.client.get(self.MENU_CATEGORIES, params={**base_payload, **{"categoryType":1}}).json()
        ids = [category["category_id"] for category in response["categories"]["category"]]
        data = {}
        for id in ids:
            response = self.client.get(self.MENU_CATEGORY, params={**base_payload, **{"categoryId":id}}).json()
            category = response["category"]["category_name"]
            data[category] = {}
            for item in response["category"]["items"]["item"]:
                if item["external_id"] not in missing_products and (item["do_not_show"] == "Core" or show_promotions):
                    data[category][item["item_name"]] = item["external_id"]
                    self.items[item["external_id"]] = item["item_name"]
                if item["do_not_show"] == "Promotional" and "-" in item["external_id"] and lookup_promo_bases:
                    name, base = self._get_base_item(item["external_id"])
                    if name and base not in missing_products:
                        self.items[base] = name
                        data[category][name] = base
        return data
    def _get_base_item(self, item):
        '''
        returns the base item, if any for a promotional item ending in a -XXX code
        '''
        base = item.split("-")[0]
        return self.lookup_item(int(base)), base

    @_check_signed_in
    def promotion_picker(self, lookup_items:bool=False, all_deals:bool=False, min_products:int=0,lookup_promo:bool=False):
        '''
        picks promotions using the users offers
        '''
        offers = self.offers(store=self.store)
        for i, offer in enumerate(offers):
            if offer["Id"] < 0 or all_deals:
                print("[{}] {} ({})".format(i+1, offer["Name"], offer["Id"]))
        offer_id = int(input("Offer # > "))
        offer = offers[offer_id-1]
        promotion = {"id":offer["Id"], "type":0, "parts":[]}
        for product in offer["ProductSets"]:
            try:
                promotion['type'] = product["Action"]["DiscountType"]
            except TypeError:
                pass
            item_id = 0
            if product["AnyProduct"] == True:
                item_id = int(input("Pick any product id > "))
            else:
                for i, item in enumerate(product["Products"]):
                    try:
                        print("[{}] {} ({})".format(i+1, self.items[item], item))
                    except KeyError:
                        if lookup_items or len(product["Products"]) <= min_products:
                            try:
                                name = self.lookup_item(item,promotions=lookup_promo)
                                if name:
                                    print("[{}] {} ({})".format(i+1, name, item))
                            except KeyError:
                                pass

            if not product["Alias"]:
                print("Item to buy for promotion")
            else:
                print(product["Alias"])
            item_id = int(input("Pick item for this category > "))
            item = product["Products"][item_id-1]
            promotion["parts"].append({"id": int(item), "alias": product["Alias"]})
        return promotion
    def lookup_item(self, item:int, promotions=False):
        # https://api.mcd.com/v3/items/nutrition/listExternal?country=US&externalItemId=1&externalItemId=2&language=en&languageName=en-US
        payload = {
                "country": self.market,
                "language": self.language[:2],
                "languageName": self.language,
                "externalItemId": item
        }
        response = self.client.get(self.LOOKUP_ITEM, params=payload).json()
        if "error" in response:
            return None
        elif response["items"]["item"]["do_not_show"] == "Core" or promotions:
            return response["items"]["item"]["item_name"]
        return None
    @_check_signed_in
    def order_picker(self, menu, promo_lookup_items:bool=False, promo_all_deals:bool=False, promo_min_products:int=0, promo_lookup_promo:bool=False):
        '''
        the main order picker, incorporating the promotion picker
        '''
        items = {"normal":[], "deals":[]}
        menu["Promotions"] = "Promotions"
        while True:
            for i, category in enumerate(menu.keys()):
                print("[{}] {}".format(i+1, category))
            category_id = int(input("Category number > "))
            menu_category = menu[list(menu.keys())[category_id-1]]
            if menu_category == "Promotions":
                items["deals"].append(self.promotion_picker(lookup_items=promo_lookup_items, all_deals=promo_all_deals, min_products=promo_min_products,lookup_promo=promo_lookup_promo))
                del menu["Promotions"] # only 1 promotion per order
                if input("done [Y/n] > ").lower() == "y":
                    break
                continue
            for i, item in enumerate(menu_category.keys()):
                print("[{}] {} ({})".format(i+1, item, menu_category[item]))
            item_id = int(input("Item number (0 to cancel) > "))
            if item_id != 0:
                item = menu_category[list(menu_category.keys())[item_id-1]]
                raw_quantity = input("Amount (default:1) > ")
                if raw_quantity == "":
                    quantity = 1
                else:
                    quantity = int(raw_quantity)
                items["normal"].append({"id":int(item),"quantity":quantity})
                if input("done [Y/n] > ").lower() == "y":
                    break
        return items


    
    @_check_signed_in
    def get_price(self, food):
        '''
        returns the price of the current order
        '''
        self.food = food
        payload = self._generate_json(food)
        response = self.client.post(self.ORDER_TOTAL, json=payload).json()
        self._check_for_error(response)
        self.food_price = response['Data']['OrderView']['TotalValue']
        return response['Data']['OrderView']['TotalValue']

    def _generate_json(self, raw_order, card=None):
        '''
        generates the json for ordering, picking up or checking the prices for an order
        '''
        base = {
        "userName": self.username,
        "languageName": self.language,
        "platform": self.platform,
        "marketId": self.market,
        "isNormalOrder": False,
        "storeId": self.store["id"],
        "application": self.application,
        "options": ["ApplyPromotion"],
        "orderView": {}
        }
        normal_product_json = []
        for item in raw_order["normal"]:
            item_json = {
                    "Choices": [],
                    "ProductCode": item["id"],
                    "Customizations": [],
                    "Quantity": item["quantity"]
            }
            normal_product_json.append(item_json)
        promotional_product_json = []
        for item in raw_order["deals"]:
            item_json = {
			"Id": item["id"],
			"Type": item["type"],
            "ProductSets": []
            }
            for part in item["parts"]:
                part_json = {
                        "Alias": part["alias"],
                        "Products": [{
                            "Choices": [],
                            "ProductCode": part["id"],
                            "Customizations": [],
                            "Quantity": 1,
                        }],
                        "Quantity": 1
                }
                item_json["ProductSets"].append(part_json)
            promotional_product_json.append(item_json)
            

		
        order_view = {
            "Market": self.market,
            "LanguageName": self.language,
            "NickName": "",
            "StoreID": self.store["id"],
            "Products": normal_product_json,
            "UserName": self.username,
            "PriceType": 2,
            "PromotionListView": promotional_product_json
        }
        if card:
            order_view["Payment"] = {
                "POD": 0,
                "OrderPaymentId": None,
                "CustomerPaymentMethodId": card["CustomerPaymentMethodId"],
                "PaymentDataId": -1,
                "PaymentMethodId": card["PaymentMethodId"]
            }
        base["orderView"] = order_view
        return base

    @_check_signed_in
    def order(self, card, food=None, store=None):
        '''
        Orders the food
        '''
        if food:
            self.food = food
        if store:
            self.store = store
        self.card = card
        payload = self._generate_json(self.food, card=card)
        response = self.client.post(self.ORDER_INITIAL, json=payload).json()
        self.order_payment_id = response['OrderView']['OrderPaymentId']
        self.food_price = response['OrderView']['TotalValue']
        self.check_in_code = response["OrderView"]["CheckInCode"]

    
    @_check_signed_in
    def pickup(self):
        '''
        CHARGES PAYMENT METHOD
        Allows food for pickup and returns the order number.
        '''
        self._get_order_pickup()
        payload = {
                "marketId": self.market,
                "languageName": self.language,
                "POSStoreNumber":self.store["id"],
                "application": self.application,
                "platform": self.platform
        }

        response = self.client.post(self.ORDER_INITIAL_CONFIRM.format(self.check_in_code), json=payload).json()
        self._get_order_pickup()
        payload = {
                "OrderPayment": {
                    "PaymentMethodId": 3,
                    "OrderPaymentId": self.order_payment_id,
                    "CustomerPaymentMethodId": self.card["CustomerPaymentMethodId"],
                    "POD": 0
                },
                "languageName": self.language,
                "platform": self.platform,
                "marketId": self.market,
                "POSStoreNumber": self.store["id"],
                "AdditionalPayments": [],
                "PriceType": 2,
                "checkInData": "0",
                "application": self.application


        }
        response = self.client.post(self.ORDER_FINAL.format(self.check_in_code), json=payload).json()
        return response["OrderNumber"]
        
    def _get_order_pickup(self):
        '''
        idk what this does, just that mcdonalds does it
        '''
        payload = {
                "application": self.application,
                "languageName": self.language,
                "marketId": self.market,
                "platform": self.platform
        }

        self.client.get(self.ORDER_PICKUP.format(self.check_in_code), params=payload)

    @_check_signed_in
    def cards(self):
        '''
        returns raw json for the cards that a user has on file
        '''
        payload = {
                "application":self.application,
                "languageName": self.language,
                "marketId": self.market,
                "platform":self.platform,
                "userName":self.username
        }
        response = self.client.get(self.PROFILE, params=payload).json()
        self._check_for_error(response)
        return response['Data']['PaymentCard']

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("usage: mcdonald.py API_KEY USERNAME PASSWORD")
        exit()
    client = Client(sys.argv[1])
    client.sign_in(sys.argv[2], sys.argv[3])
    stores = client.find_stores(*client.lookup_zip())
    menu = client.menu(stores[0], lookup_promo_bases=True)
    items = client.order_picker(menu)
    cards = client.cards()
    total = client.get_price(items)
    print("Paying {} to McDonalds. Use control + c to cancel transaction.".format(total))
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("Transaction canceled.")
        exit()
    print("Ordering food ...")
    client.order(cards[0], items, store=stores[0])
    order_number = client.pickup()
    print("Your order number is {}.".format(order_number))
