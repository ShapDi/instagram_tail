import re
import json
import random

import httpx
from httpx import AsyncClient
import bs4
import math
from bs4 import PageElement

from instagram_tail._model import (
    InstagramSettingDataClassPrivate,
    InstagramSettingsParamsDataClassPrivate,
)


class InstagramApiParamsServicePrivate:
    MAIN_PAGE = "https://www.instagram.com/"
    DEFAULT_REQUIRED_SETTINGS = [
        "SprinkleConfig",
        "RelayAPIConfigDefaults",
        "SiteData",
        "CookieCoreConfig",
        "LSD",
    ]

    def __init__(self, proxy: str | None = None):
        self.proxy = proxy
        self.csr_service = CrossSiteRequestTokenService()
        self.dyn_service = DynamicTokenService()
        self.__all_settings: dict[str, InstagramSettingDataClassPrivate] = {}

    def params(
        self, required_settings: list[str] = None, page_url: str = MAIN_PAGE
    ) -> InstagramSettingsParamsDataClassPrivate:
        settings = self.map_params(
            settings=self.require_settings(
                page_url=page_url, required_setting_names=required_settings
            )
        )
        settings.body.update(
            {
                "__csr": self.csr_service.generate(),
                "__dyn": self.dyn_service.generate(self.__all_settings),
            }
        )
        return settings

    @classmethod
    def map_params(
        cls, settings: dict[str, InstagramSettingDataClassPrivate]
    ) -> InstagramSettingsParamsDataClassPrivate:
        headers, body, cookies = [{}, {}, {}]
        sprinkle_config = settings.get("SprinkleConfig")
        relay_api_config_defaults_setting = settings.get("RelayAPIConfigDefaults")
        site_data_setting = settings.get("SiteData")
        csrf_token_setting = settings.get("CSRFToken")
        lsd_setting = settings.get("LSD")
        lsd: str | None = lsd_setting.content.get("token", None)
        headers.update(relay_api_config_defaults_setting.content.get("customHeaders"))
        headers.update(
            {"X-Fb-Lsd": lsd, "X-Csrftoken": csrf_token_setting.content.get("value")}
        )
        body.update(
            {
                "jazoest": sprinkle_config.index,
                "__hs": site_data_setting.content.get("haste_session"),
                "__hsi": site_data_setting.content.get("hsi"),
                "__spin_r": site_data_setting.content.get("__spin_r"),
                "__spin_b": site_data_setting.content.get("__spin_b"),
                "__spin_t": site_data_setting.content.get("__spin_t"),
                "__rev": site_data_setting.content.get("server_revision"),
                "lsd": lsd,
                "__s": f"{cls.session_part}:{cls.session_part}:{cls.session_part}",
            }
        )
        cookies.update({"csrftoken": csrf_token_setting.content.get("value")})
        return InstagramSettingsParamsDataClassPrivate(
            header=headers, cookie=cookies, body=body
        )

    def require_settings(
        self, page_url: str, required_setting_names: list[str] = None
    ) -> dict[str, InstagramSettingDataClassPrivate]:
        """
        Получение конфигов из фронта

        :param page_url: Pape downloaded for settings
        :param required_setting_names: Setting names
        :return: dict[InstagramSettingName, InstagramSettingDict]
        """
        if required_setting_names is None:
            required_setting_names = self.DEFAULT_REQUIRED_SETTINGS
        settings: dict[str, InstagramSettingDataClassPrivate] = {}
        with httpx.Client(proxy=self.proxy, verify=False) as session:
            response = session.get(url=page_url)
            if (
                response.status_code == 200
                and response.headers.get("content-type").split(";")[0] == "text/html"
            ):
                csrf_token = response.cookies.get("csrftoken")
                parsed_settings: dict[str, InstagramSettingDataClassPrivate] = (
                    self.parse_settings(response_text=response.text)
                )
                self.__all_settings = parsed_settings
                for required_setting in required_setting_names:
                    parsed_required_setting = parsed_settings.get(
                        required_setting, None
                    )
                    if parsed_required_setting is not None:
                        settings.update({required_setting: parsed_required_setting})
                settings.update(
                    {
                        "CSRFToken": InstagramSettingDataClassPrivate(
                            content={"value": csrf_token}, index=0
                        )
                    }
                )
        return settings

    @classmethod
    def parse_settings(
        cls, response_text: str
    ) -> dict[str, InstagramSettingDataClassPrivate]:
        soup = bs4.BeautifulSoup(response_text, "html.parser")
        max_data_content_len = 0
        script_element: PageElement | None = None
        for element in soup.find_all("script", attrs={"type": "application/json"}):
            try:
                (data_content_len,) = element.get_attribute_list(key="data-content-len")
            except Exception as e:
                continue
            if type(data_content_len) is str:
                data_content_len: int = int(data_content_len)
                if data_content_len > max_data_content_len:
                    max_data_content_len = data_content_len
                    script_element = element
        settings_json = json.loads(script_element.text)
        settings = {}
        for settings_item in settings_json["require"][0][3][0]["__bbox"]["define"]:
            settings_name, _, settings_dict, settings_value = settings_item
            settings.update(
                {
                    settings_name: InstagramSettingDataClassPrivate(
                        content=settings_dict, index=settings_value
                    )
                }
            )
        return settings

    @property
    def session_part(self) -> str:
        i = 36
        j = 6
        k = math.pow(i, j)
        a = math.floor(random.random() * k)
        a = self.convert_base(a, i)  # Convert to base 36
        return ("0" * (j - len(a)) + a)[0:6].lower()

    @classmethod
    def convert_base(cls, num, to_base=10, from_base=10):
        # first convert to decimal number
        n = int(num, from_base) if isinstance(num, str) else num
        # now convert decimal to 'to_base' base
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        res = ""
        while n > 0:
            n, m = divmod(n, to_base)
            res += alphabet[m]
        return res[::-1]


