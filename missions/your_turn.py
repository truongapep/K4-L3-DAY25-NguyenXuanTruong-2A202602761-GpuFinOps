"""Run two BTC-data extensions: python missions/your_turn.py."""
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
    result = {"source": "BTC dataset seed=25; estimates using BTC formulas",
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
    lines = ["# Your Turn — kết quả riêng trên dữ liệu BTC", "",
             "Hai extension không cộng vào mức tiết kiệm 46.1% của M5.", "",
             "## Extension 4: Ngân sách reasoning", "",
             "| Traffic | Requests | Traffic % | USD/ngày | Chi phí % | Wh/ngày | Năng lượng % |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for name, g in r["groups"].items():
        lines.append(f"| {name} | {g['requests']} | {g['traffic_pct']:.2f} | {g['cost_usd']:.4f} | {g['cost_pct']:.2f} | {g['energy_wh']:.2f} | {g['energy_pct']:.2f} |")
    lines += ["", "Tiền được tính theo model tier, cache và batch của M2. Năng lượng dùng công thức BTC: 0.30 Wh/1k token; reasoning nhân 80. Đây là ước lượng, không phải đo điện thực tế.", "",
              f"Cùng số token, reasoning tiêu thụ {r['groups']['reasoning']['energy_wh']:.2f} Wh so với {r['groups']['reasoning']['same_tokens_normal_wh']:.2f} Wh nếu chạy thường (80×). Flag reasoning tự nó không tăng đơn giá USD.", "",
              f"Kịch bản cap {r['cap_fraction']:.0%} traffic: chuyển {r['rerouted_requests']} request, còn {r['reasoning_requests_after']} reasoning request. Chọn request reasoning có output dài nhất trước, tie-break theo vị trí dòng.", "",
              "| Đại lượng | Trước | Sau | Tiết kiệm |", "|---|---:|---:|---:|",
              f"| USD/ngày | {r['baseline_cost_usd']:.4f} | {r['scenario_cost_usd']:.4f} | {r['saved_cost_usd']:.4f} |",
              f"| Wh/ngày | {r['baseline_energy_wh']:.2f} | {r['scenario_energy_wh']:.2f} | {r['saved_energy_wh']:.2f} |", "",
              "Giả định kịch bản: output của request được chuyển bằng output gốc / 6, đảo hệ số 6 của generator; giữ input, tier, cache và batch. Sản lượng token thay đổi nên không dùng kịch bản này để tuyên bố cải thiện $/1M-token ở chất lượng tương đương.", "",
              f"Nếu giữ nguyên cả output token, tiết kiệm USD = 0; tiết kiệm năng lượng ước tính = {r['same_token_saved_energy_wh']:.2f} Wh/ngày. Tách hai kịch bản giúp thấy tiền tiết kiệm đến từ output giảm, năng lượng giảm chủ yếu do bỏ hệ số reasoning.", "",
              "Routing đề xuất: chỉ bật reasoning cho nhiệm vụ phức tạp/độ tin cậy thấp, giới hạn soft budget 5%, có ngoại lệ cho tác vụ quan trọng. Dataset không có confidence hay chất lượng đáp án; cần đánh giá chất lượng trước khi áp dụng. 5% là giả định chính sách mới, không phải số BTC đo sẵn.", "",
              "## Extension 5: Carbon-aware scheduling", "",
              "Giả định: các job interruptible có thể di chuyển từ us-east-1, GPU chạy ở công suất định mức trong catalog; năng lượng = watts × hours_per_day × days × num_gpus. Dùng days thật của job, không ngoại suy tất cả thành 30 ngày như M3.", "",
              "| Job | GPU-hours | kWh | CO2 trước (g) | CO2 sau (g) | Giảm (g) |",
              "|---|---:|---:|---:|---:|---:|"]
    for j in c["jobs"]:
        lines.append(f"| {j['job_id']} | {j['gpu_hours']:.0f} | {j['energy_wh']/1000:.2f} | {j['baseline_carbon_g']:.2f} | {j['cleanest_carbon_g']:.2f} | {j['saved_carbon_g']:.2f} |")
    lines += ["", "| Vùng | USD/kWh | gCO2/kWh | Tiền điện (USD) | CO2 (g) |",
              "|---|---:|---:|---:|---:|"]
    for g in c["regions"]:
        lines.append(f"| {g['region']} | {g['usd_per_kwh']:.3f} | {g['gco2_per_kwh']} | {g['electricity_usd']:.2f} | {g['carbon_g']:.2f} |")
    lines += ["", f"Chuyển sang {c['cleanest_region']}: {c['baseline_carbon_g']/1000:.3f} → {c['cleanest_carbon_g']/1000:.3f} kgCO2e; giảm {c['saved_carbon_g']/1000:.3f} kg ({c['saved_carbon_pct']:.2f}%).", "",
              f"Sạch nhất: {c['cleanest_region']}. Điện rẻ nhất: {c['cheapest_region']}; đây là phương án cân bằng cần cân nhắc nếu ưu tiên tiền điện. Không có một vùng đồng thời rẻ nhất và sạch nhất trong bảng BTC.", "",
              "Chi phí điện tách khỏi tiền thuê GPU, không cộng vào savings M5 vì có thể đã nằm trong giá thuê. Chưa tính PUE, idle, checkpoint overhead, egress, thời gian chuyển dữ liệu, availability, latency và data residency. Region hiện tại là giả định vì workloads.csv không có cột region.", "",
              "Tái lập: `python missions/your_turn.py`; kết quả máy đọc được: `outputs/extensions_results.json`."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    run()
