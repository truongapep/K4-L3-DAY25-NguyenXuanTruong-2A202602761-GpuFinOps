"""Build reproducible analysis and a short Vietnamese write-up for M5."""
from pathlib import Path
from finops import pricing, sustainability
from missions._common import ROOT, load_csv
from missions.m2_inference_levers import MODEL_PRICES
from missions import your_turn, m4_allocation


def inference_stages():
    totals = [0.0] * 4
    for r in load_csv("token_usage.csv"):
        inp, out = int(r["input_tokens"]), int(r["output_tokens"])
        pin, pout = MODEL_PRICES[r["route_tier"]]
        totals[0] += pricing.request_cost(inp, out, *MODEL_PRICES["large"])
        totals[1] += pricing.request_cost(inp, out, pin, pout)
        totals[2] += pricing.request_cost(inp, out, pin, pout, cached_in=int(r["cached_input_tokens"]))
        totals[3] += pricing.request_cost(inp, out, pin, pout, cached_in=int(r["cached_input_tokens"]), batch=bool(int(r["is_batch"])))
    return totals


def build_analysis(r1, r2, r3, baseline, optimized, levers):
    ext = your_turn.run(verbose=False)
    allocation = m4_allocation.run(verbose=False)
    stages = inference_stages()
    savings = sum(levers.values())
    lines = ["", "## Phạm vi và mốc tham chiếu BTC", "",
             "Dữ liệu tổng hợp seed=25 và bảng giá snapshot 06/2026 của BTC. Không đo trên GPU/cloud thật. Mốc gốc lưu tại `baseline_reference.json`; hai extension được tính riêng, không sửa dữ liệu đầu vào hoặc cộng vào tổng savings M5.", "",
             f"M2 giữ nguyên {r2['total_tokens']:,} token/ngày: **${r2['baseline_per_m']:.3f} → ${r2['optimized_per_m']:.3f}/1M-token**, giảm **{r2['savings_pct']:.1f}%**. M5 giảm tổng chi phí tháng **{savings/baseline*100:.1f}%**. Đây là hai phạm vi khác nhau.", "",
             "Không chia toàn bộ tiền M5 cho token M2: M5 gồm cả training/dev trong workloads.csv, còn token_usage.csv chỉ phản ánh traffic inference. Chưa có sản lượng token tương ứng cho toàn bộ workload để xác định unit cost tổng hợp đáng tin cậy.", "",
             "## Phân tích từng biện pháp", "",
             "| Biện pháp M5 | USD/tháng | Tỷ trọng tổng savings |", "|---|---:|---:|"]
    for name, value in levers.items():
        lines.append(f"| {name} | {value:,.0f} | {value/savings*100:.2f}% |")
    lines += ["", f"Purchasing lớn nhất: chuyển job interruptible sang spot (có overhead checkpoint/rework), workload ổn định sang reserved. M3: ${r3['on_demand_monthly']:,} → ${r3['optimized_monthly']:,}/tháng, giảm {r3['savings_pct']:.1f}%. Mức đóng góp lớn vì bucket thuê GPU lớn hơn nhiều so với chi phí request.", "",
              "### Tách các biện pháp inference", "",
              "Giữ cùng request/token và áp dụng theo thứ tự cascade → cache → batch:", "",
              "| Bước | USD/ngày | Savings thêm USD/ngày |", "|---|---:|---:|",
              f"| Large model, không cache/batch | {stages[0]:.6f} | — |"]
    for i, name in enumerate(("Cascade theo route_tier", "Thêm prompt cache", "Thêm batch"), 1):
        lines.append(f"| {name} | {stages[i]:.6f} | {stages[i-1]-stages[i]:.6f} |")
    lines += ["", "Cascade giảm đơn giá bằng model nhỏ cho request đã được BTC gán tier small. Cache giảm 90% giá phần input được cache; batch giảm 50% cả request đủ điều kiện. Mức đóng góp phụ thuộc thứ tự phân rã vì chiết khấu nhân nhau; bảng không phải ba mức savings độc lập để cộng thêm vào M5. Bảng dùng số chưa làm tròn; M5 dùng daily cost làm tròn cents và savings làm tròn USD, nên có chênh lệch làm tròn nhỏ. M2 chưa có phép đo chất lượng/latency để kiểm chứng routing ngoài mô phỏng.", "",
              "### GPU-Util lie và idle", "",
              "| GPU | Util % | MFU % | MBU % |", "|---|---:|---:|---:|"]
    for lie in r1["lies"]:
        lines.append(f"| {lie['gpu_id']} | {lie['gpu_util_pct']:.1f} | {lie['mfu']*100:.1f} | {lie['mbu']*100:.1f} |")
    lines += ["", "Util cao chỉ phản ánh thời gian GPU hoạt động, chưa phản ánh FLOPs hữu ích. Memory stalls, kernel launch overhead hoặc xử lý không dùng tensor cores có thể giải thích chênh lệch; dữ liệu tổng hợp chưa đủ xác định nguyên nhân thực tế. Không được hiểu MFU 20% là 80% hóa đơn có thể thu hồi ngay.", "",
              f"M5 dùng mapping H100→A100 và A10G→L4 để ước tính right-sizing ${levers['Right-size util-lies']:,}/tháng. gpu-h100-5 có 8 giờ idle/ngày: 8 × $2.50 = ${r1['idle_waste_daily']:.0f}/ngày, tương đương ${levers['Kill idle GPUs']:,}/tháng. Cần đo throughput, VRAM và chất lượng trước khi hạ GPU.", "",
              "## Phân bổ và tính bền vững", "",
              f"Tag coverage {allocation['tag_coverage']:.1%}; đạt gate 80% của lab để chargeback. FOCUS export là 50 dòng mẫu. Team assistant có chi phí lớn nhất trong dữ liệu hiện tại; vẫn cần hoàn thiện tag project thiếu để giảm tranh chấp phân bổ.", "",
              "Snapshot M5 dùng query giả định 800 token: 0.24 Wh và 0.091 gCO2e ở us-east-1. Đây không phải năng lượng trung bình đã đo của 2,400 request. europe-north1 sạch nhất theo bảng BTC; us-east-wa có giá điện thấp nhất.", "",
              "## Hai extension và kết quả riêng", "",
              "Xem [extensions_report.md](extensions_report.md) và `extensions_results.json` để kiểm tra toàn bộ nhóm traffic, từng job, năm vùng và các giả định.", "",
              f"- Reasoning cap 5%: chuyển {ext['reasoning']['rerouted_requests']} request; ước tính giảm ${ext['reasoning']['saved_cost_usd']:.4f}/ngày và {ext['reasoning']['saved_energy_wh']:.2f} Wh/ngày khi giả định output giảm 6 lần. Giữ output không đổi: USD savings = 0, Wh savings = {ext['reasoning']['same_token_saved_energy_wh']:.2f}. Chưa kiểm chứng chất lượng.",
              f"- Carbon-aware: {len(ext['carbon']['jobs'])} job interruptible, chuyển us-east-1→europe-north1; giảm {ext['carbon']['saved_carbon_g']/1000:.3f} kgCO2e ({ext['carbon']['saved_carbon_pct']:.2f}%) trên thời lượng days thực của job. Tiền điện tách khỏi giá thuê GPU.", "",
              "## Ba hành động ưu tiên cho NimbusAI", "",
              "1. Kiểm tra duty cycle và thời hạn cam kết; áp dụng spot + checkpoint cho job interruptible, reserved cho nhu cầu ổn định. Purchasing có savings lớn nhất nhưng cần kiểm chứng interruption rate và cam kết thật.",
              "2. Áp dụng cascade/cache/batch theo nhu cầu chất lượng và latency; theo dõi $/1M-token. Tự động tắt idle ngoài giờ và thử nghiệm right-sizing với throughput/VRAM trước khi triển khai rộng.",
              "3. Hoàn thiện tag và budget theo team, đặt soft cap reasoning, ưu tiên vùng sạch cho job batch có thể chuyển. Đánh giá chất lượng, latency, egress và data residency trước khi quyết định.", "",
              "## Giới hạn mô hình và cách tái lập", "",
              "M3 quy đổi mọi job thành 30 ngày dù CSV có days khác nhau; extension carbon dùng days thật. M5 cộng các bucket/lever đơn giản, chưa chứng minh telemetry fleet và workloads là các tài nguyên tách biệt, chưa loại trừ savings chồng lặp giữa purchasing/right-sizing/idle. 46.1% là projected savings theo mô hình BTC, không phải hóa đơn thực đã giảm.", "",
              "Giữ baseline và thông số BTC để so sánh; không thêm savings extension vào M5. Chạy `python missions/run_all.py`, `python verify.py`, `pytest -q` (15 test gốc). Chạy riêng `python -m pytest -q validation/check_extensions.py` (4 test bổ sung). M5 tự tái tạo phân tích, write-up và đầu ra extension; sửa report thủ công có thể bị ghi đè. Bài viết ngắn: [writeup.md](writeup.md).", "",
              "## File code cần nộp cùng repo", "",
              "Extension 4 tích hợp tại `missions/m2_inference_levers.py` (reasoning_analysis) và M5. Extension 5 chạy tại `missions/your_turn.py` (file mới được đề cho phép). Logic tính dùng `finops/extensions.py`; M5 dùng `missions/submission.py` để tạo phân tích/write-up. Cần nộp các file code này cùng repo, không chỉ các file Markdown. `validation/check_extensions.py` và `outputs/baseline_reference.json` dùng kiểm tra riêng. README và các tài liệu yêu cầu BTC giữ nguyên."]
    write_short(r1, r2, r3, baseline, optimized, levers, ext, stages)
    return "\n".join(lines) + "\n"


