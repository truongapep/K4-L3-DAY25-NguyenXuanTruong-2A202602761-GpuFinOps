"""Run two assignment-data extensions: python missions/your_turn.py."""
from __future__ import annotations
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finops import extensions
from missions._common import ROOT, load_csv, catalog_by_type
from missions.m2_inference_levers import reasoning_analysis


def run(verbose=True):
    reasoning = reasoning_analysis()
    carbon = extensions.carbon_scheduling(load_csv("workloads.csv"), catalog_by_type())
    result = {"source": "Assignment dataset seed=25; estimates using assignment formulas",
              "reasoning": reasoning, "carbon": carbon}
    output = Path(ROOT) / "outputs"
    output.mkdir(exist_ok=True)
    (output / "extensions_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    md = render(result)
    (output / "extensions_report.md").write_text(md, encoding="utf-8")
    if verbose:
        print(md)
    return result


def render(result):
    r, c = result["reasoning"], result["carbon"]
    lines = ["# Your Turn — kết quả riêng trên dữ liệu đề bài cung cấp", "",
             "Tôi thực hiện hai extension trên dữ liệu đề bài cung cấp: ngân sách reasoning và chuyển vùng chạy để giảm carbon. Tôi ghi riêng kết quả, giữ nguyên mốc M1–M5 để so sánh.", "",
             "## Extension 4: Ngân sách reasoning", "",
             "| Traffic | Requests | Traffic % | USD/ngày | Chi phí % | Wh/ngày | Năng lượng % |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for name, g in r["groups"].items():
        lines.append(f"| {name} | {g['requests']} | {g['traffic_pct']:.2f} | {g['cost_usd']:.4f} | {g['cost_pct']:.2f} | {g['energy_wh']:.2f} | {g['energy_pct']:.2f} |")
    lines += ["", "Tôi dùng token_usage.csv, tách request theo is_reasoning=0 và is_reasoning=1. Chi phí tính theo model tier, cache và batch như M2. Năng lượng dùng công thức của đề bài: 0.30 Wh/1k token, reasoning nhân 80. Đây là năng lượng ước tính từ công thức của bài.", "",
              f"Cùng số token, reasoning tiêu thụ {r['groups']['reasoning']['energy_wh']:.2f} Wh so với {r['groups']['reasoning']['same_tokens_normal_wh']:.2f} Wh nếu chạy thường (80×). Flag reasoning tự nó không tăng đơn giá USD.", "",
              f"Tôi thử giới hạn reasoning ở {r['cap_fraction']:.0%} số request. Kết quả chuyển {r['rerouted_requests']} request, còn {r['reasoning_requests_after']} request reasoning. Tôi chọn request có output dài nhất trước; nếu bằng nhau, chọn theo thứ tự dòng trong CSV. Quy tắc này giúp chạy lại được cùng kết quả.", "",
              "| Đại lượng | Trước | Sau | Tiết kiệm |", "|---|---:|---:|---:|",
              f"| USD/ngày | {r['baseline_cost_usd']:.4f} | {r['scenario_cost_usd']:.4f} | {r['saved_cost_usd']:.4f} |",
              f"| Wh/ngày | {r['baseline_energy_wh']:.2f} | {r['scenario_energy_wh']:.2f} | {r['saved_energy_wh']:.2f} |", "",
              "Trong kịch bản này, tôi giả định output sau khi chuyển bằng output gốc / 6 vì generator nhân output reasoning với 6. Input, tier, cache và batch giữ nguyên. Do output thay đổi, kết quả chưa chứng minh chất lượng đáp án tương đương hoặc $/1M-token tốt hơn.", "",
              f"Nếu giữ nguyên cả output token, tiết kiệm USD = 0; tiết kiệm năng lượng ước tính = {r['same_token_saved_energy_wh']:.2f} Wh/ngày. Tách hai kịch bản giúp thấy tiền tiết kiệm đến từ output giảm, năng lượng giảm chủ yếu do bỏ hệ số reasoning.", "",
              "Từ kết quả, tôi đề xuất chỉ dùng reasoning khi tác vụ phức tạp hoặc độ tin cậy thấp; thử ngân sách 5% và cho phép ngoại lệ với tác vụ quan trọng. Dữ liệu chưa có confidence hay điểm chất lượng nên cần đánh giá thêm trước khi áp dụng. Mức 5% là giả định của phần mở rộng.", "",
              "## Extension 5: Carbon-aware scheduling", "",
              "Tôi chọn các job có interruptible=1 trong workloads.csv và giả định chúng đang chạy tại us-east-1. Năng lượng = watts × hours_per_day × days × num_gpus, dùng công suất định mức trong price_catalog.csv. Tôi dùng days của từng job; M3 quy đổi tất cả về 30 ngày để tính chi phí tháng.", "",
              "| Job | GPU-hours | kWh | CO2 trước (g) | CO2 sau (g) | Giảm (g) |",
              "|---|---:|---:|---:|---:|---:|"]
    for j in c["jobs"]:
        lines.append(f"| {j['job_id']} | {j['gpu_hours']:.0f} | {j['energy_wh']/1000:.2f} | {j['baseline_carbon_g']:.2f} | {j['cleanest_carbon_g']:.2f} | {j['saved_carbon_g']:.2f} |")
    lines += ["", "| Vùng | USD/kWh | gCO2/kWh | Tiền điện (USD) | CO2 (g) |",
              "|---|---:|---:|---:|---:|"]
    for g in c["regions"]:
        lines.append(f"| {g['region']} | {g['usd_per_kwh']:.3f} | {g['gco2_per_kwh']} | {g['electricity_usd']:.2f} | {g['carbon_g']:.2f} |")
    lines += ["", f"Chuyển sang {c['cleanest_region']}: {c['baseline_carbon_g']/1000:.3f} → {c['cleanest_carbon_g']/1000:.3f} kgCO2e; giảm {c['saved_carbon_g']/1000:.3f} kg ({c['saved_carbon_pct']:.2f}%).", "",
              f"Theo bảng dữ liệu của đề bài, {c['cleanest_region']} có carbon thấp nhất; {c['cheapest_region']} có giá điện thấp nhất. Tôi chọn vùng theo ưu tiên của công ty: giảm carbon hoặc giảm tiền điện. Với cùng lượng điện, giá thấp nhất và carbon thấp nhất thuộc hai vùng khác nhau.", "",
              "Tôi không cộng tiền điện tiết kiệm vào M5 vì giá thuê GPU có thể đã bao gồm điện. Phép tính chưa tính PUE, thời gian idle, checkpoint, phí truyền dữ liệu, độ trễ và quy định lưu trữ dữ liệu. Vùng nguồn là giả định vì workloads.csv không có cột region.", "",
              "## Công thức và nguồn để đối chiếu", "",
              "| Đại lượng | Cách tính |", "|---|---|",
              "| USD/request | finops.pricing.request_cost(): input chưa cache + input cache × 0.10 + output; chia 1M, nhân đơn giá tier; batch nhân 0.50 |",
              "| Wh/request | (input_tokens + output_tokens) / 1000 × 0.30; reasoning nhân 80 |",
              "| Số reasoning giữ lại tối đa | floor(tổng request × 0.05) |",
              "| Output giả định sau chuyển | output_tokens / 6; input và đơn giá giữ nguyên |",
              "| Wh/job | watts × hours_per_day × days × num_gpus |",
              "| gCO2e/job | Wh / 1000 × REGION_CARBON[region] |",
              "| Tiền điện/job | Wh / 1000 × REGION_PRICE_KWH[region] |", "",
              "Công thức USD được áp dụng riêng cho input/output theo MODEL_PRICES trong M2. Thông số carbon và giá điện lấy từ finops/sustainability.py. Số liệu chưa làm tròn lưu ở [extensions_results.json](extensions_results.json), gồm từng nhóm traffic, từng job và cả năm vùng.", "",
              "Có thể chạy lại:", "", "```powershell", "python missions/your_turn.py",
              "python -m pytest -q validation/check_extensions.py", "```", "",
              "Code tính: finops/extensions.py → reasoning_budget() và carbon_scheduling(). Log kiểm tra chung: [verification.txt](verification.txt)."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    run()
