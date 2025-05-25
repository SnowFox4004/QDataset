# QDataset 创建你的 QQ 好友数据集

QDataset 可从导出的 QQ 聊天记录中创建 sharegpt 数据集用于模型训练，保留好友/群友的珍贵回忆

## 使用

1. 使用[QQ_NT_Export](https://github.com/Tealina28/QQNT_Export/)的`dev`分支导出**Json**格式聊天记录
2. 使用`divide_chatlogs.py`构造数据集

**divide_chatlogs.py**

```bash
usage: divide_chatlogs.py [-h] [--strategy {hour,day}] [--hour HOUR] [--output OUTPUT] filepath

positional arguments:
  filepath

options:
  -h, --help            show this help message and exit
  --strategy {hour,day}, -st {hour,day}
  --hour HOUR
  --output OUTPUT, -o OUTPUT
```

## Features:

### 1. 划分策略：

- 按自定义小时划分，两消息间间隔超过 **x** 小时即划分为不同对话
- 按天划分，每天`早4:00`前后划分为两个对话
  > 每个对话至少有五十条消息

---

## 使用注意：

1. 仅供学习使用，请勿用于违法用途
2. 严禁用于任何违反中国大陆法律法规、您所在地区法律法规、QQ 软件许可及服务协议的行为，开发者不承担任何相关行为导致的直接或间接责任。
3. 本项目不对生成内容的完整性、准确性作任何担保，生成的一切内容不可用于法律取证，您不应当将其用于学习与交流外的任何用途。
