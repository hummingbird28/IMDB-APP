import logging, re, json

logging.basicConfig(level=logging.INFO)
from html import escape
from urllib.parse import unquote

import swibots as s
from swibots import (
    Client,
    BotContext,
    CommandEvent,
    InlineKeyboardButton,
    InlineMarkup,
    BotCommand,
    AppBar,
    SearchBar,
    SearchHolder,
    AppPage,
    SearchBar,
    Expansion,
    Grid,
    GridItem,
    regexp,
    CallbackQueryEvent,
)

from bs4 import BeautifulSoup
from aiohttp import ClientSession
from playwright.async_api import async_playwright, TimeoutError
from user_agent import generate_user_agent
from decouple import config


async def getSoup(url, json=False):
    async with ClientSession(headers={"User-Agent": generate_user_agent()}) as ses:
        async with ses.get(url) as res:
            if json:
                return await res.json()
            return BeautifulSoup(await res.read(), "lxml")


async def getReleases():
    async with async_playwright() as play:
        chrome = await play.chromium.launch(headless=True)
        page = await chrome.new_page(user_agent=generate_user_agent())
        await page.goto("https://www.imdb.com")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollBy(5000, 5000);")
        await page.wait_for_timeout(5000)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
    sections = soup.find_all("section", "ipc-page-section")
    Box = {}
    for sect in sections:
        title = sect.find("div", "ipc-title")
        other2 = sect.find("div", "ipc-slate-card__title-text")
        if title:
            title = title.find("h3").text
        elif other2:
            title = other2.text
        else:
            continue
        blocks = []
        cards = sect.find_all("div", "ipc-poster-card")
        for card in cards:
            img = card.find("img", "ipc-image").get("src")
            atag = card.find("a", "ipc-poster-card__title")
            id = atag.get("href").split("/")[2]
            blocks.append({"image": img, "id": id, "title": atag.text.strip()})
        if blocks:
            Box[title.strip()] = blocks
    return Box


async def getTrailerUrl(id: str):
    url = f"https://www.imdb.com/title/{id}"
    domain = f"https://imdb-video.media.imdb.com/"
    async with ClientSession(headers={"User-Agent": generate_user_agent()}) as ses:
        async with ses.get(url) as res:
            data = await res.read()
            trailer = (
                f"https://imdb-video.media-imdb.com/"
                + re.findall(f'{domain}(.*)\\"', data.decode())[0].split('"')[0]
            )
            # soup = BeautifulSoup(data, "html.parser", from_encoding="utf8")
    return unquote(unquote(trailer)).replace("\\u0026", "&")


BOT_TOKEN =  config("BOT_TOKEN", default="")

app = Client(
    BOT_TOKEN,
    app_bar=AppBar(
        title="IMDB",
        left_icon="https://img.icons8.com/?size=256&id=57KaWM5g1PJU&format=png",
        secondary_icon="https://vignette.wikia.nocookie.net/logopedia/images/8/8e/IMDB.png/revision/latest/scale-to-width-down/2000?cb=20130124112826",
    ),
).set_bot_commands(
    [
        BotCommand("start", "Get start message", True),
    ]
)


@app.on_command("start")
async def startMessage(ctx: BotContext[CommandEvent]):
    await ctx.event.message.reply_text(
        f"Hi, I am {ctx.user.name}!\nClick the below button to open app!",
        inline_markup=InlineMarkup(
            [[InlineKeyboardButton("Open App", callback_data="openapp")]]
        ),
    )


true = True
homePage = app.run(getReleases())
Glob = {}


@app.on_callback_query(regexp("searchContent"))
async def showCallback(ctx: BotContext[CallbackQueryEvent]):
    m = ctx.event.message
    query = ctx.event.details.get("searchQuery")
    if not query:
        return await ctx.event.answer("Provide a query to search", show_alert=True)
    lays, comps = [], [
        SearchBar(
            callback_data="searchContent",
            value=query,
            left_icon="https://f004.backblazeb2.com/file/switch-bucket/894f6214-a98f-11ee-9962-d41b81d4a9ef.png",
            right_icon="https://f004.backblazeb2.com/file/switch-bucket/cf431478-a98f-11ee-81e5-d41b81d4a9ef.png",
        )
    ]
    details = await getSoup(f"https://search.imdbot.workers.dev/?q={query}", True)

    lays.append(
        Grid(
            f"Search Results for {query}...",
            expansion=Expansion.EXPAND,
            size=3,
            options=[
                GridItem(
                    title=dt["#TITLE"],
                    media=dt["#IMG_POSTER"],
                    selective=True,
                    callback_data="call_" + dt["#IMDB_ID"],
                )
                for dt in details["description"]
                if dt.get("#IMG_POSTER")
            ],
        )
    )
    page = AppPage(components=comps, layouts=lays)
    if Glob.get(ctx.event.action_by_id):
        ctx.event.query_id = Glob[ctx.event.action_by_id]
    await ctx.event.answer(callback=page)


