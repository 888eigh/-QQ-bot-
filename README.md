# -QQ-bot-
写在前面
注意：1.本仓库不包含napcat架构文件和QQ安装包，需使用请自行下载
2.使用前请确保python环境为3.1.2+
3.代码运行需要nonebot，nonebot-adapter-onebot，websockets等，可自行查看头文件需要的运行库
4.项目文件夹下的多媒体资源需自行添加picture 文件夹的图片和 emotional 文件夹下的表情
5.文件夹下的boring.txt是用来添加随机话语的，每句话请用%分隔
6.使用需修改napcat文件夹下的config/onebot11_<QQ号>.json文件把
websocketClients 改成：

"websocketClients": [
{
"enable": true,
"url": "ws://127.0.0.1:8081/onebot/v11/ws"
}
]

GUI功能如下

功能模板页：欢迎语、群规、关于、帮助、AI 人设、自定义指令，填空式生成
高级设置页：API 配置、Bot 配置、NapCat 配置、日志配置、聊天配置，所有参数可改
其余可自行配置
项目文件下的exe.bat可一键打包程序为exe文件
