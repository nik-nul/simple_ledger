#!/bin/bash

# 配置参数
MAX_ITERATIONS=600
OUTPUT_DIR="pytest_failures"
PASS_PATTERN="11 passed"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo "开始执行 pytest 模糊测试..."
echo "最大执行次数: $MAX_ITERATIONS"
echo "失败日志保存目录: $OUTPUT_DIR"
echo "=========================================="

# 循环执行测试
for i in $(seq 1 $MAX_ITERATIONS); do
    echo -n "[$i/$MAX_ITERATIONS] 正在运行测试... "
    
    # 执行 pytest 并捕获所有输出（stdout 和 stderr）
    output=$(python -m pytest tests/fuzz.py -v --tb=short --hypothesis-show-statistics 2>&1)
    
    # 检查输出是否包含 "11 passed"
    if echo "$output" | grep -q "$PASS_PATTERN"; then
        echo "✓ 通过 (11 passed)"
    else
        # 生成带时间戳的文件名
        timestamp=$(date +"%Y%m%d_%H%M%S")
        filename="$OUTPUT_DIR/failure_${i}_${timestamp}.log"
        
        # 将输出写入文件
        echo "$output" > "$filename"
        
        echo "✗ 未通过，输出已保存到: $filename"
    fi
done

echo "=========================================="
echo "测试完成！共执行 $MAX_ITERATIONS 次"

# 统计失败次数
failure_count=$(ls -1 "$OUTPUT_DIR" 2>/dev/null | wc -l)
success_count=$((MAX_ITERATIONS - failure_count))

echo "成功次数: $success_count"
echo "失败次数: $failure_count"

if [ $failure_count -gt 0 ]; then
    echo "失败日志保存在: $OUTPUT_DIR/"
fi