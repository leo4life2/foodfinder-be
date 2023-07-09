import requests
import os
import json
from bs4 import BeautifulSoup
import concurrent.futures


def scrape_menu(restaurant_alias):
    """Get the menu of a restaurant from its Yelp page.

    Args:
        restaurant_alias (_type_): e.g. 'teriking-seattle'

    Returns:
        list: A list of dictionaries, each containing the name and image URL of a dish.
    """
    response = requests.get(f'https://www.yelp.com/menu/{restaurant_alias}')
    soup = BeautifulSoup(response.text, 'html.parser')

    menu_sections = soup.find('div', attrs={'class': 'menu-sections'})
    if not menu_sections:
        print(f'No menu found for {restaurant_alias}')
        return

    # find pairs of 'section-header' and 'u-space-b3'
    section_headers = menu_sections.find_all('div', class_='section-header')
    u_space_b3s = menu_sections.find_all('div', class_='u-space-b3')

    menu = {}

    for header, space in zip(section_headers, u_space_b3s):
        # find h2 tag in the 'section-header'
        section_title = header.find('h2').text.strip()

        # find 'menu-item' divs in the 'u-space-b3'
        menu_items = space.find_all('div', class_='menu-item')

        menu[section_title] = []

        for item in menu_items:
            arrange_div = item.find('div', class_='arrange')

            # find 'arrange_unit' divs in the 'arrange' div
            arrange_units = arrange_div.find_all('div', class_='arrange_unit')

            # get text of h4 tag and p tag
            h4 = arrange_units[1].find('h4')
            h4_text = h4.text.strip()
            obj = {
                'title': h4_text
            }

            h4_link = h4.find('a')
            if h4_link:
                obj['link'] = "https://www.yelp.com" + h4_link['href']

            img_url = arrange_units[0].find('img', class_='photo-box-img')
            if img_url:
                link = img_url['src']
                if '60s' in link:
                    link = link.replace('60s', '180s') # get higher resolution image. Otherwise it may be a placeholder, so ignore.
                    obj['img_url'] = link

            p_text = arrange_units[1].find(
                'p', class_='menu-item-details-description')
            if p_text:
                p_text = p_text.text.strip()
                obj['description'] = p_text

            price_text = arrange_units[1].find(
                'li', class_='menu-item-price-amount')
            if price_text:
                price_text = price_text.text.strip()
                obj['price'] = price_text

            # store in a dictionary
            menu[section_title].append(obj)

    return menu


def dish_review(restaurant_id, dish_name, limit=5):
    """Get the reviews of a dish from a restaurant.

    Args:
        restaurant_id (_type_): e.g. RhwOYGx3GV1x_e_1FMhXKg
        dish_name (_type_): url-encoded dish name, e.g. spicy%20chicken%20bowl

    Returns:
        list: A list of dictionaries, each containing the reviewer name, dish rating, review text, and date.
    """

    headers = {
        'authority': 'www.yelp.com',
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/json',
        'pragma': 'no-cache',
        'referer': 'https://www.yelp.com/biz/teriking-seattle',
        'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest',
    }

    review_link = f'https://www.yelp.com/popular_dish/{restaurant_id}/food/{dish_name}'

    response = requests.get(review_link, headers=headers,)
    if response.status_code != 200:
        # Try again with /menu/ instead of /food/
        review_link = f'https://www.yelp.com/popular_dish/{restaurant_id}/menu/{dish_name}'
        response = requests.get(
            review_link,
            headers=headers,
        )
    if response.status_code != 200:
        return None

    result = json.loads(response.text)
    reviews_raw = result["reviewData"]["reviews"]

    reviews = []
    count = 0
    for r in reviews_raw:
        if count >= limit:
            break
        count += 1
        obj = {
            "reviewer": r["userDisplayName"],
            "dish_rating": r["rating"],
            "review_text": r["text"],
            "date": r["date"]
        }
        reviews.append(obj)

    return reviews


