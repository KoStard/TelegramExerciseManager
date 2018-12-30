import requests
from main.universals import get_response
from collections.abc import Sequence
import json


class DynamicTelegraphPageCreator:
    """Create telegraph pages and update them dynamically
    so that you'll get uptodate content
    - The maximum size of the page is 64KB!
    - FAIL! You won't be able to edit old posts in telegraph
    """
    base_url = 'https://api.telegra.ph/'
    __temp_obj = object()

    def __init__(self,
                 access_token,
                 *,
                 author_name=None,
                 author_url=None,
                 page_path=None):
        # author_name and author_url are used for signature
        self.access_token = access_token
        if not author_name and not author_url:
            account = self.get_author_account_info()
            author_name = account.get('author_name')
            author_url = account.get('author_url')
        self.author_name = author_name
        self.author_url = author_url
        self.page_path = page_path

    @property
    def base_params(self):
        return {'access_token': self.access_token}

    @property
    def author_account_info(self):
        return get_response(
            self.base_url + 'getAccountInfo', payload=self.base_params)

    def get_author_account_info(
            self, *, fields=["short_name", "author_name", "author_url"]):
        # Available fields -> "short_name", "author_name", "author_url", "auth_url", "page_count"
        return get_response(
            self.base_url + 'getAccountInfo', payload=self.base_params)

    @staticmethod
    def create_account(short_name, author_name, author_url):
        return get_response(
            DynamicTelegraphPageCreator.base_url + 'createAccount',
            payload={
                'short_name': short_name,
                'author_name': author_name,
                'author_url': author_url
            })

    def revoke_access_token(self):
        account = get_response(
            self.base_url + 'revokeAccessToken', payload=self.base_params)
        self.access_token = account.get('access_token') or self.access_token
        return account

    def create_page(self, title, content, *, return_content=True):
        return get_response(
            self.base_url + 'createPage',
            payload=dict(
                self.base_params, **{
                    'title': title,
                    'author_name': self.author_name,
                    'author_url': self.author_url,
                    'content': json.dumps(content),
                    'return_content': return_content,
                }))

    def set_page(self, page):
        self.title = page['title']
        self.content = page.get('content')
        self.page_path = page['path']
        return page

    def load_and_set_page(self, path, *, return_content=True):
        return self.set_page(
            get_response(
                self.base_url + 'getPage',
                payload={
                    'path': path,
                    'return_content': return_content
                }))

    def update_page(self,
                    *,
                    content=__temp_obj,
                    title=__temp_obj,
                    return_content=__temp_obj):
        if not self.page_path:
            return
        url = self.base_url + 'editPage'
        content = self.content if content == self.__temp_obj else content
        params = dict(
            self.base_params, **{
                'path':
                self.page_path,
                'content':
                json.dumps(content),
                'title':
                self.title if title == self.__temp_obj else title,
                'return_content':
                False if return_content == self.__temp_obj else return_content,
                'author_name':
                self.author_name,
                'author_url':
                self.author_url,
            })
        print(params)
        return get_response(url, payload=params)
