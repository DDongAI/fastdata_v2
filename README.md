# 🍉 fastdata_v2

 --- 
 - 图像识别
 - pdf识别
 ---
### 🧰 项目启动
**1、⚙ 项目环境配置**
```shell
# 拉取项目
git clone https://github.com/DDongAI/fastdata_v2.git
```
```shell
cd fastdata_v2
```
```shell
# 配置环境变量
cp .env.example .env
# 配置模型
vi .env
```
```shell
# 修改其他信息
vi docker-compose.yml
vi Dockerfile
```
**2、⚙ 启动命令**
- 🛠 方式1：
```shell
cd fastdata_v2
```
```shell
docker-compose up -d
```
- 🛠 方式2：
```angular2html
略
```
--- 
### Ⓥ 版本说明
- 🔄 v-2.0
```angular2html
1、支持图片上传识别
2、支持pdf上传识别
3、添加异步，后台处理数据
```
