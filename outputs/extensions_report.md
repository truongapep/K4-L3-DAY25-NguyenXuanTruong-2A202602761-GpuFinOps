# Your Turn — kết quả riêng trên dữ liệu đề bài cung cấp

Tôi thực hiện hai extension trên dữ liệu đề bài cung cấp: ngân sách reasoning và chuyển vùng chạy để giảm carbon. Tôi ghi riêng kết quả, giữ nguyên mốc M1–M5 để so sánh.

## Extension 4: Ngân sách reasoning

| Traffic | Requests | Traffic % | USD/ngày | Chi phí % | Wh/ngày | Năng lượng % |
|---|---:|---:|---:|---:|---:|---:|
| normal | 2199 | 91.62 | 7.0882 | 83.54 | 1887.56 | 5.96 |
| reasoning | 201 | 8.38 | 1.3965 | 16.46 | 29787.74 | 94.04 |

Tôi dùng token_usage.csv, tách request theo is_reasoning=0 và is_reasoning=1. Chi phí tính theo model tier, cache và batch như M2. Năng lượng dùng công thức của đề bài: 0.30 Wh/1k token, reasoning nhân 80. Đây là năng lượng ước tính từ công thức của bài.

Cùng số token, reasoning tiêu thụ 29787.74 Wh so với 372.35 Wh nếu chạy thường (80×). Flag reasoning tự nó không tăng đơn giá USD.

Tôi thử giới hạn reasoning ở 5% số request. Kết quả chuyển 81 request, còn 120 request reasoning. Tôi chọn request có output dài nhất trước; nếu bằng nhau, chọn theo thứ tự dòng trong CSV. Quy tắc này giúp chạy lại được cùng kết quả.

| Đại lượng | Trước | Sau | Tiết kiệm |
|---|---:|---:|---:|
| USD/ngày | 8.4846 | 7.8042 | 0.6804 |
| Wh/ngày | 31675.31 | 15905.23 | 15770.08 |

Trong kịch bản này, tôi giả định output sau khi chuyển bằng output gốc / 6 vì generator nhân output reasoning với 6. Input, tier, cache và batch giữ nguyên. Do output thay đổi, kết quả chưa chứng minh chất lượng đáp án tương đương hoặc $/1M-token tốt hơn.

Nếu giữ nguyên cả output token, tiết kiệm USD = 0; tiết kiệm năng lượng ước tính = 15650.65 Wh/ngày. Tách hai kịch bản giúp thấy tiền tiết kiệm đến từ output giảm, năng lượng giảm chủ yếu do bỏ hệ số reasoning.

Từ kết quả, tôi đề xuất chỉ dùng reasoning khi tác vụ phức tạp hoặc độ tin cậy thấp; thử ngân sách 5% và cho phép ngoại lệ với tác vụ quan trọng. Dữ liệu chưa có confidence hay điểm chất lượng nên cần đánh giá thêm trước khi áp dụng. Mức 5% là giả định của phần mở rộng.

## Extension 5: Carbon-aware scheduling

Tôi chọn các job có interruptible=1 trong workloads.csv và giả định chúng đang chạy tại us-east-1. Năng lượng = watts × hours_per_day × days × num_gpus, dùng công suất định mức trong price_catalog.csv. Tôi dùng days của từng job; M3 quy đổi tất cả về 30 ngày để tính chi phí tháng.

| Job | GPU-hours | kWh | CO2 trước (g) | CO2 sau (g) | Giảm (g) |
|---|---:|---:|---:|---:|---:|
| job-train-llm | 2240 | 1568.00 | 595840.00 | 47040.00 | 548800.00 |
| job-train-embed | 200 | 80.00 | 30400.00 | 2400.00 | 28000.00 |
| job-finetune | 36 | 25.20 | 9576.00 | 756.00 | 8820.00 |
| job-dev-sandbox | 352 | 52.80 | 20064.00 | 1584.00 | 18480.00 |
| job-batch-eval | 90 | 63.00 | 23940.00 | 1890.00 | 22050.00 |

| Vùng | USD/kWh | gCO2/kWh | Tiền điện (USD) | CO2 (g) |
|---|---:|---:|---:|---:|
| us-east-1 | 0.120 | 380 | 214.68 | 679820.00 |
| us-west-2 | 0.070 | 120 | 125.23 | 214680.00 |
| europe-north1 | 0.090 | 30 | 161.01 | 53670.00 |
| europe-central2 | 0.180 | 660 | 322.02 | 1180740.00 |
| us-east-wa | 0.055 | 90 | 98.39 | 161010.00 |

Chuyển sang europe-north1: 679.820 → 53.670 kgCO2e; giảm 626.150 kg (92.11%).

Theo bảng dữ liệu của đề bài, europe-north1 có carbon thấp nhất; us-east-wa có giá điện thấp nhất. Tôi chọn vùng theo ưu tiên của công ty: giảm carbon hoặc giảm tiền điện. Với cùng lượng điện, giá thấp nhất và carbon thấp nhất thuộc hai vùng khác nhau.

Tôi không cộng tiền điện tiết kiệm vào M5 vì giá thuê GPU có thể đã bao gồm điện. Phép tính chưa tính PUE, thời gian idle, checkpoint, phí truyền dữ liệu, độ trễ và quy định lưu trữ dữ liệu. Vùng nguồn là giả định vì workloads.csv không có cột region.

## Công thức và nguồn để đối chiếu

| Đại lượng | Cách tính |
|---|---|
| USD/request | finops.pricing.request_cost(): input chưa cache + input cache × 0.10 + output; chia 1M, nhân đơn giá tier; batch nhân 0.50 |
| Wh/request | (input_tokens + output_tokens) / 1000 × 0.30; reasoning nhân 80 |
| Số reasoning giữ lại tối đa | floor(tổng request × 0.05) |
| Output giả định sau chuyển | output_tokens / 6; input và đơn giá giữ nguyên |
| Wh/job | watts × hours_per_day × days × num_gpus |
| gCO2e/job | Wh / 1000 × REGION_CARBON[region] |
| Tiền điện/job | Wh / 1000 × REGION_PRICE_KWH[region] |

Công thức USD được áp dụng riêng cho input/output theo MODEL_PRICES trong M2. Thông số carbon và giá điện lấy từ finops/sustainability.py. Số liệu chưa làm tròn lưu ở [extensions_results.json](extensions_results.json), gồm từng nhóm traffic, từng job và cả năm vùng.

Có thể chạy lại:

```powershell
python missions/your_turn.py
python -m pytest -q validation/check_extensions.py
```

Code tính: finops/extensions.py → reasoning_budget() và carbon_scheduling(). Log kiểm tra chung: [verification.txt](verification.txt).
