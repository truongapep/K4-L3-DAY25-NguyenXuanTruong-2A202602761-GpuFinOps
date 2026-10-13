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
    lines = ["", "", "## Phạm vi và mốc tham chiếu theo đề bài", "",
             "Trong bài này, tôi sử dụng dữ liệu và bảng giá tháng 06/2026 đề bài cung cấp, seed=25. Tôi giữ kết quả M1–M5 làm mốc trong `baseline_reference.json`, sau đó tính riêng hai extension. Số liệu trong báo cáo được tính trên dữ liệu mô phỏng của bài lab.", "",
             f"M2 giữ nguyên {r2['total_tokens']:,} token/ngày: **${r2['baseline_per_m']:.3f} → ${r2['optimized_per_m']:.3f}/1M-token**, giảm **{r2['savings_pct']:.1f}%**. M5 giảm tổng chi phí tháng **{savings/baseline*100:.1f}%**. Đây là hai phạm vi khác nhau.", "",
             "Tôi dùng $/1M-token của M2 để đánh giá chi phí inference. M5 có thêm chi phí training và dev, trong khi token_usage.csv chỉ chứa request inference. Vì vậy, tôi trình bày riêng chi phí tháng của M5 để không dùng sai mẫu số.", "",
             "## Phân tích từng biện pháp", "",
             "| Biện pháp M5 | Tiết kiệm USD/tháng | Tỷ trọng tiền tiết kiệm |", "|---|---:|---:|"]
    for name, value in levers.items():
        lines.append(f"| {name} | {value:,.0f} | {value/savings*100:.2f}% |")
    lines += ["", f"Biện pháp tiết kiệm nhiều nhất là chọn cách thuê GPU. Job có thể gián đoạn dùng spot, có tính chi phí checkpoint và chạy lại phần bị mất; job ổn định dùng reserved. M3 giảm từ ${r3['on_demand_monthly']:,} xuống ${r3['optimized_monthly']:,}/tháng, tương đương {r3['savings_pct']:.1f}%. Tiền thuê GPU chiếm phần lớn chi phí ban đầu nên biện pháp này đóng góp nhiều nhất.", "",
              "### Tách các biện pháp inference", "",
              "Giữ cùng request/token và áp dụng theo thứ tự cascade → cache → batch:", "",
              "| Bước | USD/ngày | Tiết kiệm thêm USD/ngày |", "|---|---:|---:|",
              f"| Large model, không cache/batch | {stages[0]:.6f} | — |"]
    for i, name in enumerate(("Cascade theo route_tier", "Thêm prompt cache", "Thêm batch"), 1):
        lines.append(f"| {name} | {stages[i]:.6f} | {stages[i-1]-stages[i]:.6f} |")
    lines += ["", "Cascade chuyển request được gán route_tier=small sang model rẻ hơn. Cache giảm 90% giá phần input đã lưu; batch giảm 50% giá request đủ điều kiện. Tôi tính theo thứ tự cascade → cache → batch, nên mức đóng góp phụ thuộc thứ tự này. Bảng dùng số chưa làm tròn; M5 làm tròn chi phí ngày đến cent và tiền tiết kiệm đến USD. Ba khoản trên đã nằm trong phần inference của M5.", "",
              "### GPU-Util lie và idle", "",
              "| GPU | Util % | MFU % | MBU % |", "|---|---:|---:|---:|"]
    for lie in r1["lies"]:
        lines.append(f"| {lie['gpu_id']} | {lie['gpu_util_pct']:.1f} | {lie['mfu']*100:.1f} | {lie['mbu']*100:.1f} |")
    lines += ["", "Qua M1, tôi thấy GPU-Util cao chưa đủ để kết luận GPU chạy hiệu quả. Util phản ánh thời gian hoạt động, còn MFU phản ánh FLOPs đạt được so với mức đỉnh. GPU có thể chờ bộ nhớ hoặc mất thời gian khởi chạy kernel. Đây là các nguyên nhân có thể xảy ra; dữ liệu của bài chưa đủ xác định nguyên nhân cụ thể.", "",
              f"M5 dùng mapping H100→A100 và A10G→L4 để ước tính right-sizing ${levers['Right-size util-lies']:,}/tháng. gpu-h100-5 có 8 giờ idle/ngày: 8 × $2.50 = ${r1['idle_waste_daily']:.0f}/ngày, tương đương ${levers['Kill idle GPUs']:,}/tháng. Cần đo throughput, VRAM và chất lượng trước khi hạ GPU.", "",
              "## Phân bổ và tính bền vững", "",
              f"M4 có tag coverage {allocation['tag_coverage']:.1%}, làm tròn khi in terminal là {allocation['tag_coverage']:.0%}. Kết quả vượt ngưỡng 80% để chargeback trong lab. FOCUS export gồm 50 dòng mẫu. Team có chi phí cao nhất là {max(allocation['by_team'], key=allocation['by_team'].get)}; tôi đề xuất bổ sung các tag project còn thiếu.", "",
              "M5 dùng một truy vấn giả định 800 token để tính 0.24 Wh và 0.091 gCO2e tại us-east-1. Con số này không phải trung bình của 2,400 request. Dòng Cheapest+cleanest region ở đầu báo cáo giữ nhãn có sẵn trong đề bài; theo bảng giá điện, europe-north1 sạch nhất còn us-east-wa có điện rẻ nhất. Bảng so sánh năm vùng nằm trong báo cáo extension.", "",
              "## Hai extension và kết quả riêng", "",
              "Xem [extensions_report.md](extensions_report.md) và `extensions_results.json` để kiểm tra toàn bộ nhóm traffic, từng job, năm vùng và các giả định.", "",
              f"- Reasoning cap 5%: chuyển {ext['reasoning']['rerouted_requests']} request; ước tính giảm ${ext['reasoning']['saved_cost_usd']:.4f}/ngày và {ext['reasoning']['saved_energy_wh']:.2f} Wh/ngày khi giả định output giảm 6 lần. Giữ output không đổi: USD savings = 0, Wh savings = {ext['reasoning']['same_token_saved_energy_wh']:.2f}. Chưa kiểm chứng chất lượng.",
              f"- Carbon-aware: {len(ext['carbon']['jobs'])} job interruptible, chuyển us-east-1→europe-north1; giảm {ext['carbon']['saved_carbon_g']/1000:.3f} kgCO2e ({ext['carbon']['saved_carbon_pct']:.2f}%) trên thời lượng days thực của job. Tiền điện tách khỏi giá thuê GPU.", "",
              "## Ba hành động ưu tiên cho NimbusAI", "",
              "1. Kiểm tra thời gian sử dụng và thời hạn job để chọn spot hoặc reserved. Tôi ưu tiên việc này vì phần thuê GPU tiết kiệm nhiều nhất.",
              "2. Dùng cascade/cache/batch theo yêu cầu chất lượng và độ trễ, theo dõi $/1M-token. Tắt GPU ngoài giờ chạy và kiểm tra throughput, VRAM trước khi đổi loại GPU.",
              "3. Bổ sung tag, đặt ngân sách theo team và giới hạn reasoning cho tác vụ cần thiết. Với job có thể chuyển vùng, so sánh giá điện, carbon và chi phí truyền dữ liệu trước khi quyết định.", "",
              "## Giới hạn mô hình và cách tái lập", "",
              "Tôi giữ cách tính theo đề bài: M3 quy đổi mọi job thành 30 ngày, còn extension carbon dùng days của từng job. M5 cộng các khoản tiết kiệm nhưng chưa kiểm tra tài nguyên có trùng nhau giữa telemetry và workloads hay không. Vì vậy, 46.1% là mức tiết kiệm dự kiến theo mô hình lab. Khi áp dụng thật cần kiểm tra phần tiết kiệm có bị tính trùng, chất lượng đáp án và độ trễ.", "",
              "Giữ baseline và thông số của đề bài để so sánh; không thêm savings extension vào M5. Chạy `python missions/run_all.py`, `python verify.py`, `pytest -q` (15 test gốc). Chạy riêng `python -m pytest -q validation/check_extensions.py` (4 test bổ sung). M5 tự tái tạo phân tích, write-up và đầu ra extension; sửa report thủ công có thể bị ghi đè. Bài viết ngắn: [writeup.md](writeup.md).", "",
              "## Nguồn số liệu để đối chiếu", "",
              "| Nội dung | Dữ liệu đầu vào | Code tính / bằng chứng |", "|---|---|---|",
              "| MFU, MBU, idle | gpu_telemetry.csv + price_catalog.csv | M1; finops/metrics.py; baseline_reference.json → M1 |",
              "| Chi phí và $/1M-token | token_usage.csv | M2; finops/pricing.py; baseline_reference.json → M2 |",
              "| Cascade → cache → batch | token_usage.csv | missions/submission.py → inference_stages() |",
              "| Spot/reserved | workloads.csv + price_catalog.csv | M3; baseline_reference.json → M3 |",
              "| Tổng tháng và bốn biện pháp | Kết quả M1–M3 | M5; baseline_reference.json → M5; savings.png |",
              "| Chi phí theo team | token_usage.csv | M4; focus_export.csv (50 dòng mẫu) |",
              "| Extension 4: reasoning | token_usage.csv | M2 → reasoning_analysis(); extensions_results.json → reasoning |",
              "| Extension 5: carbon | workloads.csv + price_catalog.csv | your_turn.py; extensions_results.json → carbon |", "",
              "Hai extension dùng hàm trong `finops/extensions.py`. `missions/submission.py` tạo phân tích và bài viết; `missions/your_turn.py` xuất số liệu JSON và báo cáo extension. Các file code được nộp cùng repo. README, dữ liệu đề bài cung cấp và test gốc giữ nguyên.", "",
              "Có thể chạy lại các lệnh sau từ thư mục repo:", "", "```powershell",
              "python missions/run_all.py", "python verify.py", "python -m pytest -q",
              "python -m pytest -q validation/check_extensions.py", "```", "",
              "Kết quả cần đạt: 11/11 checks, 15 test gốc và 4 test bổ sung. Test bổ sung so sánh từng kết quả M1–M5 với baseline_reference.json, kiểm tra USD/Wh, số request sau cap và tổng carbon từng job. Log lần kiểm tra báo cáo: [verification.txt](verification.txt)."]
    write_short(r1, r2, r3, baseline, optimized, levers, ext, stages, allocation)
    return "\n".join(lines) + "\n"