def get_menu_reviews(restaurant_alias, restaurant_id):
    """Get the menu and reviews of a restaurant.

    Args:
        restaurant_alias (_type_): e.g. 'teriking-seattle'
        restaurant_id (_type_): e.g. RhwOYGx3GV1x_e_1FMhXKg

    Returns:
        dict: A dictionary containing the menu and reviews of the restaurant.
    """
    menu = scrape_menu(restaurant_alias)
    # for i in range(len(menu)):
    #     dish = menu[i]
    #     name = dish["name"]
    #     name = name.lower().replace(" ", "%20")
    #     reviews = dish_review(restaurant_id, name)

    #     menu[i]["reviews"] = reviews

    return menu


def get_restaurants_and_menus(location, term, radius, open_now=False, categories=None, price=None, sort_by="best_match", limit=20, delivery=False):
    base_url = "https://api.yelp.com/v3/businesses/search"

    # Encode URL parameters
    encoded_location = requests.utils.quote(location)
    encoded_term = requests.utils.quote(term)

    if delivery:
        delivery = "restaurants_delivery"

    # Construct the URL with parameterized values
    url = f"{base_url}?location={encoded_location}&term={encoded_term}&radius={radius}&sort_by={sort_by}&limit={limit}&attributes={delivery}"

    if categories:
        url += f"&categories={categories}"

    if price:
        url += f"&price={price}"

    if open_now:
        url += f"&open_now={open_now}"

    api_key = os.getenv("YELP_API_KEY")
    if not api_key:
        raise Exception("YELP_API_KEY environment variable not set")
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"An error occurred getting restaurants: {response.text}")
        return
    else:
        print("Successfully got restaurants")

    result = json.loads(response.text)
    businesses = result["businesses"]

    print("Found {} restaurants".format(len(businesses)))

    # Create a thread pool and submit tasks to it
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_menu = {executor.submit(
            get_menu_reviews, bz["alias"], bz["id"]): bz for bz in businesses}

        for future in concurrent.futures.as_completed(future_to_menu):
            biz = future_to_menu[future]
            try:
                biz["menu"] = future.result()
                print(f"Successfully got menu for restaurant {biz['name']}")
            except Exception as e:
                print(
                    f"An error occurred getting menu for restaurant {biz['name']}: {e}")

    return businesses


def get_nearby_food_info(location, term, radius, open_now=False, categories=None, price=None, sort_by="best_match", limit=20, delivery=False):
    businesses = get_restaurants_and_menus(location, term, radius, open_now=open_now,
                                           categories=categories, price=price, sort_by=sort_by, limit=limit, delivery=delivery)
    result = ""

    for i in range(len(businesses)):
        b = businesses[i]

        if not b.get("menu"):
            print(f"Skipping {b['name']} because no menu was found")
            continue
        biz_string = ""
        biz_string += f"Restaurant: {b['name']}\n"
        # biz_string += f"Index: {i}\n"
        biz_string += f"Rating: {b['rating']}\n"
        biz_string += "Menu:\n"

        # dish_index = 0
        for cat, dishes in b["menu"].items():
            biz_string += f"\t{cat}\n"
            for d in dishes:
                biz_string += f"\t\tDish: {d['title']}\n"
                # biz_string += f"\t\tIndex: {dish_index}\n"
                # dish_index += 1
                if d.get("price"):
                    biz_string += f"\t\tPrice: {d['price']}\n"
                if d.get("description"):
                    biz_string += f"\t\tDescription: {d['description']}\n"
                if d.get("reviews"):
                    avg_rating = sum([r["dish_rating"]
                                     for r in d["reviews"]]) / len(d["reviews"])
                    biz_string += f"\t\tAvg Rating: {avg_rating}\n"

        result += biz_string + "\n"

    return result, businesses


def main():
    print(json.dumps(scrape_menu("saint-bread-seattle-2")))
    # # Example usage
    # location = "1524 Taylor Ave N, 98109"
    # term = "food"
    # radius = 2000
    # categories = "japanese"
    # price = 2
    # open_now = False
    # sort_by = "best_match"
    # limit = 50
    # delivery = True

    # result = get_restaurants_and_menus(location, term, radius, open_now=open_now, categories=categories, price=price, sort_by=sort_by, limit=limit, delivery=delivery)
    # with open('data.json', 'w') as outfile:
    #     json.dump(result, outfile)


if __name__ == "__main__":
    main()
