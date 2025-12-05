----如何在本地运行并测试

Terminal 输入：

Bash

pip install streamlit google-generativeai
运行程序。在终端输入：

Bash

streamlit run app.py
浏览器会自动弹出一个窗口（通常是 http://localhost:8501）。
输入你的 Key，你就可以看到你的“孩子”并和它聊天了！

---如何部署并嵌入到 Google Sites (关键一步)
既然你想用 Google Sites，你需要把上面的代码变成一个公开的 URL 链接。

创建 GitHub 仓库: 将 app.py 和一个名为 requirements.txt (内容写上 streamlit 和 google-generativeai) 的文件上传到 GitHub。

使用 Streamlit Cloud (免费且最简单):

去 share.streamlit.io 注册。

连接你的 GitHub，选择刚才那个仓库。

点击 Deploy。几分钟后，你就会获得一个网址，例如 https://my-ai-child.streamlit.app。

回到 Google Sites:

打开你的 Google Sites 编辑器。

在右侧工具栏选择 "Embed" (嵌入)。

选择 "By URL"，然后粘贴你刚才获得的 Streamlit 网址。

调整窗口大小，让它看起来像一个完整的聊天 APP。