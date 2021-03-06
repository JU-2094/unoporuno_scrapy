#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    USM -> Universal Snippet Machine

    Spider to extract data from google
    usage:
        scrapy crawl bingspider -a source=<"query"|"file_json"> 
"""
import scrapy
from scrapy.http import FormRequest, Request
from scrapy import Selector
from USM.items import UsmItem
from USM.learntools.BasicTool import Utils

__author__ = "Josué Fabricio Urbina González"


class BingSearch(scrapy.Spider):

    name = "bingspider"
    start_urls = ["https://www.bing.com/"]
    browser = 4

    def __init__(self, source=None, *args, **kwargs):
        super(BingSearch, self).__init__(*args, **kwargs)
        if source is not None:
            self.source = source
        else:
            self.source = ""

    def parse(self, response):
        type_b = self.source[-1]
        if self.source != "":
            if type_b == "1":
                search = Utils.get_query_param(Utils(), self.source)

                request = FormRequest.from_response(response,
                                                    formdata={'q': search[2]},
                                                    callback=self.bing_selector)
                request.meta['id_person'] = search[0]
                request.meta['attr'] = search[1]
                request.meta['search'] = search[2]
                request.meta['num_snip'] = 0
                yield request
            else:
                for search in Utils.get_query(Utils(), query=self.source):
                    request = FormRequest.from_response(response,
                                                        formdata={'q': search[2]},
                                                        callback=self.bing_selector)
                    request.meta['id_person'] = search[0]
                    request.meta['attr'] = search[1]
                    request.meta['search'] = search[2]
                    request.meta['num_snip'] = 0
                    yield request

    def bing_selector(self, response):
        base_url = "https://www.bing.com/"
        snippets = response.xpath("//li[@class='b_algo']").extract()
        itemproc = self.crawler.engine.scraper.itemproc

        id_person = response.meta['id_person']
        base_attr = response.meta['attr']
        search = response.meta['search']
        num_snippet = response.meta['num_snip']

        for snippet in snippets:
            num_snippet = num_snippet + 1
            storage_item = UsmItem()
            title = Selector(text=snippet).xpath("//h2/a/node()").extract()
            cite = Selector(text=snippet).xpath("//h2/a/@href").extract()
            text = Selector(text=snippet).xpath("//p").extract()

            tmp_title = ""
            for cad in title:
                tmp_title = tmp_title+cad
            for r in ["<strong>", "</strong>"]:
                tmp_title = tmp_title.replace(r,'')
            title = tmp_title

            if cite.__len__() > 0:
                cite = cite[0]
            else:
                cite = ""

            if text.__len__() > 0:
                text = text[0]
                for r in ["<p>", "</p>", "<strong>", "</strong>"]:
                    text = text.replace(r, '')
            else:
                text = ""

            if cite != "":
                self.log("------------TITLE----------------")
                self.log(title)
                self.log("------------CITE-----------------")
                self.log(cite)
                self.log("------------TEXT-----------------")
                self.log(text)
                self.log("----------ID PERSON------------------")
                self.log(id_person)
                self.log("-----------SEARCH----------------")
                self.log(search)
                self.log("--------------ATTR---------------")
                self.log(base_attr)
                self.log("-----------ENGINE SEARCH---------")
                self.log(self.browser)
                self.log("------------NUMBER SNIPPET-------")
                self.log(num_snippet)

                storage_item['title'] = title
                storage_item['cite'] = cite
                storage_item['text'] = text
                storage_item['id_person'] = id_person
                storage_item['search'] = search
                storage_item['attr'] = base_attr
                storage_item['engine_search'] = self.browser
                storage_item['number_snippet'] = num_snippet

                itemproc.process_item(storage_item, self)
        number = response.xpath("//li[@class='b_pag']/nav[@role='navigation']"
                                "//a[@class='sb_pagS']/text()").extract()
        self.log("-----------NUMBER OF PAGE-------")
        if number.__len__() > 0:
            self.log(number[0]+"")
            if int(number[0]) < 5:
                num = int(number[0])+1
                num = str(num)
                res = response.xpath("//li[@class='b_pag']/nav[@role='navigation']"
                                     "//a[@aria-label='Page "+num+"']/@href").extract()
                for url in res:
                    self.log("--URL TO FOLLOW--")
                    self.log(base_url + url)

                    request = Request(base_url + url, callback=self.bing_selector)
                    request.meta['id_person'] = id_person
                    request.meta['attr'] = base_attr
                    request.meta['search'] = search
                    request.meta['num_snip'] = num_snippet
                    yield request
