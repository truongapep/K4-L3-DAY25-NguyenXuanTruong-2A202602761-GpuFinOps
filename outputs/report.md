# NimbusAI — GPU Cost Optimization Report

**Period:** monthly  
**Baseline spend:** $27,133  
**Optimized spend:** $14,626  
**Projected savings:** $12,507  (**46%**)

## Savings by lever

| Lever | Savings (USD) |
|---|---|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

## Sustainability

- Energy per query: 0.24 Wh
- Carbon per query: 0.091 gCO2e
- Cheapest+cleanest region: europe-north1

_Figures are June-2026 as-of snapshots; re-baseline before acting._
## Phạm vi và mốc tham chiếu BTC

Dữ liệu tổng hợp seed=25 và bảng giá snapshot 06/2026 của BTC. Không đo trên GPU/cloud thật. Mốc gốc lưu tại `baseline_reference.json`; hai extension được tính riêng, không sửa dữ liệu đầu vào hoặc cộng vào tổng savings M5.

M2 giữ nguyên 7,533,027 token/ngày: **$6.488 → $1.126/1M-token**, giảm **82.6%**. M5 giảm tổng chi phí tháng **46.1%**. Đây là hai phạm vi khác nhau.

Không chia toàn bộ tiền M5 cho token M2: M5 gồm cả training/dev trong workloads.csv, còn token_usage.csv chỉ phản ánh traffic inference. Chưa có sản lượng token tương ứng cho toàn bộ workload để xác định unit cost tổng hợp đáng tin cậy.

## Phân tích từng biện pháp

| Biện pháp M5 | USD/tháng | Tỷ trọng tổng savings |
|---|---:|---:|
| Inference (cascade/cache/batch) | 1,212 | 9.69% |
| Purchasing (spot/reserved) | 10,040 | 80.28% |
| Right-size util-lies | 655 | 5.24% |
| Kill idle GPUs | 600 | 4.80% |

Purchasing lớn nhất: chuyển job interruptible sang spot (có overhead checkpoint/rework), workload ổn định sang reserved. M3: $25,667 → $15,627/tháng, giảm 39.1%. Mức đóng góp lớn vì bucket thuê GPU lớn hơn nhiều so với chi phí request.

### Tách các biện pháp inference

Giữ cùng request/token và áp dụng theo thứ tự cascade → cache → batch:

| Bước | USD/ngày | Savings thêm USD/ngày |
|---|---:|---:|
| Large model, không cache/batch | 48.874161 | — |
| Cascade theo route_tier | 11.475643 | 37.398518 |
| Thêm prompt cache | 10.279188 | 1.196455 |
| Thêm batch | 8.484623 | 1.794565 |

Cascade giảm đơn giá bằng model nhỏ cho request đã được BTC gán tier small. Cache giảm 90% giá phần input được cache; batch giảm 50% cả request đủ điều kiện. Mức đóng góp phụ thuộc thứ tự phân rã vì chiết khấu nhân nhau; bảng không phải ba mức savings độc lập để cộng thêm vào M5. Bảng dùng số chưa làm tròn; M5 dùng daily cost làm tròn cents và savings làm tròn USD, nên có chênh lệch làm tròn nhỏ. M2 chưa có phép đo chất lượng/latency để kiểm chứng routing ngoài mô phỏng.

### GPU-Util lie và idle

| GPU | Util % | MFU % | MBU % |
|---|---:|---:|---:|
| gpu-h100-4 | 98.2 | 19.4 | 20.7 |
| gpu-a10g-1 | 96.9 | 26.8 | 30.2 |

Util cao chỉ phản ánh thời gian GPU hoạt động, chưa phản ánh FLOPs hữu ích. Memory stalls, kernel launch overhead hoặc xử lý không dùng tensor cores có thể giải thích chênh lệch; dữ liệu tổng hợp chưa đủ xác định nguyên nhân thực tế. Không được hiểu MFU 20% là 80% hóa đơn có thể thu hồi ngay.

