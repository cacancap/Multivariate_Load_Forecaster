"""Package a portable source submission and the verified Tetouan run."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json

ROOT=Path(__file__).resolve().parents[1]
def main():
    run_root=ROOT/"outputs/tetouan/full"
    run=run_root/(run_root/"latest.txt").read_text().strip()
    smoke_root=ROOT/"outputs/tetouan/smoke"
    smoke=smoke_root/(smoke_root/"latest.txt").read_text().strip()
    report=ROOT/"reports/tetouan"
    if json.loads((report/"selection.json").read_text()) != json.loads((run/"selection.json").read_text()):
        raise ValueError("Export the latest run before creating the submission")
    dest=ROOT/"submission/IT3190_Tetouan.zip"
    dest.parent.mkdir(exist_ok=True)
    paths=[ROOT/x for x in ["readme.txt","pyproject.toml","requirements.txt","reports/final/REPORT.md"]]
    for folder,pattern in [("src","*.py"),("docs","*.md"),("tests","test_tetouan*.py"),
            ("scripts","tetouan*.py"),("data/tetouan/raw","*"),("reports/tetouan","*")]:
        paths.extend((ROOT/folder).rglob(pattern))
    paths+=[ROOT/"data/tetouan"/n for n in ["observations.parquet","features.json","audit.json"]]
    paths.extend(run.rglob("*"))
    paths.extend([run_root/"latest.txt",smoke_root/"latest.txt",*smoke.rglob("*")])
    stage=dest.with_suffix(".tmp")
    with ZipFile(stage,"w",ZIP_DEFLATED,compresslevel=5) as archive:
        for path in sorted(set(paths)):
            if path.is_file():
                archive.write(path,path.relative_to(ROOT).as_posix())
    with ZipFile(stage) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
    stage.replace(dest)
    print(dest,dest.stat().st_size)
if __name__=="__main__":
    main()
