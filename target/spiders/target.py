import os
import scrapy
from html import unescape


class TargetSpider(scrapy.Spider):
    name = "target"
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
    }

    shared_params = {
        'key': '9f36aeafbe60771e321a7cc95a78140772ab3e96',
        'channel': 'WEB',
        'pricing_store_id': '1771',
        'visitor_id': None,
    }

    params = {
        **shared_params,
        'category': None,
        'count': 24,
        'default_purchasability_filter': 'true',
        'include_dmc_dmr': 'true',
        'include_review_summarization': 'false',
        'new_search': 'false',
        'offset': 0,
        'page': None,
        'platform': 'desktop',
        'scheduled_delivery_store_id': '1771',
        'spellcheck': 'true',
        'store_ids': '1771,1768,1113,3374,1792',
        'useragent': headers['user-agent'],
        'zip': '52404',
    }
    params_detail = {
        **shared_params,
        'tcin': None,
        'is_bot': 'false',
        'store_id': '1771',
        'has_pricing_store_id': 'true',
        'has_financing_options': 'true',
        'include_obsolete': 'true',
        'skip_personalized': 'true',
        'skip_variation_hierarchy': 'false',
        'page': None,
    }
    MAX_LIMIT = 300
    include_headers_line = True
    if os.path.exists('output.csv'):
        data = open('output.csv', 'r').readline()
        if data:
            include_headers_line = False
    custom_settings = {
        "FEEDS": {
            "output.csv": {
                "format": "csv",
                "item_export_kwargs": {
                    "include_headers_line": include_headers_line
                }
            }
        },
    }

    def start_requests(self):
        yield scrapy.Request(
            'https://www.target.com/',
            headers=self.headers,
            callback=self.parse_home,
        )
    
    def parse_home(self, response):
        visitor_id = response.headers.getlist('Set-Cookie')[0].decode().split(';')[0].split('=')[1]
        self.params['visitor_id'] = visitor_id
        self.params_detail['visitor_id'] = visitor_id

        catalog_urls = open("catalog_urls.txt", "r").readlines()
        for category in catalog_urls:
            cat_id = category.strip().split('/N-')[1].split('?')[0]
            base_params = self.params.copy()
            base_params['category'] = cat_id
            base_params['page'] = f'/c/{cat_id}'
            params_str = '&'.join([f'{k}={v}' for k, v in base_params.items()])
            yield scrapy.Request(
                url=f'https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?{params_str}',
                headers=self.headers,
                meta={"params": base_params},
            )

    def parse(self, response):
        base_params = response.meta['params']
        data = response.json()['data']['search']

        products = data['products']
        for product in products:
            product_id = product['tcin']
            base_params_detail = self.params_detail.copy()
            base_params_detail['tcin'] = product_id
            base_params_detail['page'] = f'/p/A-{product_id}'
            params_str = '&'.join([f'{k}={v}' for k, v in base_params_detail.items()])
            yield scrapy.Request(
                url=f'https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1?{params_str}',
                headers=self.headers,
                callback=self.parse_product,
            )

        meta_page = data['search_response']['metadata']
        total_count = meta_page['total_results']
        offset = meta_page['offset']
        new_offset = offset + len(products)
        if new_offset < total_count and offset < self.MAX_LIMIT:
            base_params['offset'] = new_offset
            params_str = '&'.join([f'{k}={v}' for k, v in base_params.items()])
            yield scrapy.Request(
                url=f'https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?{params_str}',
                headers=self.headers,
                meta={"params": base_params},
            )

    def parse_product(self, response):
        main_product = response.json()['data']['product']
        children = main_product.get('children', [])
        category = main_product['category']['name']
        list_check = [main_product] if not children else children

        tcins = {}
        hierarchy = main_product.get('variation_hierarchy', [])
        for item in hierarchy:
            name1_item, value1_item = item['name'], item['value']
            if 'variation_hierarchy' not in item:
                tcins[item['tcin']] = {
                    name1_item.lower(): value1_item,
                }
            else:
                for sub_item in item['variation_hierarchy']:
                    name2_item, value2_item = sub_item['name'], sub_item['value']
                    if 'variation_hierarchy' not in sub_item:
                        tcins[sub_item['tcin']] = {
                            name1_item.lower(): value1_item,
                            name2_item.lower(): value2_item,
                        }
                    else:
                        for sub_sub_item in sub_item['variation_hierarchy']:
                            name3_item, value3_item = sub_sub_item['name'], sub_sub_item['value']
                            tcins[sub_sub_item['tcin']] = {
                                name1_item.lower(): value1_item,
                                name2_item.lower(): value2_item,
                                name3_item.lower(): value3_item,
                            }
                
        for product in list_check:
            if 'is_obsolete' in product and product['is_obsolete']:
                continue
            product_item = product['item']
            enrichment = product_item['enrichment']
            product_description = product_item['product_description']
            product_name = unescape(product_description['title'])
            product_id = product['tcin']
            price = product['price']['formatted_current_price']
            bullets = product_description['soft_bullets']['bullets']
            images = enrichment['images']
            real_desc = product_description['downstream_description']
            specs = product_description['bullet_descriptions']
            specs = [spec.replace('<B>', '').replace('</B>', '') for spec in specs]
            item = {
                'product_name': product_name,
                'meta_title': product_name,
                'product_url': enrichment['buy_url'],
                'product_category': category,
                'product_brand': product_item['primary_brand']['name'],
                'product_keywords': None,
                'meta_keywords': None,
                'product_price': price,
                'product_sku': product_id,
                'color': tcins.get(product_id, {}).get('color', None),
                'size': tcins.get(product_id, {}).get('size', None),
                'product_description': real_desc,
                'meta_description': f'Shop {product_name} at Target. Choose from Same Day Delivery, Drive Up or Order Pickup. Free standard shipping with $35 orders.',
                'product_bullets': '\n'.join(bullets),
                'specifications': '\n'.join(specs),
                'product_image1': images['primary_image_url'],
                'product_image2': images['alternate_image_urls'][0] if images.get('alternate_image_urls') else None,
            }
            yield item
