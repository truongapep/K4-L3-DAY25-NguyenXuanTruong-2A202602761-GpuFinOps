# GPU FinOps — Bài phân tích ngắn

**Học viên:** Nguyễn Xuân Trường — 2A202602761. **Nguồn:** dữ liệu mô phỏng BTC, seed=25, snapshot 06/2026.

## 1. Mốc tham chiếu và kết quả

Giữ nguyên dữ liệu, đơn giá và logic M1–M5 của BTC làm mốc. M2 phục vụ 7,533,027 token/ngày: chi phí $48.87 xuống $8.48/ngày, tương ứng $6.488 xuống $1.126/1M-token, giảm 82.6%. M5 tổng hợp $27,133 xuống $14,626/tháng, giảm $12,507 (46.1%). Các khoản này là ước tính của mô hình lab, không phải hóa đơn cloud thực tế.

M2 đo unit cost inference với cùng số token; M5 còn chứa training/dev. Không lấy token M2 làm mẫu số cho toàn bộ chi phí M5 vì chưa có sản lượng tương ứng của tất cả workload. Mốc gốc được lưu trong `baseline_reference.json`, extension được ghi riêng.

## 2. Vì sao tiết kiệm được?

Purchasing đóng góp $10,040/tháng, khoảng 80.3% tổng savings, lớn nhất do chi phí thuê GPU chiếm phần lớn baseline. Job có thể gián đoạn dùng spot với checkpoint/rework; job ổn định dùng reserved. M3 tiết kiệm 39.1%. Cam kết reserved cần xét thời hạn thật của job, không chỉ duty cycle.

Inference tiết kiệm $1,212/tháng. Phân rã theo thứ tự cascade→cache→batch: giảm lần lượt $37.3985, $1.1965, $1.7946/ngày. Cascade dùng model nhỏ cho route đã gán; cache chỉ giảm giá input được cache; batch giảm giá request chịu được độ trễ. Chiết khấu nhân nhau nên đóng góp thay đổi nếu đổi thứ tự phân rã.

`gpu-h100-4` có util 98.2% nhưng MFU 19.4%; `gpu-a10g-1` có util 96.9% nhưng MFU 26.8%. Util đo thời gian hoạt động, MFU đo FLOPs hữu ích so với peak. Memory stalls hoặc overhead có thể khiến GPU bận nhưng hiệu quả thấp; dữ liệu chưa đủ kết luận nguyên nhân. M5 ước tính right-sizing $655/tháng bằng mapping có sẵn. `gpu-h100-5` idle 8 giờ/ngày, lãng phí $20/ngày, tức $600/tháng. Cần kiểm tra throughput và VRAM trước khi đổi GPU.

## 3. Hai extension trên dữ liệu BTC

**Ngân sách reasoning:** 201 request reasoning chiếm 8.38% traffic, 16.46% chi phí và 94.04% năng lượng ước tính. Công thức BTC nhân năng lượng reasoning 80 lần ở cùng số token; flag reasoning không tự tăng đơn giá tiền. Cap 5% chuyển 81 request có output dài nhất sang xử lý thường. Nếu output giảm 6 lần (đảo hệ số generator), giảm $0.6804/ngày và 15770.08 Wh/ngày. Giữ nguyên output thì không giảm USD, chỉ giảm 15650.65 Wh theo mô hình. Chưa có confidence/chất lượng để xác thực routing; cap là kịch bản chính sách, không phải kết quả triển khai thực.

**Carbon-aware scheduling:** tính watts × GPU-hours với days thật cho 5 job interruptible. Tổng năng lượng 1789.00 kWh. Chuyển từ us-east-1 sang europe-north1 giảm carbon từ 679.820 xuống 53.670 kgCO2e, tiết kiệm 626.150 kg (92.11%). europe-north1 sạch nhất; us-east-wa có điện rẻ nhất và là lựa chọn cân bằng nếu ưu tiên chi phí. Giả định công suất định mức và job có thể di chuyển; chưa tính egress, PUE, checkpoint, latency hay quy định dữ liệu. Tiền điện không cộng thêm vào savings giá thuê GPU.

## 4. Ba hành động ưu tiên và giới hạn

1. Rà soát duty cycle/thời hạn, ưu tiên spot + checkpoint và reserved phù hợp vì purchasing có tác động lớn nhất.
2. Triển khai cascade/cache/batch có kiểm tra chất lượng và latency; tắt idle, thử right-sizing, theo dõi $/1M-token.
3. Hoàn thiện tag (hiện coverage 92%), ngân sách team, cap reasoning có ngoại lệ, chuyển job linh hoạt sang vùng sạch sau khi kiểm tra ràng buộc.

M3 dùng 30 ngày cho mọi job; carbon dùng days thực. M5 chưa loại trừ khả năng overlap giữa fleet/workloads và các lever; 46.1% là dự báo của mô hình BTC. Hai extension không cộng vào tỷ lệ này. Kết quả tái lập bằng `python missions/run_all.py`; kiểm tra bằng `python verify.py` và `pytest -q`. Chi tiết: `report.md`, `extensions_report.md`, `extensions_results.json`.
