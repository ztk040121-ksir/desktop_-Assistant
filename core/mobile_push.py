# -*- coding: utf-8 -*-
"""
NovaDesk Mobile Push Service
支持企业微信群机器人 (WeCom Webhook) 与 手机微信 (Server酱/PushDeer) 真实消息推送
"""
import requests
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PUSH_CONFIG_FILE = DATA_DIR / "push_settings.json"

def get_push_config() -> dict:
    try:
        if PUSH_CONFIG_FILE.exists():
            return json.loads(PUSH_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"wecom_webhook": "", "wechat_sendkey": ""}

def save_push_config(wecom_webhook: str = None, wechat_sendkey: str = None) -> bool:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = get_push_config()
        if wecom_webhook is not None:
            data["wecom_webhook"] = wecom_webhook.strip()
        if wechat_sendkey is not None:
            data["wechat_sendkey"] = wechat_sendkey.strip()
        PUSH_CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[MobilePush] Failed to save push config: {e}")
        return False


def send_wecom_webhook(webhook_url: str, title: str, content: str) -> Tuple[bool, str]:
    """
    通过企业微信群机器人 Webhook 推送 Markdown 卡片消息
    :param webhook_url: 企业微信机器人 Webhook 地址
    :param title: 任务标题
    :param content: 任务内容/AI执行摘要
    :return: (is_success, msg)
    """
    if not webhook_url or not webhook_url.strip().startswith("http"):
        return False, "未配置有效的企业微信 Webhook 地址"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_text = (
        f"### ⏰ NovaDesk 自动化任务报告\n"
        f"> **任务名称**：<font color=\"info\">{title}</font>\n"
        f"> **执行时间**：{now_str}\n"
        f"> **执行状态**：<font color=\"comment\">执行完成</font>\n\n"
        f"**执行结果与摘要**：\n"
        f"{content}\n\n"
        f"> *来自 NovaDesk AI 智能助手*"
    )

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": md_text
        }
    }

    try:
        resp = requests.post(webhook_url.strip(), json=payload, timeout=8)
        data = resp.json()
        if data.get("errcode") == 0:
            return True, "企业微信群机器人推送成功"
        else:
            return False, f"企业微信接口返回错误: {data.get('errmsg', '未知错误')} (errcode: {data.get('errcode')})"
    except Exception as e:
        return False, f"企业微信推送请求异常: {str(e)}"


def send_wechat_notification(send_key: str, title: str, content: str) -> Tuple[bool, str]:
    """
    通过 Server酱 (Turbo版) 或 PushDeer 将消息推送到手机个人微信服务号/小程序
    :param send_key: Server酱 SendKey 或 PushDeer PushKey
    :param title: 任务标题
    :param content: 详细内容
    :return: (is_success, msg)
    """
    if not send_key or not send_key.strip():
        return False, "未配置手机微信推送 SendKey"

    key = send_key.strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. 优先尝试 Server酱 (https://sctapi.ftqq.com/{KEY}.send)
    if key.startswith("SCT") or key.startswith("sct"):
        url = f"https://sctapi.ftqq.com/{key}.send"
        params = {
            "title": f"⏰ NovaDesk: {title}",
            "desp": f"**执行时间**: {now_str}\n\n**任务结果**:\n{content}"
        }
        try:
            resp = requests.post(url, data=params, timeout=8)
            data = resp.json()
            if data.get("code") == 0 or data.get("data", {}).get("errno") == 0:
                return True, "手机微信推送成功 (Server酱通道)"
            else:
                return False, f"Server酱返回错误: {data.get('message') or data.get('errmsg', '发送失败')}"
        except Exception as e:
            return False, f"Server酱请求异常: {e}"

    # 2. 尝试 PushDeer (https://api2.pushdeer.com/message/push)
    elif key.startswith("PDU") or key.startswith("pdu"):
        url = "https://api2.pushdeer.com/message/push"
        params = {
            "pushkey": key,
            "text": f"⏰ {title}",
            "desp": f"执行时间: {now_str}\n\n{content}",
            "type": "markdown"
        }
        try:
            resp = requests.post(url, data=params, timeout=8)
            data = resp.json()
            if data.get("code") == 0:
                return True, "手机微信推送成功 (PushDeer通道)"
            else:
                return False, f"PushDeer返回错误: {data.get('error', '发送失败')}"
        except Exception as e:
            return False, f"PushDeer请求异常: {e}"

    # 3. 通用 HTTP Webhook 兜底
    elif key.startswith("http://") or key.startswith("https://"):
        try:
            resp = requests.post(key, json={"title": title, "content": content, "time": now_str}, timeout=8)
            if resp.status_code == 200:
                return True, "自定义 Webhook 推送成功"
            else:
                return False, f"自定义 Webhook 状态码: {resp.status_code}"
        except Exception as e:
            return False, f"自定义 Webhook 异常: {e}"
    else:
        # 默认尝试 Server酱通用网关
        url = f"https://sctapi.ftqq.com/{key}.send"
        try:
            resp = requests.post(url, data={"title": f"⏰ NovaDesk: {title}", "desp": content}, timeout=8)
            data = resp.json()
            if data.get("code") == 0:
                return True, "手机微信推送成功"
            else:
                return False, f"微信通道返回错误: {data.get('message', 'SendKey无效')}"
        except Exception as e:
            return False, f"推送异常: {e}"