@app.on_callback_query(regexp("search$"))
async def showCallback(ctx: BotContext[CallbackQueryEvent]):
    m = ctx.event.message
    lays, comps = [], [
        SearchBar(
            callback_data="searchContent",
            left_icon="https://f004.backblazeb2.com/file/switch-bucket/894f6214-a98f-11ee-9962-d41b81d4a9ef.png",
            right_icon="https://f004.backblazeb2.com/file/switch-bucket/cf431478-a98f-11ee-81e5-d41b81d4a9ef.png",
        )
    ]
    Glob[ctx.event.action_by_id] = ctx.event.query_id
    await ctx.event.answer(callback=AppPage(components=comps, layouts=lays))


@app.on_callback_query(regexp("openapp"))
async def openApp(ctx: BotContext[CallbackQueryEvent]):
    lays, comps = [], [
        SearchHolder(placeholder="Search Movies, Shows..", callback_data="search")
    ]
    lays.append(
        s.Carousel(
            images=[
                s.Image(
                    "https://f004.backblazeb2.com/file/switch-bucket/42cb0d00-a806-11ee-a689-d41b81d4a9ef.jpg",
                    callback_data="call_tt3581920",
                ),
                s.Image(
                    "https://f004.backblazeb2.com/file/switch-bucket/6ab384a0-a806-11ee-a4d6-d41b81d4a9ef.png",
                    callback_data="call_tt4786824",
                ),
                s.Image(
                    "https://f004.backblazeb2.com/file/switch-bucket/8c446058-a806-11ee-a216-d41b81d4a9ef.jpg",
                    callback_data="call_tt9663764",
                ),
            ]
        )
    )
    for lay, cards in homePage.items():
        #        print(cards)
        lays.append(
            Grid(
                title=lay,
                horizontal=True,
                expansion=Expansion.EXPAND,
                options=[
                    GridItem(
                        data["title"], data["image"], callback_data=f"call_{data['id']}"
                    )
                    for data in cards[:10]
                ],
            )
        )
    return await ctx.event.answer(callback=AppPage(layouts=lays, components=comps))


@app.on_callback_query(regexp("call_(.*)"))
async def getCall(ctx: BotContext[CallbackQueryEvent]):
    imdbId = ctx.event.callback_data.split("_")[-1]
    async with ClientSession() as ses:
        async with ses.get(f"https://search.imdbot.workers.dev/?tt={imdbId}") as res:
            data = await res.json()
    name = escape(data["short"]["name"])
    comps = []
    castGrid = Grid(
        title="Cast",
        horizontal=True,
        options=[
            GridItem(
                title=opt["node"]["name"]["nameText"]["text"],
                media=opt["node"]["name"]["primaryImage"].get("url"),
                selective=True,
            )
            for opt in data["main"]["cast"]["edges"]
            if opt["node"]["name"]["primaryImage"]
        ],
    )
    lays = [castGrid]
    try:
        trailer = await getTrailerUrl(imdbId)
        rate = data["short"]["aggregateRating"]
        comps.append(
            s.VideoPlayer(
                url=trailer,
                title=name,
                subtitle="⭐ "
                + str(rate["ratingValue"])
                + f"/10 | {rate['ratingCount']}",
            )
        )
    except Exception as er:
        print(er)

    comps.append(s.Text("Description"))
    comps.append(s.Text(escape(data["short"]["description"])))
    if data["short"].get("genre"):
        comps.append(s.Text("Genre"))
        comps.append(
            s.Text("    " + " | ".join(data["short"]["genre"])),
        )

    if data["short"].get("director"):
        comps.append(s.Text("Director"))
        comps.append(
            s.Text(", ".join([dirt["name"] for dirt in data["short"]["director"]]))
        )
    if data["short"].get("datePublished"):
        comps.append(s.Text("Released: " + data["short"]["datePublished"]))
    await ctx.event.answer(callback=AppPage(layouts=lays, components=comps))


app.run()