class InstagramApiParamsServicePrivateAsync:
    MAIN_PAGE = "https://www.instagram.com/"
    DEFAULT_REQUIRED_SETTINGS = [
        "SprinkleConfig",
        "RelayAPIConfigDefaults",
        "SiteData",
        "CookieCoreConfig",
        "LSD",
    ]

    def __init__(self, proxy: str | None = None):
        self.csr_service = CrossSiteRequestTokenService()
        self.dyn_service = DynamicTokenService()
        self.__all_settings: dict[str, InstagramSettingDataClassPrivate] = {}
        self.proxy = proxy

    async def params(
        self, required_settings: list[str] = None, page_url: str = MAIN_PAGE
    ) -> InstagramSettingsParamsDataClassPrivate:
        settings = self.map_params(
            settings=await self.require_settings(
                page_url=page_url, required_setting_names=required_settings
            )
        )
        settings.body.update(
            {
                "__csr": self.csr_service.generate(),
                "__dyn": self.dyn_service.generate(self.__all_settings),
            }
        )
        return settings

    @classmethod
    def map_params(
        cls, settings: dict[str, InstagramSettingDataClassPrivate]
    ) -> InstagramSettingsParamsDataClassPrivate:
        headers, body, cookies = [{}, {}, {}]
        sprinkle_config = settings.get("SprinkleConfig")
        relay_api_config_defaults_setting = settings.get("RelayAPIConfigDefaults")
        site_data_setting = settings.get("SiteData")
        csrf_token_setting = settings.get("CSRFToken")
        lsd_setting = settings.get("LSD")
        lsd: str | None = lsd_setting.content.get("token", None)
        headers.update(relay_api_config_defaults_setting.content.get("customHeaders"))
        headers.update(
            {"X-Fb-Lsd": lsd, "X-Csrftoken": csrf_token_setting.content.get("value")}
        )
        body.update(
            {
                "jazoest": sprinkle_config.index,
                "__hs": site_data_setting.content.get("haste_session"),
                "__hsi": site_data_setting.content.get("hsi"),
                "__spin_r": site_data_setting.content.get("__spin_r"),
                "__spin_b": site_data_setting.content.get("__spin_b"),
                "__spin_t": site_data_setting.content.get("__spin_t"),
                "__rev": site_data_setting.content.get("server_revision"),
                "lsd": lsd,
                "__s": f"{cls.session_part}:{cls.session_part}:{cls.session_part}",
            }
        )
        cookies.update({"csrftoken": csrf_token_setting.content.get("value")})
        return InstagramSettingsParamsDataClassPrivate(
            header=headers, cookie=cookies, body=body
        )

    async def require_settings(
        self, page_url: str, required_setting_names: list[str] = None
    ) -> dict[str, InstagramSettingDataClassPrivate]:
        """
        Получение конфигов из фронта

        :param page_url: Pape downloaded for settings
        :param required_setting_names: Setting names
        :return: dict[InstagramSettingName, InstagramSettingDict]
        """
        if required_setting_names is None:
            required_setting_names = self.DEFAULT_REQUIRED_SETTINGS
        settings: dict[str, InstagramSettingDataClassPrivate] = {}
        async with AsyncClient(proxy=self.proxy) as session:
            print(page_url)
            response = await session.get(url=page_url, timeout=10)
            if (
                response.status_code == 200
                and response.headers.get("content-type").split(";")[0] == "text/html"
            ):
                csrf_token = response.cookies.get("csrftoken")
                parsed_settings: dict[str, InstagramSettingDataClassPrivate] = (
                    self.parse_settings(response_text=response.text)
                )
                self.__all_settings = parsed_settings
                for required_setting in required_setting_names:
                    parsed_required_setting = parsed_settings.get(
                        required_setting, None
                    )
                    if parsed_required_setting is not None:
                        settings.update({required_setting: parsed_required_setting})
                settings.update(
                    {
                        "CSRFToken": InstagramSettingDataClassPrivate(
                            content={"value": csrf_token}, index=0
                        )
                    }
                )
        return settings

    @classmethod
    def parse_settings(
        cls, response_text: str
    ) -> dict[str, InstagramSettingDataClassPrivate]:
        soup = bs4.BeautifulSoup(response_text, "html.parser")
        max_data_content_len = 0
        script_element: PageElement | None = None
        for element in soup.find_all("script", attrs={"type": "application/json"}):
            try:
                (data_content_len,) = element.get_attribute_list(key="data-content-len")
            except Exception as e:
                continue
            if type(data_content_len) is str:
                data_content_len: int = int(data_content_len)
                if data_content_len > max_data_content_len:
                    max_data_content_len = data_content_len
                    script_element = element
        settings_json = json.loads(script_element.text)
        settings = {}
        print(settings_json)
        for settings_item in settings_json["require"][0][3][0]["__bbox"]["define"]:
            settings_name, _, settings_dict, settings_value = settings_item
            settings.update(
                {
                    settings_name: InstagramSettingDataClassPrivate(
                        content=settings_dict, index=settings_value
                    )
                }
            )
        return settings

    @property
    def session_part(self) -> str:
        i = 36
        j = 6
        k = math.pow(i, j)
        a = math.floor(random.random() * k)
        a = self.convert_base(a, i)  # Convert to base 36
        return ("0" * (j - len(a)) + a)[0:6].lower()

    @classmethod
    def convert_base(cls, num, to_base=10, from_base=10):
        # first convert to decimal number
        n = int(num, from_base) if isinstance(num, str) else num
        # now convert decimal to 'to_base' base
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        res = ""
        while n > 0:
            n, m = divmod(n, to_base)
            res += alphabet[m]
        return res[::-1]


