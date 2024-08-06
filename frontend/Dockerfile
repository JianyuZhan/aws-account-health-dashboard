# 使用官方的 Node.js 作为构建环境
FROM node:22 AS build

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制所有文件到工作目录
COPY . .

# 构建 React 应用
RUN npm run build

# 使用 Nginx 作为生产环境
FROM nginx:alpine

# 将构建的应用从前一阶段复制到 Nginx 服务器的html目录下
COPY --from=build /app/build /usr/share/nginx/html

# 暴露端口
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]