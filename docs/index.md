# instagram_tail

instagram_tail - Python parsing libraries is a tool that supports asynchronous and instagram content for user selection

## Synchronous code example

```python

```

from instagram_tail import InstagramApi

## Asynchronous code example

```python
import asyncio
from instagram_tail import InstTailApiAsync

async def test():
    client = InstTailApiAsync().get_client()
    data = await client.reel("C_Bq1wpvsON")
    client.close()

asyncio.run(test())

```

## Add proxy
```python

proxy = "http://login:password@ip:port"


from instagram_tail import InstTailApi

tail_api = InstTailApi(proxy=proxy)
client = tail_api.get_client()
tail_api.close()

data = client.reel("C_Bq1wpvsON")
print(data)



```

with gratitude for the inspiration [bitt_moe](https://gitlab.com/Bitnik212)