class CrossSiteRequestTokenService:
    @staticmethod
    def generate() -> str:
        arr = []
        count = random.randint(100, 270)
        all_numbers = list(range(1, 43095))
        for i in range(count):
            random_index = random.randint(0, len(all_numbers) - 1)
            random_number = all_numbers.pop(random_index)
            arr.append(random_number)
        return BitMapUtil.to_compressed_string(arr)


class DynamicTokenService:
    @classmethod
    def generate(cls, all_settings: dict[str, InstagramSettingDataClassPrivate]) -> str:
        settings_indexes = [
            setting.index for setting_name, setting in all_settings.items()
        ]
        return BitMapUtil.to_compressed_string(settings_indexes)


class BitMapUtil:
    @classmethod
    def convert_to_binary_string(cls, num):
        binary_string = format(num, "b")
        padding = "0" * (len(binary_string) - 1)
        return padding + binary_string

    @classmethod
    def convert_to_base64_string(cls, binary_string):
        list_chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_"
        six_bit_chunks = re.findall(".{1,6}", binary_string + "00000")
        base64_string = ""
        for chunk in six_bit_chunks:
            base64_string += list_chars[int(chunk, 2)]
        return base64_string

    @classmethod
    def to_compressed_string(cls, arr: list):
        bit_map = [0] * (max(arr) + 1)
        for item in arr:
            bit_map[item] = 1
        if len(bit_map) == 0:
            return ""
        compressed_bits = []
        count = 1
        current_bit = bit_map[0]
        current_bit_string = format(current_bit, "b")
        for i in range(1, len(bit_map)):
            next_bit = bit_map[i]
            if next_bit == current_bit:
                count += 1
            else:
                compressed_bits.append(cls.convert_to_binary_string(count))
                current_bit = next_bit
                count = 1
        if count:
            compressed_bits.append(cls.convert_to_binary_string(count))
        return cls.convert_to_base64_string(
            current_bit_string + "".join(compressed_bits)
        )
