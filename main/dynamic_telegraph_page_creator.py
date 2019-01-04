import requests
from main.universals import get_response, get_response_with_urllib
from collections.abc import Sequence
import json


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class DynamicTelegraphPageCreator:
    """Create telegraph pages and update them dynamically
    so that you'll get up-to-date content
    - The maximum size of the page is 64KB!
    - You can edit even old posts -> Just save your access_token
    """

    base_url = "https://api.telegra.ph/"
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
            author_name = account.get("author_name")
            author_url = account.get("author_url")
        self.author_name = author_name
        self.author_url = author_url
        self.page_path = page_path

    @property
    def base_params(self):
        return {"access_token": self.access_token}

    @property
    def author_account_info(self):
        return get_response(
            self.base_url + "getAccountInfo", payload=self.base_params)

    def get_author_account_info(
            self, *, fields=["short_name", "author_name", "author_url"]):
        # Available fields -> "short_name", "author_name", "author_url", "auth_url", "page_count"
        return get_response(
            self.base_url + "getAccountInfo", payload=self.base_params)

    @staticmethod
    def create_account(short_name, author_name, author_url):
        return get_response(
            DynamicTelegraphPageCreator.base_url + "createAccount",
            payload={
                "short_name": short_name,
                "author_name": author_name,
                "author_url": author_url,
            },
        )

    def revoke_access_token(self):
        account = get_response(
            self.base_url + "revokeAccessToken", payload=self.base_params)
        self.access_token = account.get("access_token") or self.access_token
        return account

    def create_page(self, title, content=[], *, return_content=True):
        return get_response(
            self.base_url + "createPage",
            payload=dict(
                self.base_params, **{
                    "title": title,
                    "author_name": self.author_name,
                    "author_url": self.author_url,
                    "content": json.dumps(content),
                    "return_content": return_content,
                }),
        )

    def set_page(self, page):
        self.title = page["title"]
        self.content = page.get("content")
        self.page_path = page["path"]
        return page

    def load_and_set_page(self, path, *, return_content=True):
        return self.set_page(
            get_response(
                self.base_url + "getPage",
                payload={
                    "path": path,
                    "return_content": return_content
                },
            ))

    def update_page(self,
                    *,
                    content=__temp_obj,
                    title=__temp_obj,
                    return_content=__temp_obj):
        if not self.page_path:
            return
        url = self.base_url + "editPage"
        self.content = self.content if content == self.__temp_obj else content
        self.title = self.title if title == self.__temp_obj else title
        params = dict(
            self.base_params, **{
                "path":
                self.page_path,
                "content":
                json.dumps(self.content),
                "title":
                self.title,
                "return_content":
                False if return_content == self.__temp_obj else return_content,
                "author_name":
                self.author_name,
                "author_url":
                self.author_url,
            })
        return get_response_with_urllib(url, payload=params)

    def get_page(self, path, *, return_content=True):
        url = self.base_url + "getPage"
        return get_response(
            url, payload={
                "path": path,
                "return_content": return_content
            })

    @classproperty
    def base_element(cls):
        return {"tag": None, "attrs": {}, "children": []}  # for href and src

    @classmethod
    def createElement(cls, tag, content=None, attrs={}):
        base = cls.base_element
        base["tag"] = tag
        base["attrs"] = attrs
        if content is not None:
            if isinstance(content, Sequence) and not isinstance(content, str):
                base["children"].extend(content)
            else:
                base["children"].append(content)
        return base

    @classproperty
    def initial_content(cls):  # append element here
        return []

    @classmethod
    def create_bold(cls, content=None):
        return cls.createElement("b", content)

    @classmethod
    def create_title(cls, size=4, content=None):  # Available only 3 and 4
        return cls.createElement("h{}".format(size), content)

    @classmethod
    def create_ordered_list(cls, content=None):
        return cls.createElement("ol", content)

    @classmethod
    def create_unordered_list(cls, content=None):
        return cls.createElement("ul", content)

    @classmethod
    def create_list_item(cls, content=None):
        return cls.createElement("li", content)

    @classmethod
    def create_paragraph(cls, content=None):
        return cls.createElement("p", content)

    @classmethod
    def create_code(cls, content=None):
        return cls.createElement("code", content)

    @classmethod
    def create_blockquote(cls, content=None):
        return cls.createElement("blockquote", content)

    @classmethod
    def create_link(cls, content=None, href=""):
        return cls.createElement("a", content, {"href": href})

    @classproperty
    def enter(cls):
        return cls.createElement("br")

    @classproperty
    def hr(cls):
        return cls.createElement("hr")

    @staticmethod
    def finish(
            elements
    ):  # Will remove all empty objects, so that you'll give a smaller content
        if isinstance(elements, str):
            return elements
        if not isinstance(elements, list):
            elements = [elements]
        for element in elements:
            if isinstance(element, str):
                continue
            trash = []
            for field in element:
                if not element[field]:
                    trash.append(field)
                elif isinstance(element[field], (dict, list)):
                    DynamicTelegraphPageCreator.finish(element[field])
            for t in trash:
                del element[t]
        return elements
