# MQTT 物联网协议分析与实现

下一代互联网技术课程大作业，主要实现了MQTT 多传感器数据采集与 Web 监控

## 需要的软件

- Python 3.10以上
- uv

## 安装依赖

```powershell
uv sync
```

## MQTT 实验

打开 3 个终端，分别运行：

```powershell
uv run iot-mqtt-broker
```

```powershell
uv run iot-dashboard
```

```powershell
uv run iot-mqtt-simulator --devices 4 --interval 1 --qos 1
```

然后访问：

```text
http://127.0.0.1:8000
```

Dashboard 会显示最新传感器数据、最近消息、告警信息和 MQTT 延迟统计。数据会保存到 `data/iot_messages.db`。
