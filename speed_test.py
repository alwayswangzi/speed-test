#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging
import json
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

# 时延测试配置
LATENCY_TEST_SIZE = 1024  # 1KB for latency test
LATENCY_TEST_COUNT = 5    # 测试次数


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


def get_file_size_info(file_size_key: str) -> Dict[str, Any]:
    """
    获取文件大小信息
    
    Args:
        file_size_key: 文件大小标识符
        
    Returns:
        Dict: 包含文件大小信息的字典
    """
    file_size = FILE_SIZES.get(file_size_key, FILE_SIZES[DEFAULT_SIZE])
    
    return {
        "file_size": file_size,
        "file_size_mb": round(file_size / (1024 * 1024), 2),
        "file_name": f"test_data_{file_size_key}.bin",
        "file_size_key": file_size_key,
    }


def generate_latency_test_data() -> bytes:
    """
    生成用于时延测试的小数据包
    
    Returns:
        bytes: 测试数据
    """
    return os.urandom(LATENCY_TEST_SIZE)


def calculate_latency_stats(latencies: List[float]) -> Dict[str, float]:
    """
    计算时延统计信息
    
    Args:
        latencies: 时延列表（毫秒）
        
    Returns:
        Dict: 时延统计信息
    """
    if not latencies:
        return {
            "min": 0,
            "max": 0,
            "avg": 0,
            "median": 0,
            "jitter": 0
        }
    
    latencies.sort()
    min_latency = latencies[0]
    max_latency = latencies[-1]
    avg_latency = sum(latencies) / len(latencies)
    
    # 计算中位数
    n = len(latencies)
    if n % 2 == 0:
        median_latency = (latencies[n//2-1] + latencies[n//2]) / 2
    else:
        median_latency = latencies[n//2]
    
    # 计算抖动（标准差）
    variance = sum((x - avg_latency) ** 2 for x in latencies) / len(latencies)
    jitter = variance ** 0.5
    
    return {
        "min": round(min_latency, 2),
        "max": round(max_latency, 2),
        "avg": round(avg_latency, 2),
        "median": round(median_latency, 2),
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


@app.route("/api/test-info")
def test_info():
    """
    返回测试文件信息
    
    Query Parameters:
        size: 文件大小标识符 (默认: 50m)
        
    Returns:
        JSON: 文件信息
    """
    file_size_key = request.args.get("size", DEFAULT_SIZE)
    logger.info(f"获取文件信息: {file_size_key}")
    return jsonify(get_file_size_info(file_size_key))


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


@app.route("/api/latency-test")
def latency_test():
    """
    时延测试API
    
    Returns:
        JSON: 时延测试结果
    """
    logger.info("开始时延测试")
    
    latencies = []
    test_times = []
    
    for i in range(LATENCY_TEST_COUNT):
        start_time = time.time()
        
        # 生成测试数据
        test_data = generate_latency_test_data()
        
        # 模拟网络传输时间（这里只是生成数据的时间）
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        latencies.append(latency_ms)
        test_times.append({
            "test": i + 1,
            "latency": round(latency_ms, 2),
            "timestamp": datetime.now().isoformat()
        })
    
    # 计算统计信息
    stats = calculate_latency_stats(latencies)
    
    result = {
        "test_count": LATENCY_TEST_COUNT,
        "test_size_bytes": LATENCY_TEST_SIZE,
        "test_size_kb": round(LATENCY_TEST_SIZE / 1024, 2),
        "latencies": latencies,
        "test_details": test_times,
        "statistics": stats,
        "timestamp": datetime.now().isoformat()
    }
    
    logger.info(f"时延测试完成: 平均 {stats['avg']}ms, 抖动 {stats['jitter']}ms")
    return jsonify(result)


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