M5 dùng mapping H100→A100 và A10G→L4 để ước tính right-sizing $655/tháng. gpu-h100-5 có 8 giờ idle/ngày: 8 × $2.50 = $20/ngày, tương đương $600/tháng. Cần đo throughput, VRAM và chất lượng trước khi hạ GPU.

## Phân bổ và tính bền vững

Tag coverage 91.8%; đạt gate 80% của lab để chargeback. FOCUS export là 50 dòng mẫu. Team assistant có chi phí lớn nhất trong dữ liệu hiện tại; vẫn cần hoàn thiện tag project thiếu để giảm tranh chấp phân bổ.

Snapshot M5 dùng query giả định 800 token: 0.24 Wh và 0.091 gCO2e ở us-east-1. Đây không phải năng lượng trung bình đã đo của 2,400 request. europe-north1 sạch nhất theo bảng BTC; us-east-wa có giá điện thấp nhất.

## Hai extension và kết quả riêng

Xem [extensions_report.md](extensions_report.md) và `extensions_results.json` để kiểm tra toàn bộ nhóm traffic, từng job, năm vùng và các giả định.

- Reasoning cap 5%: chuyển 81 request; ước tính giảm $0.6804/ngày và 15770.08 Wh/ngày khi giả định output giảm 6 lần. Giữ output không đổi: USD savings = 0, Wh savings = 15650.65. Chưa kiểm chứng chất lượng.
- Carbon-aware: 5 job interruptible, chuyển us-east-1→europe-north1; giảm 626.150 kgCO2e (92.11%) trên thời lượng days thực của job. Tiền điện tách khỏi giá thuê GPU.

## Ba hành động ưu tiên cho NimbusAI

1. Kiểm tra duty cycle và thời hạn cam kết; áp dụng spot + checkpoint cho job interruptible, reserved cho nhu cầu ổn định. Purchasing có savings lớn nhất nhưng cần kiểm chứng interruption rate và cam kết thật.
2. Áp dụng cascade/cache/batch theo nhu cầu chất lượng và latency; theo dõi $/1M-token. Tự động tắt idle ngoài giờ và thử nghiệm right-sizing với throughput/VRAM trước khi triển khai rộng.
3. Hoàn thiện tag và budget theo team, đặt soft cap reasoning, ưu tiên vùng sạch cho job batch có thể chuyển. Đánh giá chất lượng, latency, egress và data residency trước khi quyết định.

## Giới hạn mô hình và cách tái lập

M3 quy đổi mọi job thành 30 ngày dù CSV có days khác nhau; extension carbon dùng days thật. M5 cộng các bucket/lever đơn giản, chưa chứng minh telemetry fleet và workloads là các tài nguyên tách biệt, chưa loại trừ savings chồng lặp giữa purchasing/right-sizing/idle. 46.1% là projected savings theo mô hình BTC, không phải hóa đơn thực đã giảm.

Giữ baseline và thông số BTC để so sánh; không thêm savings extension vào M5. Chạy `python missions/run_all.py`, `python verify.py`, `pytest -q` (15 test gốc). Chạy riêng `python -m pytest -q validation/check_extensions.py` (4 test bổ sung). M5 tự tái tạo phân tích, write-up và đầu ra extension; sửa report thủ công có thể bị ghi đè. Bài viết ngắn: [writeup.md](writeup.md).

## File code cần nộp cùng repo

Extension 4 tích hợp tại `missions/m2_inference_levers.py` (reasoning_analysis) và M5. Extension 5 chạy tại `missions/your_turn.py` (file mới được đề cho phép). Logic tính dùng `finops/extensions.py`; M5 dùng `missions/submission.py` để tạo phân tích/write-up. Cần nộp các file code này cùng repo, không chỉ các file Markdown. `validation/check_extensions.py` và `outputs/baseline_reference.json` dùng kiểm tra riêng. README và các tài liệu yêu cầu BTC giữ nguyên.