def write_short(r1, r2, r3, baseline, optimized, levers, ext, stages, allocation):
    r, c = ext["reasoning"], ext["carbon"]
    g = r["groups"]["reasoning"]
    md = f"""# GPU FinOps — Bài phân tích ngắn

**Học viên:** Nguyễn Xuân Trường — 2A202602761. **Nguồn:** dữ liệu mô phỏng của đề bài, seed=25, snapshot 06/2026.

## 1. Mốc tham chiếu và kết quả

Trong bài này, tôi sử dụng dữ liệu và đơn giá đề bài cung cấp, giữ kết quả M1–M5 làm mốc. M2 có {r2['total_tokens']:,} token/ngày: chi phí giảm từ ${r2['baseline_daily']:.2f} xuống ${r2['optimized_daily']:.2f}/ngày, tương ứng ${r2['baseline_per_m']:.3f} xuống ${r2['optimized_per_m']:.3f}/1M-token, tiết kiệm {r2['savings_pct']:.1f}%. M5 giảm từ ${baseline:,.0f} xuống ${optimized:,.0f}/tháng, tiết kiệm ${sum(levers.values()):,} ({sum(levers.values())/baseline*100:.1f}%). Tôi dùng các kết quả này để phân tích theo yêu cầu bài.

Tôi trình bày $/1M-token cho inference ở M2 và chi phí tháng cho M5. M5 có thêm training/dev nên chưa thể dùng token M2 làm mẫu số chung. Mốc ban đầu lưu trong `baseline_reference.json`; hai extension có kết quả riêng.

## 2. Vì sao tiết kiệm được?

Theo kết quả, chọn cách thuê GPU tiết kiệm nhiều nhất: ${levers['Purchasing (spot/reserved)']:,}/tháng, chiếm {levers['Purchasing (spot/reserved)']/sum(levers.values())*100:.1f}% tổng tiền tiết kiệm. Job có thể gián đoạn dùng spot với checkpoint, job ổn định dùng reserved. M3 tiết kiệm {r3['savings_pct']:.1f}%. Tôi ưu tiên biện pháp này vì tiền thuê GPU chiếm phần lớn chi phí ban đầu.

Inference tiết kiệm ${levers['Inference (cascade/cache/batch)']:,}/tháng. Tôi tính lần lượt cascade → cache → batch, được ${stages[0]-stages[1]:.4f}, ${stages[1]-stages[2]:.4f}, ${stages[2]-stages[3]:.4f}/ngày. Cascade dùng model nhỏ cho request đã gán tier small; cache giảm giá input đã lưu; batch giảm giá request không cần trả lời ngay. Chiết khấu nhân nhau nên mức đóng góp phụ thuộc thứ tự tính.

M1 chỉ ra hai GPU có util cao nhưng MFU thấp: `gpu-h100-4` và `gpu-a10g-1` (số liệu ở bảng M1 trong report.md). Tôi hiểu util cao là GPU hoạt động nhiều, chưa đồng nghĩa hiệu quả tính toán cao. Chờ bộ nhớ hoặc khởi chạy kernel có thể gây chênh lệch này. M5 ước tính đổi sang GPU nhỏ hơn tiết kiệm ${levers['Right-size util-lies']:,}/tháng; tắt GPU idle tiết kiệm ${levers['Kill idle GPUs']:,}/tháng. Khi áp dụng thật cần kiểm tra throughput và VRAM.

## 3. Hai extension trên dữ liệu đề bài cung cấp

**Ngân sách reasoning:** Tôi tách traffic theo is_reasoning. Có {g['requests']} request reasoning, chiếm {g['traffic_pct']:.2f}% request, {g['cost_pct']:.2f}% chi phí và {g['energy_pct']:.2f}% năng lượng theo công thức của đề bài. Tôi thử giới hạn 5%, chuyển {r['rerouted_requests']} request có output dài nhất sang xử lý thường. Giả định output giảm 6 lần theo hệ số generator, tiết kiệm ${r['saved_cost_usd']:.4f}/ngày và {r['saved_energy_wh']:.2f} Wh/ngày. Giữ nguyên output thì không tiết kiệm USD, chỉ giảm {r['same_token_saved_energy_wh']:.2f} Wh theo mô hình. Nhận xét của tôi là cần giới hạn reasoning theo nhu cầu tác vụ; dữ liệu hiện chưa có điểm chất lượng để kiểm chứng việc chuyển request.

**Carbon-aware scheduling:** Tôi tính năng lượng bằng công suất GPU nhân số giờ chạy, số ngày và số GPU cho {len(c['jobs'])} job có thể gián đoạn. Tổng là {c['total_energy_wh']/1000:.2f} kWh. Giả định chuyển từ us-east-1 sang europe-north1, carbon giảm từ {c['baseline_carbon_g']/1000:.3f} xuống {c['cleanest_carbon_g']/1000:.3f} kgCO2e, tiết kiệm {c['saved_carbon_g']/1000:.3f} kg ({c['saved_carbon_pct']:.2f}%). europe-north1 sạch nhất, us-east-wa có điện rẻ nhất. Tôi ghi riêng tiền điện vì giá thuê GPU có thể đã bao gồm khoản này. Phép tính dùng công suất định mức, chưa tính truyền dữ liệu và độ trễ.

## 4. Ba hành động ưu tiên và giới hạn

1. Kiểm tra thời gian sử dụng và thời hạn job để chọn spot hoặc reserved, vì đây là phần tiết kiệm lớn nhất.
2. Dùng cascade/cache/batch theo yêu cầu chất lượng và độ trễ, tắt GPU idle và theo dõi $/1M-token.
3. Bổ sung tag (coverage hiện {allocation['tag_coverage']:.1%}, làm tròn {allocation['tag_coverage']:.0%}), đặt ngân sách team, giới hạn reasoning và chọn vùng chạy phù hợp.

Tôi giữ mô hình M3 dùng 30 ngày cho mọi job; extension carbon dùng days của từng job. Mức {sum(levers.values())/baseline*100:.1f}% là dự kiến theo mô hình của đề bài, cần kiểm tra phần tiết kiệm trùng nhau trước khi áp dụng thật. Hai extension không cộng vào tỷ lệ này. Có thể chạy `python missions/run_all.py`, `python verify.py`, `pytest -q` để đối chiếu. Chi tiết phép tính, nguồn và log kiểm tra nằm trong `report.md`, `extensions_report.md`, `extensions_results.json` và `verification.txt`.
"""
    (Path(ROOT) / "outputs" / "writeup.md").write_text(md, encoding="utf-8")
