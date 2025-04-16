import base64
import binascii
import datetime
import struct

from Cryptodome import Random
from Cryptodome.Cipher import AES
from httpx import Client, AsyncClient


from nacl.public import PublicKey, SealedBox


class PasswordUtilAsync:

    def __init__(self, session: AsyncClient | None = None):
        self.session = session or AsyncClient()

    async def encrypt(self, password):
        """
        source: https://gist.github.com/lorenzodifuccia/c857afa47ede66db852e6a25c0a1a027
        """
        key_id, version, pub_key = await self.public_keys()
        key = Random.get_random_bytes(32)
        iv = bytes([0] * 12)

        time = int(datetime.datetime.now().timestamp())

        aes = AES.new(key, AES.MODE_GCM, nonce=iv, mac_len=16)
        aes.update(str(time).encode('utf-8'))
        encrypted_password, cipher_tag = aes.encrypt_and_digest(password.encode('utf-8'))

        pub_key_bytes = binascii.unhexlify(pub_key)
        seal_box = SealedBox(PublicKey(pub_key_bytes))
        encrypted_key = seal_box.encrypt(key)

        encrypted = bytes([1,
                           key_id,
                           *list(struct.pack('<h', len(encrypted_key))),
                           *list(encrypted_key),
                           *list(cipher_tag),
                           *list(encrypted_password)])
        encrypted = base64.b64encode(encrypted).decode('utf-8')

        return f'#PWD_INSTAGRAM_BROWSER:{version}:{time}:{encrypted}'

    async def public_keys(self) -> (int, int, str):
        default_url = "https://www.instagram.com/data/shared_data/"
        fallback_url = "https://storage.yandexcloud.net/bit-static/instagram/shared_data.json"  # FIXME

        async def try_download(session, url: str):
                response = await session.get(url)
                if response.status_code == 200:
                    data: dict = response.json()
                    encryption: dict = data.get("encryption", {})
                    return int(encryption.get("key_id")), int(encryption.get("version")), encryption.get("public_key")

        async with self.session as session:
            try:
                return await try_download(session, default_url)
            except Exception as e:
                print(e)
                return await try_download(session, fallback_url)
