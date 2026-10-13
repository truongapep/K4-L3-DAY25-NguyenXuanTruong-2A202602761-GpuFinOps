# Your Turn — kết quả riêng trên dữ liệu BTC

Hai extension không cộng vào mức tiết kiệm 46.1% của M5.

## Extension 4: Ngân sách reasoning

| Traffic | Requests | Traffic % | USD/ngày | Chi phí % | Wh/ngày | Năng lượng % |
|---|---:|---:|---:|---:|---:|---:|
| normal | 2199 | 91.62 | 7.0882 | 83.54 | 1887.56 | 5.96 |
| reasoning | 201 | 8.38 | 1.3965 | 16.46 | 29787.74 | 94.04 |

Tiền được tính theo model tier, cache và batch của M2. Năng lượng dùng công thức BTC: 0.30 Wh/1k token; reasoning nhân 80. Đây là ước lượng, không phải đo điện thực tế.

Cùng số token, reasoning tiêu thụ 29787.74 Wh so với 372.35 Wh nếu chạy thường (80×). Flag reasoning tự nó không tăng đơn giá USD.

Kịch bản cap 5% traffic: chuyển 81 request, còn 120 reasoning request. Chọn request reasoning có output dài nhất trước, tie-break theo vị trí dòng.

| Đại lượng | Trước | Sau | Tiết kiệm |
|---|---:|---:|---:|
| USD/ngày | 8.4846 | 7.8042 | 0.6804 |
| Wh/ngày | 31675.31 | 15905.23 | 15770.08 |

Giả định kịch bản: output của request được chuyển bằng output gốc / 6, đảo hệ số 6 của generator; giữ input, tier, cache và batch. Sản lượng token thay đổi nên không dùng kịch bản này để tuyên bố cải thiện $/1M-token ở chất lượng tương đương.

Nếu giữ nguyên cả output token, tiết kiệm USD = 0; tiết kiệm năng lượng ước tính = 15650.65 Wh/ngày. Tách hai kịch bản giúp thấy tiền tiết kiệm đến từ output giảm, năng lượng giảm chủ yếu do bỏ hệ số reasoning.

Routing đề xuất: chỉ bật reasoning cho nhiệm vụ phức tạp/độ tin cậy thấp, giới hạn soft budget 5%, có ngoại lệ cho tác vụ quan trọng. Dataset không có confidence hay chất lượng đáp án; cần đánh giá chất lượng trước khi áp dụng. 5% là giả định chính sách mới, không phải số BTC đo sẵn.

## Extension 5: Carbon-aware scheduling

Giả định: các job interruptible có thể di chuyển từ us-east-1, GPU chạy ở công suất định mức trong catalog; năng lượng = watts × hours_per_day × days × num_gpus. Dùng days thật của job, không ngoại suy tất cả thành 30 ngày như M3.

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

Sạch nhất: europe-north1. Điện rẻ nhất: us-east-wa; đây là phương án cân bằng cần cân nhắc nếu ưu tiên tiền điện. Không có một vùng đồng thời rẻ nhất và sạch nhất trong bảng BTC.

Chi phí điện tách khỏi tiền thuê GPU, không cộng vào savings M5 vì có thể đã nằm trong giá thuê. Chưa tính PUE, idle, checkpoint overhead, egress, thời gian chuyển dữ liệu, availability, latency và data residency. Region hiện tại là giả định vì workloads.csv không có cột region.

Tái lập: `python missions/your_turn.py`; kết quả máy đọc được: `outputs/extensions_results.json`.