def write_short(r1, r2, r3, baseline, optimized, levers, ext, stages):
    r, c = ext["reasoning"], ext["carbon"]
    g = r["groups"]["reasoning"]
    md = f"""# GPU FinOps — Bài phân tích ngắn

**Học viên:** Nguyễn Xuân Trường — 2A202602761. **Nguồn:** dữ liệu mô phỏng BTC, seed=25, snapshot 06/2026.

## 1. Mốc tham chiếu và kết quả

Giữ nguyên dữ liệu, đơn giá và logic M1–M5 của BTC làm mốc. M2 phục vụ {r2['total_tokens']:,} token/ngày: chi phí $48.87 xuống $8.48/ngày, tương ứng ${r2['baseline_per_m']:.3f} xuống ${r2['optimized_per_m']:.3f}/1M-token, giảm {r2['savings_pct']:.1f}%. M5 tổng hợp ${baseline:,.0f} xuống ${optimized:,.0f}/tháng, giảm ${sum(levers.values()):,} ({sum(levers.values())/baseline*100:.1f}%). Các khoản này là ước tính của mô hình lab, không phải hóa đơn cloud thực tế.

M2 đo unit cost inference với cùng số token; M5 còn chứa training/dev. Không lấy token M2 làm mẫu số cho toàn bộ chi phí M5 vì chưa có sản lượng tương ứng của tất cả workload. Mốc gốc được lưu trong `baseline_reference.json`, extension được ghi riêng.

## 2. Vì sao tiết kiệm được?

Purchasing đóng góp ${levers['Purchasing (spot/reserved)']:,}/tháng, khoảng {levers['Purchasing (spot/reserved)']/sum(levers.values())*100:.1f}% tổng savings, lớn nhất do chi phí thuê GPU chiếm phần lớn baseline. Job có thể gián đoạn dùng spot với checkpoint/rework; job ổn định dùng reserved. M3 tiết kiệm {r3['savings_pct']:.1f}%. Cam kết reserved cần xét thời hạn thật của job, không chỉ duty cycle.

Inference tiết kiệm ${levers['Inference (cascade/cache/batch)']:,}/tháng. Phân rã theo thứ tự cascade→cache→batch: giảm lần lượt ${stages[0]-stages[1]:.4f}, ${stages[1]-stages[2]:.4f}, ${stages[2]-stages[3]:.4f}/ngày. Cascade dùng model nhỏ cho route đã gán; cache chỉ giảm giá input được cache; batch giảm giá request chịu được độ trễ. Chiết khấu nhân nhau nên đóng góp thay đổi nếu đổi thứ tự phân rã.

`gpu-h100-4` có util 98.2% nhưng MFU 19.4%; `gpu-a10g-1` có util 96.9% nhưng MFU 26.8%. Util đo thời gian hoạt động, MFU đo FLOPs hữu ích so với peak. Memory stalls hoặc overhead có thể khiến GPU bận nhưng hiệu quả thấp; dữ liệu chưa đủ kết luận nguyên nhân. M5 ước tính right-sizing ${levers['Right-size util-lies']:,}/tháng bằng mapping có sẵn. `gpu-h100-5` idle 8 giờ/ngày, lãng phí $20/ngày, tức $600/tháng. Cần kiểm tra throughput và VRAM trước khi đổi GPU.

## 3. Hai extension trên dữ liệu BTC

**Ngân sách reasoning:** {g['requests']} request reasoning chiếm {g['traffic_pct']:.2f}% traffic, {g['cost_pct']:.2f}% chi phí và {g['energy_pct']:.2f}% năng lượng ước tính. Công thức BTC nhân năng lượng reasoning 80 lần ở cùng số token; flag reasoning không tự tăng đơn giá tiền. Cap 5% chuyển {r['rerouted_requests']} request có output dài nhất sang xử lý thường. Nếu output giảm 6 lần (đảo hệ số generator), giảm ${r['saved_cost_usd']:.4f}/ngày và {r['saved_energy_wh']:.2f} Wh/ngày. Giữ nguyên output thì không giảm USD, chỉ giảm {r['same_token_saved_energy_wh']:.2f} Wh theo mô hình. Chưa có confidence/chất lượng để xác thực routing; cap là kịch bản chính sách, không phải kết quả triển khai thực.

**Carbon-aware scheduling:** tính watts × GPU-hours với days thật cho {len(c['jobs'])} job interruptible. Tổng năng lượng {c['total_energy_wh']/1000:.2f} kWh. Chuyển từ us-east-1 sang europe-north1 giảm carbon từ {c['baseline_carbon_g']/1000:.3f} xuống {c['cleanest_carbon_g']/1000:.3f} kgCO2e, tiết kiệm {c['saved_carbon_g']/1000:.3f} kg ({c['saved_carbon_pct']:.2f}%). europe-north1 sạch nhất; us-east-wa có điện rẻ nhất và là lựa chọn cân bằng nếu ưu tiên chi phí. Giả định công suất định mức và job có thể di chuyển; chưa tính egress, PUE, checkpoint, latency hay quy định dữ liệu. Tiền điện không cộng thêm vào savings giá thuê GPU.

## 4. Ba hành động ưu tiên và giới hạn

1. Rà soát duty cycle/thời hạn, ưu tiên spot + checkpoint và reserved phù hợp vì purchasing có tác động lớn nhất.
2. Triển khai cascade/cache/batch có kiểm tra chất lượng và latency; tắt idle, thử right-sizing, theo dõi $/1M-token.
3. Hoàn thiện tag (hiện coverage 92%), ngân sách team, cap reasoning có ngoại lệ, chuyển job linh hoạt sang vùng sạch sau khi kiểm tra ràng buộc.

M3 dùng 30 ngày cho mọi job; carbon dùng days thực. M5 chưa loại trừ khả năng overlap giữa fleet/workloads và các lever; 46.1% là dự báo của mô hình BTC. Hai extension không cộng vào tỷ lệ này. Kết quả tái lập bằng `python missions/run_all.py`; kiểm tra bằng `python verify.py` và `pytest -q`. Chi tiết: `report.md`, `extensions_report.md`, `extensions_results.json`.
"""
    (Path(ROOT) / "outputs" / "writeup.md").write_text(md, encoding="utf-8")
