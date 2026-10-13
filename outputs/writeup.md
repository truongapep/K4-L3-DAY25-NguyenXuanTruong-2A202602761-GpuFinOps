# GPU FinOps — Bài phân tích ngắn

**Học viên:** Nguyễn Xuân Trường — 2A202602761. **Nguồn:** dữ liệu mô phỏng của đề bài, seed=25, snapshot 06/2026.

## 1. Mốc tham chiếu và kết quả

Trong bài này, tôi sử dụng dữ liệu và đơn giá đề bài cung cấp, giữ kết quả M1–M5 làm mốc. M2 có 7,533,027 token/ngày: chi phí giảm từ $48.87 xuống $8.48/ngày, tương ứng $6.488 xuống $1.126/1M-token, tiết kiệm 82.6%. M5 giảm từ $27,133 xuống $14,626/tháng, tiết kiệm $12,507 (46.1%). Tôi dùng các kết quả này để phân tích theo yêu cầu bài.

Tôi trình bày $/1M-token cho inference ở M2 và chi phí tháng cho M5. M5 có thêm training/dev nên chưa thể dùng token M2 làm mẫu số chung. Mốc ban đầu lưu trong `baseline_reference.json`; hai extension có kết quả riêng.

## 2. Vì sao tiết kiệm được?

Theo kết quả, chọn cách thuê GPU tiết kiệm nhiều nhất: $10,040/tháng, chiếm 80.3% tổng tiền tiết kiệm. Job có thể gián đoạn dùng spot với checkpoint, job ổn định dùng reserved. M3 tiết kiệm 39.1%. Tôi ưu tiên biện pháp này vì tiền thuê GPU chiếm phần lớn chi phí ban đầu.

Inference tiết kiệm $1,212/tháng. Tôi tính lần lượt cascade → cache → batch, được $37.3985, $1.1965, $1.7946/ngày. Cascade dùng model nhỏ cho request đã gán tier small; cache giảm giá input đã lưu; batch giảm giá request không cần trả lời ngay. Chiết khấu nhân nhau nên mức đóng góp phụ thuộc thứ tự tính.

M1 chỉ ra hai GPU có util cao nhưng MFU thấp: `gpu-h100-4` và `gpu-a10g-1` (số liệu ở bảng M1 trong report.md). Tôi hiểu util cao là GPU hoạt động nhiều, chưa đồng nghĩa hiệu quả tính toán cao. Chờ bộ nhớ hoặc khởi chạy kernel có thể gây chênh lệch này. M5 ước tính đổi sang GPU nhỏ hơn tiết kiệm $655/tháng; tắt GPU idle tiết kiệm $600/tháng. Khi áp dụng thật cần kiểm tra throughput và VRAM.

## 3. Hai extension trên dữ liệu đề bài cung cấp

**Ngân sách reasoning:** Tôi tách traffic theo is_reasoning. Có 201 request reasoning, chiếm 8.38% request, 16.46% chi phí và 94.04% năng lượng theo công thức của đề bài. Tôi thử giới hạn 5%, chuyển 81 request có output dài nhất sang xử lý thường. Giả định output giảm 6 lần theo hệ số generator, tiết kiệm $0.6804/ngày và 15770.08 Wh/ngày. Giữ nguyên output thì không tiết kiệm USD, chỉ giảm 15650.65 Wh theo mô hình. Nhận xét của tôi là cần giới hạn reasoning theo nhu cầu tác vụ; dữ liệu hiện chưa có điểm chất lượng để kiểm chứng việc chuyển request.

**Carbon-aware scheduling:** Tôi tính năng lượng bằng công suất GPU nhân số giờ chạy, số ngày và số GPU cho 5 job có thể gián đoạn. Tổng là 1789.00 kWh. Giả định chuyển từ us-east-1 sang europe-north1, carbon giảm từ 679.820 xuống 53.670 kgCO2e, tiết kiệm 626.150 kg (92.11%). europe-north1 sạch nhất, us-east-wa có điện rẻ nhất. Tôi ghi riêng tiền điện vì giá thuê GPU có thể đã bao gồm khoản này. Phép tính dùng công suất định mức, chưa tính truyền dữ liệu và độ trễ.

## 4. Ba hành động ưu tiên và giới hạn

1. Kiểm tra thời gian sử dụng và thời hạn job để chọn spot hoặc reserved, vì đây là phần tiết kiệm lớn nhất.
2. Dùng cascade/cache/batch theo yêu cầu chất lượng và độ trễ, tắt GPU idle và theo dõi $/1M-token.
3. Bổ sung tag (coverage hiện 91.8%, làm tròn 92%), đặt ngân sách team, giới hạn reasoning và chọn vùng chạy phù hợp.

Tôi giữ mô hình M3 dùng 30 ngày cho mọi job; extension carbon dùng days của từng job. Mức 46.1% là dự kiến theo mô hình của đề bài, cần kiểm tra phần tiết kiệm trùng nhau trước khi áp dụng thật. Hai extension không cộng vào tỷ lệ này. Có thể chạy `python missions/run_all.py`, `python verify.py`, `pytest -q` để đối chiếu. Chi tiết phép tính, nguồn và log kiểm tra nằm trong `report.md`, `extensions_report.md`, `extensions_results.json` và `verification.txt`.
