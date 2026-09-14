import asyncio

from image_service import find_nearby_image


async def main():

    result = await find_nearby_image(
        place_name="NiJo Cafe",
        lat=22.656323,
        lon=88.4401556,
        radius_m=1000,
    )

    print(result)


asyncio.run(main())