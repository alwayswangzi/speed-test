#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
import json
import socket
import requests
from typing import Dict, Generator, Any, List, Tuple
from flask import Flask, render_template, jsonify, request, Response
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 文件大小配置 (key: 标识符, value: 字节数)
FILE_SIZES: Dict[str, int] = {
    "1m": 1 * 1024 * 1024,      # 1MB - 快速测试
    "10m": 10 * 1024 * 1024,    # 10MB - 标准测试
    "50m": 50 * 1024 * 1024,    # 50MB - 详细测试 (默认)
    "100m": 100 * 1024 * 1024   # 100MB - 压力测试
}

# 流式生成配置
CHUNK_SIZE = 64 * 1024  # 64KB chunks for optimal streaming performance
DEFAULT_SIZE = "50m"     # 默认文件大小

# Ping测试配置
PING_TEST_COUNT = 5    # ping测试次数

# 网站连通性测试配置
WEBSITE_TEST_TIMEOUT = 10  # 网站测试超时时间（秒）
COMMON_WEBSITES = {
    "google": {
        "name": "Google",
        "url": "https://www.google.com",
        "description": "全球最大搜索引擎"
    },
    "youtube": {
        "name": "YouTube", 
        "url": "https://www.youtube.com",
        "description": "全球最大视频平台"
    },
    "telegram": {
        "name": "Telegram",
        "url": "https://web.telegram.org",
        "description": "即时通讯应用"
    },
    "github": {
        "name": "GitHub",
        "url": "https://github.com",
        "description": "代码托管平台"
    },
    "stackoverflow": {
        "name": "Stack Overflow",
        "url": "https://stackoverflow.com",
        "description": "程序员问答社区"
    },
    "baidu": {
        "name": "百度",
        "url": "https://www.baidu.com",
        "description": "中国最大搜索引擎"
    }
}


def generate_random_data_stream(file_size: int) -> Generator[bytes, None, None]:
    """
    生成随机数据流，不保存到磁盘
    
    Args:
        file_size: 要生成的文件大小（字节）
        
    Yields:
        bytes: 随机数据块
        
    Note:
        使用64KB分块生成，平衡内存使用和性能
    """
    remaining = file_size
    
    while remaining > 0:
        # 生成随机数据块
        current_chunk_size = min(CHUNK_SIZE, remaining)
        try:
            data = os.urandom(current_chunk_size)
            remaining -= current_chunk_size
            yield data
        except OSError as e:
            logger.error(f"生成随机数据失败: {e}")
            break




def test_website_connectivity(url: str, timeout: int = WEBSITE_TEST_TIMEOUT) -> Dict[str, Any]:
    """
    测试网站连通性和响应时间
    
    Args:
        url: 要测试的网站URL
        timeout: 超时时间（秒）
        
    Returns:
        Dict: 测试结果
    """
    result = {
        "url": url,
        "accessible": False,
        "response_time_ms": 0,
        "status_code": None,
        "error": None,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=timeout, allow_redirects=True)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # 转换为毫秒
        
        result.update({
            "accessible": True,
            "response_time_ms": round(response_time, 2),
            "status_code": response.status_code
        })
        
        logger.info(f"网站连通性测试成功: {url} - {response_time:.2f}ms (状态码: {response.status_code})")
        
    except requests.exceptions.Timeout:
        result["error"] = "连接超时"
        logger.warning(f"网站连通性测试超时: {url}")
    except requests.exceptions.ConnectionError:
        result["error"] = "连接失败"
        logger.warning(f"网站连通性测试连接失败: {url}")
    except requests.exceptions.RequestException as e:
        result["error"] = f"请求错误: {str(e)}"
        logger.warning(f"网站连通性测试请求错误: {url} - {e}")
    except Exception as e:
        result["error"] = f"未知错误: {str(e)}"
        logger.error(f"网站连通性测试未知错误: {url} - {e}")
    
    return result


def test_all_websites() -> Dict[str, Any]:
    """
    测试所有配置的网站连通性
    
    Returns:
        Dict: 所有网站的测试结果
    """
    results = {
        "websites": {},
        "summary": {
            "total": len(COMMON_WEBSITES),
            "accessible": 0,
            "failed": 0,
            "average_response_time": 0
        },
        "timestamp": datetime.now().isoformat()
    }
    
    accessible_count = 0
    total_response_time = 0
    
    for key, site_info in COMMON_WEBSITES.items():
        logger.info(f"开始测试网站: {site_info['name']} ({site_info['url']})")
        
        test_result = test_website_connectivity(site_info['url'])
        test_result.update({
            "name": site_info['name'],
            "description": site_info['description']
        })
        
        results["websites"][key] = test_result
        
        if test_result["accessible"]:
            accessible_count += 1
            total_response_time += test_result["response_time_ms"]
    
    # 计算汇总信息
    results["summary"]["accessible"] = accessible_count
    results["summary"]["failed"] = len(COMMON_WEBSITES) - accessible_count
    
    if accessible_count > 0:
        results["summary"]["average_response_time"] = round(total_response_time / accessible_count, 2)
    
    logger.info(f"网站连通性测试完成: {accessible_count}/{len(COMMON_WEBSITES)} 个网站可访问")
    
    return results


