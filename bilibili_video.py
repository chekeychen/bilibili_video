import re
import os
import plugins
import tempfile
from plugins import *
from requests import Session
from bridge.context import ContextType
from urllib.parse import urlparse
from bridge.reply import Reply, ReplyType
from common.log import logger

BASE_LINHUN_URL = "https://api.linhun.vip"

@plugins.register(name="bilibili_video",
                  desc="bilibili_video插件",
                  version="1.0",
                  author="NyankoSensei",
                  desire_priority=100)
class bilibili_video(Plugin):
    content = None
    config_data = None
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        logger.info(f"[{__class__.__name__}] inited")

    def on_handle_context(self, e_context: EventContext):
        # 只处理文本消息
        if e_context['context'].type != ContextType.TEXT:
            return
        query: str = e_context["context"].content.strip()

        if query.startswith(f"获取B站"):
            msg = query.replace("获取B站", "")
            msg = msg.strip()
            logger.info(f"[{__class__.__name__}] 收到消息: {msg}")
            # 读取配置文件
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r') as file:
                    self.config_data = json.load(file)
            else:
                logger.error(f"请先配置{config_path}文件")
                return
            
            reply = Reply()
            video_url = self.search_video(msg)
            if video_url != None:
                self.save_tempfile(video_url, e_context, 'bilibili_video')
                e_context.action = EventAction.BREAK_PASS
                return
            else:
                reply.type = ReplyType.ERROR
                reply.content = "获取失败️❌"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS

    def search_video(self, msg):
        try:
            with Session() as session:
                # 主接口
                url = BASE_LINHUN_URL + "/api/blblvi"
                logger.info(f"接口url:{url}")
                match = re.search(r'https://[^\s]+', msg)
                params = f"url={match}&apiKey={self.config_data['bilibili_video_key']}"
                response = session.get(url=url, params=params)
                json_data = response.json()
                logger.info(json_data)
                if json_data['code'] == 200:
                    text = json_data['数据']['视频']['地址']
                    return text
                else:
                    logger.error(json_data)
                    return None
        except Exception as e:
            logger.error(f"接口抛出异常:{e}")
            return None
        finally:
            session.close()


    def save_tempfile(self, url, e_context, video_name):
        logger.info("开始下载视频文件...{}".format(url))
        try:
            with Session() as session:
                response = session.get(url)
                logger.info("下载结束...")
                # 检查请求是否成功
                if response != None:
                    # 获取文件名和扩展名
                    file_name, file_ext = os.path.splitext(urlparse(url).path)
                    # file_name = file_name.replace(" ", "")
                    # file_ext = file_ext.replace(" ", "")
                    # file_ext = file_ext.replace(".mp4", "")
                    final_file_name = file_name + file_ext
                    logger.info(f"文件名：{final_file_name}")
                    with tempfile.NamedTemporaryFile(
                        prefix=video_name + ".", suffix=file_ext, delete=False
                    ) as f:
                        # 写入临时文件
                        f.write(response.content)
                        # 获取临时文件的路径
                        temp_file_path = f.name

                    logger.info("file: {}".format(temp_file_path))
                    print(f"视频文件已保存到临时文件: {temp_file_path}")
                    self._send_info(e_context, temp_file_path, ReplyType.VIDEO)
                    return
                else:
                    print("无法下载视频文件")
                    self._send_info(e_context, url, ReplyType.TEXT)
                    return
        except Exception as e:
            logger.error(f"接口抛出异常:{e}")
            return None
        finally:
            session.close()

    def _send_info(self, e_context: EventContext, content: str, type):
        reply = Reply(type, content)
        channel = e_context["channel"]
        channel.send(reply, e_context["context"])