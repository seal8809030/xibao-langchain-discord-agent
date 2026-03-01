# refactor_main.py

import discord
import os
from dotenv import load_dotenv
from src.interface.discord_bot import DiscordBotInterface
from MyLogger import ShowLog, setup_logger
import config

# 設定日誌：使用檔名作為日誌名稱，7天自動清理
script_dir = os.path.dirname(os.path.abspath(__file__))
script_name = os.path.splitext(os.path.basename(__file__))[0]
logs_dir = os.path.join(script_dir, 'logs')
setup_logger(script_name, logs_dir, 7)

# 強制排除 aiodns：在某些環境下 aiodns 會導致 DNS 解析失敗
try:
    import aiohttp.resolver
    from aiohttp.resolver import ThreadedResolver
    aiohttp.resolver.DefaultResolver = ThreadedResolver
    import aiohttp.connector
    aiohttp.connector.DefaultResolver = ThreadedResolver
except ImportError:
    pass

# 載入環境變數
load_dotenv()
DISCORD_TOKEN = config.DISCORD_BOT_TOKEN # os.getenv("DISCORD_TOKEN")

def main():
    # 1. 初始化 Discord Client
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    # 2. 初始化重構後的機器人介面
    bot = DiscordBotInterface(client)
    
    # 3. 設定事件監聽
    bot.setup_events()

    @client.event
    async def on_ready():
        ShowLog(f"系統已啟動：{client.user} (Refactored Mode)")

    # 4. 啟動機器人
    if DISCORD_TOKEN:
        client.run(DISCORD_TOKEN)
    else:
        print("錯誤: 找不到 DISCORD_TOKEN，請檢查 .env 文件。")

if __name__ == "__main__":
    main()
