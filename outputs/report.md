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

## Phạm vi và mốc tham chiếu theo đề bài

Trong bài này, tôi sử dụng dữ liệu và bảng giá tháng 06/2026 đề bài cung cấp, seed=25. Tôi giữ kết quả M1–M5 làm mốc trong `baseline_reference.json`, sau đó tính riêng hai extension. Số liệu trong báo cáo được tính trên dữ liệu mô phỏng của bài lab.

M2 giữ nguyên 7,533,027 token/ngày: **$6.488 → $1.126/1M-token**, giảm **82.6%**. M5 giảm tổng chi phí tháng **46.1%**. Đây là hai phạm vi khác nhau.

Tôi dùng $/1M-token của M2 để đánh giá chi phí inference. M5 có thêm chi phí training và dev, trong khi token_usage.csv chỉ chứa request inference. Vì vậy, tôi trình bày riêng chi phí tháng của M5 để không dùng sai mẫu số.

## Phân tích từng biện pháp

| Biện pháp M5 | Tiết kiệm USD/tháng | Tỷ trọng tiền tiết kiệm |
|---|---:|---:|
| Inference (cascade/cache/batch) | 1,212 | 9.69% |
| Purchasing (spot/reserved) | 10,040 | 80.28% |
| Right-size util-lies | 655 | 5.24% |
| Kill idle GPUs | 600 | 4.80% |

Biện pháp tiết kiệm nhiều nhất là chọn cách thuê GPU. Job có thể gián đoạn dùng spot, có tính chi phí checkpoint và chạy lại phần bị mất; job ổn định dùng reserved. M3 giảm từ $25,667 xuống $15,627/tháng, tương đương 39.1%. Tiền thuê GPU chiếm phần lớn chi phí ban đầu nên biện pháp này đóng góp nhiều nhất.

### Tách các biện pháp inference

Giữ cùng request/token và áp dụng theo thứ tự cascade → cache → batch:

| Bước | USD/ngày | Tiết kiệm thêm USD/ngày |
|---|---:|---:|
| Large model, không cache/batch | 48.874161 | — |
| Cascade theo route_tier | 11.475643 | 37.398518 |
| Thêm prompt cache | 10.279188 | 1.196455 |
| Thêm batch | 8.484623 | 1.794565 |

Cascade chuyển request được gán route_tier=small sang model rẻ hơn. Cache giảm 90% giá phần input đã lưu; batch giảm 50% giá request đủ điều kiện. Tôi tính theo thứ tự cascade → cache → batch, nên mức đóng góp phụ thuộc thứ tự này. Bảng dùng số chưa làm tròn; M5 làm tròn chi phí ngày đến cent và tiền tiết kiệm đến USD. Ba khoản trên đã nằm trong phần inference của M5.

### GPU-Util lie và idle

| GPU | Util % | MFU % | MBU % |
|---|---:|---:|---:|
| gpu-h100-4 | 98.2 | 19.4 | 20.7 |
| gpu-a10g-1 | 96.9 | 26.8 | 30.2 |

Qua M1, tôi thấy GPU-Util cao chưa đủ để kết luận GPU chạy hiệu quả. Util phản ánh thời gian hoạt động, còn MFU phản ánh FLOPs đạt được so với mức đỉnh. GPU có thể chờ bộ nhớ hoặc mất thời gian khởi chạy kernel. Đây là các nguyên nhân có thể xảy ra; dữ liệu của bài chưa đủ xác định nguyên nhân cụ thể.

M5 dùng mapping H100→A100 và A10G→L4 để ước tính right-sizing $655/tháng. gpu-h100-5 có 8 giờ idle/ngày: 8 × $2.50 = $20/ngày, tương đương $600/tháng. Cần đo throughput, VRAM và chất lượng trước khi hạ GPU.

## Phân bổ và tính bền vững

M4 có tag coverage 91.8%, làm tròn khi in terminal là 92%. Kết quả vượt ngưỡng 80% để chargeback trong lab. FOCUS export gồm 50 dòng mẫu. Team có chi phí cao nhất là assistant; tôi đề xuất bổ sung các tag project còn thiếu.

M5 dùng một truy vấn giả định 800 token để tính 0.24 Wh và 0.091 gCO2e tại us-east-1. Con số này không phải trung bình của 2,400 request. Dòng Cheapest+cleanest region ở đầu báo cáo giữ nhãn có sẵn trong đề bài; theo bảng giá điện, europe-north1 sạch nhất còn us-east-wa có điện rẻ nhất. Bảng so sánh năm vùng nằm trong báo cáo extension.

