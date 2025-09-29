const express = require("express");
const { createProxyMiddleware } = require("http-proxy-middleware");
const app = express();
app.use(express.static("web/public"));
app.use("/api", createProxyMiddleware({ target: "http://localhost:8000", changeOrigin: true, pathRewrite: { "^/api": "" }}));
app.listen(5173, () => console.log("Web on http://localhost:5173 (proxy → :8000)"));
