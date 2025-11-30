"""
MQTT Streamlit 應用程式
提供網頁介面來發布和訂閱 MQTT 訊息
"""

import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
from typing import Optional

# 頁面設定
st.set_page_config(
    page_title="MQTT 控制台",
    page_icon="📡",
    layout="wide"
)

# 初始化 session state
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = None
    st.session_state.connected = False
    st.session_state.messages = []
    st.session_state.subscribed_topics = set()

def on_connect(client, userdata, flags, rc):
    """MQTT 連線回呼函數"""
    if rc == 0:
        st.session_state.connected = True
        st.success("✅ 成功連線到 MQTT Broker!")
    else:
        st.session_state.connected = False
        st.error(f"❌ 連線失敗，錯誤代碼: {rc}")

def on_message(client, userdata, msg):
    """MQTT 訊息接收回呼函數"""
    try:
        message_data = {
            'topic': msg.topic,
            'payload': msg.payload.decode('utf-8'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'qos': msg.qos
        }
        st.session_state.messages.insert(0, message_data)
        # 只保留最近 100 條訊息
        if len(st.session_state.messages) > 100:
            st.session_state.messages = st.session_state.messages[:100]
    except Exception as e:
        st.error(f"處理訊息時發生錯誤: {e}")

def on_publish(client, userdata, mid):
    """MQTT 發布成功回呼函數"""
    st.success(f"📤 訊息發布成功 (ID: {mid})")

def connect_mqtt(broker: str, port: int, client_id: str):
    """連線到 MQTT Broker"""
    try:
        if st.session_state.mqtt_client is not None:
            disconnect_mqtt()
        
        client = mqtt.Client(client_id=client_id)
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_publish = on_publish
        
        client.connect(broker, port, 60)
        client.loop_start()
        
        st.session_state.mqtt_client = client
        time.sleep(1)  # 等待連線建立
        return True
    except Exception as e:
        st.error(f"連線錯誤: {e}")
        return False

def disconnect_mqtt():
    """斷開 MQTT 連線"""
    if st.session_state.mqtt_client is not None:
        try:
            st.session_state.mqtt_client.loop_stop()
            st.session_state.mqtt_client.disconnect()
            st.session_state.mqtt_client = None
            st.session_state.connected = False
            st.session_state.subscribed_topics.clear()
            st.success("🔌 已斷線")
        except Exception as e:
            st.error(f"斷線時發生錯誤: {e}")

def subscribe_topic(topic: str):
    """訂閱 MQTT 主題"""
    if st.session_state.mqtt_client is not None and st.session_state.connected:
        try:
            st.session_state.mqtt_client.subscribe(topic, qos=1)
            st.session_state.subscribed_topics.add(topic)
            st.success(f"✅ 已訂閱主題: {topic}")
            return True
        except Exception as e:
            st.error(f"訂閱失敗: {e}")
            return False
    else:
        st.warning("⚠️ 請先連線到 MQTT Broker")
        return False

def publish_message(topic: str, message: str, qos: int = 1, retain: bool = False):
    """發布 MQTT 訊息"""
    if st.session_state.mqtt_client is not None and st.session_state.connected:
        try:
            result = st.session_state.mqtt_client.publish(topic, message, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                st.error(f"發布失敗，錯誤代碼: {result.rc}")
                return False
        except Exception as e:
            st.error(f"發布時發生錯誤: {e}")
            return False
    else:
        st.warning("⚠️ 請先連線到 MQTT Broker")
        return False

# ============ 主介面 ============
st.title("📡 MQTT 控制台")
st.markdown("---")

# 側邊欄：連線設定
with st.sidebar:
    st.header("⚙️ 連線設定")
    
    broker = st.text_input("MQTT Broker", value="localhost", help="MQTT Broker 位址")
    port = st.number_input("埠號", min_value=1, max_value=65535, value=1883)
    client_id = st.text_input("客戶端 ID", value=f"streamlit_client_{int(time.time())}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔌 連線", use_container_width=True):
            if connect_mqtt(broker, port, client_id):
                st.rerun()
    
    with col2:
        if st.button("🔌 斷線", use_container_width=True):
            disconnect_mqtt()
            st.rerun()
    
    # 連線狀態
    if st.session_state.connected:
        st.success("🟢 已連線")
    else:
        st.error("🔴 未連線")
    
    st.markdown("---")
    
    # 訂閱主題
    st.header("📥 訂閱主題")
    subscribe_topic_input = st.text_input("主題名稱", key="subscribe_topic", placeholder="例如: test/raspberry")
    if st.button("訂閱", use_container_width=True):
        if subscribe_topic_input:
            subscribe_topic(subscribe_topic_input)
            st.rerun()
    
    # 已訂閱的主題列表
    if st.session_state.subscribed_topics:
        st.markdown("**已訂閱的主題：**")
        for topic in st.session_state.subscribed_topics:
            st.text(f"  • {topic}")

# 主內容區域
col1, col2 = st.columns([1, 1])

# 左側：發布訊息
with col1:
    st.header("📤 發布訊息")
    
    publish_topic = st.text_input("主題", key="publish_topic", placeholder="例如: test/raspberry")
    
    message_type = st.radio("訊息類型", ["文字", "JSON"], horizontal=True)
    
    if message_type == "文字":
        message_content = st.text_area("訊息內容", key="message_text", height=150)
    else:
        json_input = st.text_area("JSON 內容", key="message_json", height=150, 
                                 value='{\n  "device": "Raspberry Pi",\n  "temperature": 25.5\n}')
        try:
            json.loads(json_input)
            message_content = json_input
        except json.JSONDecodeError:
            st.error("❌ JSON 格式錯誤")
            message_content = None
    
    qos = st.slider("QoS 等級", min_value=0, max_value=2, value=1)
    retain = st.checkbox("保留訊息 (Retain)")
    
    if st.button("📤 發布", type="primary", use_container_width=True):
        if publish_topic and message_content:
            if publish_message(publish_topic, message_content, qos=qos, retain=retain):
                st.success("訊息已發布！")
        else:
            st.warning("請填寫主題和訊息內容")

# 右側：接收訊息
with col2:
    st.header("📥 接收訊息")
    
    # 清除訊息按鈕
    if st.button("🗑️ 清除訊息", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    # 顯示訊息
    if st.session_state.messages:
        for msg in st.session_state.messages[:20]:  # 只顯示最近 20 條
            with st.expander(f"📨 {msg['topic']} - {msg['timestamp']}"):
                st.text("主題:")
                st.code(msg['topic'], language=None)
                st.text("內容:")
                st.code(msg['payload'], language="json" if msg['payload'].strip().startswith('{') else None)
                st.caption(f"QoS: {msg['qos']}")
    else:
        st.info("尚未收到任何訊息。請先連線並訂閱主題。")

# 頁尾
st.markdown("---")
st.caption("💡 提示：請確保 MQTT Broker (如 Mosquitto) 正在運行")

