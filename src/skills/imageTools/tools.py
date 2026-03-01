# refactor/skills/imageTools/tools.py

import io
import os
import base64
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from PIL import Image
from openai import OpenAI
from langchain_core.tools import tool
from config import AI_API_KEY, AI_API_BASE
from MyLogger import ShowLog, ShowErrorLog
from src.core.resource import Resource

if TYPE_CHECKING:
    from src.core.session import SessionContext


def get_tools(context: "SessionContext") -> List[Any]:
    """
    獲取與會話實例綁定的圖片處理工具。
    """
    def _client():
        """初始化 OpenAI Client。"""
        # 確保路徑正確，如果 AI_API_BASE 沒有 v1 則補上
        base_url = str(AI_API_BASE)
        if "v1" not in base_url:
            base_url = f"{base_url.rstrip('/')}/v1"
        return OpenAI(base_url=base_url, api_key=AI_API_KEY)


    @tool
    def set_current_image(id: str) -> Dict[str, Any]:
        """
        手動設定當前正在操作的圖片 ID。
        """
        res = context.resources.get(id)
        if not res:
            return {"err": f"找不到圖片 ID: {id}"}
        
        context.resources.set_focus(id)
        return {"msg": f"已將圖片 {id} 設為當前操作對象"}

    @tool
    def img_gen(prompt: str, input_id: Optional[str] = None) -> Any:
        """
        生成新圖片或編輯現有圖片 (Image-to-Image)。
        生成成功後，會自動將新生成的圖片設為「當前圖片」。
        """
        try:
            content = [{"type": "text", "text": prompt}]
            
            # 如果提供了 input_id，則加入圖片上下文
            if input_id:
                res = context.resources.get(input_id)
                if not res:
                    return {"err": f"輸入圖片 ID {input_id} 無效"}
                content.append(res.to_block())
            
            client = _client()
            resp = client.chat.completions.create(
                model="gemini-3-pro-image",
                extra_body={"size": "1024x1024"},
                messages=[{"role": "user", "content": content}]
            )
            
            # 解析輸出的 Base64
            b64_data = resp.choices[0].message.content
            # 去除 Data URL 前綴 (如果是的話)
            if "," in b64_data:
                b64_data = b64_data.split(",")[-1]
            
            img_bytes = base64.b64decode(b64_data)
            
            # 封裝為 Resource 並註冊
            new_res = Resource(
                data=img_bytes,
                mime_type="image/png",
                filename="generated_image.png"
            )
            new_id = context.resources.register(new_res)
            context.resources.set_focus(new_id)
            
            return [
                {"type": "text", "text": f"圖片生成成功，ID: {new_id}"},
                new_res.to_block()
            ]
        except Exception as e:
            ShowErrorLog(f"img_gen failed: {e}")
            return {"err": str(e)}

    @tool
    def img_save(id: str, path: str) -> Dict[str, Any]:
        """
        將記憶體中的圖片實例儲存至本地磁碟路徑。
        執行後會將該圖片設為「當前圖片」。
        """
        try:
            res = context.resources.get(id)
            if not res:
                return {"err": f"找不到圖片 ID: {id}"}
            
            # 確保目錄存在
            abs_path = os.path.abspath(path)
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            with open(abs_path, "wb") as f:
                f.write(res.data)
            
            # 更新焦點
            context.resources.set_focus(id)
            return {"path": abs_path, "msg": "圖片儲存成功"}
        except Exception as e:
            ShowErrorLog(f"img_save failed: {e}")
            return {"err": str(e)}

    @tool
    def img_load(path: str) -> Dict[str, Any]:
        """
        從磁碟路徑載入圖片至記憶體並獲取控制代碼。
        載入成功後，會自動將該圖片設為「當前圖片」。
        """
        try:
            if not os.path.exists(path):
                return {"err": f"檔案不存在: {path}"}
            
            with open(path, "rb") as f:
                data = f.read()
            
            # 判斷副檔名設定 MIME
            ext = os.path.splitext(path)[1].lower()
            mime = "image/png"
            if ext in [".jpg", ".jpeg"]: mime = "image/jpeg"
            elif ext == ".gif": mime = "image/gif"
            
            res = Resource(
                data=data,
                mime_type=mime,
                filename=os.path.basename(path)
            )
            new_id = context.resources.register(res)
            context.resources.set_focus(new_id)
            
            return {"id": new_id, "msg": "圖片載入成功"}
        except Exception as e:
            ShowErrorLog(f"img_load failed: {e}")
            return {"err": str(e)}

    @tool
    def img_mem(action: str, id: Optional[str] = None) -> Any:
        """
        記憶體資源管理。
        action: 'list' (列出), 'view' (查看並設為焦點), 'del' (刪除)
        """
        try:
            if action == "list":
                all_res = context.resources.list_all()
                focused = context.resources.get_focused()
                focused_id = focused.id if focused else None
                
                res_list = []
                for r in all_res:
                    if r.mime_type.startswith("image/"):
                        res_list.append({
                            "id": r.id,
                            "filename": r.filename,
                            "is_current": r.id == focused_id
                        })
                return {"images": res_list, "current_id": focused_id}
            
            if not id:
                return {"err": "此行動需要提供圖片 ID"}
            
            res = context.resources.get(id)
            if not res:
                return {"err": f"找不到圖片 ID: {id}"}
                
            if action == "view":
                context.resources.set_focus(id)
                # 💡 返回符合 LangChain 多模態標準的內容列表
                # 這樣 middleware 或 LLM 才能正確識別這是圖片內容
                return [
                    {"type": "text", "text": f"已將圖片 {id} 設為當前焦點。"},
                    res.to_block()
                ]
            
            if action == "del":
                context.resources.unregister(id)
                return {"msg": f"已釋放圖片 {id} 佔用的記憶體"}
                
            return {"err": f"未知的行動: {action}"}
        except Exception as e:
            ShowErrorLog(f"img_mem failed: {e}")
            return {"err": str(e)}

    return [
        set_current_image,
        img_gen,
        img_save,
        img_load,
        img_mem
    ]
