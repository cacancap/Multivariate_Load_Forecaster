"""Role E: Unified orchestration, report/chart generation, PDF builder, and ZIP packaging."""

from .package import create_submission_zip
from .pdf_builder import build_pdf_report
from .pipeline import main
from .report import export_reports, plot_demo

__all__ = ["build_pdf_report", "create_submission_zip", "export_reports", "main", "plot_demo"]
