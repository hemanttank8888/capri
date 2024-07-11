import json
import os
import scrapy


class CapriSpiderSpider(scrapy.Spider):
    name = "capri_spider"
    allowed_domains = ["caprioptics.com"]
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    data_list = []

    def start_requests(self):
        url = 'https://caprioptics.com/my-account/'
        yield scrapy.Request(url, headers=self.headers, callback=self.parsea, dont_filter=True)

    def parsea(self, response):
        # Extract the nonce value from the login form
        nonce = response.css('input#woocommerce-login-nonce::attr(value)').extract_first()
        # Your login credentials
        username = 'prsny'
        password = 'prsny'

        # Form data to be sent in the POST request
        formdata = {
            'username': username,
            'password': password,
            'woocommerce-login-nonce': nonce,
            '_wp_http_referer': '/',
            'rememberme': 'forever',
            'redirect': '',
            'login': 'Login'
        }

        login_url = 'https://caprioptics.com/'

        # Create a FormRequest to log in
        yield scrapy.FormRequest(
            url=login_url,
            formdata=formdata,
            headers=self.headers,
            callback=self.after_login,
            meta={'dont_redirect': True},
            errback=self.handle_error
        )

    def after_login(self, response):
        self.log("Login successful!")
        cookies = response.headers.getlist('Set-Cookie')
        cookie_value = cookies[1].decode('utf-8') if len(cookies) > 1 else None
        url = "https://caprioptics.com/browse/"
        yield scrapy.Request(
            url,
            headers=self.headers,
            cookies={'cookie': cookie_value},
            callback=self.parse,
            dont_filter=True,
            meta={'headers': self.headers, 'cookies': cookies}
        )

    def handle_error(self, failure):
        request = failure.request
        response = failure.value.response
        self.log(f"Request failed: {request}, Status code: {response.status}")
        cookies = response.headers.getlist('Set-Cookie')
        self.log("Cookies: %s" % cookies)
        cookie_value = cookies[1].decode('utf-8') if len(cookies) > 1 else None
        url = "https://caprioptics.com/browse/"
        yield scrapy.Request(
            url,
            headers=self.headers,
            cookies={'cookie': cookie_value},
            callback=self.parse,
            dont_filter=True,
            meta={'cookies': cookies}
        )

    def parse(self, response):
        all_collection = response.xpath("//h2/following-sibling::div[@class='buttons']/a[1]/@href").getall()
        for url_collection in all_collection:
            yield scrapy.Request(url_collection, headers=self.headers ,callback=self.parse_collection, dont_filter=True)

    def parse_collection(self, response):
        all_filter = response.xpath("//h2[contains(text(), 'Filter by:')]/following-sibling::div[1]/ul/li/a/@href").getall()

        for filter_url in all_filter:
            yield scrapy.Request(filter_url, headers=self.headers ,callback=self.parse_filer, dont_filter=True)

    def parse_filer(self, response):
        all_filter = response.xpath("//div[@class='cont']/a/@href").getall()
        heading = (response.url).split("/")[-2].replace("-"," ")
        for product_url in all_filter:
            yield scrapy.Request(product_url, headers=self.headers ,callback=self.parse_product, dont_filter=True, meta={"heading": heading})

    def parse_product(self, response):

        heading = response.meta["heading"]
        product_name = (response.xpath("//div[@class='title']/h1/text()").get())
        material = response.xpath("//dt[.='Material:']/following-sibling::dd[1]/text()").get()
        features = response.xpath("//dt[.='Features:']/following-sibling::dd[1]/text()").get()
        all_data = response.xpath("//div[@class='woo-custom-product-table attrib-table']//tbody/tr")
        for data in all_data:
            color = data.xpath("./th[starts-with(@class, 'col-color col-attribute_pa_color shown')]/text()").get()
            size = data.xpath("./td[@class='col-attribute_pa_size']/text()").get()
            a = data.xpath("./td[@class='col-a']/text()").get()
            b = data.xpath("./td[@class='col-b']/text()").get()
            ed = data.xpath("./td[@class='col-ed']/text()").get()
            circ = data.xpath("./td[@class='col-circ']/text()").get()
            upc = data.xpath("./td[@class='col-upc']/text()").get()

            data_dict = {
                "heading": heading,
                'upc': upc,
                'color': color,
                'size': size,
                'product_name': product_name,
                'material': material,
                'features': features,
                'a': a,
                'b': b,
                'ed': ed,
                'circ': circ,

            }
            print(data_dict)
            color = color.replace(" ", "%20")
            id = "".join(product_name.split())
            url = f"https://caprioptics.com/wp-content/uploads/{id}%20{color}.jpg"
            yield scrapy.Request(url, callback=self.image_response, headers=self.headers, meta = {"data_dict": data_dict})

    def image_response(self, response):
        data_dict = response.meta["data_dict"]
        image_data = response.body
        image_filename = f"image_output/{data_dict['product_name']}/{data_dict['upc']}.jpg"
        os.makedirs(os.path.dirname(image_filename), exist_ok=True)
        with open(image_filename, 'wb') as image_file:
            image_file.write(image_data)

        self.data_list.append(data_dict)

    def closed(self, reason):
        with open("output.json", "w") as output_file:
            json.dump(self.data_list, output_file)











