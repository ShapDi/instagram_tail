# Welcome to instagram_tail

instagram_tail - Python parsing libraries is a tool that supports asynchronous and instagram content for user selection

## Synchronous code example

```python
from instagram_tail import InstagramApi

client = InstagramApi().get_client()
data = client().reel("C_Bq1wpvsON")
```

from instagram_tail import InstagramApi

## Asynchronous code example

```python
import asyncio
from instagram_tail import InstagramApi

client = InstagramApi().get_client_async()


async def test():
    data = await client().reel("C_Bq1wpvsON")
    print(data)

asyncio.run(test())

```

## Add proxy
```python

proxy = "http://login:password@ip:port"

import asyncio
from instagram_tail import InstagramApi

client = InstagramApi().get_client_async()


async def test():
    data = await client(proxy=proxy).reel("C_Bq1wpvsON")
    print(data)

asyncio.run(test())


```

with gratitude for the inspiration [bitt_moe](https://gitlab.com/Bitnik212)
