# refactor/interface/discord_bot.py

import discord
import io
import asyncio
import re
from typing import List, Dict, Any, Optional
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
)
from MyLogger import ShowLog, ShowErrorLog, log_callback
from src.core.session import SessionContext
from src.core.agent import Orchestrator
from src.skills.infra import get_base_tools
from langchain_tavily import TavilySearch
from markitdown import MarkItDown

class DiscordBotInterface:
    """
    重構後的 Discord 機器人。
    負責處理 Discord 事件，並將核心邏輯委託給 Orchestrator。
    """
    def __init__(self, client: discord.Client):
        self.client = client
        self._markitdown = MarkItDown()

    async def _format_message(self, msg: discord.Message, context: SessionContext) -> BaseMessage:
        """將 Discord 訊息轉換為 LangChain 訊息物件並註冊資源。"""
        is_ai = msg.author == self.client.user
        role = "assistant" if is_ai else "user"
        content_list = []
        
        # 1. 處理文字內容
        text_content = msg.clean_content
        if text_content:
            if role == "user":
                text_content = f"{msg.author.display_name}: {text_content}"
            content_list.append({"type": "text", "text": text_content})
        
        # 2. 處理附件 (圖片和語音)
        for attachment in msg.attachments:
            await self._process_attachment(attachment, context, content_list)

        if is_ai:
            return AIMessage(content=content_list)
        return HumanMessage(content=content_list)

    async def _process_attachment(self, attachment: discord.Attachment, context: SessionContext, content_list: List[Dict]):
        """處理單個附件並更新內容列表。"""
        if not attachment.content_type:
            return

        try:
            res_id = None
            handle_info = ""
            
            # 獲取標準化 MIME
            mime = attachment.content_type.split(";")[0].strip() if attachment.content_type else ""

            # 判斷是否為支援的文件類型
            is_supported_doc = (
                mime.startswith("text/") or
                mime == "application/pdf" or
                mime == "application/json" or
                mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or
                mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or
                mime == "application/msword"  # .doc (透過系統 antiword 支援)
            )

            if attachment.content_type.startswith("image/"):
                img_bytes = await attachment.read()
                res_id = context.add_image_resource(img_bytes, attachment.filename)
                handle_info = f"\n[圖片 ID: {res_id}]"
            elif attachment.content_type.startswith("audio/") or attachment.filename == "voice-message.ogg":
                audio_bytes = await attachment.read()
                mime = attachment.content_type if attachment.content_type.startswith("audio/") else "audio/ogg"
                res_id = context.add_audio_resource(audio_bytes, attachment.filename, mime_type=mime)
                handle_info = f"\n[語音 ID: {res_id}]"
            elif is_supported_doc:
                doc_bytes = await attachment.read()
                res_id = context.add_resource(doc_bytes, attachment.filename, attachment.content_type)
                
                # 使用 MarkItDown 轉換為 Markdown 文字
                try:
                    # 獲取副檔名以利 MarkItDown 識別
                    ext = "." + attachment.filename.split(".")[-1].lower() if "." in attachment.filename else ""
                    
                    # 針對舊型 .doc 進行特殊處理 (MarkItDown 有時對 stream + .doc 比較嚴格)
                    if ext == ".doc":
                        # 嘗試使用 antiword 直接讀取 (如果 MarkItDown 沒接，我就手動接軌)
                        try:
                            process = await asyncio.create_subprocess_exec(
                                "antiword", "-",
                                stdin=asyncio.subprocess.PIPE,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            stdout, stderr = await process.communicate(input=doc_bytes)
                            if process.returncode == 0:
                                content_text = stdout.decode("utf-8", errors="replace")
                            else:
                                raise Exception(f"Antiword error: {stderr.decode()}")
                        except Exception as e:
                            ShowErrorLog(f"[介面] Antiword 降級處理失敗: {e}")
                            # 仍嘗試讓 MarkItDown 跑最後一遍
                            conversion_result = await asyncio.to_thread(
                                self._markitdown.convert_stream, io.BytesIO(doc_bytes), extension=ext
                            )
                            content_text = conversion_result.text_content
                    else:
                        # 執行轉換 (轉換通常是 CPU 密集型，建議在 thread 中執行)
                        conversion_result = await asyncio.to_thread(
                            self._markitdown.convert_stream,
                            io.BytesIO(doc_bytes),
                            extension=ext
                        )
                        content_text = conversion_result.text_content
                    
                    # 注入轉換後的文字到對話中
                    handle_info = f"\n\n--- 文件內容: {attachment.filename} (ID: {res_id}) ---\n{content_text}\n--- 結束 ---"
                except Exception as ex:
                    ShowErrorLog(f"[介面] MarkItDown 轉換失敗 ({attachment.filename}): {ex}")
                    handle_info = f"\n[文件 ID: {res_id}] (轉換失敗: {ex})"

            if res_id:
                resource = context.resources.get(res_id)
                content_list.append(resource.to_block())
                
                # 注入參考資訊到文字區塊
                if content_list and content_list[0]["type"] == "text":
                    content_list[0]["text"] += handle_info
                else:
                    content_list.insert(0, {"type": "text", "text": handle_info})
                    
        except Exception as e:
            ShowErrorLog(f"[介面] 資源註冊失敗: {e}")

    async def get_context_messages(self, channel: discord.abc.Messageable, current_message: discord.Message, context: SessionContext, limit: int = 10) -> List[BaseMessage]:
        """獲取歷史訊息上下文。"""
        messages: List[BaseMessage] = []
        async for msg in channel.history(limit=limit, before=current_message):
            if not msg.content and not msg.attachments: continue
            messages.append(await self._format_message(msg, context))
        
        messages.reverse()
        messages.append(await self._format_message(current_message, context))
        return messages

    def _should_respond(self, message: discord.Message) -> bool:
        """判斷是否應該回應此訊息。"""
        if message.author == self.client.user: return False

        # 1. 被提及 (Mention)
        if self.client.user.mentioned_in(message): return True
        
        # 2. 回覆機器人的訊息 (Reply)
        if message.reference:
            # 這裡需要異步獲取被回覆的訊息，但在同步過濾中我們先做基本判斷
            # 實際判斷移至 handle_message 中進一步確認
            pass

        # 3. 語音訊息
        has_voice = any(
            att.filename == "voice-message.ogg" or 
            (att.content_type and att.content_type.startswith("audio/"))
            for att in message.attachments
        )
        if has_voice: return True

        return False

    async def _setup_logging_thread(self, message: discord.Message) -> Optional[discord.Thread]:
        """建立「思考中」的討論串。"""
        try:
            if isinstance(message.channel, discord.Thread):
                return None
            
            title = f"Thinking - {message.clean_content[:50]}"
            if hasattr(message, "create_thread"):
                return await message.create_thread(name=title, auto_archive_duration=60)
            elif hasattr(message.channel, "create_thread"):
                return await message.channel.create_thread(name=title, message=message, auto_archive_duration=60)
        except Exception as e:
            ShowErrorLog(f"[介面] 無法建立討論串: {e}")
        return None

    def _create_log_hook(self, thread: Optional[discord.Thread]):
        """建立日誌鉤子，實現 1 秒緩衝發送與內容截斷機制。"""
        log_buffer = []
        lock = asyncio.Lock()

        async def flush_buffer():
            await asyncio.sleep(1.0)  # 緩衝一秒
            
            async with lock:
                if not log_buffer or not thread:
                    return
                
                # 按照需求：每條線不允許超過 1000/緩存條數 個字
                lines_count = len(log_buffer)
                max_line_len = max(10, 1000 // lines_count)
                
                processed_lines = []
                for line in log_buffer:
                    if len(line) > max_line_len:
                        processed_lines.append(line[:max_line_len] + "...")
                    else:
                        processed_lines.append(line)
                
                final_content = "\n".join(processed_lines)
                log_buffer.clear()
                
            try:
                # 在 event loop 中發送
                await thread.send(f"```\n{final_content}\n```")
            except Exception as e:
                # 這裡不能用 ShowErrorLog 會造成死循環
                print(f"[LogHook] Failed to send: {e}")

        def discord_log_hook(content):
            if not thread:
                return

            # 清理日誌格式
            clean_content = re.sub(r'^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{3} #\s*\d+ ', '', content)

            async def add_and_trigger():
                async with lock:
                    is_new_cycle = (len(log_buffer) == 0)
                    log_buffer.append(clean_content)
                
                if is_new_cycle:
                    # 只有第一條日誌進入時觸發 flush
                    asyncio.create_task(flush_buffer())

            # 將協程排入機器人的事件迴圈
            asyncio.run_coroutine_threadsafe(add_and_trigger(), self.client.loop)

        return discord_log_hook

    async def handle_message(self, message: discord.Message):
        """處理單一訊息請求的主要進入點。"""
        if message.author == self.client.user: return

        # 檢測是否回覆機器人 (進階檢測)
        is_mentioned = self.client.user.mentioned_in(message)
        if not is_mentioned and message.reference:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg.author == self.client.user: is_mentioned = True
            except: pass

        # 檢測語音
        if not is_mentioned:
            is_mentioned = any(att.filename == "voice-message.ogg" or (att.content_type and att.content_type.startswith("audio/")) for att in message.attachments)

        if not is_mentioned: return

        ShowLog(f"[介面] 開始處理對話請求")
        
        # 1. 建立討論串與日誌鉤子
        thread = await self._setup_logging_thread(message)
        log_token = log_callback.set(self._create_log_hook(thread))

        try:
            # 2. 初始化 Orchestrator
            main_context = SessionContext(guild=message.guild, channel=message.channel, loop=asyncio.get_running_loop())
            base_tools = [TavilySearch()] + get_base_tools(main_context)
            orchestrator = Orchestrator(main_context, base_tools)
            
            async with message.channel.typing():
                # 3. 獲取上下文並執行
                messages = await self.get_context_messages(message.channel, message, main_context)
                response = await asyncio.to_thread(orchestrator.invoke, messages)
                
                # 4. 處理回應文字
                await self._send_response(message, response)
                
                # 5. 處理焦點資源 (圖片)
                await self._send_focused_resources(message, main_context)
                
        except Exception as e:
            ShowErrorLog(f"會話處理出錯: {e}")
            await message.channel.send(f"⚠️ 出錯了：{str(e)}")
        finally:
            log_callback.reset(log_token)

    async def _send_response(self, message: discord.Message, response: Dict):
        """發送文字回應。"""
        if "messages" in response and response["messages"]:
            reply_text = response["messages"][-1].content
            reply_text = reply_text.replace("喜寶:", "").replace("喜寶：", "").strip()
            if reply_text: await message.reply(reply_text)

    async def _send_focused_resources(self, message: discord.Message, context: SessionContext):
        """發送處理後的資源內容。"""
        focused_res = context.resources.get_focused()
        if focused_res and focused_res.mime_type.startswith("image/"):
            file = discord.File(io.BytesIO(focused_res.data), filename=focused_res.filename)
            await message.channel.send(file=file)

    def setup_events(self):
        """掛載事件至 Client。"""
        @self.client.event
        async def on_message(message: discord.Message):
            await self.handle_message(message)
