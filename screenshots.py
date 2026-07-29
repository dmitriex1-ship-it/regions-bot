import asyncio
from playwright.async_api import async_playwright

URLS = {
    "01": "https://www.google.com/maps/place/Adygea",
    "02": "https://www.google.com/maps/place/Bashkortostan",
    "03": "https://www.google.com/maps/place/Buryatia",
    "04": "https://www.google.com/maps/place/Altai+Republic",
    "05": "https://www.google.com/maps/place/Dagestan",
    "06": "https://www.google.com/maps/place/Ingushetia",
    "07": "https://www.google.com/maps/place/Kabardino-Balkaria",
    "08": "https://www.google.com/maps/place/Kalmykia",
    "09": "https://www.google.com/maps/place/Karachay-Cherkessia",
    "10": "https://www.google.com/maps/place/Karelia",
    "11": "https://www.google.com/maps/place/Komi+Republic",
    "12": "https://www.google.com/maps/place/Mari+El",
    "13": "https://www.google.com/maps/place/Mordovia",
    "14": "https://www.google.com/maps/place/Sakha+Republic",
    "15": "https://www.google.com/maps/place/North+Ossetia",
    "16": "https://www.google.com/maps/place/Tatarstan",
    "17": "https://www.google.com/maps/place/Tuva",
    "18": "https://www.google.com/maps/place/Udmurtia",
    "19": "https://www.google.com/maps/place/Khakassia",
    "20": "https://www.google.com/maps/place/Chechnya",
    "21": "https://www.google.com/maps/place/Chuvashia",
    "22": "https://www.google.com/maps/place/Altai+Krai",
    "23": "https://www.google.com/maps/place/Krasnodar+Krai",
    "24": "https://www.google.com/maps/place/Krasnoyarsk+Krai",
    "25": "https://www.google.com/maps/place/Primorsky+Krai",
    "26": "https://www.google.com/maps/place/Stavropol+Krai",
    "27": "https://www.google.com/maps/place/Khabarovsk+Krai",
    "28": "https://www.google.com/maps/place/Amur+Oblast",
    "29": "https://www.google.com/maps/place/Arkhangelsk+Oblast",
    "30": "https://www.google.com/maps/place/Astrakhan+Oblast",
    "31": "https://www.google.com/maps/place/Belgorod+Oblast",
    "32": "https://www.google.com/maps/place/Bryansk+Oblast",
    "33": "https://www.google.com/maps/place/Vladimir+Oblast",
    "34": "https://www.google.com/maps/place/Volgograd+Oblast",
    "35": "https://www.google.com/maps/place/Vologda+Oblast",
    "36": "https://www.google.com/maps/place/Voronezh+Oblast",
    "37": "https://www.google.com/maps/place/Ivanovo+Oblast",
    "38": "https://www.google.com/maps/place/Irkutsk+Oblast",
    "39": "https://www.google.com/maps/place/Kaliningrad+Oblast",
    "40": "https://www.google.com/maps/place/Kaluga+Oblast",
    "41": "https://www.google.com/maps/place/Kamchatka+Krai",
    "42": "https://www.google.com/maps/place/Kemerovo+Oblast",
    "43": "https://www.google.com/maps/place/Kirov+Oblast",
    "44": "https://www.google.com/maps/place/Kostroma+Oblast",
    "45": "https://www.google.com/maps/place/Kurgan+Oblast",
    "46": "https://www.google.com/maps/place/Kursk+Oblast",
    "47": "https://www.google.com/maps/place/Leningrad+Oblast",
    "48": "https://www.google.com/maps/place/Lipetsk+Oblast",
    "49": "https://www.google.com/maps/place/Magadan+Oblast",
    "50": "https://www.google.com/maps/place/Moscow+Oblast",
    "51": "https://www.google.com/maps/place/Murmansk+Oblast",
    "52": "https://www.google.com/maps/place/Nizhny+Novgorod+Oblast",
    "53": "https://www.google.com/maps/place/Novgorod+Oblast",
    "54": "https://www.google.com/maps/place/Novosibirsk+Oblast",
    "55": "https://www.google.com/maps/place/Omsk+Oblast",
    "56": "https://www.google.com/maps/place/Orenburg+Oblast",
    "57": "https://www.google.com/maps/place/Oryol+Oblast",
    "58": "https://www.google.com/maps/place/Penza+Oblast",
    "59": "https://www.google.com/maps/place/Perm+Krai",
    "60": "https://www.google.com/maps/place/Pskov+Oblast",
    "61": "https://www.google.com/maps/place/Rostov+Oblast",
    "62": "https://www.google.com/maps/place/Ryazan+Oblast",
    "63": "https://www.google.com/maps/place/Samara+Oblast",
    "64": "https://www.google.com/maps/place/Saratov+Oblast",
    "65": "https://www.google.com/maps/place/Sakhalin+Oblast",
    "66": "https://www.google.com/maps/place/Sverdlovsk+Oblast",
    "67": "https://www.google.com/maps/place/Smolensk+Oblast",
    "68": "https://www.google.com/maps/place/Tambov+Oblast",
    "69": "https://www.google.com/maps/place/Tver+Oblast",
    "70": "https://www.google.com/maps/place/Tomsk+Oblast",
    "71": "https://www.google.com/maps/place/Tula+Oblast",
    "72": "https://www.google.com/maps/place/Tyumen+Oblast",
    "73": "https://www.google.com/maps/place/Ulyanovsk+Oblast",
    "74": "https://www.google.com/maps/place/Chelyabinsk+Oblast",
    "75": "https://www.google.com/maps/place/Zabaykalsky+Krai",
    "76": "https://www.google.com/maps/place/Yaroslavl+Oblast",
    "77": "https://www.google.com/maps/place/Moscow",
    "78": "https://www.google.com/maps/place/Saint+Petersburg",
    "79": "https://www.google.com/maps/place/Jewish+Autonomous+Oblast",
    "82": "https://www.google.com/maps/place/Crimea",
    "83": "https://www.google.com/maps/place/Nenets+Autonomous+Okrug",
    "86": "https://www.google.com/maps/place/Khanty-Mansi+Autonomous+Okrug",
    "87": "https://www.google.com/maps/place/Chukotka+Autonomous+Okrug",
    "89": "https://www.google.com/maps/place/Yamalo-Nenets+Autonomous+Okrug",
    "92": "https://www.google.com/maps/place/Sevastopol",
}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 600, "height": 400})
        for code, url in URLS.items():
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                try:
                    await page.click('button[aria-label="Закрыть"]', timeout=2000)
                except:
                    pass
                for _ in range(10):
                    await page.keyboard.press("-")
                    await asyncio.sleep(0.1)
                await asyncio.sleep(1)
                await page.screenshot(path=f"images/{code}.png", full_page=False)
                print(f"✅ {code}")
            except Exception as e:
                print(f"❌ {code}: {e}")
        await browser.close()

asyncio.run(main())
