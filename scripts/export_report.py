"""Export a small, shareable report without copying raw data or model binaries."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("reports/final"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    run = args.run_dir.resolve()
    if not (run / "COMPLETE.json").exists():
        raise ValueError("Only completed experiments may be exported")
    process_file = run / "process_resources.json"
    recovered = (run / "recovery_resources.json").exists() and (run / "recovery.json").exists() and json.loads((run / "recovery.json").read_text())["status"] == "complete"
    if process_file.exists() and not json.loads(process_file.read_text())["finished"] and not recovered:
        raise ValueError("Wait for the experiment process to exit before exporting resource totals")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    files = ["REPORT.md", "metrics.csv", "mape_by_horizon.png", "config.json", "environment.json", "recovery_environment.json", "data_quality.json", "coverage.json", "folds.json", "input_provenance.json", "selected_models.json", "ensemble_selection.json", "search_results.json", "default_cv_metrics.csv", "feature_ablation.csv", "peak_summary_delay0.csv", "peak_summary_delay1.csv", "model_reload_verification.json", "inference_benchmark.json"]
    for name in files:
        if (run / name).exists():
            shutil.copyfile(run / name, out / name)
    for name in ("DATA_AUDIT.md", "data_audit.json", "weather_status.json"):
        if (root / "outputs" / name).exists():
            shutil.copyfile(root / "outputs" / name, out / name)
    for path in (root / "outputs/exploration").glob("*"):
        if path.is_file():
            shutil.copyfile(path, out / path.name)
    resources = json.loads((run / "resources.json").read_text())
    totals = {"stage_seconds_sum": sum(r["seconds"] for r in resources), "peak_sampled_stage_rss_mib": max(r["peak_rss_mb"] for r in resources), "notes": "Resource fields ending _mb in the original recorder use 1024**2 bytes (MiB)."}
    if recovered:
        recovery = json.loads((run / "recovery_resources.json").read_text())
        prior = json.loads(process_file.read_text()) if process_file.exists() else {}
        totals.update(wall_seconds=recovery["seconds"] + prior.get("elapsed_seconds", 0),
                      peak_process_working_set_mib=max(recovery["peak_rss_mb"], prior.get("peak_working_set_mb", 0)),
                      process_measurement_method="Sum of observed active time before interruption and recovered holdout; excludes downtime. Peaks are the maximum recorded across both sessions.",
                      recovered_holdout=True, frozen_selection_verified=json.loads((run / "recovery.json").read_text())["contract_unchanged"],
                      prior_active_seconds_observed=prior.get("elapsed_seconds"), recovery_seconds=recovery["seconds"])
        shutil.copyfile(run / "recovery.json", out / "recovery.json")
    elif process_file.exists():
        process = json.loads(process_file.read_text())
        totals.update(wall_seconds=process["elapsed_seconds"], peak_process_working_set_mib=process["peak_working_set_mb"], process_measurement_method=process["method"])
    elif (run / "overall_resources.json").exists():
        total = json.loads((run / "overall_resources.json").read_text())
        totals.update(wall_seconds=total["seconds"], peak_process_working_set_mib=total["peak_rss_mb"])
    (out / "resource_summary.json").write_text(json.dumps(totals, indent=2), encoding="utf-8")
    source = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (root / "src").rglob("*.py")}
    (out / "source_snapshot_sha256.json").write_text(json.dumps({"captured_at": "report export, after numerical replay checks", "files": source}, indent=2), encoding="utf-8")
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    choices = json.loads((run / "selected_models.json").read_text())
    chosen = min(choices, key=lambda row: row["all_horizon_cv_mape_percent"])
    ensemble = json.loads((run / "ensemble_selection.json").read_text())
    default_name = chosen["model"]
    if ensemble and ensemble["mape_percent"] < chosen["all_horizon_cv_mape_percent"] - 0.1:
        default_name = "weighted_ensemble"
    metrics = pd.read_csv(run / "metrics.csv")
    selected_test = metrics[(metrics.model == default_name) & (metrics["slice"] == "overall") & (metrics.delay_hours == 0)].iloc[0]
    summary = {"selection_basis": "validation only, before holdout", "default_inference_model": default_name, "best_individual": chosen, "ensemble": ensemble, "test_mape_percent_delay0": float(selected_test.mape_percent), "aspirational_target_met": bool(selected_test.mape_percent < 3.5)}
    (out / "selection_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report += f"\n\n## Lựa chọn trước khi xem kiểm thử\n\nMô hình mặc định theo validation: **{default_name}**. Mô hình đơn dẫn đầu validation: **{chosen['model']}**, MAPE CV trên 24 bước **{chosen['all_horizon_cv_mape_percent']:.3f}%**. Thứ hạng trên bảng kiểm thử chỉ mô tả kết quả, không được dùng để thay đổi lựa chọn này.\n"
    report += f"\nMAPE kiểm thử của lựa chọn mặc định (độ trễ 0): **{selected_test.mape_percent:.3f}%**. " + ("Đạt mục tiêu nghiên cứu dưới 3,5%." if selected_test.mape_percent < 3.5 else "Chưa đạt mục tiêu nghiên cứu dưới 3,5%.") + "\n"
    report += "\n\n## Tài nguyên toàn phiên và kiểm tra bàn giao\n\n"
    if "wall_seconds" in totals:
        report += f"Thời gian toàn phiên được quan sát: **{totals['wall_seconds'] / 60:.1f} phút**. RAM đỉnh toàn tiến trình: **{totals['peak_process_working_set_mib']:.1f} MiB**. Xem resource_summary.json để phân biệt thời gian toàn phiên với tổng thời gian từng khâu.\n\n"
    if recovered:
        report += "Phiên đầu bị ngắt trong lúc kiểm thử. Phần kiểm thử được khôi phục từ cấu hình/trọng số đã khóa; SHA-256 của các tệp lựa chọn được kiểm tra không thay đổi. Không tìm tham số lại. Thời gian trên cộng các khoảng hoạt động đã quan sát, không tính thời gian gián đoạn; đây không phải thời gian của một lượt chạy liền mạch.\n\n"
    if (run / "inference_benchmark.json").exists():
        bench = json.loads((run / "inference_benchmark.json").read_text())
        report += f"Một lần dự báo đủ 24 giờ bằng mô hình mặc định có trung vị **{bench['median_seconds']:.2f} giây** qua ba lần đo. Dữ liệu đầu vào đã ở trong bộ nhớ; phép đo gồm nạp mô hình và tạo đặc trưng, bộ đệm tệp có thể đã ấm. Xem inference_benchmark.json.\n\n"
    report += "Bản chạy đầy đủ được khởi động trước tối ưu mặt nạ thời gian. Phép đo tối ưu riêng không được dùng để suy diễn hoặc hiệu chỉnh thời gian huấn luyện toàn phiên. numerical_replay_checks.json ghi đối chiếu số trên dữ liệu thật sau tối ưu.\n\n"
    report += "Thời tiết đã được thu thập và kiểm tra, nhưng nhánh thời tiết chưa được huấn luyện khi quy ước timestamp còn chưa xác nhận. weather_status.json ghi trạng thái này. Các chỉ số trong bảng thuộc nhánh phụ tải và lịch.\n\n"
    report += "Các tệp lớn (dự báo từng giờ và mô hình) nằm trong thư mục chạy gốc. Thư mục báo cáo này chỉ chứa kết quả nhỏ để nhóm chia sẻ và xem xét.\n\n![MAPE theo khoảng cách dự báo](mape_by_horizon.png)\n"
    (out / "REPORT.md").write_text(report, encoding="utf-8")
    print(f"Shareable report: {out / 'REPORT.md'}")


if __name__ == "__main__":
    main()