def calculate_ping_stats(pings: List[float]) -> Dict[str, float]:
    """
    计算ping统计信息
    
    Args:
        pings: ping时延列表（毫秒）
        
    Returns:
        Dict: ping统计信息
    """
    if not pings:
        return {
            "min": 0,
            "max": 0,
            "avg": 0,
            "median": 0,
            "jitter": 0
        }
    
    pings.sort()
    min_ping = pings[0]
    max_ping = pings[-1]
    avg_ping = sum(pings) / len(pings)
    
    # 计算中位数
    n = len(pings)
    if n % 2 == 0:
        median_ping = (pings[n//2-1] + pings[n//2]) / 2
    else:
        median_ping = pings[n//2]
    
    # 计算抖动（标准差）
    variance = sum((x - avg_ping) ** 2 for x in pings) / len(pings)
    jitter = variance ** 0.5
    
    return {
        "min": round(min_ping, 2),
        "max": round(max_ping, 2),
        "avg": round(avg_ping, 2),
        "median": round(median_ping, 2),
        "jitter": round(jitter, 2)
    }


@app.route("/")
def index():
    """主页面"""
    logger.info("用户访问主页面")
    return render_template("index.html")


@app.route("/download")
def download_file():
    """
    提供文件下载 - 使用流式生成，不保存文件
    
    Query Parameters:
        size: 文件大小标识符 (默认: 50m)
        
    Returns:
        Response: 流式下载响应
    """
    file_size_key = request.args.get("size", DEFAULT_SIZE)
    file_size = FILE_SIZES.get(file_size_key, FILE_SIZES[DEFAULT_SIZE])
    
    logger.info(f"开始生成 {file_size / (1024*1024):.1f}MB 随机数据流 (key: {file_size_key})")
    
    # 创建响应流
    def generate():
        """内部生成器函数"""
        try:
            data_stream = generate_random_data_stream(file_size)
            for chunk in data_stream:
                yield chunk
        except Exception as e:
            logger.error(f"数据流生成错误: {e}")
            yield b""
    
    # 返回流式响应
    response = Response(
        generate(),
        mimetype="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=test_data_{file_size_key}.bin",
            "Content-Length": str(file_size),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
    
    return response




@app.route("/api/file-sizes")
def get_file_sizes():
    """
    返回所有可用的文件大小选项
    
    Returns:
        JSON: 文件大小选项列表
    """
    sizes = []
    for key, size_bytes in FILE_SIZES.items():
        sizes.append({
            "key": key,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / (1024 * 1024), 2),
            "display_name": f"{round(size_bytes / (1024 * 1024), 2)} MB"
        })
    
    logger.info(f"返回 {len(sizes)} 个文件大小选项")
    return jsonify({"sizes": sizes})


@app.route("/api/ping")
def ping():
    """
    简单的ping测试，返回服务器响应时间
    
    Returns:
        JSON: ping结果
    """
    start_time = time.time()
    
    # 简单的响应
    response_data = {
        "status": "ok",
        "message": "pong",
        "timestamp": datetime.now().isoformat(),
        "server_time": time.time()
    }
    
    end_time = time.time()
    response_time = (end_time - start_time) * 1000
    
    response_data["response_time_ms"] = round(response_time, 2)
    
    logger.info(f"Ping测试: {response_time:.2f}ms")
    return jsonify(response_data)


@app.route("/api/website-test")
def website_test():
    """
    测试常用网站的连通性和延时
    
    Returns:
        JSON: 网站连通性测试结果
    """
    logger.info("开始网站连通性测试")
    
    try:
        results = test_all_websites()
        logger.info(f"网站连通性测试完成: {results['summary']['accessible']}/{results['summary']['total']} 个网站可访问")
        return jsonify(results)
    except Exception as e:
        logger.error(f"网站连通性测试失败: {e}")
        return jsonify({
            "error": f"网站连通性测试失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route("/api/websites")
def get_websites():
    """
    返回所有可测试的网站列表
    
    Returns:
        JSON: 网站列表
    """
    websites = []
    for key, site_info in COMMON_WEBSITES.items():
        websites.append({
            "key": key,
            "name": site_info['name'],
            "url": site_info['url'],
            "description": site_info['description']
        })
    
    logger.info(f"返回 {len(websites)} 个可测试网站")
    return jsonify({"websites": websites})


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    logger.warning(f"404错误: {request.url}")
    return jsonify({"error": "页面未找到"}), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"500错误: {error}")
    return jsonify({"error": "服务器内部错误"}), 500


def validate_configuration():
    """验证配置"""
    if not FILE_SIZES:
        raise ValueError("FILE_SIZES配置不能为空")
    
    if DEFAULT_SIZE not in FILE_SIZES:
        raise ValueError(f"默认大小 {DEFAULT_SIZE} 不在FILE_SIZES中")
    
    logger.info("配置验证通过")


def print_startup_info():
    """打印启动信息"""
    print("=" * 60)
    print("🚀 下载速度测试服务器")
    print("=" * 60)
    print(f"📊 支持的文件大小: {', '.join([f'{size}MB' for size in [1, 10, 50, 100]])}")
    print(f"🎯 默认选择: {FILE_SIZES[DEFAULT_SIZE] / (1024*1024):.0f}MB")
    print("访问地址: http://localhost:5000")
    print("=" * 60)


if __name__ == "__main__":
    try:
        # 验证配置
        validate_configuration()
        
        # 确保templates目录存在
        os.makedirs("templates", exist_ok=True)
        
        # 打印启动信息
        print_startup_info()
        
        # 启动服务器
        app.run(host="0.0.0.0", port=5000, debug=False)
        
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        print(f"启动失败: {e}")
        exit(1)