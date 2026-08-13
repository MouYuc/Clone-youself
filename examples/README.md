# 示例 Examples

两个可直接运行的台词示例：

也可以用 WebUI 操作（浏览器界面）：`python ../tools/guangpu_webui.py`，
上传这两个文件即可批量合成；详见 `../docs/WEBUI_GUIDE.md`。

## 1. 普通话输入（自动转轻中广普）

```bash
python ../tools/guangpu_local_tts.py 台词示例_普通话输入.txt ../output
```

输入写普通话，工具自动转换：是→系、不是→唔系、最重要→最紧要、
没有→冇、什么→乜嘢、你说→你话、的→嘅。

## 2. 广普直写（精确控制浓度）

```bash
python ../tools/guangpu_local_tts.py 台词示例_广普直写.txt ../output
```

台词直接写粤字，读音由广普词典保证（系→hei1、嘅→ge3、㗎→ga3 等）。
适合你已经清楚想要什么浓度的情况。

## 说明

- 以 `#` 开头的行会被忽略，可用于注释
- 一行一句，建议 5~20 字；长句请自行断行
- 输出为 mp3，命名 `001_台词前几字.mp3`