## Hai extension và kết quả riêng

Xem [extensions_report.md](extensions_report.md) và `extensions_results.json` để kiểm tra toàn bộ nhóm traffic, từng job, năm vùng và các giả định.

- Reasoning cap 5%: chuyển 81 request; ước tính giảm $0.6804/ngày và 15770.08 Wh/ngày khi giả định output giảm 6 lần. Giữ output không đổi: USD savings = 0, Wh savings = 15650.65. Chưa kiểm chứng chất lượng.
- Carbon-aware: 5 job interruptible, chuyển us-east-1→europe-north1; giảm 626.150 kgCO2e (92.11%) trên thời lượng days thực của job. Tiền điện tách khỏi giá thuê GPU.

## Ba hành động ưu tiên cho NimbusAI

1. Kiểm tra thời gian sử dụng và thời hạn job để chọn spot hoặc reserved. Tôi ưu tiên việc này vì phần thuê GPU tiết kiệm nhiều nhất.
2. Dùng cascade/cache/batch theo yêu cầu chất lượng và độ trễ, theo dõi $/1M-token. Tắt GPU ngoài giờ chạy và kiểm tra throughput, VRAM trước khi đổi loại GPU.
3. Bổ sung tag, đặt ngân sách theo team và giới hạn reasoning cho tác vụ cần thiết. Với job có thể chuyển vùng, so sánh giá điện, carbon và chi phí truyền dữ liệu trước khi quyết định.

## Giới hạn mô hình và cách tái lập

Tôi giữ cách tính theo đề bài: M3 quy đổi mọi job thành 30 ngày, còn extension carbon dùng days của từng job. M5 cộng các khoản tiết kiệm nhưng chưa kiểm tra tài nguyên có trùng nhau giữa telemetry và workloads hay không. Vì vậy, 46.1% là mức tiết kiệm dự kiến theo mô hình lab. Khi áp dụng thật cần kiểm tra phần tiết kiệm có bị tính trùng, chất lượng đáp án và độ trễ.

Giữ baseline và thông số của đề bài để so sánh; không thêm savings extension vào M5. Chạy `python missions/run_all.py`, `python verify.py`, `pytest -q` (15 test gốc). Chạy riêng `python -m pytest -q validation/check_extensions.py` (4 test bổ sung). M5 tự tái tạo phân tích, write-up và đầu ra extension; sửa report thủ công có thể bị ghi đè. Bài viết ngắn: [writeup.md](writeup.md).

## Nguồn số liệu để đối chiếu

| Nội dung | Dữ liệu đầu vào | Code tính / bằng chứng |
|---|---|---|
| MFU, MBU, idle | gpu_telemetry.csv + price_catalog.csv | M1; finops/metrics.py; baseline_reference.json → M1 |
| Chi phí và $/1M-token | token_usage.csv | M2; finops/pricing.py; baseline_reference.json → M2 |
| Cascade → cache → batch | token_usage.csv | missions/submission.py → inference_stages() |
| Spot/reserved | workloads.csv + price_catalog.csv | M3; baseline_reference.json → M3 |
| Tổng tháng và bốn biện pháp | Kết quả M1–M3 | M5; baseline_reference.json → M5; savings.png |
| Chi phí theo team | token_usage.csv | M4; focus_export.csv (50 dòng mẫu) |
| Extension 4: reasoning | token_usage.csv | M2 → reasoning_analysis(); extensions_results.json → reasoning |
| Extension 5: carbon | workloads.csv + price_catalog.csv | your_turn.py; extensions_results.json → carbon |

Hai extension dùng hàm trong `finops/extensions.py`. `missions/submission.py` tạo phân tích và bài viết; `missions/your_turn.py` xuất số liệu JSON và báo cáo extension. Các file code được nộp cùng repo. README, dữ liệu đề bài cung cấp và test gốc giữ nguyên.

Có thể chạy lại các lệnh sau từ thư mục repo:

```powershell
python missions/run_all.py
python verify.py
python -m pytest -q
python -m pytest -q validation/check_extensions.py
```

Kết quả cần đạt: 11/11 checks, 15 test gốc và 4 test bổ sung. Test bổ sung so sánh từng kết quả M1–M5 với baseline_reference.json, kiểm tra USD/Wh, số request sau cap và tổng carbon từng job. Log lần kiểm tra báo cáo: [verification.txt](verification.txt).
