import re
import os
import traceback

from requests import Response
from pyquery import PyQuery
from time import perf_counter, time
from json import dumps

from requests.sessions import Session
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import repeat

from sipri.helpers import Datetime, Parser, logging

class Sipri:
    def __init__(self) -> None:
        self.__BASE_URL: str = 'https://www.sipri.org'
        self.__datetime: Datetime = Datetime()
        self.__parser: Parser = Parser()
        self.__category: str = None
        self.__timeout: int = 10
        self.__sub_categorys: dict = {}

        self.__request: Session = Session()
        self.__request.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/118.0'})

    def __download_pdf(self, url: str, output: str) -> None:
        try:
            response: Response = self.__request.get(url, timeout=self.__timeout)

            if(response.status_code != 200): raise Exception(response)

            if(not os.path.exists(output)):
                os.makedirs(output)
            
            output: str = f'{output}/{url.split("/")[-1].replace("/", "_")[:250]}'

            with open(output, 'wb') as file:
                file.write(response.content)

            logging.info(f'[pdf] {output}')

            return output
        except Exception as e:
            logging.error(e)
            return None
    
    def __get_urls_pdf_unoda(self, url: str):
        response: Response = self.__request.get(url, timeout=self.__timeout)

        pdfs = re.compile(r'(https?://[^"\']+\.pdf)')

        return pdfs.findall(response.text)

    def __get_category(self, html: str) -> None:
        self.__category = self.__parser.execute(html, '#main-menu-link-content1039af4d-1b27-4aa0-9b00-c3d6d1d69b93 a.sf-depth-1.menuparent').text()
        
        for a in self.__parser.execute(html, '#main-menu-link-content1039af4d-1b27-4aa0-9b00-c3d6d1d69b93 ul li a'):
            # self.__sub_categorys.update({'/commentary/essay': 'Essays'})
            self.__sub_categorys.update({PyQuery(a).attr('href'): PyQuery(a).text()})
    
    def __get_per_page(self, router: str, category: str) -> None:
        url: str = f'{self.__BASE_URL}{router}'

        response: Response = self.__request.get(url, timeout=self.__timeout)
        logging.info(f'[{router}] {response}')

        parser: PyQuery = self.__parser.execute(response.text, '.content.column')
        img: PyQuery = parser('img:first-child')


        title: str = parser("#sipri-2016-page-title h1").text()
        output: str = f'{self.__category}/{category}'
        
        pdfs: any = re.compile(r'(https?://[^"\']+\.pdf)').findall(response.text)
        unodas: any = re.compile(r'(https:\/\/meetings\.unoda\.org\/[^"]*)').findall(response.text)

        path_data_pdf: list = []

        if (unodas): 
            for unoda in unodas:
                pdfs += self.__get_urls_pdf_unoda(unoda)
        
        if(pdfs):
            with ThreadPoolExecutor() as executor:
                try:
                    futures = [executor.submit(self.__download_pdf, match, f'{output}/pdf/{title.replace(" ", "_").replace("/", "_")[:250]}') for match in set(pdfs)]
                    path_data_pdf = [future.result() for future in as_completed(futures) if future.result()]
                    
                except Exception as e:
                    logging.error(e)
                    traceback.print_exc()

        if(not os.path.exists(output)):
            os.makedirs(output)

        try:
            with open(f'{output}/{title.replace(" ", "_").replace("/", "_")[:250]}.json', 'w') as file:
                file.write(dumps({
                    "link": url, 
                    "tag": [self.__BASE_URL.split('/')[-1], self.__category],
                    "domain": self.__BASE_URL.split('/')[-1],
                    "category": parser('#sipri-2016-breadcrumbs nav').text().replace('\n', ' '),
                    "title": title,
                    "created_date": parser('time').attr('datetime'),
                    "image_name": img.attr("src").split('/')[-1].split('?')[0] if img.attr("src") else None,
                    "image_description": img.attr('title') if img.attr('title') else None,
                    "path_data_image": self.__BASE_URL + img.attr("src") if img.attr("src") else None,
                    "content": parser('.body.field--label-hidden').text().replace('\n', ''),
                    'crawling_time_epoch': int(time()),
                    "crawling_time": self.__datetime.now(),
                    "path_data_pdf": path_data_pdf 
                }, indent=2, ensure_ascii=False))
        except Exception as e:
            logging.error(e)
            traceback.print_exc()

        logging.info(f'[json] {output}/{title.replace(" ", "_").replace("/", "_")[:250]}.json')
        
    def __get_urls_per_category(self, category: str):
        page: int = 0
        data: dict = {}
        data[self.__sub_categorys[category]]: list = [] 
        
        while(True):
            response: Response = self.__request.get(f'{self.__BASE_URL}{category}?page={page}', timeout=self.__timeout)

            contents: list = self.__parser.execute(response.text, 'div.views-row')
            
            if not contents:
                logging.info(f'[{page}] [{category}] {response} finishh')
                break

            for content in contents:
                data[self.__sub_categorys[category]].append(self.__parser.execute(content, 'h3 a').attr('href'))

            logging.info(f'[{page}] [{category}] {response}')

            # break
            page += 1

        return data


    def start(self):
        response: Response = self.__request.get(self.__BASE_URL, timeout=self.__timeout)

        self.__get_category(response.text)

        logging.info(self.__sub_categorys)

        with ThreadPoolExecutor() as executor:
            try:
                results = executor.map(self.__get_urls_per_category, self.__sub_categorys)

                for result in results:
                    try:
                        [[category], [urls]] = [result.keys(), result.values()]

                        with ThreadPoolExecutor() as executor:
                            executor.map(self.__get_per_page, urls, repeat(category))
                    except Exception as e:
                        logging.error(e)
                        traceback.print_exc()

            except Exception as e:
                logging.error(e)
                traceback.print_exc()

# testing
if(__name__ == '__main__'):
    start = perf_counter()
    sipri: Sipri = Sipri()
    sipri.start()
    # data = sipri.download('https://carnegieendowment.org/files/CMEC_63_Mansour_PMF_Final_Web.pdf')
    # with open('test.pdf', 'wb') as file:
    #     file.write(data)

    print(perf_counter() - start)

